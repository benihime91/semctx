"""File skeleton renderer."""

from pathlib import Path

from beartype import beartype

from semctx.core.parser import analyze_file


@beartype
def get_file_skeleton(root_dir: Path, file_path: str) -> str:
    """Render parsed headers and symbols for one file."""
    resolved_root_dir = root_dir.resolve()
    resolved_file_path = (resolved_root_dir / file_path).resolve()
    analysis = analyze_file(resolved_file_path)
    relative_path = analysis.file_path.relative_to(resolved_root_dir)
    lines = [f"file: {relative_path.as_posix()}", f"language: {analysis.language}"]
    if analysis.header_lines:
        lines.append("header:")
        for header_line in analysis.header_lines:
            lines.append(f"  - {header_line}")
    if analysis.symbols:
        lines.append("symbols:")
        for symbol in analysis.symbols:
            lines.append(
                f"  - {symbol.kind} {symbol.name} [{symbol.line_start}-{symbol.line_end}] :: {symbol.signature}"
            )
    else:
        lines.append("symbols: none")
    return "\n".join(lines)
