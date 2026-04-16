# CLI discovery JSON integration tests.
# FEATURE: JSON output for tree and skeleton commands.
import json
from pathlib import Path

from typer.testing import CliRunner

from semctx.cli import app

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "demo_project"


def test_tree_and_skeleton_commands_emit_json() -> None:
    runner = CliRunner()
    tree_result = runner.invoke(
        app,
        [
            "--json",
            "--target-dir",
            str(FIXTURE_ROOT),
            "tree",
            ".",
            "--depth-limit",
            "3",
        ],
        prog_name="semctx",
    )
    skeleton_result = runner.invoke(
        app,
        ["--json", "--target-dir", str(FIXTURE_ROOT), "skeleton", "app/main.py"],
        prog_name="semctx",
    )

    tree_payload = json.loads(tree_result.stdout)
    skeleton_payload = json.loads(skeleton_result.stdout)

    assert tree_result.exit_code == 0
    assert tree_payload["command"] == "tree"
    assert tree_payload["root"] == "demo_project"
    assert any(file["path"] == "app/main.py" for file in tree_payload["files"])
    assert skeleton_result.exit_code == 0
    assert skeleton_payload["command"] == "skeleton"
    assert skeleton_payload["file"]["path"] == "app/main.py"
    assert skeleton_payload["file"]["symbols"][0]["name"] == "Greeter"
