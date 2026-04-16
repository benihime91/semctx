"""Index-store row helpers."""

from beartype import beartype

from semctx.core.index_models import (
    CodeChunkRecord,
    EmbeddingRecord,
    IdentifierDocumentRecord,
    IndexMetadata,
    IndexedFileRecord,
)

METADATA_KEYS = (
    "schema_version",
    "target_dir_identity",
    "provider",
    "model",
    "parser_version",
    "chunker_version",
    "ignore_fingerprint",
)


@beartype
def build_metadata_rows(metadata: IndexMetadata) -> tuple[tuple[str, str], ...]:
    """Serialize index metadata into key/value rows."""
    return (
        ("schema_version", metadata.schema_version),
        ("target_dir_identity", metadata.target_dir_identity),
        ("provider", metadata.provider),
        ("model", metadata.model),
        ("parser_version", metadata.parser_version),
        ("chunker_version", metadata.chunker_version),
        ("ignore_fingerprint", metadata.ignore_fingerprint),
    )


@beartype
def hydrate_metadata(rows: list[tuple[object, object]]) -> IndexMetadata | None:
    """Hydrate index metadata from SQLite rows."""
    values = {str(key): str(value) for key, value in rows}
    if not set(METADATA_KEYS) <= values.keys():
        return None
    return IndexMetadata(
        schema_version=values["schema_version"],
        target_dir_identity=values.get("target_dir_identity", ""),
        provider=values["provider"],
        model=values["model"],
        parser_version=values["parser_version"],
        chunker_version=values["chunker_version"],
        ignore_fingerprint=values["ignore_fingerprint"],
    )


@beartype
def build_indexed_file_rows(
    records: list[IndexedFileRecord],
) -> list[tuple[str, int, int, str]]:
    """Serialize indexed file records for SQLite writes."""
    return [
        (record.relative_path, record.mtime_ns, record.size_bytes, record.content_hash)
        for record in records
    ]


@beartype
def build_embedding_rows(
    records: list[EmbeddingRecord],
) -> list[tuple[str, str, str, str]]:
    """Serialize embedding records for SQLite writes."""
    return [
        (record.embedding_id, record.provider, record.model, record.vector_json)
        for record in records
    ]


@beartype
def build_chunk_rows(
    records: list[CodeChunkRecord],
) -> list[tuple[str, str, int, int, str, str, str, str, str, str, str, str, str]]:
    """Serialize code chunk records for SQLite writes."""
    return [
        (
            record.chunk_id,
            record.relative_path,
            record.start_line,
            record.end_line,
            record.content,
            record.indexed_text,
            record.symbol_text,
            record.path_text,
            record.header_text,
            record.file_symbol_text,
            record.local_symbol_text,
            record.body_text,
            record.embedding_id,
        )
        for record in records
    ]


@beartype
def build_identifier_doc_rows(
    records: list[IdentifierDocumentRecord],
) -> list[tuple[str, str, str, int, int, str, str, str, str, str, str, str, str]]:
    """Serialize identifier document records for SQLite writes."""
    return [
        (
            record.doc_id,
            record.relative_path,
            record.symbol_name,
            record.start_line,
            record.end_line,
            record.content,
            record.indexed_text,
            record.path_text,
            record.header_text,
            record.symbol_name_text,
            record.signature_text,
            record.context_text,
            record.embedding_id,
        )
        for record in records
    ]
