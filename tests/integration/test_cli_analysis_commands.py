# CLI integration tests for analysis commands.
# FEATURE: Blast-radius command flows.
import json
from pathlib import Path

from typer.testing import CliRunner

from semctx.cli import app


def test_blast_radius_command_reports_external_fixture_usages(tmp_path: Path) -> None:
  fixture_root = _write_blast_radius_fixture(tmp_path)
  runner = CliRunner()
  result = runner.invoke(
    app,
    ["--target-dir", str(fixture_root), "blast-radius", "Greeter", "app/main.py"],
    prog_name="semctx",
  )

  assert result.exit_code == 0
  assert "symbol: Greeter" in result.stdout
  assert "definition: class Greeter [3-8]" in result.stdout
  assert "usages: 3" in result.stdout
  assert "- app/consumer.py:1 :: from app.main import Greeter" in result.stdout
  assert "- app/consumer.py:4 :: greeter = Greeter(prefix)" in result.stdout
  assert '- src/widget.ts:2 :: export const greeterName = "Greeter";' in result.stdout


def test_blast_radius_command_emits_json(tmp_path: Path) -> None:
  fixture_root = _write_blast_radius_fixture(tmp_path)
  runner = CliRunner()
  result = runner.invoke(
    app,
    [
      "--json",
      "--target-dir",
      str(fixture_root),
      "blast-radius",
      "Greeter",
      "app/main.py",
    ],
    prog_name="semctx",
  )

  payload = json.loads(result.stdout)

  assert result.exit_code == 0
  assert payload["command"] == "blast-radius"
  assert payload["definition"]["name"] == "Greeter"
  assert len(payload["usages"]) == 3
  assert payload["usages"][0]["relative_path"] == "app/consumer.py"


def _write_blast_radius_fixture(root_dir: Path) -> Path:
  app_dir = root_dir / "app"
  src_dir = root_dir / "src"
  app_dir.mkdir(parents=True)
  src_dir.mkdir(parents=True)
  (app_dir / "main.py").write_text(
    "# Main application module.\n# FEATURE: Blast radius fixture.\nclass Greeter:\n    def __init__(self, prefix: str) -> None:\n        self.prefix = prefix\n\n    def greet(self, person: str) -> str:\n        return f'{self.prefix}, {person}!'\n"
  )
  (app_dir / "consumer.py").write_text(
    "from app.main import Greeter\n\ndef build_message(prefix: str, name: str) -> str:\n    greeter = Greeter(prefix)\n    return greeter.greet(name)\n"
  )
  (src_dir / "widget.ts").write_text('// Widget helpers.\nexport const greeterName = "Greeter";\n')
  return root_dir
