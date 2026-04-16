"""Index database path routing helpers."""

from pathlib import Path

from beartype import beartype

from semctx.core.embedding_provider import EmbeddingProviderConfig, resolve_explicit_embedding_provider

INDEX_DB_NAME = "index.db"
EMBEDDINGS_DIR_NAME = "embeddings"


@beartype
def get_index_db_path(cache_dir: Path, provider: EmbeddingProviderConfig) -> Path:
  """Return the SQLite path for one explicit provider/model index."""
  return cache_dir / EMBEDDINGS_DIR_NAME / provider.cache_namespace / INDEX_DB_NAME


@beartype
def get_requested_index_db_path(
  cache_dir: Path,
  provider_name: str | None,
  model: str | None,
) -> Path:
  """Return the SQLite path for an explicitly selected provider/model index."""
  return get_index_db_path(cache_dir, resolve_explicit_embedding_provider(provider_name, model))


@beartype
def get_legacy_index_db_path(cache_dir: Path) -> Path:
  """Return the legacy shared SQLite path kept for compatibility flows."""
  return cache_dir / INDEX_DB_NAME


@beartype
def resolve_active_index_db_path(
  cache_dir: Path,
  provider_name: str | None,
  model: str | None,
  provider: EmbeddingProviderConfig | None = None,
) -> Path:
  """Resolve the explicit index DB path for model-targeted operations."""
  if provider is not None:
    return get_index_db_path(cache_dir, provider)
  return get_requested_index_db_path(cache_dir, provider_name, model)


@beartype
def get_all_index_db_paths(cache_dir: Path) -> tuple[Path, ...]:
  """Return every namespaced index database path under the cache directory."""
  embeddings_dir = cache_dir / EMBEDDINGS_DIR_NAME
  if not embeddings_dir.exists():
    return ()
  return tuple(sorted(path for path in embeddings_dir.glob(f"*/{INDEX_DB_NAME}") if path.is_file()))
