"""Build regex-index trigram sets from walked files."""

from pathlib import Path

from beartype import beartype

from semctx.core.regex_index_store import RegexFileTrigramSet, RegexIndexedFileRecord
from semctx.core.walker import FileEntry, walk_target_directory

TRIGRAM_LENGTH = 3


@beartype
def extract_trigrams(content: str) -> frozenset[str]:
  """Extract distinct lowercased trigrams from file content."""
  if len(content) < TRIGRAM_LENGTH:
    return frozenset()
  lowered = content.lower()
  return frozenset(lowered[index : index + TRIGRAM_LENGTH] for index in range(len(lowered) - TRIGRAM_LENGTH + 1))


@beartype
def build_file_trigram_set(entry: FileEntry) -> RegexFileTrigramSet:
  """Read one discovered file and return its trigram snapshot."""
  stat_result = entry.absolute_path.stat()
  content = entry.absolute_path.read_text(encoding="utf-8", errors="replace")
  return RegexFileTrigramSet(
    record=RegexIndexedFileRecord(
      relative_path=entry.relative_path.as_posix(),
      mtime_ns=int(stat_result.st_mtime_ns),
      size_bytes=int(stat_result.st_size),
    ),
    trigrams=extract_trigrams(content),
  )


@beartype
def collect_regex_index_entries(target_dir: Path, depth_limit: int) -> tuple[FileEntry, ...]:
  """Collect the file entries the regex index should track."""
  return tuple(
    walk_target_directory(
      target_dir=target_dir,
      depth_limit=depth_limit,
      include_index_text_files=True,
    )
  )
