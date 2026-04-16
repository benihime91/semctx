"""Index data models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IndexMetadata:
  """Store rebuild-relevant index metadata."""

  schema_version: str
  provider: str
  model: str
  parser_version: str
  chunker_version: str
  ignore_fingerprint: str
  target_dir_identity: str = ""


@dataclass(frozen=True)
class IndexedFileRecord:
  """Store file fingerprint data for refresh planning."""

  relative_path: str
  mtime_ns: int
  size_bytes: int
  content_hash: str


@dataclass(frozen=True)
class CodeChunkRecord:
  """Store one indexed code chunk row."""

  chunk_id: str
  relative_path: str
  start_line: int
  end_line: int
  content: str
  indexed_text: str
  symbol_text: str
  path_text: str
  header_text: str
  file_symbol_text: str
  local_symbol_text: str
  body_text: str
  embedding_id: str


@dataclass(frozen=True)
class IdentifierDocumentRecord:
  """Store one indexed identifier document row."""

  doc_id: str
  relative_path: str
  symbol_name: str
  start_line: int
  end_line: int
  content: str
  indexed_text: str
  path_text: str
  header_text: str
  symbol_name_text: str
  signature_text: str
  context_text: str
  embedding_id: str


@dataclass(frozen=True)
class EmbeddingRecord:
  """Store one persisted embedding row."""

  embedding_id: str
  provider: str
  model: str
  vector_json: str


@dataclass(frozen=True)
class RefreshPlan:
  """Describe the work needed to refresh the local index."""

  rebuild_required: bool
  changed_paths: tuple[str, ...]
  removed_paths: tuple[str, ...]
