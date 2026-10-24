"""Read and write schema-validated proposal package documents."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

PACKAGE_FILES = ("manifest.json", "proposal.json", "context.json")
JsonObject = dict[str, Any]


class PackageError(ValueError):
    """Base error for malformed or unreadable proposal packages."""


class PackageValidationError(PackageError):
    """A proposal package contains one or more schema violations."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("package schema validation failed:\n" + "\n".join(issues))


@dataclass(frozen=True, slots=True)
class PackageDocuments:
    """The three validated JSON documents in one proposal package."""

    manifest: JsonObject
    proposal: JsonObject
    context: JsonObject


def _default_contracts_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "contracts"


def _definition_schema(schema: Mapping[str, Any], definition: str) -> JsonObject:
    return {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": f"#/$defs/{definition}",
    }


def _load_schema(path: Path) -> JsonObject:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackageError(f"could not load contract schema {path}: {error}") from error
    if not isinstance(document, dict):
        raise PackageError(f"contract schema {path} must contain a JSON object")
    return document


def _load_validators(contracts_dir: Path) -> dict[str, Draft202012Validator]:
    proposal_schema = _load_schema(contracts_dir / "proposal-package.schema.json")
    context_schema = _load_schema(contracts_dir / "context-scene.schema.json")
    try:
        Draft202012Validator.check_schema(proposal_schema)
        Draft202012Validator.check_schema(context_schema)
    except SchemaError as error:
        raise PackageError(f"invalid contract schema: {error.message}") from error

    format_checker = FormatChecker()
    return {
        "manifest": Draft202012Validator(
            _definition_schema(proposal_schema, "manifest"),
            format_checker=format_checker,
        ),
        "proposal": Draft202012Validator(
            _definition_schema(proposal_schema, "proposal"),
            format_checker=format_checker,
        ),
        "context": Draft202012Validator(context_schema, format_checker=format_checker),
    }


def _format_error(filename: str, error: ValidationError) -> str:
    path = "$"
    for part in error.absolute_path:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return f"{filename} at {path}: {error.message}"


def validate_package(
    package: PackageDocuments,
    contracts_dir: Path | None = None,
) -> None:
    """Raise with field-level issues when any package document violates its schema."""
    validators = _load_validators((contracts_dir or _default_contracts_dir()).resolve())
    documents = {
        "manifest": package.manifest,
        "proposal": package.proposal,
        "context": package.context,
    }
    issues = [
        _format_error(f"{kind}.json", error)
        for kind, document in documents.items()
        for error in sorted(
            validators[kind].iter_errors(document),
            key=lambda item: (item.json_path, item.message),
        )
    ]
    if issues:
        raise PackageValidationError(issues)


def _read_json_object(path: Path) -> JsonObject:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise PackageError(f"could not read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise PackageError(
            f"invalid JSON in {path} at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    if not isinstance(document, dict):
        raise PackageError(f"{path} must contain a JSON object")
    return document


def read_package(
    package_dir: Path,
    contracts_dir: Path | None = None,
) -> PackageDocuments:
    """Read all three package files and reject the package unless each is schema-valid."""
    package = PackageDocuments(
        manifest=_read_json_object(package_dir / "manifest.json"),
        proposal=_read_json_object(package_dir / "proposal.json"),
        context=_read_json_object(package_dir / "context.json"),
    )
    validate_package(package, contracts_dir)
    return package


def write_package(
    package_dir: Path,
    package: PackageDocuments,
    contracts_dir: Path | None = None,
) -> None:
    """Validate and write a new package directory without replacing an existing version."""
    validate_package(package, contracts_dir)
    try:
        package_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise PackageError(f"package directory already exists: {package_dir}") from error

    documents = {
        "manifest.json": package.manifest,
        "proposal.json": package.proposal,
        "context.json": package.context,
    }
    for filename, document in documents.items():
        text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        (package_dir / filename).write_text(text, encoding="utf-8")
