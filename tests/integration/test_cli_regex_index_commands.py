# Regex-index CLI integration tests.
import json
from pathlib import Path

from typer.testing import CliRunner

from semctx.cli import app
from semctx.tools.regex_index_db_paths import get_regex_index_db_path, get_regex_index_dir


def test_regex_index_init_and_status_report_expected_counts(tmp_path: Path) -> None:
  _write_workspace(tmp_path)
  runner = CliRunner()
  base_args = ["--cache-dir", str(tmp_path / ".semctx")]

  init_result = runner.invoke(app, [*base_args, "regex-index", "init", "--target-dir", str(tmp_path)], prog_name="semctx")
  status_result = runner.invoke(app, [*base_args, "regex-index", "status", "--target-dir", str(tmp_path)], prog_name="semctx")

  assert init_result.exit_code == 0
  assert "Regex index initialized." in init_result.stdout
  assert status_result.exit_code == 0
  assert "Regex index: present." in status_result.stdout
  assert "indexed files: 2" in status_result.stdout
  assert get_regex_index_db_path(tmp_path / ".semctx").exists() is True


def test_regex_index_refresh_and_full_refresh_update_status(tmp_path: Path) -> None:
  _write_workspace(tmp_path)
  runner = CliRunner()
  base_args = ["--json", "--cache-dir", str(tmp_path / ".semctx")]
  runner.invoke(app, [*base_args, "regex-index", "init", "--target-dir", str(tmp_path)], prog_name="semctx")
  (tmp_path / "app" / "main.py").write_text("print('updated')\n", encoding="utf-8")

  stale_status = runner.invoke(app, [*base_args, "regex-index", "status", "--target-dir", str(tmp_path)], prog_name="semctx")
  refresh_result = runner.invoke(app, [*base_args, "regex-index", "refresh", "--target-dir", str(tmp_path)], prog_name="semctx")
  full_refresh_result = runner.invoke(app, [*base_args, "regex-index", "refresh", "--target-dir", str(tmp_path), "--full"], prog_name="semctx")

  stale_payload = json.loads(stale_status.stdout)
  refresh_payload = json.loads(refresh_result.stdout)
  full_refresh_payload = json.loads(full_refresh_result.stdout)

  assert stale_status.exit_code == 0
  assert stale_payload["status"]["stale_file_count"] == 1
  assert refresh_result.exit_code == 0
  assert refresh_payload["status"]["stale_file_count"] == 0
  assert full_refresh_result.exit_code == 0
  assert full_refresh_payload["subcommand"] == "refresh"
  assert full_refresh_payload["status"]["exists"] is True


def test_regex_index_clear_and_clear_all_remove_expected_artifacts(tmp_path: Path) -> None:
  _write_workspace(tmp_path)
  runner = CliRunner()
  base_args = ["--cache-dir", str(tmp_path / ".semctx")]
  db_path = get_regex_index_db_path(tmp_path / ".semctx")
  regex_dir = get_regex_index_dir(tmp_path / ".semctx")

  runner.invoke(app, [*base_args, "regex-index", "init", "--target-dir", str(tmp_path)], prog_name="semctx")
  clear_result = runner.invoke(app, [*base_args, "regex-index", "clear", "--target-dir", str(tmp_path)], prog_name="semctx")
  assert clear_result.exit_code == 0
  assert clear_result.stdout == "Regex index cleared.\n"
  assert db_path.exists() is False
  assert regex_dir.exists() is True

  runner.invoke(app, [*base_args, "regex-index", "init", "--target-dir", str(tmp_path)], prog_name="semctx")
  clear_all_result = runner.invoke(app, [*base_args, "regex-index", "clear", "--target-dir", str(tmp_path), "--all"], prog_name="semctx")

  assert clear_all_result.exit_code == 0
  assert clear_all_result.stdout == "Regex index cleared.\n"
  assert regex_dir.exists() is False


def test_regex_index_json_mode_returns_structured_payloads_for_all_subcommands(tmp_path: Path) -> None:
  _write_workspace(tmp_path)
  runner = CliRunner()
  base_args = ["--json", "--cache-dir", str(tmp_path / ".semctx")]

  init_result = runner.invoke(app, [*base_args, "regex-index", "init", "--target-dir", str(tmp_path)], prog_name="semctx")
  status_result = runner.invoke(app, [*base_args, "regex-index", "status", "--target-dir", str(tmp_path)], prog_name="semctx")
  refresh_result = runner.invoke(app, [*base_args, "regex-index", "refresh", "--target-dir", str(tmp_path)], prog_name="semctx")
  clear_result = runner.invoke(app, [*base_args, "regex-index", "clear", "--target-dir", str(tmp_path)], prog_name="semctx")

  init_payload = json.loads(init_result.stdout)
  status_payload = json.loads(status_result.stdout)
  refresh_payload = json.loads(refresh_result.stdout)
  clear_payload = json.loads(clear_result.stdout)

  assert init_result.exit_code == 0
  assert init_payload == {
    "command": "regex-index",
    "status": {
      "current_file_count": 2,
      "exists": True,
      "indexed_file_count": 2,
      "missing_from_index_count": 0,
      "missing_on_disk_count": 0,
      "schema_version": "1",
      "stale": False,
      "stale_file_count": 0,
    },
    "subcommand": "init",
  }
  assert status_payload["command"] == "regex-index"
  assert status_payload["subcommand"] == "status"
  assert status_payload["status"]["exists"] is True
  assert refresh_payload["command"] == "regex-index"
  assert refresh_payload["subcommand"] == "refresh"
  assert refresh_payload["status"]["exists"] is True
  assert clear_payload == {
    "clear_all": False,
    "cleared": True,
    "command": "regex-index",
    "subcommand": "clear",
  }


def test_regex_index_status_reports_storage_errors_with_regex_index_error_code(tmp_path: Path) -> None:
  _write_workspace(tmp_path)
  runner = CliRunner()
  cache_dir = tmp_path / ".semctx"
  db_path = get_regex_index_db_path(cache_dir)
  db_path.parent.mkdir(parents=True, exist_ok=True)
  db_path.write_bytes(b"not a database")

  result = runner.invoke(
    app,
    ["--json", "--cache-dir", str(cache_dir), "regex-index", "status", "--target-dir", str(tmp_path)],
    prog_name="semctx",
  )
  payload = json.loads(result.stdout)

  assert result.exit_code == 1
  assert payload["command"] == "regex-index"
  assert payload["error"] == "regex_index_error"


def _write_workspace(root_dir: Path) -> None:
  (root_dir / "app").mkdir(parents=True)
  (root_dir / "docs").mkdir(parents=True)
  (root_dir / "app" / "main.py").write_text("print('hello')\n", encoding="utf-8")
  (root_dir / "docs" / "guide.md").write_text("guide text\n", encoding="utf-8")
