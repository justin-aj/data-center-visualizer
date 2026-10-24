"""Command-line interface for the Data Center Visualizer pipeline."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from dcviz_pipeline.contract_check import run_contract_check

COMMANDS = (
    "contract-check",
    "fetch",
    "context",
    "extract-plan",
    "georef",
    "package",
    "validate",
)


def _run_stub(args: argparse.Namespace) -> int:
    """Report that a scaffolded command has not been implemented yet."""
    print(f"{args.command}: not implemented")
    return 0


def _run_contract_check(_args: argparse.Namespace) -> int:
    """Validate contract fixtures and published proposal packages."""
    return run_contract_check()


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level command parser and its stub subcommands."""
    parser = argparse.ArgumentParser(
        prog="dcviz",
        description="Build and validate Data Center Visualizer proposal packages.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in COMMANDS:
        subparser = subparsers.add_parser(command)
        handler = _run_contract_check if command == "contract-check" else _run_stub
        subparser.set_defaults(handler=handler)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected pipeline command."""
    args = build_parser().parse_args(argv)
    return args.handler(args)
