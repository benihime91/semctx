"""Regex search helpers for the grep command."""

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from beartype import beartype

from semctx.core.walker import CODE_SUFFIXES, INDEX_TEXT_SUFFIXES, FileEntry, walk_target_directory
from semctx.tools.grep_match_stream import collect_streamed_line_matches

if TYPE_CHECKING:
  from semctx.core.regex_index_store import RegexIndexedFileRecord

CandidateState = tuple[frozenset[str], dict[str, "RegexIndexedFileRecord"]]

DEFAULT_GREP_DEPTH_LIMIT = 8


class InvalidRegexPatternError(ValueError):
  """Raised when a grep pattern cannot be compiled."""


@dataclass(frozen=True)
class GrepMatch:
  """Describe one matching line from grep search."""

  relative_path: Path
  line_number: int
  line_text: str
  context_before: tuple[str, ...] = ()
  context_after: tuple[str, ...] = ()


@dataclass(frozen=True)
class GrepSearchResult:
  """Describe one completed grep search."""

  matches: list[GrepMatch]
  match_count: int
  truncated: bool


@beartype
def grep_search(
  target_dir: Path,
  pattern: str,
  depth_limit: int = DEFAULT_GREP_DEPTH_LIMIT,
  ignore_case: bool = False,
  fixed_strings: bool = False,
  max_count: int | None = None,
  before_context: int = 0,
  after_context: int = 0,
  include: tuple[str, ...] = (),
  exclude: tuple[str, ...] = (),
  code_only: bool = False,
  text_only: bool = False,
  cache_dir: Path | None = None,
) -> GrepSearchResult:
  """Search supported files under one target directory for matching lines."""
  compiled_pattern = _compile_pattern(pattern, ignore_case, fixed_strings)
  candidate_paths = _resolve_candidate_paths(
    cache_dir=cache_dir,
    pattern=pattern,
    fixed_strings=fixed_strings,
  )
  matches: list[GrepMatch] = []
  match_count = 0
  for entry in walk_target_directory(
    target_dir=target_dir,
    depth_limit=depth_limit,
    include_index_text_files=True,
  ):
    if candidate_paths is not None and not _should_scan_entry(entry, candidate_paths):
      continue
    if not _matches_path_filters(entry.relative_path, include, exclude):
      continue
    if not _matches_scope(entry.relative_path, code_only, text_only):
      continue
    entry_matches = _collect_entry_matches(entry, compiled_pattern, before_context, after_context)
    match_count += len(entry_matches)
    if max_count is None:
      matches.extend(entry_matches)
      continue
    remaining_slots = max(max_count - len(matches), 0)
    if remaining_slots:
      matches.extend(entry_matches[:remaining_slots])
  return GrepSearchResult(
    matches=matches,
    match_count=match_count,
    truncated=max_count is not None and match_count > len(matches),
  )


def _resolve_candidate_paths(
  cache_dir: Path | None,
  pattern: str,
  fixed_strings: bool,
) -> CandidateState | None:
  """Return indexed candidates plus tracked freshness metadata, or None for full scan."""
  if cache_dir is None:
    return None
  try:
    from semctx.core.regex_index_store import RegexIndexStore
    from semctx.tools.regex_index_candidates import extract_required_trigrams
    from semctx.tools.regex_index_db_paths import get_regex_index_db_path

    db_path = get_regex_index_db_path(cache_dir)
    if not db_path.exists():
      return None
    required_trigrams = extract_required_trigrams(pattern=pattern, fixed_strings=fixed_strings)
    if required_trigrams is None:
      return None
    store = RegexIndexStore(db_path)
    indexed_records = {record.relative_path: record for record in store.load_indexed_files()}
    indexed_candidates = store.candidate_paths_for_trigrams(required_trigrams)
  except Exception:
    return None
  return indexed_candidates, indexed_records


def _should_scan_entry(
  entry: FileEntry,
  candidate_state: CandidateState,
) -> bool:
  """Return whether one walked entry should still be scanned."""
  indexed_candidates, indexed_records = candidate_state
  posix_path = entry.relative_path.as_posix()
  if posix_path in indexed_candidates:
    return True
  indexed = indexed_records.get(posix_path)
  if indexed is None:
    return True
  stat_result = entry.absolute_path.stat()
  return indexed.mtime_ns != int(stat_result.st_mtime_ns) or indexed.size_bytes != int(stat_result.st_size)


def _compile_pattern(pattern: str, ignore_case: bool, fixed_strings: bool) -> re.Pattern[str]:
  """Compile the requested regex pattern once for the full search."""
  flags = re.IGNORECASE if ignore_case else 0
  source_pattern = re.escape(pattern) if fixed_strings else pattern
  try:
    return re.compile(source_pattern, flags)
  except re.error as error:
    raise InvalidRegexPatternError(f"Invalid regex pattern: {error}") from error


def _collect_entry_matches(
  entry: FileEntry,
  pattern: re.Pattern[str],
  before_context: int,
  after_context: int,
) -> list[GrepMatch]:
  """Collect matching lines from one discovered file."""
  entry_matches: list[GrepMatch] = []
  for match in collect_streamed_line_matches(entry.absolute_path, pattern, before_context, after_context):
    entry_matches.append(
      GrepMatch(
        relative_path=entry.relative_path,
        line_number=match.line_number,
        line_text=match.line_text,
        context_before=match.context_before,
        context_after=match.context_after,
      )
    )
  return entry_matches


def _matches_path_filters(relative_path: Path, include: tuple[str, ...], exclude: tuple[str, ...]) -> bool:
  """Return whether one relative path matches the requested include and exclude filters."""
  path = PurePosixPath(relative_path.as_posix())
  if include and not any(path.match(pattern) for pattern in include):
    return False
  return not any(path.match(pattern) for pattern in exclude)


def _matches_scope(relative_path: Path, code_only: bool, text_only: bool) -> bool:
  """Return whether one relative path belongs to the requested search scope."""
  suffix = relative_path.suffix.lower()
  if code_only:
    return suffix in CODE_SUFFIXES
  if text_only:
    return suffix in INDEX_TEXT_SUFFIXES
  return True
