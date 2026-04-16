"""Index store helpers."""

import sqlite3
from pathlib import Path

from beartype import beartype

from semctx.core.index_embedding_cleanup import (
  delete_unreferenced_embeddings,
  load_embedding_ids,
)
from semctx.core.index_models import (
  EmbeddingRecord,
  IndexMetadata,
  IndexedFileRecord,
)
from semctx.core.index_schema import ensure_index_schema
from semctx.core.index_store_documents import IndexStoreDocumentMixin
from semctx.core.index_store_rows import (
  build_embedding_rows,
  build_indexed_file_rows,
  build_metadata_rows,
  hydrate_metadata,
)


@beartype
class IndexStore(IndexStoreDocumentMixin):
  """Persist index metadata, files, documents, and vectors in SQLite."""

  def __init__(self, db_path: Path) -> None:
    """Open or initialize the backing SQLite database."""
    self.db_path = db_path
    ensure_index_schema(db_path)

  @beartype
  def set_metadata(self, metadata: IndexMetadata) -> None:
    """Replace the stored index metadata."""
    with self._connect() as connection:
      connection.executemany(
        "INSERT OR REPLACE INTO index_metadata(key, value) VALUES (?, ?)",
        build_metadata_rows(metadata),
      )
      connection.commit()

  @beartype
  def load_metadata(self) -> IndexMetadata | None:
    """Load stored index metadata when available."""
    with self._connect() as connection:
      rows = connection.execute("SELECT key, value FROM index_metadata WHERE key != 'schema_version' OR value != ''").fetchall()
    return hydrate_metadata(rows)

  @beartype
  def replace_indexed_files(self, records: list[IndexedFileRecord]) -> None:
    """Replace the tracked file manifest and clean stale vectors."""
    with self._connect() as connection:
      relative_paths = tuple(record.relative_path for record in records)
      if relative_paths:
        placeholders = ", ".join("?" for _ in relative_paths)
        stale_embedding_ids = load_embedding_ids(
          connection,
          f"SELECT embedding_id FROM code_chunks WHERE relative_path NOT IN ({placeholders}) UNION SELECT embedding_id FROM identifier_docs WHERE relative_path NOT IN ({placeholders})",
          (*relative_paths, *relative_paths),
        )
        connection.execute(
          f"DELETE FROM indexed_files WHERE relative_path NOT IN ({placeholders})",
          relative_paths,
        )
      else:
        stale_embedding_ids = load_embedding_ids(
          connection,
          "SELECT embedding_id FROM code_chunks UNION SELECT embedding_id FROM identifier_docs",
        )
        connection.execute("DELETE FROM indexed_files")
      connection.executemany(
        "INSERT OR REPLACE INTO indexed_files(relative_path, mtime_ns, size_bytes, content_hash) VALUES (?, ?, ?, ?)",
        build_indexed_file_rows(records),
      )
      delete_unreferenced_embeddings(connection, stale_embedding_ids)
      connection.commit()

  @beartype
  def load_indexed_files(self) -> tuple[IndexedFileRecord, ...]:
    """Load the tracked indexed file manifest."""
    with self._connect() as connection:
      rows = connection.execute("SELECT relative_path, mtime_ns, size_bytes, content_hash FROM indexed_files ORDER BY relative_path").fetchall()
    return tuple(IndexedFileRecord(*tuple(row)) for row in rows)

  @beartype
  def replace_embeddings(self, records: list[EmbeddingRecord]) -> None:
    """Upsert embedding rows by embedding id."""
    with self._connect() as connection:
      connection.executemany(
        "INSERT OR REPLACE INTO embeddings(embedding_id, provider, model, vector_json) VALUES (?, ?, ?, ?)",
        build_embedding_rows(records),
      )
      connection.commit()

  def _connect(self) -> sqlite3.Connection:
    """Create a SQLite connection with foreign keys enabled."""
    connection = sqlite3.connect(self.db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
