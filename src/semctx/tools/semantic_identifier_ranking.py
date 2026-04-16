"""Identifier-search loading and ranking helpers."""

from dataclasses import dataclass
from pathlib import Path

from beartype import beartype

from semctx.core.embeddings import cosine_similarity
from semctx.core.index_store import IndexStore
from semctx.tools.identifier_search_support import infer_identifier_kind
from semctx.tools.search_intent import SearchIntent
from semctx.tools.search_ranking import (
  SearchRankingOptions,
  compute_combined_score,
  compute_fielded_keyword_score,
  get_identifier_field_weights,
  passes_score_thresholds,
)
from semctx.tools.search_result_diversity import RankedIdentifierMatch


@dataclass(frozen=True)
class IndexedIdentifier:
  """Represent one indexed identifier plus its stored fields."""

  relative_path: Path
  symbol_name: str
  signature: str
  path_text: str
  header_text: str
  symbol_name_text: str
  signature_text: str
  context_text: str
  line_start: int
  line_end: int
  vector: list[float]


@beartype
def load_index_store(db_path: Path) -> IndexStore:
  """Load the identifier-search index store or fail clearly."""
  if not db_path.exists():
    raise FileNotFoundError("Index not found. Run `semctx index init` first.")
  return IndexStore(db_path)


@beartype
def load_identifiers(store: IndexStore) -> list[IndexedIdentifier]:
  """Load all indexed identifiers for the current canonical target dir."""
  return [
    IndexedIdentifier(
      relative_path=Path(record.relative_path),
      symbol_name=record.symbol_name,
      signature=record.content,
      path_text=record.path_text,
      header_text=record.header_text,
      symbol_name_text=record.symbol_name_text,
      signature_text=record.signature_text,
      context_text=record.context_text,
      line_start=record.start_line,
      line_end=record.end_line,
      vector=vector,
    )
    for record, vector in store.load_identifier_docs_with_vectors()
  ]


@beartype
def rank_identifier(
  identifier: IndexedIdentifier,
  query: str,
  query_terms: tuple[str, ...],
  query_vector: list[float],
  ranking_options: SearchRankingOptions,
  intent: SearchIntent,
) -> RankedIdentifierMatch | None:
  """Rank one indexed identifier for the current query."""
  raw_semantic_score = cosine_similarity(query_vector, identifier.vector)
  semantic_score = max(raw_semantic_score, 0.0)
  lexical_score = compute_fielded_keyword_score(
    query=query,
    query_terms=query_terms,
    field_texts={
      "path": identifier.path_text,
      "header": identifier.header_text,
      "symbol_name": identifier.symbol_name_text,
      "signature": identifier.signature_text,
      "context": identifier.context_text,
    },
    field_weights=get_identifier_field_weights(intent),
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
  return RankedIdentifierMatch(
    relative_path=identifier.relative_path,
    kind=infer_identifier_kind(identifier.signature),
    name=identifier.symbol_name,
    signature=identifier.signature,
    header_text=identifier.header_text,
    line_start=identifier.line_start,
    line_end=identifier.line_end,
    score=round(score, 4),
    semantic_score=round(semantic_score, 4),
    lexical_score=round(lexical_score, 4),
  )
