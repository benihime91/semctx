"""Tree command helpers."""

import click
import typer
from beartype import beartype

from semctx.commands.output_format import JsonObject, render_output
from semctx.commands.runtime_context import get_runtime_settings
from semctx.config.runtime_settings import RuntimeSettings
from semctx.core.parser import analyze_file
from semctx.core.walker import walk_directory
from semctx.tools.context_tree import get_context_tree


@beartype
def run_tree_command(
    runtime_settings: RuntimeSettings,
    target_path: str = ".",
    depth_limit: int = 2,
    include_symbols: bool = True,
    max_tokens: int = 20_000,
) -> str:
    """Run the tree command and return text output."""
    return get_context_tree(
        root_dir=runtime_settings.root_dir,
        target_path=target_path,
        depth_limit=depth_limit,
        include_symbols=include_symbols,
        max_tokens=max_tokens,
    )


@beartype
def build_tree_payload(
    runtime_settings: RuntimeSettings,
    target_path: str = ".",
    depth_limit: int = 2,
    include_symbols: bool = True,
    max_tokens: int = 20_000,
) -> JsonObject:
    """Build the JSON payload for a tree run."""
    entries = walk_directory(
        root_dir=runtime_settings.root_dir,
        target_path=target_path,
        depth_limit=depth_limit,
    )
    directories = sorted(
        {
            parent.as_posix()
            for entry in entries
            for parent in entry.relative_path.parents
            if parent.as_posix() != "."
        }
    )
    files = []
    for entry in entries:
        analysis = analyze_file(entry.absolute_path)
        files.append(
            {
                "path": entry.relative_path,
                "language": analysis.language,
                "header_lines": analysis.header_lines,
                "symbols": analysis.symbols if include_symbols else (),
            }
        )
    return {
        "command": "tree",
        "depth_limit": depth_limit,
        "directories": directories,
        "files": files,
        "include_symbols": include_symbols,
        "max_tokens": max_tokens,
        "root": runtime_settings.root_dir.name,
        "target_path": target_path,
    }


@beartype
def register_tree_command(app: typer.Typer) -> None:
    """Register the tree command on the root CLI."""

    @app.command("tree")
    @beartype
    def tree_command(
        ctx: click.Context,
        target_path: str = typer.Argument(".", help="Relative path to inspect."),
        depth_limit: int = typer.Option(
            2, "--depth-limit", min=0, help="Directory depth limit."
        ),
        include_symbols: bool = typer.Option(
            True, "--include-symbols/--no-symbols", help="Include parsed symbols."
        ),
        max_tokens: int = typer.Option(
            20_000, "--max-tokens", min=1, help="Approximate output token budget."
        ),
    ) -> None:
        """Render a context tree for the requested path."""
        runtime_settings = get_runtime_settings(ctx)
        text_output = run_tree_command(
            runtime_settings=runtime_settings,
            target_path=target_path,
            depth_limit=depth_limit,
            include_symbols=include_symbols,
            max_tokens=max_tokens,
        )
        typer.echo(
            render_output(
                text_output=text_output,
                payload=build_tree_payload(
                    runtime_settings=runtime_settings,
                    target_path=target_path,
                    depth_limit=depth_limit,
                    include_symbols=include_symbols,
                    max_tokens=max_tokens,
                ),
                json_output=runtime_settings.json_output,
            )
        )
