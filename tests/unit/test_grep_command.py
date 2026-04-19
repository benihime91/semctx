# Grep command unit tests.
import json
from pathlib import Path

import pytest

from semctx.commands import grep_command
from semctx.config.runtime_settings import build_runtime_settings
from semctx.tools.grep_search import InvalidRegexPatternError, grep_search


def test_build_grep_payload_collects_matches_and_json_shape(tmp_path: Path, monkeypatch) -> None:
  _write_project(tmp_path)
  monkeypatch.chdir(tmp_path)
  payload = grep_command.build_grep_payload(
    runtime_settings=build_runtime_settings(root_dir=tmp_path, cache_dir=tmp_path / ".semctx", json_output=True),
    pattern="TODO|FIXME",
  )
  rendered = json.loads(grep_command.render_output("ignored", payload, True))
  assert set(rendered) == {"command", "depth_limit", "match_count", "matches", "query", "returned_count", "target_dir", "truncated"}
  assert rendered["command"] == "grep" and rendered["query"] == "TODO|FIXME" and rendered["target_dir"] == "." and rendered["depth_limit"] == 8
  assert rendered["match_count"] == 7 and rendered["returned_count"] == 7 and rendered["truncated"] is False
  assert rendered["matches"] == [
    {"context_after": [], "context_before": [], "line_number": 1, "line_text": "# TODO: top level", "relative_path": "app/main.py"},
    {"context_after": [], "context_before": [], "line_number": 3, "line_text": "# TODO: second", "relative_path": "app/main.py"},
    {"context_after": [], "context_before": [], "line_number": 1, "line_text": "TODO in markdown text", "relative_path": "docs/guide.md"},
    {"context_after": [], "context_before": [], "line_number": 1, "line_text": "FIXME in markdown alt", "relative_path": "docs/notes.markdown"},
    {"context_after": [], "context_before": [], "line_number": 1, "line_text": "TODO in mdx text", "relative_path": "docs/page.mdx"},
    {"context_after": [], "context_before": [], "line_number": 1, "line_text": "// FIXME: nested", "relative_path": "nested/deep/widget.ts"},
    {"context_after": [], "context_before": [], "line_number": 1, "line_text": "TODO in text file is now included", "relative_path": "notes.txt"},
  ]


def test_run_grep_command_reports_no_matches(tmp_path: Path) -> None:
  _write_project(tmp_path)
  output = grep_command.run_grep_command(runtime_settings=build_runtime_settings(root_dir=tmp_path, cache_dir=tmp_path / ".semctx"), pattern="DOES_NOT_EXIST")
  assert output == "No matches found."


def test_build_grep_payload_rejects_invalid_regex(tmp_path: Path) -> None:
  _write_project(tmp_path)
  with pytest.raises(InvalidRegexPatternError, match="Invalid regex pattern"):
    grep_command.build_grep_payload(runtime_settings=build_runtime_settings(root_dir=tmp_path, cache_dir=tmp_path / ".semctx"), pattern="(")


def test_build_grep_payload_respects_target_dir_and_depth_limit(tmp_path: Path) -> None:
  _write_project(tmp_path)
  nested_payload = grep_command.build_grep_payload(
    runtime_settings=build_runtime_settings(target_dir=tmp_path / "nested", cache_dir=tmp_path / ".semctx"), pattern="FIXME", target_dir="nested"
  )
  shallow_payload = grep_command.build_grep_payload(runtime_settings=build_runtime_settings(target_dir=tmp_path, cache_dir=tmp_path / ".semctx"), pattern="FIXME", depth_limit=0)
  assert nested_payload["target_dir"] == "nested"
  assert json.loads(grep_command.render_output("ignored", nested_payload, True))["matches"] == [
    {"context_after": [], "context_before": [], "line_number": 1, "line_text": "// FIXME: nested", "relative_path": "deep/widget.ts"}
  ]
  assert shallow_payload["match_count"] == 0


def test_grep_search_respects_fixed_strings_ignore_case_and_max_count(tmp_path: Path) -> None:
  _write_project(tmp_path)
  result = grep_search(target_dir=tmp_path, pattern="todo:", ignore_case=True, fixed_strings=True, max_count=1)
  assert result.match_count == 2 and result.truncated is True and len(result.matches) == 1
  assert result.matches[0].relative_path == Path("app/main.py")


def test_grep_search_includes_existing_text_index_suffixes(tmp_path: Path) -> None:
  _write_project(tmp_path)
  result = grep_search(target_dir=tmp_path, pattern="TODO|FIXME")
  assert {"notes.txt", "docs/guide.md", "docs/page.mdx", "docs/notes.markdown"} <= {match.relative_path.as_posix() for match in result.matches}


def test_grep_search_collects_context_and_truncation_metadata(tmp_path: Path) -> None:
  _write_project(tmp_path)
  result = grep_search(target_dir=tmp_path, pattern="TODO", before_context=1, after_context=1, max_count=2)
  assert result.match_count == 5 and result.truncated is True
  assert [(match.relative_path.as_posix(), match.line_number) for match in result.matches] == [("app/main.py", 1), ("app/main.py", 3)]
  assert result.matches[0].context_before == () and result.matches[0].context_after == ("print('hello')",)


def test_grep_search_respects_include_exclude_and_scope_filters(tmp_path: Path) -> None:
  _write_project(tmp_path)
  text_result = grep_search(target_dir=tmp_path, pattern="TODO|FIXME", include=("docs/*", "notes.txt"), exclude=("*.markdown",), text_only=True)
  code_result = grep_search(target_dir=tmp_path, pattern="TODO|FIXME", include=("nested/**/*.ts",), code_only=True)
  assert [match.relative_path.as_posix() for match in text_result.matches] == ["docs/guide.md", "docs/page.mdx", "notes.txt"]
  assert [match.relative_path.as_posix() for match in code_result.matches] == ["nested/deep/widget.ts"]


def test_build_grep_payload_supports_summary_only(tmp_path: Path) -> None:
  _write_project(tmp_path)
  payload = grep_command.build_grep_payload(
    runtime_settings=build_runtime_settings(root_dir=tmp_path, cache_dir=tmp_path / ".semctx", json_output=True),
    pattern="TODO|FIXME",
    summary_only=True,
    max_count=2,
  )
  assert payload["match_count"] == 7 and payload["returned_count"] == 0 and payload["truncated"] is True and payload["matches"] == []


def test_build_grep_payload_rejects_conflicting_scope_toggles(tmp_path: Path) -> None:
  _write_project(tmp_path)
  with pytest.raises(grep_command.InvalidGrepArgumentsError, match="cannot be used together"):
    grep_command.build_grep_payload(runtime_settings=build_runtime_settings(root_dir=tmp_path, cache_dir=tmp_path / ".semctx"), pattern="TODO", code_only=True, text_only=True)


def _write_project(root_dir: Path) -> None:
  (root_dir / "app").mkdir(parents=True)
  (root_dir / "docs").mkdir(parents=True)
  (root_dir / "nested" / "deep").mkdir(parents=True)
  for relative_path, content in {
    "notes.txt": "TODO in text file is now included\n",
    "docs/guide.md": "TODO in markdown text\n",
    "docs/page.mdx": "TODO in mdx text\n",
    "docs/notes.markdown": "FIXME in markdown alt\n",
    "app/main.py": "# TODO: top level\nprint('hello')\n# TODO: second\n",
    "nested/deep/widget.ts": "// FIXME: nested\nexport const widget = true\n",
  }.items():
    (root_dir / relative_path).write_text(content, encoding="utf-8")
