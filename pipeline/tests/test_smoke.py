"""Smoke tests for the initial pipeline scaffold."""

from dcviz_pipeline import __version__
from dcviz_pipeline.cli import COMMANDS, build_parser, main


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_cli_exposes_every_pipeline_command() -> None:
    parser = build_parser()
    subparsers_action = next(
        action for action in parser._actions if hasattr(action, "choices") and action.choices
    )

    assert set(subparsers_action.choices) == set(COMMANDS)


def test_stub_command_runs(capsys) -> None:
    assert main(["validate"]) == 0
    assert capsys.readouterr().out == "validate: not implemented\n"
