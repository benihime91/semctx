"""Regex-index lifecycle helpers."""

import shutil
from pathlib import Path

from beartype import beartype

from semctx.config.runtime_settings import RuntimeSettings
from semctx.core.regex_index_schema import get_regex_schema_version
from semctx.core.regex_index_store import RegexIndexStore
from semctx.tools.regex_index_builder import build_file_trigram_set, collect_regex_index_entries
from semctx.tools.regex_index_db_paths import get_regex_index_db_path, get_regex_index_dir
from semctx.tools.regex_index_status import RegexIndexStatus

DEFAULT_REGEX_INDEX_DEPTH_LIMIT = 64


@beartype
def init_regex_index(
  runtime_settings: RuntimeSettings,
  depth_limit: int = DEFAULT_REGEX_INDEX_DEPTH_LIMIT,
) -> RegexIndexStatus:
  """Build a fresh regex candidate-prefilter index."""
  db_path = get_regex_index_db_path(runtime_settings.cache_dir)
  store = RegexIndexStore(db_path)
  existing_paths = tuple(record.relative_path for record in store.load_indexed_files())
  store.delete_files(existing_paths)
  entries = collect_regex_index_entries(runtime_settings.target_dir, depth_limit)
  store.replace_files_and_trigrams(tuple(build_file_trigram_set(entry) for entry in entries))
  return _build_status(runtime_settings, depth_limit, db_path)


@beartype
def status_regex_index(
  runtime_settings: RuntimeSettings,
  depth_limit: int = DEFAULT_REGEX_INDEX_DEPTH_LIMIT,
) -> RegexIndexStatus:
  """Inspect the current regex-index status."""
  db_path = get_regex_index_db_path(runtime_settings.cache_dir)
  return _build_status(runtime_settings, depth_limit, db_path)


@beartype
def refresh_regex_index(
  runtime_settings: RuntimeSettings,
  depth_limit: int = DEFAULT_REGEX_INDEX_DEPTH_LIMIT,
  full: bool = False,
) -> RegexIndexStatus:
  """Refresh the regex index incrementally or fully."""
  db_path = get_regex_index_db_path(runtime_settings.cache_dir)
  if full or not db_path.exists():
    return init_regex_index(runtime_settings, depth_limit)
  store = RegexIndexStore(db_path)
  indexed_records = {record.relative_path: record for record in store.load_indexed_files()}
  current_entries = collect_regex_index_entries(runtime_settings.target_dir, depth_limit)
  current_paths = {entry.relative_path.as_posix() for entry in current_entries}
  stale_entries = []
  for entry in current_entries:
    posix_path = entry.relative_path.as_posix()
    stat_result = entry.absolute_path.stat()
    indexed = indexed_records.get(posix_path)
    if indexed is None:
      stale_entries.append(entry)
      continue
    if indexed.mtime_ns != int(stat_result.st_mtime_ns) or indexed.size_bytes != int(stat_result.st_size):
      stale_entries.append(entry)
  if stale_entries:
    store.replace_files_and_trigrams(tuple(build_file_trigram_set(entry) for entry in stale_entries))
  removed_paths = tuple(path for path in indexed_records if path not in current_paths)
  store.delete_files(removed_paths)
  return _build_status(runtime_settings, depth_limit, db_path)


@beartype
def clear_regex_index(
  runtime_settings: RuntimeSettings,
  clear_all: bool = False,
) -> bool:
  """Delete the workspace regex index or all regex-index artifacts."""
  if clear_all:
    regex_dir = get_regex_index_dir(runtime_settings.cache_dir)
    if not regex_dir.exists():
      return False
    shutil.rmtree(regex_dir)
    return True
  db_path = get_regex_index_db_path(runtime_settings.cache_dir)
  if not db_path.exists():
    return False
  db_path.unlink()
  return True


@beartype
def _build_status(
  runtime_settings: RuntimeSettings,
  depth_limit: int,
  db_path: Path,
) -> RegexIndexStatus:
  """Compute freshness-aware status for the regex index."""
  if not db_path.exists():
    return RegexIndexStatus(False, 0, 0, 0, 0, 0, None)
  store = RegexIndexStore(db_path)
  indexed_records = {record.relative_path: record for record in store.load_indexed_files()}
  current_entries = collect_regex_index_entries(runtime_settings.target_dir, depth_limit)
  current_paths: set[str] = set()
  stale_file_count = 0
  missing_from_index_count = 0
  for entry in current_entries:
    posix_path = entry.relative_path.as_posix()
    current_paths.add(posix_path)
    stat_result = entry.absolute_path.stat()
    indexed = indexed_records.get(posix_path)
    if indexed is None:
      missing_from_index_count += 1
      continue
    if indexed.mtime_ns != int(stat_result.st_mtime_ns) or indexed.size_bytes != int(stat_result.st_size):
      stale_file_count += 1
  missing_on_disk_count = sum(1 for path in indexed_records if path not in current_paths)
  return RegexIndexStatus(
    exists=True,
    indexed_file_count=len(indexed_records),
    current_file_count=len(current_paths),
    stale_file_count=stale_file_count,
    missing_from_index_count=missing_from_index_count,
    missing_on_disk_count=missing_on_disk_count,
    schema_version=get_regex_schema_version(db_path),
  )
