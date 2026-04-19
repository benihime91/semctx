# Regex index lifecycle unit tests.
import os
from pathlib import Path

from semctx.config.runtime_settings import build_runtime_settings
from semctx.config.runtime_settings import RuntimeSettings
from semctx.core.regex_index_store import RegexIndexStore
from semctx.tools.regex_index_db_paths import get_regex_index_db_path, get_regex_index_dir
from semctx.tools.regex_index_lifecycle import clear_regex_index, init_regex_index, refresh_regex_index, status_regex_index


def test_regex_index_lifecycle_init_and_clean_status(tmp_path: Path) -> None:
  runtime_settings = _build_workspace(tmp_path)

  initial_status = init_regex_index(runtime_settings, depth_limit=4)
  current_status = status_regex_index(runtime_settings, depth_limit=4)
  store = RegexIndexStore(get_regex_index_db_path(runtime_settings.cache_dir))

  assert initial_status.exists is True
  assert initial_status.stale is False
  assert current_status.stale is False
  assert current_status.indexed_file_count == 2
  assert [record.relative_path for record in store.load_indexed_files()] == ["app/main.py", "docs/guide.md"]


def test_status_regex_index_reports_stale_and_missing_files(tmp_path: Path) -> None:
  runtime_settings = _build_workspace(tmp_path)
  init_regex_index(runtime_settings, depth_limit=4)
  main_path = tmp_path / "app" / "main.py"
  guide_path = tmp_path / "docs" / "guide.md"
  main_stat = main_path.stat()
  os.utime(main_path, ns=(main_stat.st_atime_ns, main_stat.st_mtime_ns + 1_000_000))
  (tmp_path / "docs" / "new.md").write_text("brand new file\n", encoding="utf-8")
  guide_path.unlink()

  status = status_regex_index(runtime_settings, depth_limit=4)

  assert status.stale_file_count == 1
  assert status.missing_from_index_count == 1
  assert status.missing_on_disk_count == 1
  assert status.stale is True


def test_refresh_regex_index_updates_stale_and_new_files_without_full_rebuild(tmp_path: Path) -> None:
  runtime_settings = _build_workspace(tmp_path)
  init_regex_index(runtime_settings, depth_limit=4)
  main_path = tmp_path / "app" / "main.py"
  main_path.write_text("print('updated')\n", encoding="utf-8")
  (tmp_path / "docs" / "new.md").write_text("brand new file\n", encoding="utf-8")

  refreshed_status = refresh_regex_index(runtime_settings, depth_limit=4)
  store = RegexIndexStore(get_regex_index_db_path(runtime_settings.cache_dir))

  assert refreshed_status.stale is False
  assert refreshed_status.stale_file_count == 0
  assert refreshed_status.missing_from_index_count == 0
  assert [record.relative_path for record in store.load_indexed_files()] == [
    "app/main.py",
    "docs/guide.md",
    "docs/new.md",
  ]


def test_refresh_regex_index_full_rebuilds_when_database_is_missing(tmp_path: Path) -> None:
  runtime_settings = _build_workspace(tmp_path)

  refreshed_status = refresh_regex_index(runtime_settings, depth_limit=4, full=True)

  assert refreshed_status.exists is True
  assert refreshed_status.indexed_file_count == 2


def test_clear_regex_index_removes_db_and_regex_directory(tmp_path: Path) -> None:
  runtime_settings = _build_workspace(tmp_path)
  init_regex_index(runtime_settings, depth_limit=4)
  db_path = get_regex_index_db_path(runtime_settings.cache_dir)
  regex_dir = get_regex_index_dir(runtime_settings.cache_dir)

  assert clear_regex_index(runtime_settings) is True
  assert db_path.exists() is False
  assert regex_dir.exists() is True

  init_regex_index(runtime_settings, depth_limit=4)

  assert clear_regex_index(runtime_settings, clear_all=True) is True
  assert regex_dir.exists() is False


def _build_workspace(root_dir: Path) -> RuntimeSettings:
  (root_dir / "app").mkdir(parents=True)
  (root_dir / "docs").mkdir(parents=True)
  (root_dir / "app" / "main.py").write_text("print('hello')\n", encoding="utf-8")
  (root_dir / "docs" / "guide.md").write_text("guide text\n", encoding="utf-8")
  return build_runtime_settings(root_dir=root_dir, cache_dir=root_dir / ".semctx")
