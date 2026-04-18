# Grep CLI integration tests.
# FEATURE: Root grep command output and error handling.
import json
from pathlib import Path

from typer.testing import CliRunner

from semctx.cli import app


def test_grep_command_emits_plain_text_output(tmp_path: Path) -> None:
  _write_project(tmp_path)
  runner = CliRunner()

  result = runner.invoke(
    app,
    ["--target-dir", str(tmp_path), "grep", "TODO|FIXME"],
    prog_name="semctx",
  )

  assert result.exit_code == 0
  assert result.stderr == ""
  assert result.stdout == (
    "app/main.py:1 :: # TODO: first\napp/main.py:3 :: # TODO: third\ndocs/guide.md:1 :: TODO in markdown\nnested/deep/widget.ts:1 :: // FIXME: second\nnotes.txt:1 :: FIXME in text\n"
  )


def test_grep_command_emits_json_output(tmp_path: Path) -> None:
  _write_project(tmp_path)
  runner = CliRunner()

  result = runner.invoke(
    app,
    ["--json", "--target-dir", str(tmp_path), "grep", "TODO|FIXME"],
    prog_name="semctx",
  )

  payload = json.loads(result.stdout)

  assert result.exit_code == 0
  assert result.stderr == ""
  assert payload == {
    "command": "grep",
    "depth_limit": 8,
    "match_count": 5,
    "matches": [
      {"context_after": [], "context_before": [], "line_number": 1, "line_text": "# TODO: first", "relative_path": "app/main.py"},
      {
        "context_after": [],
        "context_before": [],
        "line_number": 3,
        "line_text": "# TODO: third",
        "relative_path": "app/main.py",
      },
      {
        "context_after": [],
        "context_before": [],
        "line_number": 1,
        "line_text": "TODO in markdown",
        "relative_path": "docs/guide.md",
      },
      {"context_after": [], "context_before": [], "line_number": 1, "line_text": "// FIXME: second", "relative_path": "nested/deep/widget.ts"},
      {
        "context_after": [],
        "context_before": [],
        "line_number": 1,
        "line_text": "FIXME in text",
        "relative_path": "notes.txt",
      },
    ],
    "query": "TODO|FIXME",
    "returned_count": 5,
    "target_dir": tmp_path.as_posix(),
    "truncated": False,
  }


def test_grep_command_supports_context_and_summary_modes(tmp_path: Path) -> None:
  _write_project(tmp_path)
  runner = CliRunner()

  context_result = runner.invoke(
    app,
    ["--json", "--target-dir", str(tmp_path), "grep", "TODO", "--context", "1", "--max-count", "2"],
    prog_name="semctx",
  )
  summary_result = runner.invoke(
    app,
    ["--json", "--target-dir", str(tmp_path), "grep", "TODO|FIXME", "--summary-only", "--max-count", "2"],
    prog_name="semctx",
  )

  context_payload = json.loads(context_result.stdout)
  summary_payload = json.loads(summary_result.stdout)

  assert context_result.exit_code == 0
  assert context_payload["match_count"] == 3
  assert context_payload["returned_count"] == 2
  assert context_payload["truncated"] is True
  assert context_payload["matches"][0]["context_after"] == ["print('hello')"]
  assert summary_payload["match_count"] == 5
  assert summary_payload["returned_count"] == 0
  assert summary_payload["truncated"] is True
  assert summary_payload["matches"] == []


def test_grep_command_reports_invalid_regex_without_traceback(tmp_path: Path) -> None:
  _write_project(tmp_path)
  runner = CliRunner()

  text_result = runner.invoke(
    app,
    ["--target-dir", str(tmp_path), "grep", "("],
    prog_name="semctx",
  )
  json_result = runner.invoke(
    app,
    ["--json", "--target-dir", str(tmp_path), "grep", "("],
    prog_name="semctx",
  )

  json_payload = json.loads(json_result.stdout)

  assert text_result.exit_code == 1
  assert text_result.stderr == ""
  assert "Invalid regex pattern:" in text_result.stdout
  assert "Traceback" not in text_result.stdout
  assert json_result.exit_code == 1
  assert json_result.stderr == ""
  assert json_payload["command"] == "grep"
  assert json_payload["error"] == "invalid_regex"
  assert "Invalid regex pattern:" in json_payload["message"]


def test_grep_command_rejects_conflicting_scope_toggles(tmp_path: Path) -> None:
  _write_project(tmp_path)
  runner = CliRunner()

  result = runner.invoke(
    app,
    ["--json", "--target-dir", str(tmp_path), "grep", "TODO", "--code-only", "--text-only"],
    prog_name="semctx",
  )

  payload = json.loads(result.stdout)
  assert result.exit_code == 1
  assert payload["command"] == "grep"
  assert payload["error"] == "invalid_arguments"
  assert payload["details"] == {"code_only": True, "text_only": True}


def _write_project(root_dir: Path) -> None:
  (root_dir / "app").mkdir(parents=True)
  (root_dir / "docs").mkdir(parents=True)
  (root_dir / "nested" / "deep").mkdir(parents=True)
  (root_dir / "docs" / "guide.md").write_text(
    "TODO in markdown\n",
    encoding="utf-8",
  )
  (root_dir / "notes.txt").write_text(
    "FIXME in text\n",
    encoding="utf-8",
  )
  (root_dir / "app" / "main.py").write_text(
    "# TODO: first\nprint('hello')\n# TODO: third\n",
    encoding="utf-8",
  )
  (root_dir / "nested" / "deep" / "widget.ts").write_text(
    "// FIXME: second\nexport const widget = true\n",
    encoding="utf-8",
  )
