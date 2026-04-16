"""Field-aware search ranking helpers."""

from beartype import beartype

from semctx.tools.search_intent import SearchIntent
from semctx.tools.search_tokenizer import tokenize_search_terms

CODE_FIELD_WEIGHT_PROFILES = {
  SearchIntent.SYMBOL_LOOKUP: {
    "local_symbol": 0.35,
    "file_symbol": 0.25,
    "path": 0.15,
    "header": 0.15,
    "body": 0.10,
  },
  SearchIntent.IMPLEMENTATION_LOOKUP: {
    "header": 0.25,
    "path": 0.25,
    "file_symbol": 0.20,
    "local_symbol": 0.15,
    "body": 0.15,
  },
  SearchIntent.CONCEPT_LOOKUP: {
    "header": 0.30,
    "body": 0.30,
    "file_symbol": 0.20,
    "path": 0.20,
  },
  SearchIntent.WORKFLOW_LOOKUP: {
    "header": 0.30,
    "file_symbol": 0.25,
    "path": 0.25,
    "body": 0.20,
  },
}
IDENTIFIER_FIELD_WEIGHT_PROFILES = {
  SearchIntent.SYMBOL_LOOKUP: {
    "symbol_name": 0.40,
    "signature": 0.25,
    "path": 0.15,
    "header": 0.15,
    "context": 0.05,
  },
  SearchIntent.IMPLEMENTATION_LOOKUP: {
    "header": 0.30,
    "signature": 0.25,
    "path": 0.20,
    "symbol_name": 0.15,
    "context": 0.10,
  },
  SearchIntent.CONCEPT_LOOKUP: {
    "header": 0.30,
    "context": 0.30,
    "signature": 0.20,
    "path": 0.20,
  },
  SearchIntent.WORKFLOW_LOOKUP: {
    "header": 0.30,
    "signature": 0.30,
    "path": 0.20,
    "context": 0.20,
  },
}


@beartype
def get_code_field_weights(intent: SearchIntent) -> dict[str, float]:
  """Return code-search field weights for one intent."""
  return dict(CODE_FIELD_WEIGHT_PROFILES[intent])


@beartype
def get_identifier_field_weights(intent: SearchIntent) -> dict[str, float]:
  """Return identifier-search field weights for one intent."""
  return dict(IDENTIFIER_FIELD_WEIGHT_PROFILES[intent])


@beartype
def compute_fielded_keyword_score(
  query: str,
  query_terms: tuple[str, ...],
  field_texts: dict[str, str],
  field_weights: dict[str, float],
) -> float:
  """Compute weighted lexical relevance across stored fields."""
  if not query_terms:
    return 0.0
  active_fields = [(name, weight) for name, weight in field_weights.items() if weight > 0 and field_texts.get(name, "").strip()]
  if not active_fields:
    return 0.0
  total_weight = sum(weight for _, weight in active_fields)
  weighted_score = sum(_compute_field_score(query, query_terms, field_texts[name]) * weight for name, weight in active_fields)
  return _clamp01(weighted_score / total_weight)


def _compute_field_score(query: str, query_terms: tuple[str, ...], field_text: str) -> float:
  """Compute lexical relevance for one field."""
  normalized_field_text = field_text.strip()
  if not normalized_field_text:
    return 0.0
  term_coverage = _get_term_coverage(set(query_terms), set(tokenize_search_terms(normalized_field_text)))
  return _clamp01(term_coverage * 0.85 + _get_phrase_boost(query, normalized_field_text))


def _get_phrase_boost(query: str, doc_text: str) -> float:
  """Return a small boost for direct phrase matches."""
  query_phrase = query.strip().lower()
  return 0.15 if query_phrase and query_phrase in doc_text.lower() else 0.0


def _clamp01(value: float) -> float:
  """Clamp a numeric value into the inclusive 0-1 range."""
  return min(1.0, max(0.0, value))


def _get_term_coverage(query_terms: set[str], doc_terms: set[str]) -> float:
  """Measure how many query terms appear in one field."""
  if not query_terms:
    return 0.0
  matched_terms = sum(1 for term in query_terms if term in doc_terms)
  return matched_terms / len(query_terms)
