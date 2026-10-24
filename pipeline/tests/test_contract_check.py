"""Tests for contract fixture and published-package validation."""

from __future__ import annotations

import json
import shutil
from io import StringIO
from pathlib import Path

from dcviz_pipeline.contract_check import run_contract_check

REPO_ROOT = Path(__file__).resolve().parents[2]


def _copy_contracts(destination: Path) -> None:
    shutil.copytree(REPO_ROOT / "contracts", destination / "contracts")


def test_repository_contract_fixtures_pass() -> None:
    output = StringIO()

    result = run_contract_check(REPO_ROOT, output)

    assert result == 0
    report = output.getvalue()
    assert "6 valid fixtures, 15 invalid fixtures" in report
    assert "PASS fixture manifest.approximate.json" in report
    assert "PASS fixture manifest.proposal-v1.1.json" in report
    assert "PASS fixture manifest.context-only.json" in report


def test_checker_requires_invalid_fixtures_to_fail(tmp_path: Path) -> None:
    _copy_contracts(tmp_path)
    unexpected_valid = tmp_path / "contracts/fixtures/invalid/proposal-unexpected-valid.json"
    unexpected_valid.write_text('{"features": []}\n', encoding="utf-8")
    output = StringIO()

    result = run_contract_check(tmp_path, output)

    assert result == 1
    assert "expected schema rejection, but the document passed" in output.getvalue()


def test_checker_validates_published_context_only_triplet(tmp_path: Path) -> None:
    _copy_contracts(tmp_path)
    source = tmp_path / "contracts/fixtures/synthetic-site"
    package = tmp_path / "data/published/synthetic-civic-site/1.1.0-context-only"
    package.mkdir(parents=True)
    shutil.copy(source / "manifest.context-only.json", package / "manifest.json")
    shutil.copy(source / "context.json", package / "context.json")
    (package / "proposal.json").write_text('{"features": []}\n', encoding="utf-8")
    output = StringIO()

    result = run_contract_check(tmp_path, output)

    assert result == 0
    report = output.getvalue()
    assert (
        "PASS published package "
        "data/published/synthetic-civic-site/1.1.0-context-only/manifest.json"
    ) in report
    assert (
        "PASS published package "
        "data/published/synthetic-civic-site/1.1.0-context-only/proposal.json"
    ) in report
    assert (
        "PASS published package "
        "data/published/synthetic-civic-site/1.1.0-context-only/context.json"
    ) in report


def test_checker_validates_published_packages_and_reports_fields(tmp_path: Path) -> None:
    _copy_contracts(tmp_path)
    source = tmp_path / "contracts/fixtures/synthetic-site"
    package = tmp_path / "data/published/synthetic-civic-site/1.0.0"
    package.mkdir(parents=True)
    shutil.copy(source / "proposal.json", package / "proposal.json")
    shutil.copy(source / "context.json", package / "context.json")
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    del manifest["projectId"]
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    output = StringIO()

    result = run_contract_check(tmp_path, output)

    assert result == 1
    report = output.getvalue()
    assert "published package data/published/synthetic-civic-site/1.0.0/manifest.json" in report
    assert "'projectId' is a required property" in report
