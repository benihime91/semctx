"""State helpers for index lifecycle flows."""

from collections.abc import Callable
from pathlib import Path

from beartype import beartype

from semctx.config.runtime_settings import RuntimeSettings
from semctx.core.embedding_provider import EmbeddingProviderConfig
from semctx.core.embeddings import EmbeddingFetcher
from semctx.core.index_manifest import plan_refresh
from semctx.core.index_models import IndexMetadata, IndexedFileRecord, RefreshPlan
from semctx.core.index_store import IndexStore
from semctx.tools.index_building import (
  build_metadata,
  collect_current_files,
  index_file,
  rebuild_index,
)
from semctx.tools.index_status import IndexStatus, build_status, missing_index_status


@beartype
def load_store(db_path: Path) -> IndexStore | None:
  """Load the index store only when the database exists."""
  if not db_path.exists():
    return None
  return IndexStore(db_path)


@beartype
def build_ready_status(
  store: IndexStore,
  metadata: IndexMetadata,
  db_path: Path,
) -> IndexStatus:
  """Build the steady-state status after successful writes."""
  return build_status(store, metadata, RefreshPlan(False, (), ()), db_path)


@beartype
def rebuild_ready_index(
  runtime_settings: RuntimeSettings,
  provider: EmbeddingProviderConfig,
  metadata: IndexMetadata,
  current_files: tuple[IndexedFileRecord, ...],
  fetcher: EmbeddingFetcher | None,
  db_path: Path,
) -> IndexStatus:
  """Rebuild the full index and return the ready status."""
  store = rebuild_index(
    runtime_settings,
    provider,
    metadata,
    current_files,
    fetcher,
    db_path,
  )
  return build_ready_status(store, metadata, db_path)


@beartype
def inspect_existing_status(
  runtime_settings: RuntimeSettings,
  db_path: Path,
  provider_name: str | None,
  model: str | None,
  depth_limit: int,
  resolve_provider: Callable[..., EmbeddingProviderConfig],
) -> IndexStatus:
  """Build status for an existing or missing index database."""
  store = load_store(db_path)
  if store is None:
    return missing_index_status(db_path)
  stored_metadata = store.load_metadata()
  if stored_metadata is None:
    return missing_index_status(db_path)
  provider = resolve_provider(
    provider_name=provider_name or stored_metadata.provider,
    model=model or stored_metadata.model,
    default_provider=stored_metadata.provider,
  )
  refresh_plan = plan_refresh(
    stored_metadata=stored_metadata,
    expected_metadata=build_metadata(runtime_settings.target_dir, provider),
    stored_files=store.load_indexed_files(),
    current_files=collect_current_files(runtime_settings.target_dir, depth_limit),
  )
  return build_status(store, stored_metadata, refresh_plan, db_path)


@beartype
def refresh_existing_index(
  runtime_settings: RuntimeSettings,
  store: IndexStore,
  metadata: IndexMetadata,
  current_files: tuple[IndexedFileRecord, ...],
  refresh_plan: RefreshPlan,
  provider: EmbeddingProviderConfig,
  fetcher: EmbeddingFetcher | None,
  db_path: Path,
) -> IndexStatus:
  """Refresh changed indexed files and return the ready status."""
  current_by_path = {record.relative_path: record for record in current_files}
  store.set_metadata(metadata)
  store.replace_indexed_files(list(current_files))
  for relative_path in refresh_plan.changed_paths:
    index_file(
      store=store,
      cache_dir=runtime_settings.cache_dir,
      file_path=runtime_settings.target_dir / relative_path,
      record=current_by_path[relative_path],
      provider=provider,
      fetcher=fetcher,
    )
  return build_ready_status(store, metadata, db_path)
