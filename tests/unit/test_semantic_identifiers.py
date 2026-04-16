# Semantic identifier unit tests.
# FEATURE: Ranked indexed identifier matches.
from pathlib import Path

from semctx.core.embedding_provider import resolve_explicit_embedding_provider
from semctx.config.runtime_settings import build_runtime_settings
from semctx.tools.index_lifecycle import init_index
from semctx.tools.semantic_identifiers import semantic_identifier_search
from tests.unit.semantic_identifier_fixtures import (
  fake_fetch_embeddings,
  write_demo_files,
  write_direct_hit_identifier_files,
  write_identifier_intent_files,
  vector_for_text,
)

MODEL_SELECTOR = "ollama/test-model"
SEARCH_PROVIDER = resolve_explicit_embedding_provider(None, MODEL_SELECTOR)


def test_semantic_identifier_search_reads_identifier_docs_from_index_and_uses_cache(
  tmp_path: Path,
) -> None:
  write_demo_files(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )
  init_index(runtime_settings, model=MODEL_SELECTOR, fetcher=fake_fetch_embeddings)
  fetch_count = {"value": 0}

  def fake_query_fetch(texts: list[str], model: object) -> list[list[float]]:
    fetch_count["value"] += 1
    assert texts == ["build widget function"]
    del model
    return [vector_for_text(text) for text in texts]

  first_results = semantic_identifier_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="build widget function",
    model=MODEL_SELECTOR,
    provider=SEARCH_PROVIDER,
    top_k=3,
    depth_limit=3,
    embedding_fetcher=fake_query_fetch,
  )
  second_results = semantic_identifier_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="build widget function",
    model=MODEL_SELECTOR,
    provider=SEARCH_PROVIDER,
    top_k=3,
    depth_limit=3,
    embedding_fetcher=fake_query_fetch,
  )

  assert fetch_count["value"] == 1
  assert first_results[0].relative_path.as_posix() == "src/widget.ts"
  assert first_results[0].name == "buildWidget"
  assert first_results[0].kind == "function"
  assert first_results[0].line_start == 7
  assert "function buildWidget" in first_results[0].signature
  assert first_results[0].score > first_results[1].score
  assert first_results[0].semantic_score >= 0.0
  assert first_results[0].lexical_score >= 0.0
  assert second_results == first_results


def test_semantic_identifier_search_prefers_symbol_name_for_symbol_lookup(
  tmp_path: Path,
) -> None:
  runtime_settings = _build_identifier_runtime(tmp_path)

  results = semantic_identifier_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="buildIndexMetadata",
    model=MODEL_SELECTOR,
    provider=SEARCH_PROVIDER,
    top_k=3,
    depth_limit=3,
    embedding_fetcher=fake_fetch_embeddings,
  )

  assert results
  assert results[0].relative_path.as_posix() == "src/index_status.ts"
  assert results[0].name == "buildIndexMetadata"
  assert results[0].score > results[1].score


def test_semantic_identifier_search_prefers_signature_and_header_for_implementation_query(
  tmp_path: Path,
) -> None:
  runtime_settings = _build_identifier_runtime(tmp_path)

  results = semantic_identifier_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="sqlite index refresh",
    model=MODEL_SELECTOR,
    provider=SEARCH_PROVIDER,
    top_k=3,
    depth_limit=3,
    embedding_fetcher=fake_fetch_embeddings,
  )

  assert results
  assert results[0].relative_path.as_posix() == "src/index_status.ts"
  assert results[0].name == "refreshSqliteIndexState"
  assert results[0].lexical_score > results[1].lexical_score


def test_semantic_identifier_search_prefers_workflow_identifier_for_workflow_query(
  tmp_path: Path,
) -> None:
  runtime_settings = _build_identifier_runtime(tmp_path)

  results = semantic_identifier_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="how refresh works",
    model=MODEL_SELECTOR,
    provider=SEARCH_PROVIDER,
    top_k=3,
    depth_limit=3,
    embedding_fetcher=fake_fetch_embeddings,
  )

  assert results
  assert results[0].relative_path.as_posix() == "src/refresh_workflow.ts"
  assert results[0].name == "howRefreshWorks"
  assert results[0].score > results[1].score


def test_semantic_identifier_search_exact_symbol_hit_wins_decisively(
  tmp_path: Path,
) -> None:
  runtime_settings = _build_direct_hit_runtime(tmp_path)

  results = semantic_identifier_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="buildIndexMetadata",
    model=MODEL_SELECTOR,
    provider=SEARCH_PROVIDER,
    top_k=3,
    depth_limit=3,
    embedding_fetcher=fake_fetch_embeddings,
  )

  assert results
  assert results[0].name == "buildIndexMetadata"
  assert results[0].score - results[1].score >= 0.079


def test_semantic_identifier_search_normalized_symbol_hit_beats_related_neighbors(
  tmp_path: Path,
) -> None:
  runtime_settings = _build_direct_hit_runtime(tmp_path)

  results = semantic_identifier_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="build index metadata",
    model=MODEL_SELECTOR,
    provider=SEARCH_PROVIDER,
    top_k=3,
    depth_limit=3,
    embedding_fetcher=fake_fetch_embeddings,
  )

  assert results
  assert results[0].name == "buildIndexMetadata"
  assert results[0].score >= results[1].score + 0.05


def _build_identifier_runtime(tmp_path: Path):
  write_identifier_intent_files(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )
  init_index(runtime_settings, model=MODEL_SELECTOR, fetcher=fake_fetch_embeddings)
  return runtime_settings


def _build_direct_hit_runtime(tmp_path: Path):
  write_direct_hit_identifier_files(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )
  init_index(runtime_settings, model=MODEL_SELECTOR, fetcher=fake_fetch_embeddings)
  return runtime_settings
