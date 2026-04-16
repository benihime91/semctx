"""Index manifest helpers."""

import hashlib
from pathlib import Path

from beartype import beartype

from semctx.core.index_models import IndexMetadata, IndexedFileRecord, RefreshPlan
from semctx.core.index_schema import SCHEMA_VERSION

PARSER_VERSION = "2"
CHUNKER_VERSION = "2"


@beartype
def build_index_metadata(
  provider: str,
  model: str,
  ignore_fingerprint: str,
  target_dir_identity: str = "",
  parser_version: str = PARSER_VERSION,
  chunker_version: str = CHUNKER_VERSION,
) -> IndexMetadata:
  """Build normalized index metadata for one provider setup."""
  return IndexMetadata(
    schema_version=SCHEMA_VERSION,
    target_dir_identity=target_dir_identity,
    provider=provider,
    model=model,
    parser_version=parser_version,
    chunker_version=chunker_version,
    ignore_fingerprint=ignore_fingerprint,
  )


@beartype
def build_indexed_file_record(file_path: Path, relative_path: str) -> IndexedFileRecord:
  """Build a manifest record for one indexed file."""
  payload = file_path.read_bytes()
  file_stat = file_path.stat()
  return IndexedFileRecord(
    relative_path=relative_path,
    mtime_ns=file_stat.st_mtime_ns,
    size_bytes=file_stat.st_size,
    content_hash=hashlib.sha256(payload).hexdigest(),
  )


@beartype
def needs_full_rebuild(old: IndexMetadata, new: IndexMetadata) -> bool:
  """Check whether metadata changes require a full rebuild."""
  return old != new


@beartype
def plan_refresh(
  stored_metadata: IndexMetadata | None,
  expected_metadata: IndexMetadata,
  stored_files: tuple[IndexedFileRecord, ...],
  current_files: tuple[IndexedFileRecord, ...],
) -> RefreshPlan:
  """Plan changed and removed files for an index refresh."""
  current_paths = tuple(record.relative_path for record in current_files)
  if stored_metadata is None or needs_full_rebuild(stored_metadata, expected_metadata):
    return RefreshPlan(
      rebuild_required=True,
      changed_paths=tuple(sorted(current_paths)),
      removed_paths=(),
    )
  stored_by_path = {record.relative_path: record for record in stored_files}
  current_by_path = {record.relative_path: record for record in current_files}
  changed_paths = tuple(sorted(relative_path for relative_path, current_record in current_by_path.items() if stored_by_path.get(relative_path) != current_record))
  removed_paths = tuple(sorted(relative_path for relative_path in stored_by_path if relative_path not in current_by_path))
  return RefreshPlan(
    rebuild_required=False,
    changed_paths=changed_paths,
    removed_paths=removed_paths,
  )
