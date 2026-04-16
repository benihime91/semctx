"""Parser data models."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SymbolInfo:
    """Describe one parsed symbol."""

    kind: str
    name: str
    signature: str
    line_start: int
    line_end: int


@dataclass(frozen=True)
class FileAnalysis:
    """Store parsed file metadata and symbols."""

    file_path: Path
    language: str
    header_lines: tuple[str, ...]
    symbols: tuple[SymbolInfo, ...]
