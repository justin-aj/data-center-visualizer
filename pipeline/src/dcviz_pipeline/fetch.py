"""Download and cache source material listed in data/sources.yaml."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, TextIO
from urllib.parse import unquote, urlparse

import requests
import yaml

_REQUIRED_FIELDS = {
    "id",
    "title",
    "issuer",
    "url",
    "license",
    "distributable",
    "status",
    "usedFor",
}
_SOURCE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CONTENT_SUFFIXES = {
    "application/json": ".json",
    "application/pdf": ".pdf",
    "application/geo+json": ".geojson",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
    "text/csv": ".csv",
}


class ResponseLike(Protocol):
    """Subset of a requests response used by the downloader."""

    url: str
    headers: Mapping[str, str]

    def raise_for_status(self) -> None: ...

    def iter_content(self, chunk_size: int) -> Sequence[bytes]: ...

    def close(self) -> None: ...


class SessionLike(Protocol):
    """HTTP session interface accepted by fetch_sources."""

    def get(
        self,
        url: str,
        *,
        stream: bool,
        timeout: tuple[int, int],
    ) -> ResponseLike: ...


class SourceManifestError(ValueError):
    """The source manifest is malformed or incomplete."""


class FetchError(RuntimeError):
    """A source could not be safely promoted into the cache."""


@dataclass(frozen=True, slots=True)
class Source:
    """One validated entry from the source manifest."""

    id: str
    title: str
    issuer: str
    url: str
    license: str
    distributable: bool
    status: str
    used_for: tuple[str, ...]
    expected_sha256: str | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _required_string(entry: Mapping[str, Any], field: str, index: int) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SourceManifestError(f"sources[{index}].{field} must be a non-empty string")
    return value.strip()


def load_sources(path: Path) -> list[Source]:
    """Load and validate source entries without performing network requests."""
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SourceManifestError(f"could not read source manifest {path}: {error}") from error
    except yaml.YAMLError as error:
        raise SourceManifestError(f"invalid YAML in source manifest {path}: {error}") from error

    if not isinstance(document, dict) or not isinstance(document.get("sources"), list):
        raise SourceManifestError("source manifest must contain a sources list")
    if not document["sources"]:
        raise SourceManifestError("source manifest must contain at least one source")

    sources: list[Source] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(document["sources"]):
        if not isinstance(entry, dict):
            raise SourceManifestError(f"sources[{index}] must be an object")
        missing = sorted(_REQUIRED_FIELDS - entry.keys())
        if missing:
            raise SourceManifestError(
                f"sources[{index}] is missing required fields: {', '.join(missing)}"
            )

        source_id = _required_string(entry, "id", index)
        if not _SOURCE_ID.fullmatch(source_id):
            raise SourceManifestError(
                f"sources[{index}].id must use lowercase letters, digits, and single hyphens"
            )
        if source_id in seen_ids:
            raise SourceManifestError(f"duplicate source id: {source_id}")
        seen_ids.add(source_id)

        url = _required_string(entry, "url", index)
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise SourceManifestError(f"sources[{index}].url must be an HTTPS URL")

        status = _required_string(entry, "status", index)
        if status not in {"verified", "unverified"}:
            raise SourceManifestError(
                f"sources[{index}].status must be verified or unverified"
            )
        if not isinstance(entry["distributable"], bool):
            raise SourceManifestError(f"sources[{index}].distributable must be a boolean")

        used_for = entry["usedFor"]
        if (
            not isinstance(used_for, list)
            or not used_for
            or any(not isinstance(value, str) or not value.strip() for value in used_for)
        ):
            raise SourceManifestError(
                f"sources[{index}].usedFor must be a non-empty list of strings"
            )

        expected_sha256 = entry.get("expectedSha256")
        if expected_sha256 is not None:
            if not isinstance(expected_sha256, str) or not _SHA256.fullmatch(
                expected_sha256.lower()
            ):
                raise SourceManifestError(
                    f"sources[{index}].expectedSha256 must be a 64-character hex digest"
                )
            expected_sha256 = expected_sha256.lower()

        sources.append(
            Source(
                id=source_id,
                title=_required_string(entry, "title", index),
                issuer=_required_string(entry, "issuer", index),
                url=url,
                license=_required_string(entry, "license", index),
                distributable=entry["distributable"],
                status=status,
                used_for=tuple(value.strip() for value in used_for),
                expected_sha256=expected_sha256,
            )
        )
    return sources


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _timestamp(clock: Callable[[], datetime]) -> str:
    value = clock()
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _load_previous_records(log_path: Path) -> dict[str, dict[str, Any]]:
    if not log_path.is_file():
        return {}
    try:
        document = json.loads(log_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    records = document.get("sources") if isinstance(document, dict) else None
    if not isinstance(records, list):
        return {}
    return {
        record["id"]: record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }


def _cache_record(
    source: Source,
    raw_dir: Path,
    previous: Mapping[str, Any] | None,
    checked_at: str,
) -> dict[str, Any] | None:
    if previous is None or previous.get("outcome") not in {"downloaded", "cached"}:
        return None
    local_name = previous.get("localPath")
    recorded_sha256 = previous.get("sha256")
    if (
        not isinstance(local_name, str)
        or Path(local_name).name != local_name
        or not isinstance(recorded_sha256, str)
        or not _SHA256.fullmatch(recorded_sha256)
    ):
        return None

    local_path = raw_dir / local_name
    if not local_path.is_file() or local_path.stat().st_size == 0:
        return None
    actual_sha256 = _sha256(local_path)
    if actual_sha256 != recorded_sha256:
        return None
    if source.expected_sha256 is not None and actual_sha256 != source.expected_sha256:
        return None

    return {
        "id": source.id,
        "title": source.title,
        "url": source.url,
        "finalUrl": previous.get("finalUrl", source.url),
        "localPath": local_name,
        "sha256": actual_sha256,
        "bytes": local_path.stat().st_size,
        "contentType": previous.get("contentType"),
        "retrievedAt": previous.get("retrievedAt"),
        "checkedAt": checked_at,
        "outcome": "cached",
    }


def _safe_suffix(value: str) -> str | None:
    suffix = Path(value).suffix.lower()
    if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
        return suffix
    return None


def _response_suffix(response: ResponseLike) -> str:
    disposition = response.headers.get("content-disposition", "")
    filename_match = re.search(
        r"filename\*?=(?:UTF-8''|\")?([^\";]+)",
        disposition,
        flags=re.IGNORECASE,
    )
    if filename_match:
        suffix = _safe_suffix(unquote(filename_match.group(1).strip()))
        if suffix:
            return suffix

    suffix = _safe_suffix(urlparse(response.url).path)
    if suffix:
        return suffix
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    return _CONTENT_SUFFIXES.get(content_type, ".bin")


def _download_source(
    source: Source,
    raw_dir: Path,
    session: SessionLike,
    retrieved_at: str,
) -> dict[str, Any]:
    part_path = raw_dir / f".{source.id}.part"
    response: ResponseLike | None = None
    try:
        response = session.get(source.url, stream=True, timeout=(15, 180))
        response.raise_for_status()
        digest = hashlib.sha256()
        byte_count = 0
        with part_path.open("wb") as destination:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                destination.write(chunk)
                digest.update(chunk)
                byte_count += len(chunk)
        if byte_count == 0:
            raise FetchError("response body was empty")

        actual_sha256 = digest.hexdigest()
        if source.expected_sha256 is not None and actual_sha256 != source.expected_sha256:
            raise FetchError(
                f"sha256 mismatch: expected {source.expected_sha256}, got {actual_sha256}"
            )

        target = raw_dir / f"{source.id}{_response_suffix(response)}"
        part_path.replace(target)
        return {
            "id": source.id,
            "title": source.title,
            "url": source.url,
            "finalUrl": response.url,
            "localPath": target.name,
            "sha256": actual_sha256,
            "bytes": byte_count,
            "contentType": response.headers.get("content-type"),
            "retrievedAt": retrieved_at,
            "checkedAt": retrieved_at,
            "outcome": "downloaded",
        }
    finally:
        if response is not None:
            response.close()
        if part_path.exists():
            part_path.unlink()


def _write_log(log_path: Path, generated_at: str, records: list[dict[str, Any]]) -> None:
    document = {"generatedAt": generated_at, "sources": records}
    part_path = log_path.with_suffix(".json.part")
    part_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    part_path.replace(log_path)


def fetch_sources(
    manifest_path: Path,
    raw_dir: Path,
    *,
    session: SessionLike | None = None,
    clock: Callable[[], datetime] | None = None,
    stream: TextIO | None = None,
) -> int:
    """Fetch every source, continuing after failures and recording every outcome."""
    output = stream or sys.stdout
    try:
        sources = load_sources(manifest_path)
    except SourceManifestError as error:
        print(f"ERROR source manifest: {error}", file=output)
        return 1

    raw_dir.mkdir(parents=True, exist_ok=True)
    log_path = raw_dir / "fetch-log.json"
    previous_records = _load_previous_records(log_path)
    checked_at = _timestamp(clock or (lambda: datetime.now(UTC)))
    client = session or requests.Session()
    if isinstance(client, requests.Session):
        client.headers.update({"User-Agent": "DataCenterVisualizer/0.1 source-fetch"})

    records: list[dict[str, Any]] = []
    success = True
    for source in sources:
        cached = _cache_record(source, raw_dir, previous_records.get(source.id), checked_at)
        if cached is not None:
            records.append(cached)
            print(
                f"CACHED {source.id} ({cached['bytes']} bytes, sha256 {cached['sha256']})",
                file=output,
            )
            continue

        try:
            record = _download_source(source, raw_dir, client, checked_at)
        except (FetchError, OSError, requests.RequestException) as error:
            success = False
            record = {
                "id": source.id,
                "title": source.title,
                "url": source.url,
                "checkedAt": checked_at,
                "outcome": "failed",
                "error": str(error),
            }
            print(f"ERROR {source.id}: {error}", file=output)
        else:
            print(
                f"FETCHED {source.id} ({record['bytes']} bytes, sha256 {record['sha256']})",
                file=output,
            )
        records.append(record)

    _write_log(log_path, checked_at, records)
    completed = sum(record["outcome"] in {"downloaded", "cached"} for record in records)
    print(f"Fetch summary: {completed}/{len(records)} sources available", file=output)
    return 0 if success else 1


def run_fetch() -> int:
    """Fetch the workspace source manifest into its ignored raw-data cache."""
    root = _repo_root()
    return fetch_sources(root / "data/sources.yaml", root / "data/raw")


if __name__ == "__main__":
    raise SystemExit(run_fetch())
