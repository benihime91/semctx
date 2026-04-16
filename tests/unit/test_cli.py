# CLI unit smoke tests.
# FEATURE: CLI Scaffold.
from typer.testing import CliRunner

from semctx.cli import app


def test_cli_shows_help() -> None:
  runner = CliRunner()
  result = runner.invoke(app, ["--help"], prog_name="semctx")
  assert result.exit_code == 0
  assert "semctx" in result.stdout
  assert "--json" in result.stdout
  assert "--target-dir" in result.stdout
  assert "--root-dir" not in result.stdout
