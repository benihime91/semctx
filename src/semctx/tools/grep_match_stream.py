"""Streaming line matcher for grep file scans."""

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
import re

from beartype import beartype


@dataclass(frozen=True)
class StreamedLineMatch:
  """Describe one streaming line match plus its surrounding context."""

  line_number: int
  line_text: str
  context_before: tuple[str, ...]
  context_after: tuple[str, ...]


@dataclass
class _PendingLineMatch:
  """Track one in-flight match until its after-context is complete."""

  line_number: int
  line_text: str
  context_before: tuple[str, ...]
  remaining_after: int
  context_after: list[str] = field(default_factory=list)


@beartype
def collect_streamed_line_matches(
  file_path: Path,
  pattern: re.Pattern[str],
  before_context: int,
  after_context: int,
) -> list[StreamedLineMatch]:
  """Stream one file and collect grep matches with exact context semantics."""
  matches: list[_PendingLineMatch] = []
  active_matches: deque[_PendingLineMatch] = deque()
  before_lines: deque[str] = deque(maxlen=before_context)
  with file_path.open("r", encoding="utf-8", errors="replace") as handle:
    for line_number, raw_line in enumerate(handle, start=1):
      line_text = raw_line.rstrip("\n")
      _advance_active_matches(active_matches, line_text)
      if pattern.search(line_text):
        match = _PendingLineMatch(
          line_number=line_number,
          line_text=line_text,
          context_before=tuple(before_lines),
          remaining_after=after_context,
        )
        matches.append(match)
        if after_context > 0:
          active_matches.append(match)
      before_lines.append(line_text)
  return [
    StreamedLineMatch(
      line_number=match.line_number,
      line_text=match.line_text,
      context_before=match.context_before,
      context_after=tuple(match.context_after),
    )
    for match in matches
  ]


def _advance_active_matches(active_matches: deque[_PendingLineMatch], line_text: str) -> None:
  """Feed one newly read line into all pending after-context windows."""
  for _ in range(len(active_matches)):
    match = active_matches.popleft()
    match.context_after.append(line_text)
    match.remaining_after -= 1
    if match.remaining_after > 0:
      active_matches.append(match)
