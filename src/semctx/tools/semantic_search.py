"""File-level semantic search."""

from dataclasses import dataclass
from pathlib import Path

from beartype import beartype

from semctx.core.embedding_provider import EmbeddingProviderConfig, resolve_embedding_provider
from semctx.core.embeddings import (
  EmbeddingFetcher,
  fetch_embeddings,
  get_cached_embeddings,
)
from semctx.tools.search_intent import classify_search_intent
from semctx.tools.search_ranking import resolve_search_ranking_options
from semctx.tools.search_result_diversity import RankedCodeMatch, diversify_code_matches
from semctx.tools.semantic_search_support import (
  load_legacy_index_store,
  load_chunks,
  load_index_store,
  rank_chunk,
)
from semctx.tools.search_tokenizer import tokenize_search_terms


@dataclass(frozen=True)
class CodeSearchMatch:
  """Describe one ranked code-search result."""

  relative_path: Path
  start_line: int
  end_line: int
  score: float
  semantic_score: float
  lexical_score: float
  snippet: str


@beartype
def semantic_code_search(
  *,
  target_dir: Path | None = None,
  root_dir: Path | None = None,
  cache_dir: Path,
  query: str,
  provider: EmbeddingProviderConfig | None = None,
  top_k: int = 5,
  embedding_fetcher: EmbeddingFetcher | None = None,
) -> list[CodeSearchMatch]:
  """Return the top ranked indexed code chunks for a query.

  Args:
      target_dir: Canonical target directory for the search session.
      root_dir: Deprecated compatibility alias for target_dir.
      cache_dir: Cache directory that holds the local index.
      query: Search text to rank against indexed chunks.
      provider: Explicit provider/model selection for namespaced DB loading.
      top_k: Maximum number of matches to return.
      embedding_fetcher: Optional embedding fetcher override.

  Returns:
      The ranked code-search matches.
  """
  del target_dir, root_dir
  ranking_options = resolve_search_ranking_options(top_k=top_k)
  store = load_legacy_index_store(cache_dir) if provider is None else load_index_store(cache_dir, provider)
  metadata = store.load_metadata()
  if metadata is None:
    raise FileNotFoundError("Index not found. Run `semctx index init` first.")
  if provider is None:
    query_provider = resolve_embedding_provider(metadata.provider, metadata.model)
  else:
    if metadata.provider != provider.provider_name or metadata.model != provider.model:
      raise ValueError("Selected provider/model does not match the targeted index metadata.")
    query_provider = provider
  query_vector = get_cached_embeddings(
    cache_dir=cache_dir,
    model=query_provider,
    texts=[query],
    fetcher=embedding_fetcher or fetch_embeddings,
  )[0]
  query_terms = tuple(dict.fromkeys(tokenize_search_terms(query)))
  intent = classify_search_intent(query)
  matches: list[RankedCodeMatch] = []
  for chunk in load_chunks(store):
    match = rank_chunk(chunk, query, query_terms, query_vector, ranking_options, intent)
    if match is not None:
      matches.append(match)
  matches.sort(
    key=lambda match: (
      -match.score,
      -match.lexical_score,
      -match.semantic_score,
      match.relative_path.as_posix(),
      match.start_line,
    )
  )
  return [
    CodeSearchMatch(
      relative_path=match.relative_path,
      start_line=match.start_line,
      end_line=match.end_line,
      score=match.score,
      semantic_score=match.semantic_score,
      lexical_score=match.lexical_score,
      snippet=match.snippet,
    )
    for match in diversify_code_matches(matches, ranking_options.top_k)
  ]
