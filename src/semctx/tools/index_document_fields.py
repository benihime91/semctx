"""Index document field helpers."""

from beartype import beartype

from semctx.core.chunker import TextChunk
from semctx.core.parser_models import SymbolInfo


@beartype
def build_chunk_fields(
    relative_path: str,
    chunk: TextChunk,
    header_lines: tuple[str, ...],
    symbols: tuple[SymbolInfo, ...],
) -> tuple[str, str, str, str, str]:
    """Build stored field text for one code chunk."""
    header_text = "\n".join(header_lines)
    file_symbol_text = build_file_symbol_text(symbols)
    symbol = find_chunk_symbol(chunk, symbols)
    local_symbol_text = join_text_parts(symbol.signature, symbol.name) if symbol else ""
    return (
        relative_path,
        header_text,
        file_symbol_text,
        local_symbol_text,
        chunk.content,
    )


@beartype
def build_identifier_fields(
    relative_path: str, symbol: SymbolInfo, header_lines: tuple[str, ...]
) -> tuple[str, str, str, str, str]:
    """Build stored field text for one identifier."""
    header_text = "\n".join(header_lines)
    return (
        relative_path,
        header_text,
        symbol.name,
        symbol.signature,
        join_text_parts(header_text, symbol.name, symbol.signature, relative_path),
    )


def find_chunk_symbol(
    chunk: TextChunk, symbols: tuple[SymbolInfo, ...]
) -> SymbolInfo | None:
    """Find the symbol that best matches one chunk range."""
    for symbol in symbols:
        if symbol.line_start == chunk.start_line and symbol.line_end == chunk.end_line:
            return symbol
    for symbol in symbols:
        if symbol.line_start <= chunk.start_line <= chunk.end_line <= symbol.line_end:
            return symbol
    return None


def build_file_symbol_text(symbols: tuple[SymbolInfo, ...]) -> str:
    """Build deduplicated symbol text for one file."""
    return join_text_parts(
        *dict.fromkeys(
            part
            for symbol in symbols
            for part in (symbol.signature, symbol.name)
            if part
        )
    )


def join_text_parts(*parts: str) -> str:
    """Join non-empty text parts with stable newlines."""
    return "\n".join(part for part in parts if part)
