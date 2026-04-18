# Regex index store unit tests.
import sqlite3
from pathlib import Path

from semctx.core.regex_index_schema import REGEX_REQUIRED_TABLE_NAMES, REGEX_SCHEMA_VERSION
from semctx.core.regex_index_store import SQLITE_DELETE_BATCH_SIZE, RegexFileTrigramSet, RegexIndexedFileRecord, RegexIndexStore


def test_regex_index_store_creates_schema_on_fresh_database(tmp_path: Path) -> None:
  db_path = tmp_path / ".semctx" / "regex" / "index.db"
  RegexIndexStore(db_path)

  with sqlite3.connect(db_path) as connection:
    table_rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    version_row = connection.execute(
      "SELECT value FROM regex_index_metadata WHERE key = ?",
      ("schema_version",),
    ).fetchone()

  assert set(name for (name,) in table_rows) >= set(REGEX_REQUIRED_TABLE_NAMES)
  assert version_row == (REGEX_SCHEMA_VERSION,)


def test_regex_index_store_round_trips_metadata(tmp_path: Path) -> None:
  store = RegexIndexStore(tmp_path / "index.db")

  store.set_metadata({"target_dir": "/tmp/workspace", "note": "fresh"})

  assert store.load_metadata() == {
    "schema_version": REGEX_SCHEMA_VERSION,
    "target_dir": "/tmp/workspace",
    "note": "fresh",
  }


def test_replace_files_and_trigrams_replaces_targeted_files_and_wipes_stale_trigrams(tmp_path: Path) -> None:
  store = RegexIndexStore(tmp_path / "index.db")
  store.replace_files_and_trigrams(
    (
      _item("a.py", 1, 10, {"abc", "bcd"}),
      _item("b.py", 2, 20, {"abc", "cde"}),
    )
  )

  store.replace_files_and_trigrams((_item("a.py", 3, 30, {"xyz"}),))

  assert store.load_indexed_files() == (
    RegexIndexedFileRecord("a.py", 3, 30),
    RegexIndexedFileRecord("b.py", 2, 20),
  )
  assert store.candidate_paths_for_trigrams(("abc",)) == frozenset({"b.py"})
  assert store.candidate_paths_for_trigrams(("xyz",)) == frozenset({"a.py"})


def test_candidate_paths_for_trigrams_returns_intersection_and_empty_input(tmp_path: Path) -> None:
  store = RegexIndexStore(tmp_path / "index.db")
  store.replace_files_and_trigrams(
    (
      _item("a.py", 1, 10, {"abc", "bcd", "cde"}),
      _item("b.py", 2, 20, {"abc", "bcd"}),
      _item("c.py", 3, 30, {"bcd", "cde"}),
    )
  )

  assert store.candidate_paths_for_trigrams(("abc", "bcd")) == frozenset({"a.py", "b.py"})
  assert store.candidate_paths_for_trigrams(("abc", "missing")) == frozenset()
  assert store.candidate_paths_for_trigrams(()) == frozenset()


def test_delete_files_chunks_large_batches_without_losing_rows(tmp_path: Path) -> None:
  store = RegexIndexStore(tmp_path / "index.db")
  items = tuple(_item(f"file_{index}.py", index, index + 100, {f"t{index:03d}"}) for index in range(SQLITE_DELETE_BATCH_SIZE + 5))
  store.replace_files_and_trigrams(items)

  store.delete_files(tuple(item.record.relative_path for item in items))

  assert store.load_indexed_files() == ()
  assert store.candidate_paths_for_trigrams(("t000",)) == frozenset()


def _item(relative_path: str, mtime_ns: int, size_bytes: int, trigrams: set[str]) -> RegexFileTrigramSet:
  return RegexFileTrigramSet(
    record=RegexIndexedFileRecord(relative_path=relative_path, mtime_ns=mtime_ns, size_bytes=size_bytes),
    trigrams=frozenset(trigrams),
  )
