"""Identifier-level semantic search."""

from dataclasses import dataclass
from pathlib import Path

from beartype import beartype

from semctx.core.embedding_provider import resolve_embedding_provider
from semctx.core.embeddings import (
  EmbeddingFetcher,
  fetch_embeddings,
  get_cached_embeddings,
)
from semctx.tools.identifier_search_support import (
  dedupe_search_terms,
)
from semctx.tools.index_lifecycle import get_index_db_path
from semctx.tools.search_intent import classify_search_intent
from semctx.tools.search_ranking import resolve_search_ranking_options
from semctx.tools.search_result_diversity import promote_identifier_matches
from semctx.tools.semantic_identifier_ranking import (
  load_identifiers,
  load_index_store,
  rank_identifier,
)
from semctx.tools.search_tokenizer import tokenize_search_terms


@dataclass(frozen=True)
class IdentifierSearchMatch:
  """Describe one ranked identifier-search result."""

  relative_path: Path
  kind: str
  name: str
  signature: str
  line_start: int
  line_end: int
  score: float
  semantic_score: float
  lexical_score: float


@beartype
def semantic_identifier_search(
  *,
  target_dir: Path | None = None,
  root_dir: Path | None = None,
  cache_dir: Path,
  query: str,
  model: str | None = None,
  top_k: int = 5,
  depth_limit: int = 8,
  embedding_fetcher: EmbeddingFetcher | None = None,
) -> list[IdentifierSearchMatch]:
  """Return the top ranked indexed identifiers for a query.

  Args:
      target_dir: Canonical target directory for the search session.
      root_dir: Deprecated compatibility alias for target_dir.
      cache_dir: Cache directory that holds the local index.
      query: Search text to rank against indexed identifiers.
      model: Optional model override retained for API compatibility.
      top_k: Maximum number of matches to return.
      depth_limit: Unused retained argument for API compatibility.
      embedding_fetcher: Optional embedding fetcher override.

  Returns:
      The ranked identifier-search matches.
  """
  del target_dir, root_dir, model, depth_limit
  ranking_options = resolve_search_ranking_options(top_k=top_k)
  store = load_index_store(get_index_db_path(cache_dir))
  metadata = store.load_metadata()
  if metadata is None:
    raise FileNotFoundError("Index not found. Run `semctx index init` first.")
  identifiers = load_identifiers(store)
  if not identifiers:
    return []
  provider = resolve_embedding_provider(metadata.provider, metadata.model)
  query_vector = get_cached_embeddings(
    cache_dir=cache_dir,
    model=provider,
    texts=[query],
    fetcher=embedding_fetcher or fetch_embeddings,
  )[0]
  query_terms = dedupe_search_terms(tokenize_search_terms(query))
  intent = classify_search_intent(query)
  matches = [
    match
    for identifier in identifiers
    if (
      match := rank_identifier(
        identifier=identifier,
        query=query,
        query_terms=query_terms,
        query_vector=query_vector,
        ranking_options=ranking_options,
        intent=intent,
      )
    )
    is not None
  ]
  matches.sort(
    key=lambda match: (
      -match.score,
      -match.lexical_score,
      -match.semantic_score,
      match.relative_path.as_posix(),
      match.line_start,
      match.name,
    )
  )
  return [
    IdentifierSearchMatch(
      relative_path=match.relative_path,
      kind=match.kind,
      name=match.name,
      signature=match.signature,
      line_start=match.line_start,
      line_end=match.line_end,
      score=match.score,
      semantic_score=match.semantic_score,
      lexical_score=match.lexical_score,
    )
    for match in promote_identifier_matches(matches, ranking_options.top_k, query)
  ]
