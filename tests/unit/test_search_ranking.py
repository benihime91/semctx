# Search ranking unit tests.
# FEATURE: Shared tokenizer, field profiles, and weighted lexical scoring.
import pytest

from semctx.tools.search_intent import SearchIntent
from semctx.tools.search_ranking import (
    compute_combined_score,
    compute_fielded_keyword_score,
    compute_keyword_score,
    get_code_field_weights,
    get_identifier_field_weights,
    passes_score_thresholds,
    resolve_search_ranking_options,
)
from semctx.tools.search_tokenizer import tokenize_search_terms


def test_tokenize_splits_camel_case_terms() -> None:
    assert tokenize_search_terms("buildIndex metadata") == (
        "build",
        "index",
        "metadata",
    )


def test_compute_keyword_score_weights_term_symbol_and_phrase_matches() -> None:
    score = compute_keyword_score(
        query="index status",
        query_terms=("index", "status"),
        doc_text="index status view",
        symbol_text="IndexStatus renderIndexStatus",
    )

    assert score > 0.7


def test_compute_fielded_keyword_score_prefers_symbol_field_for_symbol_lookup() -> None:
    query = "IndexStatus"
    query_terms = tokenize_search_terms(query)
    weights = get_code_field_weights(SearchIntent.SYMBOL_LOOKUP)
    symbol_score = compute_fielded_keyword_score(
        query=query,
        query_terms=query_terms,
        field_texts={
            "path": "src/semctx/tools/index_status.py",
            "header": "Index status helpers",
            "file_symbol": "build_index_status load_index_status",
            "local_symbol": "IndexStatus",
            "body": "status output for the index command",
        },
        field_weights=weights,
    )
    body_score = compute_fielded_keyword_score(
        query=query,
        query_terms=query_terms,
        field_texts={
            "path": "src/semctx/tools/index_status.py",
            "header": "Index status helpers",
            "file_symbol": "build_index_status load_index_status",
            "local_symbol": "",
            "body": "IndexStatus appears only in trailing body prose.",
        },
        field_weights=weights,
    )

    assert symbol_score > body_score


def test_compute_fielded_keyword_score_uses_identifier_profile() -> None:
    query = "refresh flow"
    query_terms = tokenize_search_terms(query)
    score = compute_fielded_keyword_score(
        query=query,
        query_terms=query_terms,
        field_texts={
            "path": "src/semctx/tools/index_lifecycle.py",
            "header": "Refresh flow lifecycle helpers",
            "symbol_name": "plan_refresh",
            "signature": "def plan_refresh_flow(cache_dir: Path) -> RefreshPlan",
            "context": "refresh flow and readiness checks",
        },
        field_weights=get_identifier_field_weights(SearchIntent.WORKFLOW_LOOKUP),
    )

    assert score > 0.5


def test_get_code_field_weights_returns_workflow_profile() -> None:
    assert get_code_field_weights(SearchIntent.WORKFLOW_LOOKUP) == {
        "header": 0.30,
        "file_symbol": 0.25,
        "path": 0.25,
        "body": 0.20,
    }


def test_resolve_search_ranking_options_normalizes_thresholds() -> None:
    options = resolve_search_ranking_options(
        min_semantic_score=25,
        min_keyword_score=0.4,
        min_combined_score=15,
    )

    assert options.semantic_weight == 0.72
    assert options.keyword_weight == 0.28
    assert options.min_semantic_score == 0.25
    assert options.min_keyword_score == 0.4
    assert options.min_combined_score == 0.15


def test_compute_combined_score_uses_weighted_average() -> None:
    score = compute_combined_score(
        semantic_score=0.5,
        keyword_score=0.75,
        semantic_weight=0.72,
        keyword_weight=0.28,
    )

    assert score == pytest.approx(0.57)


def test_passes_score_thresholds_checks_match_requirements() -> None:
    assert passes_score_thresholds(
        semantic_score=0.5,
        keyword_score=0.35,
        combined_score=0.46,
        min_semantic_score=0.25,
        min_keyword_score=0.3,
        min_combined_score=0.4,
        require_keyword_match=True,
        require_semantic_match=True,
    )
    assert not passes_score_thresholds(
        semantic_score=-0.1,
        keyword_score=0.35,
        combined_score=0.2,
        require_semantic_match=True,
    )
