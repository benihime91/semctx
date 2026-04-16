"""Index document helpers."""

import hashlib
import json

from beartype import beartype

from semctx.core.chunker import TextChunk
from semctx.core.embedding_provider import EmbeddingProviderConfig
from semctx.core.index_models import (
    CodeChunkRecord,
    EmbeddingRecord,
    IdentifierDocumentRecord,
)
from semctx.core.parser_models import SymbolInfo
from semctx.tools.index_document_fields import (
    build_chunk_fields,
    build_identifier_fields,
    join_text_parts,
)


@beartype
def build_chunk_records(
    relative_path: str,
    chunks: list[TextChunk],
    provider: EmbeddingProviderConfig,
    vectors: list[list[float]],
    header_lines: tuple[str, ...] = (),
    symbols: tuple[SymbolInfo, ...] = (),
) -> tuple[list[CodeChunkRecord], list[EmbeddingRecord]]:
    """Build code chunk and embedding rows for one file."""
    records: list[CodeChunkRecord] = []
    embeddings: list[EmbeddingRecord] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        path_text, header_text, file_symbol_text, local_symbol_text, body_text = (
            build_chunk_fields(
                relative_path=relative_path,
                chunk=chunk,
                header_lines=header_lines,
                symbols=symbols,
            )
        )
        indexed_text, symbol_text = build_chunk_indexed_text(
            relative_path=relative_path,
            chunk=chunk,
            header_lines=header_lines,
            symbols=symbols,
        )
        embedding_id = hash_value(provider.provider_name, provider.model, indexed_text)
        records.append(
            CodeChunkRecord(
                hash_value(
                    relative_path,
                    chunk.kind,
                    str(chunk.start_line),
                    str(chunk.end_line),
                ),
                relative_path,
                chunk.start_line,
                chunk.end_line,
                chunk.content,
                indexed_text,
                symbol_text,
                path_text,
                header_text,
                file_symbol_text,
                local_symbol_text,
                body_text,
                embedding_id,
            )
        )
        embeddings.append(
            EmbeddingRecord(
                embedding_id, provider.provider_name, provider.model, json.dumps(vector)
            )
        )
    return records, embeddings


@beartype
def build_identifier_records(
    relative_path: str,
    symbols: tuple[SymbolInfo, ...],
    provider: EmbeddingProviderConfig,
    vectors: list[list[float]],
    header_lines: tuple[str, ...] = (),
) -> tuple[list[IdentifierDocumentRecord], list[EmbeddingRecord]]:
    """Build identifier document and embedding rows for one file."""
    records: list[IdentifierDocumentRecord] = []
    embeddings: list[EmbeddingRecord] = []
    for symbol, vector in zip(symbols, vectors, strict=True):
        path_text, header_text, symbol_name_text, signature_text, context_text = (
            build_identifier_fields(
                relative_path=relative_path,
                symbol=symbol,
                header_lines=header_lines,
            )
        )
        indexed_text = build_identifier_indexed_text(
            relative_path=relative_path,
            symbol=symbol,
            header_lines=header_lines,
        )
        embedding_id = hash_value(provider.provider_name, provider.model, indexed_text)
        records.append(
            IdentifierDocumentRecord(
                hash_value(
                    relative_path,
                    symbol.name,
                    str(symbol.line_start),
                    str(symbol.line_end),
                ),
                relative_path,
                symbol.name,
                symbol.line_start,
                symbol.line_end,
                symbol.signature,
                indexed_text,
                path_text,
                header_text,
                symbol_name_text,
                signature_text,
                context_text,
                embedding_id,
            )
        )
        embeddings.append(
            EmbeddingRecord(
                embedding_id, provider.provider_name, provider.model, json.dumps(vector)
            )
        )
    return records, embeddings


@beartype
def hash_value(*parts: str) -> str:
    """Hash stable string parts into a deterministic identifier."""
    return hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()


@beartype
def build_chunk_indexed_text(
    relative_path: str,
    chunk: TextChunk,
    header_lines: tuple[str, ...],
    symbols: tuple[SymbolInfo, ...],
) -> tuple[str, str]:
    """Build the stored indexed text and local symbol text for a chunk."""
    _, header_text, file_symbol_text, local_symbol_text, body_text = build_chunk_fields(
        relative_path=relative_path,
        chunk=chunk,
        header_lines=header_lines,
        symbols=symbols,
    )
    return join_text_parts(
        header_text,
        file_symbol_text,
        local_symbol_text,
        body_text,
        relative_path,
    ), local_symbol_text


@beartype
def build_identifier_indexed_text(
    relative_path: str, symbol: SymbolInfo, header_lines: tuple[str, ...]
) -> str:
    """Build the stored indexed text for one identifier."""
    _, header_text, symbol_name_text, signature_text, context_text = (
        build_identifier_fields(
            relative_path=relative_path,
            symbol=symbol,
            header_lines=header_lines,
        )
    )
    return join_text_parts(
        header_text, symbol_name_text, signature_text, relative_path, context_text
    )
