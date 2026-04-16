"""File parser helpers."""

from pathlib import Path

from beartype import beartype

from semctx.core.parser_models import FileAnalysis, SymbolInfo
from semctx.core.tree_sitter_runtime import extract_symbols_with_tree_sitter

SUPPORTED_LANGUAGES = {
  ".go": "go",
  ".js": "javascript",
  ".jsx": "javascript",
  ".kt": "kotlin",
  ".kts": "kotlin",
  ".py": "python",
  ".rs": "rust",
  ".ts": "typescript",
  ".tsx": "typescript",
}


@beartype
def extract_header_lines(content: str) -> list[str]:
  """Extract the first header comment lines from a file."""
  header_lines: list[str] = []
  for raw_line in content.splitlines()[:2]:
    stripped_line = raw_line.strip()
    if stripped_line.startswith("#"):
      header_lines.append(stripped_line.lstrip("# "))
    elif stripped_line.startswith("//"):
      header_lines.append(stripped_line.lstrip("/ "))
  return header_lines


@beartype
def analyze_file(file_path: Path) -> FileAnalysis:
  """Analyze one file for headers, language, and symbols."""
  resolved_file_path = file_path.resolve()
  content = resolved_file_path.read_text()
  suffix = resolved_file_path.suffix.lower()
  language = SUPPORTED_LANGUAGES.get(suffix, "text")
  header_lines = tuple(extract_header_lines(content))
  symbols = tuple(_extract_symbols(language, resolved_file_path))
  return FileAnalysis(
    file_path=resolved_file_path,
    language=language,
    header_lines=header_lines,
    symbols=symbols,
  )


@beartype
def _extract_symbols(language: str, file_path: Path) -> list[SymbolInfo]:
  """Extract symbols using tree-sitter."""
  tree_sitter_symbols = extract_symbols_with_tree_sitter(file_path, language)
  return [
    SymbolInfo(
      kind=str(symbol["kind"]),
      name=str(symbol["name"]),
      signature=str(symbol["signature"]),
      line_start=_coerce_line_number(symbol["line_start"]),
      line_end=_coerce_line_number(symbol["line_end"]),
    )
    for symbol in tree_sitter_symbols
  ]


@beartype
def _coerce_line_number(value: object) -> int:
  """Normalize a tree-sitter line number to an integer."""
  if isinstance(value, int):
    return value
  if isinstance(value, float):
    return int(value)
  if isinstance(value, str):
    return int(value)
  raise ValueError(f"Unsupported line number value: {value!r}")
