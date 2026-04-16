"""Index schema helpers."""

import sqlite3
from pathlib import Path

from beartype import beartype

SCHEMA_VERSION = "3"
REQUIRED_TABLE_NAMES = (
    "index_metadata",
    "indexed_files",
    "code_chunks",
    "identifier_docs",
    "embeddings",
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS index_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS indexed_files (
    relative_path TEXT PRIMARY KEY,
    mtime_ns INTEGER NOT NULL,
    size_bytes INTEGER NOT NULL,
    content_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    vector_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS code_chunks (
    chunk_id TEXT PRIMARY KEY,
    relative_path TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    content TEXT NOT NULL,
    indexed_text TEXT NOT NULL,
    symbol_text TEXT NOT NULL,
    path_text TEXT NOT NULL,
    header_text TEXT NOT NULL,
    file_symbol_text TEXT NOT NULL,
    local_symbol_text TEXT NOT NULL,
    body_text TEXT NOT NULL,
    embedding_id TEXT NOT NULL,
    FOREIGN KEY(relative_path) REFERENCES indexed_files(relative_path) ON DELETE CASCADE,
    FOREIGN KEY(embedding_id) REFERENCES embeddings(embedding_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS identifier_docs (
    doc_id TEXT PRIMARY KEY,
    relative_path TEXT NOT NULL,
    symbol_name TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    content TEXT NOT NULL,
    indexed_text TEXT NOT NULL,
    path_text TEXT NOT NULL,
    header_text TEXT NOT NULL,
    symbol_name_text TEXT NOT NULL,
    signature_text TEXT NOT NULL,
    context_text TEXT NOT NULL,
    embedding_id TEXT NOT NULL,
    FOREIGN KEY(relative_path) REFERENCES indexed_files(relative_path) ON DELETE CASCADE,
    FOREIGN KEY(embedding_id) REFERENCES embeddings(embedding_id) ON DELETE CASCADE
);
"""


@beartype
def ensure_index_schema(db_path: Path) -> None:
    """Create the local index schema when it does not exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(_SCHEMA_SQL)
        connection.execute(
            "INSERT OR IGNORE INTO index_metadata(key, value) VALUES (?, ?)",
            ("schema_version", SCHEMA_VERSION),
        )
        connection.commit()


@beartype
def get_schema_version(db_path: Path) -> str | None:
    """Read the stored schema version when available."""
    if not db_path.exists():
        return None
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT value FROM index_metadata WHERE key = ?",
            ("schema_version",),
        ).fetchone()
    if row is None:
        return None
    return str(row[0])
