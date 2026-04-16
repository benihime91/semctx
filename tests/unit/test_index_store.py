# Index store unit tests.
# FEATURE: SQLite schema and CRUD foundations.
import sqlite3
from pathlib import Path

from semctx.core.index_models import (
  CodeChunkRecord,
  EmbeddingRecord,
  IdentifierDocumentRecord,
  IndexMetadata,
  IndexedFileRecord,
)
from semctx.core.index_schema import ensure_index_schema
from semctx.core.index_store import IndexStore
from semctx.core.parser_models import SymbolInfo
from semctx.core.embedding_provider import resolve_embedding_provider
from semctx.core.chunker import TextChunk
from semctx.tools.index_documents import build_chunk_records


def test_ensure_index_schema_creates_required_tables(tmp_path: Path) -> None:
  db_path = tmp_path / "index.db"

  ensure_index_schema(db_path)

  with sqlite3.connect(db_path) as conn:
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

  assert {
    "index_metadata",
    "indexed_files",
    "code_chunks",
    "identifier_docs",
    "embeddings",
  } <= names


def test_index_store_round_trips_metadata_and_indexed_files(tmp_path: Path) -> None:
  store = IndexStore(tmp_path / "index.db")
  metadata = IndexMetadata("1", "ollama", "model-a", "1", "1", "ignore-1")
  records = [
    IndexedFileRecord("src/a.py", 10, 100, "hash-a"),
    IndexedFileRecord("src/b.py", 11, 200, "hash-b"),
  ]

  store.set_metadata(metadata)
  store.replace_indexed_files(records)

  assert store.load_metadata() == metadata
  assert store.load_indexed_files() == tuple(records)


def test_build_chunk_records_preserve_display_content_and_indexed_text() -> None:
  chunk = TextChunk(
    relative_path="app/main.py",
    start_line=3,
    end_line=4,
    content='def make_message() -> str:\n    return "hi"',
    kind="function",
  )
  symbol = SymbolInfo("function", "make_message", "def make_message() -> str", 3, 4)
  helper_symbol = SymbolInfo(
    "function",
    "refresh_index_state",
    "def refresh_index_state() -> str",
    6,
    7,
  )
  provider = resolve_embedding_provider("ollama", "model-a")

  records, _ = build_chunk_records(
    relative_path="app/main.py",
    chunks=[chunk],
    provider=provider,
    vectors=[[0.1, 0.2]],
    header_lines=("Main greeting module",),
    symbols=(symbol, helper_symbol),
  )

  assert records[0].content == chunk.content
  assert "Main greeting module" in records[0].indexed_text
  assert "make_message" in records[0].indexed_text
  assert "refresh_index_state" in records[0].indexed_text
  assert "app/main.py" in records[0].indexed_text
  assert records[0].symbol_text == "def make_message() -> str\nmake_message"
  assert records[0].path_text == "app/main.py"
  assert records[0].header_text == "Main greeting module"
  assert "refresh_index_state" in records[0].file_symbol_text
  assert records[0].local_symbol_text == "def make_message() -> str\nmake_message"
  assert records[0].body_text == chunk.content


def test_index_store_replaces_chunks_and_identifier_docs(tmp_path: Path) -> None:
  store = IndexStore(tmp_path / "index.db")
  store.replace_indexed_files([IndexedFileRecord("src/a.py", 10, 100, "hash-a")])
  store.replace_embeddings(
    [
      EmbeddingRecord("embed-1", "ollama", "model-a", "[0.1, 0.2]"),
      EmbeddingRecord("embed-2", "ollama", "model-a", "[0.3, 0.4]"),
      EmbeddingRecord("embed-3", "ollama", "model-a", "[0.5, 0.6]"),
    ]
  )
  first_chunk = CodeChunkRecord(
    "chunk-1",
    "src/a.py",
    1,
    3,
    "print('a')",
    "header\nprint('a')\nsrc/a.py",
    "print",
    "src/a.py",
    "header",
    "print",
    "print",
    "print('a')",
    "embed-1",
  )
  second_chunk = CodeChunkRecord(
    "chunk-2",
    "src/a.py",
    4,
    6,
    "print('b')",
    "header\nprint('b')\nsrc/a.py",
    "print",
    "src/a.py",
    "header",
    "print",
    "print",
    "print('b')",
    "embed-2",
  )
  identifier_doc = IdentifierDocumentRecord(
    "doc-1",
    "src/a.py",
    "Greeter",
    1,
    3,
    "class Greeter",
    "header\nGreeter\nclass Greeter\nsrc/a.py",
    "src/a.py",
    "header",
    "Greeter",
    "class Greeter",
    "header\nGreeter\nclass Greeter\nsrc/a.py",
    "embed-3",
  )

  store.replace_file_chunks("src/a.py", [first_chunk])
  store.replace_file_chunks("src/a.py", [second_chunk])
  store.replace_identifier_docs("src/a.py", [identifier_doc])

  assert store.load_code_chunks() == (second_chunk,)
  assert store.load_code_chunks_with_vectors() == ((second_chunk, [0.3, 0.4]),)
  assert store.load_identifier_docs() == (identifier_doc,)
  assert store.load_identifier_docs_with_vectors() == ((identifier_doc, [0.5, 0.6]),)
  assert store.load_code_chunks()[0].path_text == "src/a.py"
  assert store.load_code_chunks()[0].header_text == "header"
  assert store.load_identifier_docs()[0].symbol_name_text == "Greeter"
  assert store.load_identifier_docs()[0].signature_text == "class Greeter"

  with sqlite3.connect(tmp_path / "index.db") as conn:
    embedding_ids = {row[0] for row in conn.execute("SELECT embedding_id FROM embeddings")}

  assert embedding_ids == {"embed-2", "embed-3"}
