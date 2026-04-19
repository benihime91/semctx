"""Regex index status rendering helpers."""

from dataclasses import dataclass

from beartype import beartype


@dataclass(frozen=True)
class RegexIndexStatus:
  """Describe the current state of the regex candidate-prefilter index."""

  exists: bool
  indexed_file_count: int
  current_file_count: int
  stale_file_count: int
  missing_from_index_count: int
  missing_on_disk_count: int
  schema_version: str | None

  @property
  def stale(self) -> bool:
    """Return whether the index is stale enough that grep will fall back often."""
    return self.stale_file_count > 0 or self.missing_from_index_count > 0 or self.missing_on_disk_count > 0


@beartype
def render_regex_index_status(status: RegexIndexStatus) -> str:
  """Render a human-readable summary of the regex index status."""
  if not status.exists:
    return "Regex index: not built."
  lines = [
    "Regex index: present.",
    f"  schema: {status.schema_version or 'unknown'}",
    f"  indexed files: {status.indexed_file_count}",
    f"  current files: {status.current_file_count}",
    f"  stale files: {status.stale_file_count}",
    f"  missing from index: {status.missing_from_index_count}",
    f"  missing on disk: {status.missing_on_disk_count}",
  ]
  return "\n".join(lines)
