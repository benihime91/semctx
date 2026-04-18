"""Regex index database path routing helpers."""

from pathlib import Path

from beartype import beartype

REGEX_DIR_NAME = "regex"
REGEX_INDEX_DB_NAME = "index.db"


@beartype
def get_regex_index_db_path(cache_dir: Path) -> Path:
  """Return the SQLite path for the workspace regex candidate index."""
  return cache_dir / REGEX_DIR_NAME / REGEX_INDEX_DB_NAME


@beartype
def get_regex_index_dir(cache_dir: Path) -> Path:
  """Return the directory that holds all regex-index artifacts."""
  return cache_dir / REGEX_DIR_NAME
