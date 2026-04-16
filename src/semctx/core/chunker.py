"""Chunking helpers."""

from dataclasses import dataclass
import re
from pathlib import Path

from beartype import beartype

from semctx.core.parser import analyze_file
from semctx.core.chunker_sections import build_markdown_sections, build_paragraphs

CODE_SUFFIXES = frozenset({".go", ".js", ".jsx", ".kt", ".kts", ".py", ".rs", ".ts", ".tsx"})
MARKDOWN_SUFFIXES = frozenset({".markdown", ".md", ".mdx"})
MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+\S")
DEFAULT_TEXT_CHUNK_CHARS = 600


@dataclass(frozen=True)
class TextChunk:
  """Describe one indexed text chunk."""

  relative_path: str
  start_line: int
  end_line: int
  content: str
  kind: str


@beartype
def build_chunks(file_path: Path, relative_path: str | None = None) -> list[TextChunk]:
  """Build chunks using code, markdown, or fallback text rules."""
  suffix = file_path.suffix.lower()
  if suffix in CODE_SUFFIXES:
    return build_code_chunks(file_path, relative_path=relative_path)
  if suffix in MARKDOWN_SUFFIXES:
    return build_markdown_chunks(file_path, relative_path=relative_path)
  return build_text_chunks(file_path, relative_path=relative_path)


@beartype
def build_code_chunks(file_path: Path, relative_path: str | None = None) -> list[TextChunk]:
  """Build chunks aligned to parsed symbols when possible."""
  resolved_file_path = file_path.resolve()
  analysis = analyze_file(resolved_file_path)
  if not analysis.symbols:
    return build_text_chunks(resolved_file_path, relative_path=relative_path)
  lines = resolved_file_path.read_text(encoding="utf-8").splitlines()
  chunk_path = _resolve_relative_path(resolved_file_path, relative_path)
  return [
    TextChunk(
      relative_path=chunk_path,
      start_line=symbol.line_start,
      end_line=symbol.line_end,
      content="\n".join(lines[symbol.line_start - 1 : symbol.line_end]).strip(),
      kind=symbol.kind,
    )
    for symbol in analysis.symbols
  ]


@beartype
def build_markdown_chunks(file_path: Path, relative_path: str | None = None) -> list[TextChunk]:
  """Build chunks from markdown headings."""
  resolved_file_path = file_path.resolve()
  lines = resolved_file_path.read_text(encoding="utf-8").splitlines()
  sections = build_markdown_sections(lines, MARKDOWN_HEADING_PATTERN)
  if not sections:
    return build_text_chunks(resolved_file_path, relative_path=relative_path)
  chunk_path = _resolve_relative_path(resolved_file_path, relative_path)
  return [
    TextChunk(
      relative_path=chunk_path,
      start_line=start_line,
      end_line=end_line,
      content="\n".join(lines[start_line - 1 : end_line]).strip(),
      kind="markdown",
    )
    for start_line, end_line in sections
  ]


@beartype
def build_text_chunks(
  file_path: Path,
  relative_path: str | None = None,
  max_chars: int = DEFAULT_TEXT_CHUNK_CHARS,
) -> list[TextChunk]:
  """Build fallback text chunks from paragraph-like sections."""
  resolved_file_path = file_path.resolve()
  lines = resolved_file_path.read_text(encoding="utf-8").splitlines()
  paragraphs = build_paragraphs(lines, max_chars)
  chunk_path = _resolve_relative_path(resolved_file_path, relative_path)
  chunks: list[TextChunk] = []
  current_start = 0
  current_end = 0
  current_parts: list[str] = []
  for start_line, end_line, content in paragraphs:
    proposed_content = "\n\n".join([*current_parts, content]) if current_parts else content
    if current_parts and len(proposed_content) > max_chars:
      chunks.append(
        TextChunk(
          relative_path=chunk_path,
          start_line=current_start,
          end_line=current_end,
          content="\n\n".join(current_parts),
          kind="text",
        )
      )
      current_parts = [content]
      current_start = start_line
      current_end = end_line
      continue
    if not current_parts:
      current_start = start_line
    current_parts.append(content)
    current_end = end_line
  if current_parts:
    chunks.append(
      TextChunk(
        relative_path=chunk_path,
        start_line=current_start,
        end_line=current_end,
        content="\n\n".join(current_parts),
        kind="text",
      )
    )
  return chunks or [
    TextChunk(
      relative_path=chunk_path,
      start_line=1,
      end_line=max(1, len(lines)),
      content="\n".join(lines).strip(),
      kind="text",
    )
  ]


@beartype
def _resolve_relative_path(file_path: Path, relative_path: str | None) -> str:
  """Resolve the stored relative path for a chunk."""
  if relative_path is not None:
    return relative_path
  return file_path.name
