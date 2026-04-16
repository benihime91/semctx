"""Code-search loading and ranking helpers."""

from dataclasses import dataclass
from pathlib import Path

from beartype import beartype

from semctx.core.embedding_provider import EmbeddingProviderConfig
from semctx.core.embeddings import cosine_similarity
from semctx.core.index_store import IndexStore
from semctx.tools.index_lifecycle import get_index_db_path, get_legacy_index_db_path
from semctx.tools.search_intent import SearchIntent
from semctx.tools.search_ranking import (
  SearchRankingOptions,
  compute_combined_score,
  compute_fielded_keyword_score,
  get_code_field_weights,
  passes_score_thresholds,
)
from semctx.tools.search_result_diversity import RankedCodeMatch

SNIPPET_CHAR_LIMIT = 240


@dataclass(frozen=True)
class IndexedChunk:
  """Represent one indexed code chunk plus its stored fields."""

  relative_path: Path
  start_line: int
  end_line: int
  content: str
  path_text: str
  header_text: str
  file_symbol_text: str
  local_symbol_text: str
  body_text: str
  vector: list[float]


@beartype
def load_index_store(cache_dir: Path, provider: EmbeddingProviderConfig) -> IndexStore:
  """Load the explicitly targeted code-search index store or fail clearly."""
  db_path = get_index_db_path(cache_dir, provider)
  if not db_path.exists():
    raise FileNotFoundError("Index not found. Run `semctx index init` first.")
  return IndexStore(db_path)


@beartype
def load_legacy_index_store(cache_dir: Path) -> IndexStore:
  """Load the legacy shared code-search index store or fail clearly."""
  db_path = get_legacy_index_db_path(cache_dir)
  if not db_path.exists():
    raise FileNotFoundError("Index not found. Run `semctx index init` first.")
  return IndexStore(db_path)


@beartype
def load_chunks(store: IndexStore) -> list[IndexedChunk]:
  """Load all indexed chunks for the current canonical target dir."""
  return [
    IndexedChunk(
      relative_path=Path(record.relative_path),
      start_line=record.start_line,
      end_line=record.end_line,
      content=record.content,
      path_text=record.path_text,
      header_text=record.header_text,
      file_symbol_text=record.file_symbol_text,
      local_symbol_text=record.local_symbol_text,
      body_text=record.body_text,
      vector=vector,
    )
    for record, vector in store.load_code_chunks_with_vectors()
  ]


@beartype
def rank_chunk(
  chunk: IndexedChunk,
  query: str,
  query_terms: tuple[str, ...],
  query_vector: list[float],
  ranking_options: SearchRankingOptions,
  intent: SearchIntent,
) -> RankedCodeMatch | None:
  """Rank one indexed chunk for the current query."""
  raw_semantic_score = cosine_similarity(query_vector, chunk.vector)
  semantic_score = max(raw_semantic_score, 0.0)
  lexical_score = compute_fielded_keyword_score(
    query=query,
    query_terms=query_terms,
    field_texts={
      "path": chunk.path_text,
      "header": chunk.header_text,
      "file_symbol": chunk.file_symbol_text,
      "local_symbol": chunk.local_symbol_text,
      "body": chunk.body_text,
    },
    field_weights=get_code_field_weights(intent),
  )
  score = compute_combined_score(
    semantic_score=semantic_score,
    keyword_score=lexical_score,
    semantic_weight=ranking_options.semantic_weight,
    keyword_weight=ranking_options.keyword_weight,
  )
  if not passes_score_thresholds(
    semantic_score=semantic_score,
    keyword_score=lexical_score,
    combined_score=score,
    min_semantic_score=ranking_options.min_semantic_score,
    min_keyword_score=ranking_options.min_keyword_score,
    min_combined_score=ranking_options.min_combined_score,
    require_keyword_match=ranking_options.require_keyword_match,
    require_semantic_match=ranking_options.require_semantic_match,
  ):
    return None
  return RankedCodeMatch(
    relative_path=chunk.relative_path,
    start_line=chunk.start_line,
    end_line=chunk.end_line,
    score=round(score, 4),
    semantic_score=round(semantic_score, 4),
    lexical_score=round(lexical_score, 4),
    snippet=build_snippet(chunk.content),
  )


@beartype
def build_snippet(content: str) -> str:
  """Compress multiline chunk text into a short preview."""
  compact = " ".join(line.strip() for line in content.splitlines() if line.strip())
  if len(compact) <= SNIPPET_CHAR_LIMIT:
    return compact
  return f"{compact[: SNIPPET_CHAR_LIMIT - 3].rstrip()}..."
