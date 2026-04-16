# Semantic search unit tests.
# FEATURE: Ranked indexed chunk-level code matches.
from pathlib import Path

from semctx.config.runtime_settings import build_runtime_settings
from semctx.tools.index_lifecycle import init_index
from semctx.tools.semantic_search import semantic_code_search
from tests.unit.semantic_search_fixtures import (
  fake_fetch_embeddings,
  vector_for_text,
  write_broad_query_files,
  write_demo_files,
  write_diversity_query_files,
  write_intent_ranking_files,
)


def test_semantic_code_search_returns_chunk_line_ranges_from_index(
  tmp_path: Path,
) -> None:
  write_demo_files(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )
  init_index(runtime_settings, model="test-model", fetcher=fake_fetch_embeddings)
  fetch_count = {"value": 0}

  def fake_query_fetch(texts: list[str], model: object) -> list[list[float]]:
    fetch_count["value"] += 1
    assert texts == ["hello greeting message"]
    del model
    return [vector_for_text(text) for text in texts]

  first_results = semantic_code_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="hello greeting message",
    top_k=3,
    embedding_fetcher=fake_query_fetch,
  )
  second_results = semantic_code_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="hello greeting message",
    top_k=3,
    embedding_fetcher=fake_query_fetch,
  )

  assert fetch_count["value"] == 1
  assert first_results
  assert [match.relative_path.as_posix() for match in first_results] == [
    "app/main.py",
    "app/main.py",
  ]
  assert first_results[0].start_line >= 1
  assert first_results[0].end_line >= first_results[0].start_line
  assert first_results[0].score >= first_results[1].score
  assert first_results[0].semantic_score >= 0.0
  assert first_results[0].lexical_score >= 0.0
  assert "Hello" in first_results[0].snippet or "make_message" in first_results[0].snippet
  assert second_results == first_results


def test_semantic_code_search_prefers_lifecycle_file_for_broad_query(
  tmp_path: Path,
) -> None:
  write_broad_query_files(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )
  init_index(runtime_settings, model="test-model", fetcher=fake_fetch_embeddings)

  results = semantic_code_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="sqlite index refresh",
    top_k=3,
    embedding_fetcher=fake_fetch_embeddings,
  )

  assert results
  assert results[0].relative_path.as_posix() == "semctx/tools/index_status.py"
  assert results[0].score >= results[1].score
  assert results[0].semantic_score >= 0.0
  assert results[0].lexical_score >= 0.0


def test_semantic_code_search_prefers_symbol_rich_match_for_symbol_lookup(
  tmp_path: Path,
) -> None:
  write_intent_ranking_files(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )
  init_index(runtime_settings, model="test-model", fetcher=fake_fetch_embeddings)

  results = semantic_code_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="build index metadata",
    top_k=3,
    embedding_fetcher=fake_fetch_embeddings,
  )

  assert results
  assert results[0].relative_path.as_posix() == "semctx/core/index_metadata.py"


def test_semantic_code_search_prefers_workflow_file_for_workflow_lookup(
  tmp_path: Path,
) -> None:
  write_intent_ranking_files(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )
  init_index(runtime_settings, model="test-model", fetcher=fake_fetch_embeddings)

  results = semantic_code_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="how refresh works",
    top_k=3,
    embedding_fetcher=fake_fetch_embeddings,
  )

  assert results
  assert results[0].relative_path.as_posix() == "semctx/tools/how_refresh_works.py"


def test_semantic_code_search_limits_same_file_duplication_for_close_scores(
  tmp_path: Path,
) -> None:
  write_diversity_query_files(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )
  init_index(runtime_settings, model="test-model", fetcher=fake_fetch_embeddings)

  results = semantic_code_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="sqlite index refresh",
    top_k=5,
    embedding_fetcher=fake_fetch_embeddings,
  )

  assert len({match.relative_path.as_posix() for match in results[:4]}) == 4
  assert {match.relative_path.as_posix() for match in results[:4]} == {
    "semctx/tools/index_refresh.py",
    "semctx/tools/index_refresh_helper.py",
    "semctx/tools/refresh_guidance.py",
    "semctx/tools/refresh_runner.py",
  }
  assert [match.relative_path.as_posix() for match in results].count("semctx/tools/index_refresh.py") == 2


def test_semantic_code_search_prefers_primary_chunk_over_helper_chunk_when_scores_are_close(
  tmp_path: Path,
) -> None:
  write_diversity_query_files(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )
  init_index(runtime_settings, model="test-model", fetcher=fake_fetch_embeddings)

  results = semantic_code_search(
    root_dir=tmp_path,
    cache_dir=runtime_settings.cache_dir,
    query="sqlite index refresh",
    top_k=3,
    embedding_fetcher=fake_fetch_embeddings,
  )

  first_primary = next(match for match in results if match.relative_path.as_posix() == "semctx/tools/index_refresh.py")

  assert (first_primary.start_line, first_primary.end_line) == (3, 5)
