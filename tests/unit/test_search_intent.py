# Search intent unit tests.
# FEATURE: Deterministic reduced-core query classification.
from semctx.tools.search_intent import SearchIntent, classify_search_intent


def test_classify_search_intent_recognizes_symbol_lookup() -> None:
    assert classify_search_intent("IndexStatus") is SearchIntent.SYMBOL_LOOKUP


def test_classify_search_intent_recognizes_symbol_lookup_for_symbol_fragments() -> None:
    assert classify_search_intent("build index metadata") is SearchIntent.SYMBOL_LOOKUP


def test_classify_search_intent_recognizes_implementation_lookup() -> None:
    assert (
        classify_search_intent("sqlite index refresh")
        is SearchIntent.IMPLEMENTATION_LOOKUP
    )


def test_classify_search_intent_recognizes_concept_lookup() -> None:
    assert (
        classify_search_intent("semantic search quality") is SearchIntent.CONCEPT_LOOKUP
    )


def test_classify_search_intent_recognizes_workflow_lookup() -> None:
    assert classify_search_intent("how refresh works") is SearchIntent.WORKFLOW_LOOKUP


def test_classify_search_intent_prefers_workflow_over_implementation_terms() -> None:
    assert (
        classify_search_intent("index lifecycle flow") is SearchIntent.WORKFLOW_LOOKUP
    )
