"""Index lifecycle helpers."""

from pathlib import Path
from beartype import beartype
from semctx.config.runtime_settings import RuntimeSettings
from semctx.core.embedding_provider import resolve_requested_embedding_provider
from semctx.core.embeddings import EmbeddingFetcher
from semctx.core.index_manifest import plan_refresh
from semctx.core.index_store import IndexStore
from semctx.tools.index_building import build_metadata, collect_current_files
from semctx.tools.index_lifecycle_state import (
  inspect_existing_status,
  rebuild_ready_index,
  refresh_existing_index,
)
from semctx.tools.index_status import IndexStatus, render_index_status

INDEX_DB_NAME = "index.db"
DEFAULT_INDEX_PROVIDER = "ollama"
DEFAULT_INDEX_DEPTH_LIMIT = 64
__all__ = [
  "clear_index",
  "ensure_search_ready_index",
  "get_index_db_path",
  "init_index",
  "refresh_index",
  "render_index_status",
  "status_index",
]


@beartype
def get_index_db_path(cache_dir: Path) -> Path:
  """Return the SQLite path for the local search index."""
  return cache_dir / INDEX_DB_NAME


@beartype
def init_index(
  runtime_settings: RuntimeSettings,
  provider_name: str | None = None,
  model: str | None = None,
  depth_limit: int = DEFAULT_INDEX_DEPTH_LIMIT,
  fetcher: EmbeddingFetcher | None = None,
) -> IndexStatus:
  """Build a fresh local search index."""
  provider = resolve_requested_embedding_provider(
    provider_name=provider_name,
    model=model,
    default_provider=DEFAULT_INDEX_PROVIDER,
  )
  current_files = collect_current_files(runtime_settings.target_dir, depth_limit)
  return rebuild_ready_index(
    runtime_settings,
    provider,
    build_metadata(runtime_settings.target_dir, provider),
    current_files,
    fetcher,
    get_index_db_path(runtime_settings.cache_dir),
  )


@beartype
def status_index(
  runtime_settings: RuntimeSettings,
  provider_name: str | None = None,
  model: str | None = None,
  depth_limit: int = DEFAULT_INDEX_DEPTH_LIMIT,
) -> IndexStatus:
  """Inspect current local index status."""
  return inspect_existing_status(
    runtime_settings,
    get_index_db_path(runtime_settings.cache_dir),
    provider_name,
    model,
    depth_limit,
    resolve_requested_embedding_provider,
  )


@beartype
def refresh_index(
  runtime_settings: RuntimeSettings,
  provider_name: str | None = None,
  model: str | None = None,
  depth_limit: int = DEFAULT_INDEX_DEPTH_LIMIT,
  full: bool = False,
  fetcher: EmbeddingFetcher | None = None,
) -> IndexStatus:
  """Refresh the local index or require a full rebuild when needed."""
  current_status = status_index(runtime_settings, provider_name, model, depth_limit)
  provider = resolve_requested_embedding_provider(
    provider_name=provider_name or current_status.provider,
    model=model or current_status.model,
    default_provider=current_status.provider or DEFAULT_INDEX_PROVIDER,
  )
  current_files = collect_current_files(runtime_settings.target_dir, depth_limit)
  metadata = build_metadata(runtime_settings.target_dir, provider)
  if not current_status.exists and not full:
    raise FileNotFoundError("Index not found. Run `semctx index init` first.")
  if full or not current_status.exists:
    return rebuild_ready_index(
      runtime_settings,
      provider,
      metadata,
      current_files,
      fetcher,
      get_index_db_path(runtime_settings.cache_dir),
    )
  store = IndexStore(get_index_db_path(runtime_settings.cache_dir))
  refresh_plan = plan_refresh(
    stored_metadata=store.load_metadata(),
    expected_metadata=metadata,
    stored_files=store.load_indexed_files(),
    current_files=current_files,
  )
  if refresh_plan.rebuild_required:
    raise ValueError("Full rebuild required. Run `semctx index refresh --full`.")
  return refresh_existing_index(
    runtime_settings,
    store,
    metadata,
    current_files,
    refresh_plan,
    provider,
    fetcher,
    get_index_db_path(runtime_settings.cache_dir),
  )


@beartype
def ensure_search_ready_index(
  runtime_settings: RuntimeSettings,
  provider_name: str | None = None,
  model: str | None = None,
  fetcher: EmbeddingFetcher | None = None,
) -> IndexStatus:
  """Ensure search has a ready index, auto-recovering only when safe."""
  status = status_index(runtime_settings=runtime_settings, provider_name=provider_name, model=model)
  if not status.exists:
    return init_index(
      runtime_settings=runtime_settings,
      provider_name=provider_name,
      model=model,
      fetcher=fetcher,
    )
  if status.rebuild_required:
    raise ValueError("Full rebuild required. Run `semctx index refresh --full`.")
  if status.stale:
    return refresh_index(
      runtime_settings=runtime_settings,
      provider_name=provider_name,
      model=model,
      fetcher=fetcher,
    )
  return status


@beartype
def clear_index(runtime_settings: RuntimeSettings) -> bool:
  """Delete the local index database when it exists."""
  db_path = get_index_db_path(runtime_settings.cache_dir)
  if not db_path.exists():
    return False
  db_path.unlink()
  return True
