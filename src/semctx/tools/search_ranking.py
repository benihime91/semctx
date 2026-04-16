"""Search ranking helpers."""

from dataclasses import dataclass

from beartype import beartype

from semctx.tools.search_field_ranking import (
    compute_fielded_keyword_score,
    get_code_field_weights,
    get_identifier_field_weights,
)
from semctx.tools.search_tokenizer import tokenize_search_terms

DEFAULT_TOP_K = 5
DEFAULT_SEMANTIC_WEIGHT = 0.72
DEFAULT_KEYWORD_WEIGHT = 0.28
DEFAULT_MIN_SEMANTIC_SCORE = 0.0
DEFAULT_MIN_KEYWORD_SCORE = 0.0
DEFAULT_MIN_COMBINED_SCORE = 0.1
__all__ = [
    "DEFAULT_KEYWORD_WEIGHT",
    "DEFAULT_MIN_COMBINED_SCORE",
    "DEFAULT_MIN_KEYWORD_SCORE",
    "DEFAULT_MIN_SEMANTIC_SCORE",
    "DEFAULT_SEMANTIC_WEIGHT",
    "DEFAULT_TOP_K",
    "SearchRankingOptions",
    "compute_combined_score",
    "compute_fielded_keyword_score",
    "compute_keyword_score",
    "get_code_field_weights",
    "get_identifier_field_weights",
    "passes_score_thresholds",
    "resolve_search_ranking_options",
]


@dataclass(frozen=True)
class SearchRankingOptions:
    """Describe normalized ranking settings for search results."""

    top_k: int = DEFAULT_TOP_K
    semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT
    keyword_weight: float = DEFAULT_KEYWORD_WEIGHT
    min_semantic_score: float = DEFAULT_MIN_SEMANTIC_SCORE
    min_keyword_score: float = DEFAULT_MIN_KEYWORD_SCORE
    min_combined_score: float = DEFAULT_MIN_COMBINED_SCORE
    require_keyword_match: bool = False
    require_semantic_match: bool = False


@beartype
def resolve_search_ranking_options(
    top_k: int | None = None,
    semantic_weight: float | None = None,
    keyword_weight: float | None = None,
    min_semantic_score: float | int | None = None,
    min_keyword_score: float | int | None = None,
    min_combined_score: float | int | None = None,
    require_keyword_match: bool = False,
    require_semantic_match: bool = False,
) -> SearchRankingOptions:
    """Normalize caller-provided ranking options."""
    return SearchRankingOptions(
        top_k=_normalize_top_k(top_k, DEFAULT_TOP_K),
        semantic_weight=_normalize_weight(semantic_weight, DEFAULT_SEMANTIC_WEIGHT),
        keyword_weight=_normalize_weight(keyword_weight, DEFAULT_KEYWORD_WEIGHT),
        min_semantic_score=_normalize_threshold(
            min_semantic_score, DEFAULT_MIN_SEMANTIC_SCORE
        ),
        min_keyword_score=_normalize_threshold(
            min_keyword_score, DEFAULT_MIN_KEYWORD_SCORE
        ),
        min_combined_score=_normalize_threshold(
            min_combined_score, DEFAULT_MIN_COMBINED_SCORE
        ),
        require_keyword_match=require_keyword_match,
        require_semantic_match=require_semantic_match,
    )


@beartype
def compute_keyword_score(
    query: str,
    query_terms: tuple[str, ...],
    doc_text: str,
    symbol_text: str,
) -> float:
    """Compute lexical relevance for a whole-document text match."""
    unique_query_terms = set(query_terms)
    if not unique_query_terms:
        return 0.0
    normalized_doc_text = doc_text.strip()
    term_coverage = _get_term_coverage(
        unique_query_terms, set(tokenize_search_terms(normalized_doc_text))
    )
    symbol_coverage = _get_term_coverage(
        unique_query_terms, set(tokenize_search_terms(symbol_text))
    )
    phrase_boost = (
        0.15
        if query.strip() and query.strip().lower() in normalized_doc_text.lower()
        else 0.0
    )
    return _clamp01(term_coverage * 0.65 + symbol_coverage * 0.20 + phrase_boost)


@beartype
def compute_combined_score(
    semantic_score: float,
    keyword_score: float,
    semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT,
    keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
) -> float:
    """Combine semantic and lexical scores into one bounded score."""
    semantic_component = max(semantic_score, 0.0)
    total_weight = semantic_weight + keyword_weight
    if total_weight <= 0:
        return _clamp01(semantic_component)
    return _clamp01(
        (semantic_weight * semantic_component + keyword_weight * keyword_score)
        / total_weight
    )


@beartype
def passes_score_thresholds(
    semantic_score: float,
    keyword_score: float,
    combined_score: float,
    min_semantic_score: float = DEFAULT_MIN_SEMANTIC_SCORE,
    min_keyword_score: float = DEFAULT_MIN_KEYWORD_SCORE,
    min_combined_score: float = DEFAULT_MIN_COMBINED_SCORE,
    require_keyword_match: bool = False,
    require_semantic_match: bool = False,
) -> bool:
    """Check whether a ranked result clears all score thresholds."""
    if require_semantic_match and semantic_score <= 0:
        return False
    if require_keyword_match and keyword_score <= 0:
        return False
    return not (
        max(semantic_score, 0.0) < min_semantic_score
        or keyword_score < min_keyword_score
        or combined_score < min_combined_score
    )


def _clamp01(value: float) -> float:
    """Clamp a numeric value into the inclusive 0-1 range."""
    return min(1.0, max(0.0, value))


def _normalize_threshold(value: float | int | None, fallback: float) -> float:
    """Normalize score thresholds from ratios or percentages."""
    if value is None or not value == value:
        return fallback
    if value > 1:
        return _clamp01(value / 100)
    return _clamp01(value)


def _normalize_weight(value: float | None, fallback: float) -> float:
    """Normalize an optional ranking weight."""
    if value is None or not value == value or value < 0:
        return fallback
    return value


def _normalize_top_k(value: int | None, fallback: int) -> int:
    """Normalize top-k values to a positive integer."""
    if value is None:
        return fallback
    return max(1, int(value))


def _get_term_coverage(query_terms: set[str], doc_terms: set[str]) -> float:
    """Measure how many query terms appear in one document."""
    if not query_terms:
        return 0.0
    matched_terms = sum(1 for term in query_terms if term in doc_terms)
    return matched_terms / len(query_terms)
