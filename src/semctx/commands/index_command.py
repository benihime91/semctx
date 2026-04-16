"""Index command helpers."""

import click
import typer
from beartype import beartype

from semctx.commands.output_format import JsonObject, render_error, render_output
from semctx.commands.runtime_context import build_command_runtime_settings
from semctx.tools.index_lifecycle import (
    DEFAULT_INDEX_DEPTH_LIMIT,
    clear_index,
    get_index_db_path,
    init_index,
    refresh_index,
    render_index_status,
    status_index,
)

index_app = typer.Typer(
    help="Build and maintain the local search index.", no_args_is_help=True
)
__all__ = ["register_index_commands", "render_index_status"]


@beartype
def register_index_commands(app: typer.Typer) -> None:
    """Register the index command group on the root CLI."""
    app.add_typer(index_app, name="index")


@index_app.command("init")
@beartype
def init_command(
    ctx: click.Context,
    model: str | None = typer.Option(
        None,
        "--model",
        help="Embedding model override as provider/model.",
    ),
    target_dir: str | None = typer.Option(
        None, "--target-dir", help="Directory whose contents are indexed."
    ),
    depth_limit: int = typer.Option(
        DEFAULT_INDEX_DEPTH_LIMIT, "--depth-limit", min=0, help="Directory depth limit."
    ),
) -> None:
    """Build a fresh local search index."""
    runtime_settings = build_command_runtime_settings(ctx, target_dir)
    status = init_index(
        runtime_settings,
        model=model,
        depth_limit=depth_limit,
    )
    typer.echo(
        render_output(
            f"Index initialized.\n{render_index_status(status)}",
            {"command": "index", "status": status, "subcommand": "init"},
            runtime_settings.json_output,
        )
    )


@index_app.command("status")
@beartype
def status_command(
    ctx: click.Context,
    model: str | None = typer.Option(
        None,
        "--model",
        help="Embedding model override as provider/model.",
    ),
    target_dir: str | None = typer.Option(
        None, "--target-dir", help="Directory whose index status to inspect."
    ),
    depth_limit: int = typer.Option(
        DEFAULT_INDEX_DEPTH_LIMIT, "--depth-limit", min=0, help="Directory depth limit."
    ),
) -> None:
    """Show current local index status."""
    runtime_settings = build_command_runtime_settings(ctx, target_dir)
    status = status_index(runtime_settings, model=model, depth_limit=depth_limit)
    typer.echo(
        render_output(
            render_index_status(status),
            {"command": "index", "status": status, "subcommand": "status"},
            runtime_settings.json_output,
        )
    )


@index_app.command("refresh")
@beartype
def refresh_command(
    ctx: click.Context,
    model: str | None = typer.Option(
        None,
        "--model",
        help="Embedding model override as provider/model.",
    ),
    target_dir: str | None = typer.Option(
        None, "--target-dir", help="Directory whose contents are refreshed."
    ),
    depth_limit: int = typer.Option(
        DEFAULT_INDEX_DEPTH_LIMIT, "--depth-limit", min=0, help="Directory depth limit."
    ),
    full: bool = typer.Option(False, "--full", help="Rebuild the entire index."),
) -> None:
    """Refresh the local index or rebuild it fully."""
    runtime_settings = build_command_runtime_settings(ctx, target_dir)
    try:
        status = refresh_index(
            runtime_settings,
            model=model,
            depth_limit=depth_limit,
            full=full,
        )
    except FileNotFoundError as error:
        _exit_with_error(
            runtime_settings.json_output, "index", str(error), "index_not_found"
        )
    except ValueError as error:
        _exit_with_error(
            runtime_settings.json_output, "index", str(error), "full_rebuild_required"
        )
    label = "Index rebuilt." if full else "Index refreshed."
    typer.echo(
        render_output(
            f"{label}\n{render_index_status(status)}",
            {"command": "index", "status": status, "subcommand": "refresh"},
            runtime_settings.json_output,
        )
    )


@index_app.command("clear")
@beartype
def clear_command(ctx: click.Context) -> None:
    """Remove the local search index database when present."""
    runtime_settings = build_command_runtime_settings(ctx)
    cleared = clear_index(runtime_settings)
    db_path = get_index_db_path(runtime_settings.cache_dir)
    text_output = "Index cleared." if cleared else "No index found."
    payload: JsonObject = {
        "cleared": cleared,
        "command": "index",
        "db_path": db_path,
        "subcommand": "clear",
    }
    typer.echo(render_output(text_output, payload, runtime_settings.json_output))


@beartype
def _exit_with_error(json_output: bool, command: str, message: str, error: str) -> None:
    """Render a CLI error and exit with a non-zero status."""
    if json_output:
        typer.echo(render_error(command, error, message))
    else:
        typer.echo(message)
    raise typer.Exit(code=1)
