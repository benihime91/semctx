"""Index building helpers."""

from pathlib import Path

from beartype import beartype

from semctx.config.runtime_settings import RuntimeSettings
from semctx.core.chunker import build_chunks
from semctx.core.embedding_provider import EmbeddingProviderConfig
from semctx.core.embeddings import (
  EmbeddingFetcher,
  fetch_embeddings,
  get_cached_embeddings,
)
from semctx.core.index_manifest import (
  build_index_metadata,
  build_indexed_file_record,
)
from semctx.core.index_models import IndexMetadata, IndexedFileRecord
from semctx.core.index_store import IndexStore
from semctx.core.parser import analyze_file
from semctx.core.walker import walk_target_directory
from semctx.tools.index_documents import (
  build_chunk_indexed_text,
  build_chunk_records,
  build_identifier_indexed_text,
  build_identifier_records,
  hash_value,
)


@beartype
def rebuild_index(
  runtime_settings: RuntimeSettings,
  provider: EmbeddingProviderConfig,
  metadata: IndexMetadata,
  current_files: tuple[IndexedFileRecord, ...],
  fetcher: EmbeddingFetcher | None,
  db_path: Path,
) -> IndexStore:
  """Rebuild the local search index from scratch."""
  if db_path.exists():
    db_path.unlink()
  store = IndexStore(db_path)
  store.set_metadata(metadata)
  store.replace_indexed_files(list(current_files))
  for record in current_files:
    index_file(
      store=store,
      cache_dir=runtime_settings.cache_dir,
      file_path=runtime_settings.target_dir / record.relative_path,
      record=record,
      provider=provider,
      fetcher=fetcher,
    )
  return store


@beartype
def index_file(
  store: IndexStore,
  cache_dir: Path,
  file_path: Path,
  record: IndexedFileRecord,
  provider: EmbeddingProviderConfig,
  fetcher: EmbeddingFetcher | None,
) -> None:
  """Index one file's chunks, identifiers, and embeddings."""
  analysis = analyze_file(file_path)
  chunks = build_chunks(file_path, relative_path=record.relative_path)
  chunk_texts = [
    build_chunk_indexed_text(
      relative_path=record.relative_path,
      chunk=chunk,
      header_lines=analysis.header_lines,
      symbols=analysis.symbols,
    )[0]
    for chunk in chunks
  ]
  chunk_vectors = get_cached_embeddings(
    cache_dir=cache_dir,
    model=provider,
    texts=chunk_texts,
    fetcher=fetcher or fetch_embeddings,
  )
  chunk_records, chunk_embeddings = build_chunk_records(
    record.relative_path,
    chunks,
    provider,
    chunk_vectors,
    header_lines=analysis.header_lines,
    symbols=analysis.symbols,
  )
  identifier_texts = [
    build_identifier_indexed_text(
      relative_path=record.relative_path,
      symbol=symbol,
      header_lines=analysis.header_lines,
    )
    for symbol in analysis.symbols
  ]
  identifier_vectors = get_cached_embeddings(
    cache_dir=cache_dir,
    model=provider,
    texts=identifier_texts,
    fetcher=fetcher or fetch_embeddings,
  )
  doc_records, doc_embeddings = build_identifier_records(
    record.relative_path,
    analysis.symbols,
    provider,
    identifier_vectors,
    header_lines=analysis.header_lines,
  )
  store.replace_embeddings(list({row.embedding_id: row for row in [*chunk_embeddings, *doc_embeddings]}.values()))
  store.replace_file_chunks(record.relative_path, chunk_records)
  store.replace_identifier_docs(record.relative_path, doc_records)


@beartype
def collect_current_files(target_dir: Path, depth_limit: int) -> tuple[IndexedFileRecord, ...]:
  """Collect current file fingerprints for the requested scope."""
  return tuple(
    build_indexed_file_record(entry.absolute_path, entry.relative_path.as_posix())
    for entry in walk_target_directory(
      target_dir=target_dir,
      depth_limit=depth_limit,
      include_index_text_files=True,
    )
  )


@beartype
def build_metadata(target_dir: Path, provider: EmbeddingProviderConfig) -> IndexMetadata:
  """Build current metadata for the requested index configuration."""
  return build_index_metadata(
    target_dir_identity=str(target_dir.resolve()),
    provider=provider.provider_name,
    model=provider.model,
    ignore_fingerprint=hash_value(*_load_ignore_sources(target_dir)),
  )


@beartype
def _load_ignore_sources(target_dir: Path) -> tuple[str, str]:
  """Load ignore file contents for fingerprinting."""
  gitignore_path = target_dir / ".gitignore"
  ignore_path = target_dir / ".ignore"
  gitignore = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
  ignore = ignore_path.read_text(encoding="utf-8") if ignore_path.exists() else ""
  return gitignore, ignore
