"""Index-store document mixin helpers."""

import json
import sqlite3

from beartype import beartype

from semctx.core.index_embedding_cleanup import (
    delete_unreferenced_embeddings,
    load_embedding_ids,
)
from semctx.core.index_models import CodeChunkRecord, IdentifierDocumentRecord
from semctx.core.index_store_rows import build_chunk_rows, build_identifier_doc_rows


class IndexStoreDocumentMixin:
    """Provide chunk and identifier document storage helpers."""

    def _connect(self) -> sqlite3.Connection:
        """Return an active SQLite connection."""
        raise NotImplementedError

    @beartype
    def replace_file_chunks(
        self,
        relative_path: str,
        chunks: list[CodeChunkRecord],
    ) -> None:
        """Replace all indexed chunks for one file."""
        with self._connect() as connection:
            stale_embedding_ids = load_embedding_ids(
                connection,
                "SELECT embedding_id FROM code_chunks WHERE relative_path = ?",
                (relative_path,),
            )
            connection.execute(
                "DELETE FROM code_chunks WHERE relative_path = ?", (relative_path,)
            )
            connection.executemany(
                "INSERT INTO code_chunks(chunk_id, relative_path, start_line, end_line, content, indexed_text, symbol_text, path_text, header_text, file_symbol_text, local_symbol_text, body_text, embedding_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                build_chunk_rows(chunks),
            )
            delete_unreferenced_embeddings(connection, stale_embedding_ids)
            connection.commit()

    @beartype
    def load_code_chunks(self) -> tuple[CodeChunkRecord, ...]:
        """Load stored code chunk records without vectors."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT chunk_id, relative_path, start_line, end_line, content, indexed_text, symbol_text, path_text, header_text, file_symbol_text, local_symbol_text, body_text, embedding_id FROM code_chunks ORDER BY relative_path, start_line, chunk_id"
            ).fetchall()
        return tuple(CodeChunkRecord(*tuple(row)) for row in rows)

    @beartype
    def load_code_chunks_with_vectors(
        self,
    ) -> tuple[tuple[CodeChunkRecord, list[float]], ...]:
        """Load stored code chunk records with embedding vectors."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT c.chunk_id, c.relative_path, c.start_line, c.end_line, c.content, c.indexed_text, c.symbol_text, c.path_text, c.header_text, c.file_symbol_text, c.local_symbol_text, c.body_text, c.embedding_id, e.vector_json FROM code_chunks AS c JOIN embeddings AS e ON e.embedding_id = c.embedding_id ORDER BY c.relative_path, c.start_line, c.chunk_id"
            ).fetchall()
        return tuple(
            (
                CodeChunkRecord(*tuple(row[:13])),
                [float(value) for value in json.loads(str(row[13]))],
            )
            for row in rows
        )

    @beartype
    def replace_identifier_docs(
        self,
        relative_path: str,
        docs: list[IdentifierDocumentRecord],
    ) -> None:
        """Replace all indexed identifier documents for one file."""
        with self._connect() as connection:
            stale_embedding_ids = load_embedding_ids(
                connection,
                "SELECT embedding_id FROM identifier_docs WHERE relative_path = ?",
                (relative_path,),
            )
            connection.execute(
                "DELETE FROM identifier_docs WHERE relative_path = ?",
                (relative_path,),
            )
            connection.executemany(
                "INSERT INTO identifier_docs(doc_id, relative_path, symbol_name, start_line, end_line, content, indexed_text, path_text, header_text, symbol_name_text, signature_text, context_text, embedding_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                build_identifier_doc_rows(docs),
            )
            delete_unreferenced_embeddings(connection, stale_embedding_ids)
            connection.commit()

    @beartype
    def load_identifier_docs(
        self,
    ) -> tuple[IdentifierDocumentRecord, ...]:
        """Load stored identifier documents without vectors."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT doc_id, relative_path, symbol_name, start_line, end_line, content, indexed_text, path_text, header_text, symbol_name_text, signature_text, context_text, embedding_id FROM identifier_docs ORDER BY relative_path, start_line, doc_id"
            ).fetchall()
        return tuple(IdentifierDocumentRecord(*tuple(row)) for row in rows)

    @beartype
    def load_identifier_docs_with_vectors(
        self,
    ) -> tuple[tuple[IdentifierDocumentRecord, list[float]], ...]:
        """Load stored identifier documents with embedding vectors."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT d.doc_id, d.relative_path, d.symbol_name, d.start_line, d.end_line, d.content, d.indexed_text, d.path_text, d.header_text, d.symbol_name_text, d.signature_text, d.context_text, d.embedding_id, e.vector_json FROM identifier_docs AS d JOIN embeddings AS e ON e.embedding_id = d.embedding_id ORDER BY d.relative_path, d.start_line, d.doc_id"
            ).fetchall()
        return tuple(
            (
                IdentifierDocumentRecord(*tuple(row[:13])),
                [float(value) for value in json.loads(str(row[13]))],
            )
            for row in rows
        )
