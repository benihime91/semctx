"""Semctx root CLI."""

from pathlib import Path

import click
import typer
from beartype import beartype

from semctx.commands.blast_radius_command import register_blast_radius_command
from semctx.commands.index_command import register_index_commands
from semctx.commands.search_code_command import register_search_code_command
from semctx.commands.search_identifiers_command import (
    register_search_identifiers_command,
)
from semctx.commands.skeleton_command import register_skeleton_command
from semctx.commands.tree_command import register_tree_command
from semctx.config.runtime_settings import build_runtime_settings

app = typer.Typer(help="semctx CLI", no_args_is_help=True)


@app.callback()
@beartype
def root(
    ctx: click.Context,
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    target_dir: Path = typer.Option(
        Path.cwd(),
        "--target-dir",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Directory whose contents are indexed and searched.",
    ),
    cache_dir: Path | None = typer.Option(
        None,
        "--cache-dir",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Cache directory.",
    ),
) -> None:
    """Build shared runtime settings for CLI commands."""
    ctx.obj = build_runtime_settings(
        target_dir=target_dir,
        cache_dir=cache_dir,
        json_output=json_output,
    )


@beartype
def main() -> None:
    """Run the semctx CLI."""
    app()


register_tree_command(app)
register_skeleton_command(app)
register_search_code_command(app)
register_search_identifiers_command(app)
register_blast_radius_command(app)
register_index_commands(app)
