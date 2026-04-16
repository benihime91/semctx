"""Search-intent classification helpers."""

from enum import Enum
import re

from beartype import beartype

from semctx.tools.search_tokenizer import tokenize_search_terms

CAMEL_CASE_PATTERN = re.compile(r"[a-z][A-Z]|[A-Z]{2,}[a-z]")
WORKFLOW_TERMS = frozenset(
    {
        "flow",
        "how",
        "lifecycle",
        "pipeline",
        "process",
        "steps",
        "trace",
        "works",
        "workflow",
    }
)
SYMBOL_VERBS = frozenset(
    {
        "build",
        "classify",
        "compute",
        "find",
        "get",
        "infer",
        "load",
        "open",
        "parse",
        "render",
        "resolve",
        "tokenize",
    }
)
IMPLEMENTATION_TERMS = frozenset(
    {
        "embedding",
        "implementation",
        "impl",
        "index",
        "ollama",
        "provider",
        "refresh",
        "sqlite",
    }
)


class SearchIntent(str, Enum):
    """Describe the main retrieval intent buckets."""

    SYMBOL_LOOKUP = "symbol_lookup"
    IMPLEMENTATION_LOOKUP = "implementation_lookup"
    CONCEPT_LOOKUP = "concept_lookup"
    WORKFLOW_LOOKUP = "workflow_lookup"


@beartype
def classify_search_intent(query: str) -> SearchIntent:
    """Classify a query into the best-fit retrieval intent."""
    normalized_query = query.strip()
    terms = tokenize_search_terms(normalized_query)
    if _contains_workflow_terms(terms):
        return SearchIntent.WORKFLOW_LOOKUP
    if _looks_symbol_like(normalized_query, terms):
        return SearchIntent.SYMBOL_LOOKUP
    if _contains_implementation_terms(terms):
        return SearchIntent.IMPLEMENTATION_LOOKUP
    return SearchIntent.CONCEPT_LOOKUP


@beartype
def _contains_workflow_terms(terms: tuple[str, ...]) -> bool:
    """Check whether a query uses workflow-oriented terms."""
    return any(term in WORKFLOW_TERMS for term in terms)


@beartype
def _contains_implementation_terms(terms: tuple[str, ...]) -> bool:
    """Check whether a query uses implementation-oriented terms."""
    return any(term in IMPLEMENTATION_TERMS for term in terms)


@beartype
def _looks_symbol_like(query: str, terms: tuple[str, ...]) -> bool:
    """Check whether a query looks like a symbol lookup."""
    if not terms:
        return False
    if _has_symbol_format(query):
        return True
    if len(terms) <= 4 and terms[0] in SYMBOL_VERBS:
        return True
    return False


@beartype
def _has_symbol_format(query: str) -> bool:
    """Check whether raw query text looks like a symbol name."""
    compact_query = query.strip()
    if "_" in compact_query:
        return True
    return bool(CAMEL_CASE_PATTERN.search(compact_query))
