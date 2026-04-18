# Regex index builder unit tests.
from pathlib import Path

from semctx.core.walker import FileEntry
from semctx.tools.regex_index_builder import build_file_trigram_set, collect_regex_index_entries, extract_trigrams


def test_extract_trigrams_handles_short_and_lowercased_content() -> None:
  assert extract_trigrams("") == frozenset()
  assert extract_trigrams("ab") == frozenset()
  assert extract_trigrams("Hello") == frozenset({"hel", "ell", "llo"})


def test_build_file_trigram_set_records_file_stat_and_trigrams(tmp_path: Path) -> None:
  file_path = tmp_path / "sample.py"
  file_path.write_text("Hello\n", encoding="utf-8")
  file_stat = file_path.stat()
  trigram_set = build_file_trigram_set(FileEntry(absolute_path=file_path, relative_path=Path("sample.py"), depth=0))

  assert trigram_set.record.relative_path == "sample.py"
  assert trigram_set.record.mtime_ns == int(file_stat.st_mtime_ns)
  assert trigram_set.record.size_bytes == int(file_stat.st_size)
  assert trigram_set.trigrams == frozenset({"hel", "ell", "llo", "lo\n"})


def test_collect_regex_index_entries_includes_code_and_text_files(tmp_path: Path) -> None:
  (tmp_path / "pkg").mkdir()
  (tmp_path / "docs").mkdir()
  (tmp_path / ".semctx").mkdir()
  (tmp_path / "pkg" / "main.py").write_text("print('hi')\n", encoding="utf-8")
  (tmp_path / "docs" / "guide.md").write_text("hello\n", encoding="utf-8")
  (tmp_path / ".semctx" / "ignored.py").write_text("print('skip')\n", encoding="utf-8")

  entries = collect_regex_index_entries(tmp_path, depth_limit=4)

  assert [entry.relative_path.as_posix() for entry in entries] == ["docs/guide.md", "pkg/main.py"]
