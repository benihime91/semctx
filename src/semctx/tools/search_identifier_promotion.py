"""Identifier promotion helpers."""

from dataclasses import dataclass
from pathlib import Path

from beartype import beartype
from semctx.tools.search_tokenizer import tokenize_search_terms

IDENTIFIER_EXACT_NAME_BOOST = 0.12
IDENTIFIER_NORMALIZED_NAME_BOOST = 0.08
IDENTIFIER_SUBSET_NAME_BOOST = 0.04
IDENTIFIER_SIGNATURE_BOOST = 0.03
IDENTIFIER_HEADER_BOOST = 0.02


@dataclass(frozen=True)
class RankedIdentifierMatch:
    """Represent one intermediate ranked identifier match."""

    relative_path: Path
    kind: str
    name: str
    signature: str
    header_text: str
    line_start: int
    line_end: int
    score: float
    semantic_score: float
    lexical_score: float


@beartype
def promote_identifier_matches(
    matches: list[RankedIdentifierMatch], top_k: int, query: str
) -> list[RankedIdentifierMatch]:
    """Promote direct-hit identifier matches before truncation."""
    promoted = [_apply_identifier_promotion(match, query) for match in matches]
    promoted.sort(
        key=lambda match: (
            -match.score,
            -match.lexical_score,
            -match.semantic_score,
            match.relative_path.as_posix(),
            match.line_start,
            match.name,
        )
    )
    return promoted[:top_k]


def _apply_identifier_promotion(
    match: RankedIdentifierMatch, query: str
) -> RankedIdentifierMatch:
    """Apply identifier-specific score boosts to one match."""
    boost = _identifier_boost(match, query)
    if boost <= 0:
        return match
    return RankedIdentifierMatch(
        relative_path=match.relative_path,
        kind=match.kind,
        name=match.name,
        signature=match.signature,
        header_text=match.header_text,
        line_start=match.line_start,
        line_end=match.line_end,
        score=round(match.score + boost, 4),
        semantic_score=match.semantic_score,
        lexical_score=match.lexical_score,
    )


def _identifier_boost(match: RankedIdentifierMatch, query: str) -> float:
    """Compute a direct-hit promotion boost for one match."""
    query_phrase = query.strip().lower()
    query_terms = _normalize_terms(query)
    name_terms = _normalize_terms(match.name)
    boost = 0.0
    if _normalize_text(match.name) == _normalize_text(query):
        boost += IDENTIFIER_EXACT_NAME_BOOST
    elif name_terms == query_terms:
        boost += IDENTIFIER_NORMALIZED_NAME_BOOST
    elif _is_strong_name_subset(query_terms, name_terms):
        boost += IDENTIFIER_SUBSET_NAME_BOOST
    if query_phrase and query_phrase in match.signature.lower():
        boost += IDENTIFIER_SIGNATURE_BOOST
    if query_phrase and query_phrase in match.header_text.lower():
        boost += IDENTIFIER_HEADER_BOOST
    return boost


def _normalize_text(text: str) -> str:
    """Normalize text for exact identifier comparisons."""
    return "".join(_normalize_terms(text))


def _normalize_terms(text: str) -> tuple[str, ...]:
    """Normalize text into deduplicated search terms."""
    return tuple(dict.fromkeys(tokenize_search_terms(text)))


def _is_strong_name_subset(
    query_terms: tuple[str, ...], name_terms: tuple[str, ...]
) -> bool:
    """Check whether query terms are a strong subset of a longer name."""
    if len(query_terms) < 2 or len(name_terms) <= len(query_terms):
        return False
    return set(query_terms).issubset(name_terms)
