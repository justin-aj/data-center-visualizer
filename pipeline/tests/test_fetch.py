"""Tests for source manifest parsing, downloads, caching, and CLI routing."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

import requests
import yaml

from dcviz_pipeline import cli
from dcviz_pipeline.fetch import SourceManifestError, fetch_sources, load_sources

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXED_TIME = datetime(2026, 10, 24, 16, 30, tzinfo=UTC)


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        url: str,
        content_type: str = "application/octet-stream",
        content_disposition: str | None = None,
        status_code: int = 200,
    ) -> None:
        self.body = body
        self.url = url
        self.status_code = status_code
        self.headers = {"content-type": content_type}
        if content_disposition is not None:
            self.headers["content-disposition"] = content_disposition
        self.closed = False

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} response")

    def iter_content(self, chunk_size: int) -> list[bytes]:
        return [
            self.body[index : index + chunk_size]
            for index in range(0, len(self.body), chunk_size)
        ]

    def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse | Exception]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get(
        self,
        url: str,
        *,
        stream: bool,
        timeout: tuple[int, int],
    ) -> FakeResponse:
        assert stream is True
        assert timeout == (15, 180)
        self.calls.append(url)
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response


def _source(
    source_id: str,
    url: str,
    *,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    source: dict[str, Any] = {
        "id": source_id,
        "title": f"Source {source_id}",
        "issuer": "Test issuer",
        "url": url,
        "license": "Test-only fixture license",
        "distributable": True,
        "status": "verified",
        "usedFor": ["Mocked fetch test"],
    }
    if expected_sha256 is not None:
        source["expectedSha256"] = expected_sha256
    return source


def _write_manifest(path: Path, sources: list[dict[str, Any]]) -> None:
    path.write_text(yaml.safe_dump({"sources": sources}, sort_keys=False), encoding="utf-8")


def test_workspace_manifest_records_verified_and_unverified_sources() -> None:
    sources = load_sources(REPO_ROOT / "data/sources.yaml")

    assert len(sources) == 16
    assert {source.status for source in sources} == {"verified", "unverified"}
    assert all(not source.distributable for source in sources if source.id.startswith("lowell-"))
    assert any(source.id == "massgis-buildings-lowell-160" for source in sources)
    assert any(source.id == "osm-building-heights-pilot" for source in sources)


def test_load_sources_rejects_invalid_status(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.yaml"
    source = _source("source-one", "https://example.test/source")
    source["status"] = "assumed"
    _write_manifest(manifest, [source])

    try:
        load_sources(manifest)
    except SourceManifestError as error:
        assert "must be verified or unverified" in str(error)
    else:
        raise AssertionError("invalid source status was accepted")


def test_clean_fetch_downloads_every_source_and_records_hashes(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.yaml"
    raw_dir = tmp_path / "raw"
    pdf_body = b"synthetic pdf bytes"
    json_body = b'{"features": []}'
    sources = [
        _source("plan-source", "https://example.test/plan"),
        _source("context-source", "https://example.test/context"),
    ]
    _write_manifest(manifest, sources)
    session = FakeSession(
        {
            sources[0]["url"]: FakeResponse(
                pdf_body,
                url=sources[0]["url"],
                content_type="application/pdf",
                content_disposition='inline; filename="plan.pdf"',
            ),
            sources[1]["url"]: FakeResponse(
                json_body,
                url=sources[1]["url"],
                content_type="application/json; charset=utf-8",
            ),
        }
    )
    output = StringIO()

    result = fetch_sources(
        manifest,
        raw_dir,
        session=session,
        clock=lambda: FIXED_TIME,
        stream=output,
    )

    assert result == 0
    assert session.calls == [source["url"] for source in sources]
    assert (raw_dir / "plan-source.pdf").read_bytes() == pdf_body
    assert (raw_dir / "context-source.json").read_bytes() == json_body
    log = json.loads((raw_dir / "fetch-log.json").read_text(encoding="utf-8"))
    assert log["generatedAt"] == "2026-10-24T16:30:00Z"
    assert [record["outcome"] for record in log["sources"]] == ["downloaded", "downloaded"]
    assert log["sources"][0]["sha256"] == hashlib.sha256(pdf_body).hexdigest()
    assert log["sources"][1]["sha256"] == hashlib.sha256(json_body).hexdigest()
    assert "Fetch summary: 2/2 sources available" in output.getvalue()


def test_second_fetch_uses_verified_cache_without_http(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.yaml"
    raw_dir = tmp_path / "raw"
    body = b"cached source"
    source = _source("cached-source", "https://example.test/source.zip")
    _write_manifest(manifest, [source])
    first_session = FakeSession(
        {source["url"]: FakeResponse(body, url=source["url"], content_type="application/zip")}
    )
    assert (
        fetch_sources(
            manifest,
            raw_dir,
            session=first_session,
            clock=lambda: FIXED_TIME,
            stream=StringIO(),
        )
        == 0
    )
    no_http_session = FakeSession({})

    result = fetch_sources(
        manifest,
        raw_dir,
        session=no_http_session,
        clock=lambda: FIXED_TIME,
        stream=StringIO(),
    )

    assert result == 0
    assert no_http_session.calls == []
    log = json.loads((raw_dir / "fetch-log.json").read_text(encoding="utf-8"))
    assert log["sources"][0]["outcome"] == "cached"
    assert log["sources"][0]["sha256"] == hashlib.sha256(body).hexdigest()


def test_hash_mismatch_fails_safely_and_later_sources_are_attempted(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.yaml"
    raw_dir = tmp_path / "raw"
    corrupt_body = b"changed"
    good_body = b"available"
    sources = [
        _source("pinned-source", "https://example.test/pinned", expected_sha256="0" * 64),
        _source("later-source", "https://example.test/later"),
    ]
    _write_manifest(manifest, sources)
    session = FakeSession(
        {
            sources[0]["url"]: FakeResponse(corrupt_body, url=sources[0]["url"]),
            sources[1]["url"]: FakeResponse(
                good_body,
                url=sources[1]["url"],
                content_type="application/json",
            ),
        }
    )
    output = StringIO()

    result = fetch_sources(
        manifest,
        raw_dir,
        session=session,
        clock=lambda: FIXED_TIME,
        stream=output,
    )

    assert result == 1
    assert session.calls == [source["url"] for source in sources]
    assert not any(raw_dir.glob("pinned-source.*"))
    assert (raw_dir / "later-source.json").read_bytes() == good_body
    log = json.loads((raw_dir / "fetch-log.json").read_text(encoding="utf-8"))
    assert [record["outcome"] for record in log["sources"]] == ["failed", "downloaded"]
    assert "sha256 mismatch" in output.getvalue()


def test_network_failure_is_logged_without_blocking_later_source(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.yaml"
    raw_dir = tmp_path / "raw"
    sources = [
        _source("offline-source", "https://example.test/offline"),
        _source("reachable-source", "https://example.test/reachable"),
    ]
    _write_manifest(manifest, sources)
    session = FakeSession(
        {
            sources[0]["url"]: requests.ConnectionError("offline"),
            sources[1]["url"]: FakeResponse(b"ok", url=sources[1]["url"]),
        }
    )

    result = fetch_sources(
        manifest,
        raw_dir,
        session=session,
        clock=lambda: FIXED_TIME,
        stream=StringIO(),
    )

    assert result == 1
    assert session.calls == [source["url"] for source in sources]
    assert (raw_dir / "reachable-source.bin").read_bytes() == b"ok"
    log = json.loads((raw_dir / "fetch-log.json").read_text(encoding="utf-8"))
    assert log["sources"][0]["error"] == "offline"
    assert log["sources"][1]["outcome"] == "downloaded"


def test_fetch_cli_routes_to_real_handler(monkeypatch) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(cli, "run_fetch", lambda: calls.append(True) or 0)

    assert cli.main(["fetch"]) == 0
    assert calls == [True]
