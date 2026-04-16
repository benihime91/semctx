"""Index status helpers."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from beartype import beartype

from semctx.core.index_models import IndexMetadata, RefreshPlan
from semctx.core.index_store import IndexStore


@beartype
@dataclass(frozen=True)
class IndexStatus:
  """Describe the current local index state."""

  exists: bool
  stale: bool
  rebuild_required: bool
  provider: str | None
  model: str | None
  indexed_file_count: int
  code_chunk_count: int
  identifier_doc_count: int
  changed_paths: tuple[str, ...]
  removed_paths: tuple[str, ...]
  db_path: Path


@beartype
def build_status(
  store: IndexStore,
  metadata: IndexMetadata,
  refresh_plan: RefreshPlan,
  db_path: Path,
) -> IndexStatus:
  """Build a normalized index status payload."""
  del store
  indexed_file_count, code_chunk_count, identifier_doc_count = _load_status_counts(db_path)
  return IndexStatus(
    exists=True,
    stale=refresh_plan.rebuild_required or bool(refresh_plan.changed_paths or refresh_plan.removed_paths),
    rebuild_required=refresh_plan.rebuild_required,
    provider=metadata.provider,
    model=metadata.model,
    indexed_file_count=indexed_file_count,
    code_chunk_count=code_chunk_count,
    identifier_doc_count=identifier_doc_count,
    changed_paths=refresh_plan.changed_paths,
    removed_paths=refresh_plan.removed_paths,
    db_path=db_path,
  )


@beartype
def missing_index_status(db_path: Path) -> IndexStatus:
  """Build the status payload for a missing index."""
  return IndexStatus(False, False, False, None, None, 0, 0, 0, (), (), db_path)


@beartype
def render_index_status(status: IndexStatus) -> str:
  """Render index status as plain text."""
  if not status.exists:
    return "Index not found. Run `semctx index init` first."
  state = "rebuild required" if status.rebuild_required else "stale" if status.stale else "ready"
  lines = [
    f"Status: {state}",
    f"Database: {status.db_path}",
    f"Model: {render_model_selector(status)}",
    f"Indexed files: {status.indexed_file_count}",
    f"Code chunks: {status.code_chunk_count}",
    f"Identifier docs: {status.identifier_doc_count}",
  ]
  if status.changed_paths:
    lines.append(f"Changed paths: {', '.join(status.changed_paths)}")
  if status.removed_paths:
    lines.append(f"Removed paths: {', '.join(status.removed_paths)}")
  return "\n".join(lines)


@beartype
def render_model_selector(status: IndexStatus) -> str:
  """Render the canonical provider/model selector for human-facing text."""
  if status.provider and status.model:
    return f"{status.provider}/{status.model}"
  if status.model:
    return status.model
  return "unknown"


@beartype
def _load_status_counts(db_path: Path) -> tuple[int, int, int]:
  """Load row counts for the main index tables."""
  with sqlite3.connect(db_path) as connection:
    return (
      _count_rows(connection, "indexed_files"),
      _count_rows(connection, "code_chunks"),
      _count_rows(connection, "identifier_docs"),
    )


@beartype
def _count_rows(connection: sqlite3.Connection, table_name: str) -> int:
  """Count rows in one table, returning zero when absent."""
  try:
    row = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
  except sqlite3.OperationalError:
    return 0
  return int(row[0]) if row is not None else 0
