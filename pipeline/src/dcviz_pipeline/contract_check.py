"""Validate Data Center Visualizer contract fixtures and published packages."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TextIO

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

PACKAGE_FILES = ("manifest.json", "proposal.json", "context.json")


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _definition_schema(schema: Mapping[str, Any], definition: str) -> dict[str, Any]:
    """Build a standalone schema that retains references to the root definitions."""
    return {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": f"#/$defs/{definition}",
    }


def _load_validators(repo_root: Path) -> dict[str, Draft202012Validator]:
    contracts_dir = repo_root / "contracts"
    proposal_schema = json.loads(
        (contracts_dir / "proposal-package.schema.json").read_text(encoding="utf-8")
    )
    context_schema = json.loads(
        (contracts_dir / "context-scene.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(proposal_schema)
    Draft202012Validator.check_schema(context_schema)
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


def _format_error_path(error: ValidationError) -> str:
    path = "$"
    for part in error.absolute_path:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _validation_errors(
    path: Path, validator: Draft202012Validator
) -> tuple[list[ValidationError], str | None]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [], str(error)

    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    return errors, None


def _expect_valid(
    path: Path,
    validator: Draft202012Validator,
    label: str,
    stream: TextIO,
) -> bool:
    errors, load_error = _validation_errors(path, validator)
    if load_error is not None:
        print(f"ERROR {label}: {load_error}", file=stream)
        return False
    if errors:
        for error in errors:
            print(
                f"ERROR {label} at {_format_error_path(error)}: {error.message}",
                file=stream,
            )
        return False

    print(f"PASS {label}", file=stream)
    return True


def _expect_invalid(
    path: Path,
    validator: Draft202012Validator,
    label: str,
    stream: TextIO,
) -> bool:
    errors, load_error = _validation_errors(path, validator)
    if load_error is not None or errors:
        print(f"PASS {label} rejected", file=stream)
        return True

    print(f"ERROR {label}: expected schema rejection, but the document passed", file=stream)
    return False


def _validator_for_filename(
    filename: str, validators: Mapping[str, Draft202012Validator]
) -> Draft202012Validator:
    if filename.startswith("manifest"):
        return validators["manifest"]
    if filename.startswith("proposal"):
        return validators["proposal"]
    if filename.startswith("context"):
        return validators["context"]
    raise ValueError(f"cannot select a schema for {filename!r}")


def _published_package_dirs(repo_root: Path) -> list[Path]:
    published_root = repo_root / "data" / "published"
    if not published_root.exists():
        return []

    package_dirs = {
        path.parent
        for filename in PACKAGE_FILES
        for path in published_root.rglob(filename)
        if path.is_file()
    }
    return sorted(package_dirs)


def run_contract_check(repo_root: Path | None = None, stream: TextIO | None = None) -> int:
    """Validate schemas, fixtures, and all discovered published packages."""
    root = (repo_root or _default_repo_root()).resolve()
    output = stream or sys.stdout

    try:
        validators = _load_validators(root)
    except (OSError, json.JSONDecodeError, KeyError, SchemaError) as error:
        print(f"ERROR loading contract schemas: {error}", file=output)
        return 1

    print("PASS Draft 2020-12 contract schemas", file=output)
    success = True
    valid_count = 0
    invalid_count = 0

    fixture_dir = root / "contracts" / "fixtures" / "synthetic-site"
    valid_targets = (
        (fixture_dir / "manifest.json", validators["manifest"]),
        (fixture_dir / "manifest.approximate.json", validators["manifest"]),
        (fixture_dir / "proposal.json", validators["proposal"]),
        (fixture_dir / "context.json", validators["context"]),
    )
    for path, validator in valid_targets:
        passed = _expect_valid(path, validator, f"fixture {path.name}", output)
        success = passed and success
        valid_count += int(passed)

    invalid_dir = root / "contracts" / "fixtures" / "invalid"
    invalid_paths = sorted(invalid_dir.glob("*.json"))
    if not invalid_paths:
        print("ERROR no invalid contract fixtures found", file=output)
        success = False

    for path in invalid_paths:
        try:
            validator = _validator_for_filename(path.name, validators)
        except ValueError as error:
            print(f"ERROR invalid fixture {path.name}: {error}", file=output)
            success = False
            continue
        passed = _expect_invalid(path, validator, f"invalid fixture {path.name}", output)
        success = passed and success
        invalid_count += int(passed)

    package_dirs = _published_package_dirs(root)
    for package_dir in package_dirs:
        relative_dir = package_dir.relative_to(root)
        for filename in PACKAGE_FILES:
            path = package_dir / filename
            label = f"published package {relative_dir}/{filename}"
            if not path.is_file():
                print(f"ERROR {label}: required file is missing", file=output)
                success = False
                continue
            validator = _validator_for_filename(filename, validators)
            success = _expect_valid(path, validator, label, output) and success

    print(
        "Contract validation summary: "
        f"{valid_count} valid fixtures, {invalid_count} invalid fixtures, "
        f"{len(package_dirs)} published packages",
        file=output,
    )
    return 0 if success else 1


def main() -> int:
    """Run contract validation from a module or console entry point."""
    return run_contract_check()


if __name__ == "__main__":
    raise SystemExit(main())
