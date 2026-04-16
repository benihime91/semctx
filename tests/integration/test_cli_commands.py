# CLI integration tests.
# FEATURE: Retained root, discovery, and analysis commands.
from pathlib import Path

from typer.testing import CliRunner

from semctx.cli import app

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "demo_project"


def test_root_help_lists_retained_commands_only() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"], prog_name="semctx")

    assert result.exit_code == 0
    assert "--target-dir" in result.stdout
    assert "--root-dir" not in result.stdout
    for command_name in [
        "tree",
        "skeleton",
        "index",
        "search-code",
        "search-identifiers",
        "blast-radius",
    ]:
        assert command_name in result.stdout
    for removed_name in [
        "navigate",
        "propose-commit",
        "restore",
        "hub",
        "memory",
    ]:
        assert removed_name not in result.stdout


def test_blast_radius_help_lists_required_arguments() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["blast-radius", "--help"], prog_name="semctx")

    assert result.exit_code == 0
    assert "SYMBOL_NAME" in result.stdout
    assert "FILE_CONTEXT" in result.stdout


def test_tree_command_renders_fixture_symbols() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["--target-dir", str(FIXTURE_ROOT), "tree", ".", "--depth-limit", "3"],
        prog_name="semctx",
    )

    assert result.exit_code == 0
    assert "demo_project/" in result.stdout
    assert "class Greeter [3-8]" in result.stdout
    assert "function buildWidget [7-9]" in result.stdout
    assert "ignored.py" not in result.stdout


def test_skeleton_command_renders_fixture_signatures() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["--target-dir", str(FIXTURE_ROOT), "skeleton", "app/main.py"],
        prog_name="semctx",
    )

    assert result.exit_code == 0
    assert "file: app/main.py" in result.stdout
    assert "class Greeter [3-8] :: class Greeter:" in result.stdout
    assert (
        "function make_message [11-13] :: def make_message(person: str) -> str:"
        in result.stdout
    )
