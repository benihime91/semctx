"""Regex candidate-prefilter index store."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from beartype import beartype

from semctx.core.regex_index_schema import ensure_regex_index_schema


@dataclass(frozen=True)
class RegexIndexedFileRecord:
  """Describe one file tracked by the regex index."""

  relative_path: str
  mtime_ns: int
  size_bytes: int


@dataclass(frozen=True)
class RegexFileTrigramSet:
  """Describe one file plus its extracted trigram set."""

  record: RegexIndexedFileRecord
  trigrams: frozenset[str]


@beartype
class RegexIndexStore:
  """Persist regex-index metadata, files, and trigrams in SQLite."""

  def __init__(self, db_path: Path) -> None:
    """Open or initialize the backing SQLite database."""
    self.db_path = db_path
    ensure_regex_index_schema(db_path)

  @beartype
  def set_metadata(self, items: dict[str, str]) -> None:
    """Upsert regex-index metadata rows."""
    with self._connect() as connection:
      connection.executemany(
        "INSERT OR REPLACE INTO regex_index_metadata(key, value) VALUES (?, ?)",
        tuple((key, value) for key, value in items.items()),
      )
      connection.commit()

  @beartype
  def load_metadata(self) -> dict[str, str]:
    """Load all regex-index metadata rows."""
    with self._connect() as connection:
      rows = connection.execute("SELECT key, value FROM regex_index_metadata").fetchall()
    return {str(key): str(value) for key, value in rows}

  @beartype
  def load_indexed_files(self) -> tuple[RegexIndexedFileRecord, ...]:
    """Load the tracked indexed-file manifest."""
    with self._connect() as connection:
      rows = connection.execute("SELECT relative_path, mtime_ns, size_bytes FROM regex_indexed_files ORDER BY relative_path").fetchall()
    return tuple(RegexIndexedFileRecord(relative_path=str(row[0]), mtime_ns=int(row[1]), size_bytes=int(row[2])) for row in rows)

  @beartype
  def replace_files_and_trigrams(self, items: tuple[RegexFileTrigramSet, ...]) -> None:
    """Replace the indexed rows for the provided files and refresh their trigrams."""
    if not items:
      return
    with self._connect() as connection:
      connection.executemany(
        "INSERT OR REPLACE INTO regex_indexed_files(relative_path, mtime_ns, size_bytes) VALUES (?, ?, ?)",
        tuple((item.record.relative_path, item.record.mtime_ns, item.record.size_bytes) for item in items),
      )
      connection.executemany(
        "DELETE FROM regex_trigrams WHERE relative_path = ?",
        tuple((item.record.relative_path,) for item in items),
      )
      trigram_rows = tuple((trigram, item.record.relative_path) for item in items for trigram in item.trigrams)
      if trigram_rows:
        connection.executemany(
          "INSERT OR IGNORE INTO regex_trigrams(trigram, relative_path) VALUES (?, ?)",
          trigram_rows,
        )
      connection.commit()

  @beartype
  def delete_files(self, relative_paths: tuple[str, ...]) -> None:
    """Delete tracked files and their trigrams by relative path."""
    if not relative_paths:
      return
    placeholders = ", ".join("?" for _ in relative_paths)
    with self._connect() as connection:
      connection.execute(
        f"DELETE FROM regex_indexed_files WHERE relative_path IN ({placeholders})",
        relative_paths,
      )
      connection.commit()

  @beartype
  def candidate_paths_for_trigrams(self, trigrams: tuple[str, ...]) -> frozenset[str]:
    """Return the intersection of candidate paths for every required trigram."""
    if not trigrams:
      return frozenset()
    with self._connect() as connection:
      result: set[str] | None = None
      for trigram in trigrams:
        rows = connection.execute(
          "SELECT relative_path FROM regex_trigrams WHERE trigram = ?",
          (trigram,),
        ).fetchall()
        current = {str(row[0]) for row in rows}
        result = current if result is None else result & current
        if not result:
          return frozenset()
    return frozenset(result or set())

  def _connect(self) -> sqlite3.Connection:
    """Create a SQLite connection with foreign keys enabled."""
    connection = sqlite3.connect(self.db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
