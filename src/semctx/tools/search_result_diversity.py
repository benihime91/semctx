"""Search result diversity helpers."""

from dataclasses import dataclass
from pathlib import Path

from beartype import beartype
from semctx.tools.search_identifier_promotion import (
    RankedIdentifierMatch,
    promote_identifier_matches,
)

CLOSE_SCORE_GAP = 0.03
ADJACENT_LINE_GAP = 3
FILE_DIVERSITY_SCORE_GAP = 0.06
__all__ = [
    "RankedCodeMatch",
    "RankedIdentifierMatch",
    "diversify_code_matches",
    "promote_identifier_matches",
]


@dataclass(frozen=True)
class RankedCodeMatch:
    """Represent one intermediate ranked code-search match."""

    relative_path: Path
    start_line: int
    end_line: int
    score: float
    semantic_score: float
    lexical_score: float
    snippet: str


@beartype
def diversify_code_matches(
    matches: list[RankedCodeMatch], top_k: int
) -> list[RankedCodeMatch]:
    """Reduce same-file repetition in ranked code-search results."""
    selected: list[RankedCodeMatch] = []
    deferred: list[RankedCodeMatch] = []
    for index, match in enumerate(matches):
        representative = _find_same_file_representative(selected, match)
        if representative is None:
            if _should_defer_for_file_diversity(matches, index, selected):
                deferred.append(match)
                continue
            if _should_promote_primary_match(selected, match):
                selected.insert(len(selected) - 1, match)
                continue
            selected.append(match)
            continue
        if _is_better_primary_match(match, representative):
            selected[selected.index(representative)] = match
            deferred.append(representative)
            continue
        deferred.append(match)
    return _fill_remaining_slots(selected, deferred, top_k)


def _find_same_file_representative(
    selected: list[RankedCodeMatch], candidate: RankedCodeMatch
) -> RankedCodeMatch | None:
    """Find the already selected nearby match for the same file."""
    for match in selected:
        if _is_same_file_duplicate(match, candidate):
            return match
    return None


def _should_defer_for_file_diversity(
    matches: list[RankedCodeMatch], index: int, selected: list[RankedCodeMatch]
) -> bool:
    """Defer a duplicate file hit when another file is close in score."""
    candidate = matches[index]
    selected_paths = {match.relative_path for match in selected}
    if candidate.relative_path not in selected_paths:
        return False
    return any(
        contender.relative_path not in selected_paths
        for contender in matches[index + 1 :]
        if candidate.score - contender.score <= FILE_DIVERSITY_SCORE_GAP
    )


def _should_promote_primary_match(
    selected: list[RankedCodeMatch], candidate: RankedCodeMatch
) -> bool:
    """Prefer a broader nearby match as the file's primary result."""
    if not selected:
        return False
    current = selected[-1]
    if current.relative_path == candidate.relative_path:
        return False
    if current.score - candidate.score > FILE_DIVERSITY_SCORE_GAP:
        return False
    return _is_better_primary_match(candidate, current)


def _is_same_file_duplicate(left: RankedCodeMatch, right: RankedCodeMatch) -> bool:
    """Check whether two matches are near-duplicate hits in one file."""
    if left.relative_path != right.relative_path:
        return False
    if abs(left.score - right.score) > CLOSE_SCORE_GAP:
        return False
    return _line_gap(left, right) <= ADJACENT_LINE_GAP


def _is_better_primary_match(
    candidate: RankedCodeMatch, current: RankedCodeMatch
) -> bool:
    """Check whether one match is a better primary representative."""
    return _primary_match_key(candidate) > _primary_match_key(current)


def _primary_match_key(match: RankedCodeMatch) -> tuple[int, float, float, int]:
    """Build the comparison key for primary file matches."""
    return (
        _line_span(match),
        match.lexical_score,
        match.semantic_score,
        -match.start_line,
    )


def _fill_remaining_slots(
    selected: list[RankedCodeMatch], deferred: list[RankedCodeMatch], top_k: int
) -> list[RankedCodeMatch]:
    """Fill remaining result slots from deferred matches."""
    if len(selected) >= top_k:
        return selected[:top_k]
    for match in deferred:
        if len(selected) >= top_k:
            break
        selected.append(match)
    return selected


def _line_gap(left: RankedCodeMatch, right: RankedCodeMatch) -> int:
    """Measure the gap between two line ranges."""
    if right.start_line <= left.end_line and left.start_line <= right.end_line:
        return 0
    return max(left.start_line, right.start_line) - min(left.end_line, right.end_line)


def _line_span(match: RankedCodeMatch) -> int:
    """Measure the height of one line range."""
    return match.end_line - match.start_line
