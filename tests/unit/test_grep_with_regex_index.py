# Grep + regex-index integration unit tests.
import os
from pathlib import Path
from re import Pattern

from pytest import MonkeyPatch

import semctx.tools.grep_search as grep_search_module
from semctx.config.runtime_settings import build_runtime_settings
from semctx.core.walker import FileEntry
from semctx.tools.grep_search import GrepMatch, GrepSearchResult, grep_search
from semctx.tools.regex_index_lifecycle import init_regex_index


def test_grep_without_cache_dir_falls_back_to_full_scan(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
  _write_workspace(tmp_path)

  walk_calls, scanned_paths, result = _run_recorded_search(tmp_path, monkeypatch, pattern="needle")

  assert walk_calls == 1
  assert scanned_paths == _all_searchable_paths()
  assert [match.relative_path.as_posix() for match in result.matches] == ["app/main.py", "notes.txt"]


def test_grep_with_cache_dir_but_no_db_falls_back_to_full_scan(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
  _write_workspace(tmp_path)

  walk_calls, scanned_paths, result = _run_recorded_search(tmp_path, monkeypatch, pattern="needle", cache_dir=tmp_path / ".semctx")

  assert walk_calls == 1
  assert scanned_paths == _all_searchable_paths()
  assert [match.relative_path.as_posix() for match in result.matches] == ["app/main.py", "notes.txt"]


def test_grep_with_built_regex_index_uses_one_tree_walk_and_narrows_candidates(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
  _write_workspace(tmp_path)
  init_regex_index(_build_runtime_settings(tmp_path), depth_limit=4)

  walk_calls, scanned_paths, result = _run_recorded_search(tmp_path, monkeypatch, pattern="needle", cache_dir=tmp_path / ".semctx")

  assert walk_calls == 1
  assert scanned_paths == ["app/main.py", "notes.txt"]
  assert [match.relative_path.as_posix() for match in result.matches] == ["app/main.py", "notes.txt"]


def test_grep_with_stale_file_still_returns_true_matches(tmp_path: Path) -> None:
  _write_workspace(tmp_path, main_text="print('hello')\n")
  init_regex_index(_build_runtime_settings(tmp_path), depth_limit=4)
  main_path = tmp_path / "app" / "main.py"
  main_path.write_text("needle after change\n", encoding="utf-8")
  stat_result = main_path.stat()
  os.utime(main_path, ns=(stat_result.st_atime_ns, stat_result.st_mtime_ns + 1_000_000))

  result = grep_search(target_dir=tmp_path, pattern="needle", cache_dir=tmp_path / ".semctx")

  assert [match.relative_path.as_posix() for match in result.matches] == ["app/main.py", "notes.txt"]


def test_grep_with_new_unindexed_file_still_returns_true_matches(tmp_path: Path) -> None:
  _write_workspace(tmp_path)
  init_regex_index(_build_runtime_settings(tmp_path), depth_limit=4)
  (tmp_path / "docs" / "new.md").write_text("needle in new file\n", encoding="utf-8")

  result = grep_search(target_dir=tmp_path, pattern="needle", cache_dir=tmp_path / ".semctx")

  assert [match.relative_path.as_posix() for match in result.matches] == ["app/main.py", "docs/new.md", "notes.txt"]


def test_grep_with_short_literal_falls_back_to_full_scan(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
  _write_workspace(tmp_path)
  init_regex_index(_build_runtime_settings(tmp_path), depth_limit=4)

  walk_calls, scanned_paths, result = _run_recorded_search(
    tmp_path,
    monkeypatch,
    pattern="hi",
    fixed_strings=True,
    cache_dir=tmp_path / ".semctx",
  )

  assert walk_calls == 1
  assert scanned_paths == _all_searchable_paths()
  assert result.match_count == 1
  assert [match.relative_path.as_posix() for match in result.matches] == ["docs/guide.md"]


def test_grep_with_alternation_falls_back_to_full_scan(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
  _write_workspace(tmp_path)
  (tmp_path / "app" / "main.py").write_text("abc here\n", encoding="utf-8")
  (tmp_path / "notes.txt").write_text("xyz_longer here\n", encoding="utf-8")
  init_regex_index(_build_runtime_settings(tmp_path), depth_limit=4)

  walk_calls, scanned_paths, result = _run_recorded_search(
    tmp_path,
    monkeypatch,
    pattern="abc|xyz_longer",
    cache_dir=tmp_path / ".semctx",
  )

  assert walk_calls == 1
  assert scanned_paths == _all_searchable_paths()
  assert [match.relative_path.as_posix() for match in result.matches] == ["app/main.py", "notes.txt"]


def _run_recorded_search(
  root_dir: Path,
  monkeypatch: MonkeyPatch,
  *,
  pattern: str,
  fixed_strings: bool = False,
  cache_dir: Path | None = None,
) -> tuple[int, list[str], GrepSearchResult]:
  original = grep_search_module._collect_entry_matches
  original_walk = grep_search_module.walk_target_directory
  scanned_paths: list[str] = []
  walk_calls = 0

  def _recording_wrapper(
    entry: FileEntry,
    pattern: Pattern[str],
    before_context: int,
    after_context: int,
  ) -> list[GrepMatch]:
    scanned_paths.append(entry.relative_path.as_posix())
    return original(entry, pattern, before_context, after_context)

  def _recording_walk(*args, **kwargs):
    nonlocal walk_calls
    walk_calls += 1
    yield from original_walk(*args, **kwargs)

  monkeypatch.setattr(grep_search_module, "_collect_entry_matches", _recording_wrapper)
  monkeypatch.setattr(grep_search_module, "walk_target_directory", _recording_walk)
  result = grep_search(target_dir=root_dir, pattern=pattern, fixed_strings=fixed_strings, cache_dir=cache_dir)
  return walk_calls, scanned_paths, result


def _build_runtime_settings(root_dir: Path):
  return build_runtime_settings(root_dir=root_dir, cache_dir=root_dir / ".semctx")


def _all_searchable_paths() -> list[str]:
  return ["app/main.py", "docs/guide.md", "docs/other.md", "notes.txt"]


def _write_workspace(root_dir: Path, main_text: str = "needle in app\n") -> None:
  (root_dir / "app").mkdir(parents=True)
  (root_dir / "docs").mkdir(parents=True)
  (root_dir / "app" / "main.py").write_text(main_text, encoding="utf-8")
  (root_dir / "docs" / "guide.md").write_text("hi there\n", encoding="utf-8")
  (root_dir / "docs" / "other.md").write_text("just docs\n", encoding="utf-8")
  (root_dir / "notes.txt").write_text("needle in notes\n", encoding="utf-8")
