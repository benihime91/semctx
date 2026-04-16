# Chunker unit tests.
# FEATURE: Code, markdown, and fallback chunking.
from pathlib import Path

from semctx.core.chunker import (
    build_code_chunks,
    build_markdown_chunks,
    build_text_chunks,
)


def test_build_code_chunks_uses_symbol_ranges(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        'class Greeter:\n    def greet(self) -> str:\n        return "hi"\n',
        encoding="utf-8",
    )

    chunks = build_code_chunks(file_path)

    assert [(chunk.kind, chunk.start_line, chunk.end_line) for chunk in chunks] == [
        ("class", 1, 3),
        ("function", 2, 3),
    ]
    assert (
        chunks[0].content
        == 'class Greeter:\n    def greet(self) -> str:\n        return "hi"'
    )


def test_build_markdown_chunks_splits_on_headings(tmp_path: Path) -> None:
    file_path = tmp_path / "guide.md"
    file_path.write_text(
        "# Overview\nIntro section.\n## Details\nMore detail here.\n",
        encoding="utf-8",
    )

    chunks = build_markdown_chunks(file_path)

    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [(1, 2), (3, 4)]
    assert [chunk.kind for chunk in chunks] == ["markdown", "markdown"]
    assert chunks[1].content.startswith("## Details")


def test_build_text_chunks_uses_bounded_paragraph_groups(tmp_path: Path) -> None:
    file_path = tmp_path / "notes.txt"
    file_path.write_text(
        "first short paragraph\n\nsecond short paragraph\n\nthird short paragraph\n",
        encoding="utf-8",
    )

    chunks = build_text_chunks(file_path, max_chars=30)

    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [
        (1, 1),
        (3, 3),
        (5, 5),
    ]
    assert [chunk.kind for chunk in chunks] == ["text", "text", "text"]
    assert all(len(chunk.content) <= 30 for chunk in chunks)


def test_build_text_chunks_splits_long_paragraphs_by_line(tmp_path: Path) -> None:
    file_path = tmp_path / "long.txt"
    file_path.write_text(
        "alpha alpha alpha\nbeta beta beta\ngamma gamma gamma\n",
        encoding="utf-8",
    )

    chunks = build_text_chunks(file_path, max_chars=20)

    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [
        (1, 1),
        (2, 2),
        (3, 3),
    ]
    assert all(len(chunk.content) <= 20 for chunk in chunks)


def test_build_code_chunks_go_uses_symbol_ranges(tmp_path: Path) -> None:
    file_path = tmp_path / "main.go"
    file_path.write_text(
        "package main\n\n"
        "type S struct {\n\tX int\n}\n\n"
        "func main() {\n}\n",
        encoding="utf-8",
    )

    chunks = build_code_chunks(file_path)

    assert [(chunk.kind, chunk.start_line, chunk.end_line) for chunk in chunks] == [
        ("struct", 3, 5),
        ("function", 7, 8),
    ]


def test_build_code_chunks_rust_uses_symbol_ranges(tmp_path: Path) -> None:
    file_path = tmp_path / "lib.rs"
    file_path.write_text(
        "pub struct Config {\n    x: i32,\n}\n\n"
        "pub fn run() {\n}\n",
        encoding="utf-8",
    )

    chunks = build_code_chunks(file_path)

    assert [(chunk.kind, chunk.start_line, chunk.end_line) for chunk in chunks] == [
        ("struct", 1, 3),
        ("function", 5, 6),
    ]


def test_build_code_chunks_kotlin_uses_symbol_ranges(tmp_path: Path) -> None:
    file_path = tmp_path / "Demo.kt"
    file_path.write_text(
        "package demo\n\n"
        "fun greet() {\n}\n\n"
        "object Singleton {\n}\n",
        encoding="utf-8",
    )

    chunks = build_code_chunks(file_path)

    assert [(chunk.kind, chunk.start_line, chunk.end_line) for chunk in chunks] == [
        ("function", 3, 4),
        ("object", 6, 7),
    ]
