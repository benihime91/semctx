"""Index embedding cleanup helpers."""

import sqlite3

from beartype import beartype


@beartype
def delete_unreferenced_embeddings(connection: sqlite3.Connection, embedding_ids: tuple[str, ...]) -> None:
  """Delete embedding rows no longer referenced by any document."""
  if not embedding_ids:
    return
  for embedding_id in embedding_ids:
    reference_count = connection.execute(
      "SELECT COUNT(*) FROM code_chunks WHERE embedding_id = ? UNION ALL SELECT COUNT(*) FROM identifier_docs WHERE embedding_id = ?",
      (embedding_id, embedding_id),
    ).fetchall()
    if sum(int(row[0]) for row in reference_count) == 0:
      connection.execute("DELETE FROM embeddings WHERE embedding_id = ?", (embedding_id,))


@beartype
def load_embedding_ids(
  connection: sqlite3.Connection,
  query: str,
  params: tuple[object, ...] = (),
) -> tuple[str, ...]:
  """Load embedding ids from a SQL query."""
  rows = connection.execute(query, params).fetchall()
  return tuple(str(row[0]) for row in rows)
