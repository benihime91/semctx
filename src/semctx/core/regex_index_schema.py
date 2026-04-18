"""Regex candidate-prefilter index schema."""

import sqlite3
from pathlib import Path

from beartype import beartype

REGEX_SCHEMA_VERSION = "1"
REGEX_REQUIRED_TABLE_NAMES = (
  "regex_index_metadata",
  "regex_indexed_files",
  "regex_trigrams",
)

_REGEX_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS regex_index_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS regex_indexed_files (
    relative_path TEXT PRIMARY KEY,
    mtime_ns INTEGER NOT NULL,
    size_bytes INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS regex_trigrams (
    trigram TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    PRIMARY KEY (trigram, relative_path),
    FOREIGN KEY (relative_path) REFERENCES regex_indexed_files(relative_path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS regex_trigrams_by_path ON regex_trigrams(relative_path);
"""


@beartype
def ensure_regex_index_schema(db_path: Path) -> None:
  """Create the regex candidate-prefilter schema when missing."""
  db_path.parent.mkdir(parents=True, exist_ok=True)
  with sqlite3.connect(db_path) as connection:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(_REGEX_SCHEMA_SQL)
    connection.execute(
      "INSERT OR IGNORE INTO regex_index_metadata(key, value) VALUES (?, ?)",
      ("schema_version", REGEX_SCHEMA_VERSION),
    )
    connection.commit()


@beartype
def get_regex_schema_version(db_path: Path) -> str | None:
  """Read the stored regex-index schema version when available."""
  if not db_path.exists():
    return None
  with sqlite3.connect(db_path) as connection:
    row = connection.execute(
      "SELECT value FROM regex_index_metadata WHERE key = ?",
      ("schema_version",),
    ).fetchone()
  return None if row is None else str(row[0])
