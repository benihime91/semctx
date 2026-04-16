"""Context tree renderer."""

from pathlib import Path

from beartype import beartype

from semctx.core.parser import analyze_file
from semctx.core.walker import walk_directory


@beartype
def get_context_tree(
    root_dir: Path,
    target_path: str = ".",
    depth_limit: int = 2,
    include_symbols: bool = True,
    max_tokens: int = 20_000,
) -> str:
    """Render a context tree within the requested token budget."""
    entries = walk_directory(
        root_dir=root_dir, target_path=target_path, depth_limit=depth_limit
    )
    render_modes = [
        {"include_headers": True, "include_symbols": include_symbols},
        {"include_headers": True, "include_symbols": False},
        {"include_headers": False, "include_symbols": False},
    ]
    rendered_output = ""
    for render_mode in render_modes:
        rendered_output = _render_tree(
            root_dir=root_dir.resolve(),
            entries=entries,
            include_headers=bool(render_mode["include_headers"]),
            include_symbols=bool(render_mode["include_symbols"]),
        )
        if _estimate_token_count(rendered_output) <= max_tokens:
            return rendered_output
    return rendered_output


@beartype
def _render_tree(
    root_dir: Path, entries: list, include_headers: bool, include_symbols: bool
) -> str:
    """Render one context tree mode."""
    lines = [f"{root_dir.name}/"]
    file_analyses = {
        entry.relative_path: analyze_file(entry.absolute_path) for entry in entries
    }
    seen_directories: set[Path] = set()
    for entry in entries:
        for directory in entry.relative_path.parents[::-1]:
            if directory == Path(".") or directory in seen_directories:
                continue
            seen_directories.add(directory)
            lines.append(f"{_indent(directory)}{directory.name}/")
        lines.append(f"{_indent(entry.relative_path)}{entry.relative_path.name}")
        analysis = file_analyses[entry.relative_path]
        if include_headers and analysis.header_lines:
            header_text = " | ".join(analysis.header_lines)
            lines.append(
                f"{_indent(entry.relative_path, extra_levels=1)}header: {header_text}"
            )
        if include_symbols:
            for symbol in analysis.symbols:
                lines.append(
                    f"{_indent(entry.relative_path, extra_levels=1)}{symbol.kind} {symbol.name} [{symbol.line_start}-{symbol.line_end}]"
                )
    return "\n".join(lines)


@beartype
def _estimate_token_count(content: str) -> int:
    """Estimate token count with a simple word split."""
    return max(1, len(content.split()))


@beartype
def _indent(relative_path: Path, extra_levels: int = 0) -> str:
    """Build indentation for one relative path line."""
    depth = len(relative_path.parts) - 1 + extra_levels
    return "  " * max(depth + 1, 1)
