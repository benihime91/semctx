"""Index command helpers."""

import click
import typer
from beartype import beartype

from semctx.commands.model_selection_contract import (
  CommandContractError,
  ExplicitModelRequiredError,
  InvalidCommandSelectionError,
  require_explicit_model,
  validate_clear_selection,
)
from semctx.commands.output_format import JsonObject, render_error, render_output
from semctx.commands.runtime_context import build_command_runtime_settings
from semctx.core.embedding_provider import resolve_explicit_embedding_provider
from semctx.tools.index_lifecycle import (
  DEFAULT_INDEX_DEPTH_LIMIT,
  clear_index,
  get_all_index_db_paths,
  get_index_db_path,
  init_index,
  refresh_index,
  render_index_status,
  status_index,
)

index_app = typer.Typer(help="Build and maintain the local search index.", no_args_is_help=True)
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
    help="Required embedding model selector as provider/model.",
  ),
  target_dir: str | None = typer.Option(None, "--target-dir", help="Directory whose contents are indexed."),
  depth_limit: int = typer.Option(DEFAULT_INDEX_DEPTH_LIMIT, "--depth-limit", min=0, help="Directory depth limit."),
) -> None:
  """Build a fresh local search index."""
  runtime_settings = build_command_runtime_settings(ctx, target_dir)
  try:
    status = init_index(
      runtime_settings,
      model=require_explicit_model(model, "index init"),
      depth_limit=depth_limit,
    )
  except ExplicitModelRequiredError as error:
    _exit_with_error(runtime_settings.json_output, "index", str(error), "explicit_model_required")
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
    help="Required embedding model selector as provider/model.",
  ),
  target_dir: str | None = typer.Option(None, "--target-dir", help="Directory whose index status to inspect."),
  depth_limit: int = typer.Option(DEFAULT_INDEX_DEPTH_LIMIT, "--depth-limit", min=0, help="Directory depth limit."),
) -> None:
  """Show current local index status."""
  runtime_settings = build_command_runtime_settings(ctx, target_dir)
  try:
    status = status_index(runtime_settings, model=require_explicit_model(model, "index status"), depth_limit=depth_limit)
  except ExplicitModelRequiredError as error:
    _exit_with_error(runtime_settings.json_output, "index", str(error), "explicit_model_required")
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
    help="Required embedding model selector as provider/model.",
  ),
  target_dir: str | None = typer.Option(None, "--target-dir", help="Directory whose contents are refreshed."),
  depth_limit: int = typer.Option(DEFAULT_INDEX_DEPTH_LIMIT, "--depth-limit", min=0, help="Directory depth limit."),
  full: bool = typer.Option(False, "--full", help="Rebuild the entire index."),
) -> None:
  """Refresh the local index or rebuild it fully."""
  runtime_settings = build_command_runtime_settings(ctx, target_dir)
  try:
    status = refresh_index(
      runtime_settings,
      model=require_explicit_model(model, "index refresh"),
      depth_limit=depth_limit,
      full=full,
    )
  except ExplicitModelRequiredError as error:
    _exit_with_error(runtime_settings.json_output, "index", str(error), "explicit_model_required")
  except FileNotFoundError as error:
    _exit_with_error(runtime_settings.json_output, "index", str(error), "index_not_found")
  except ValueError as error:
    _exit_with_error(runtime_settings.json_output, "index", str(error), "full_rebuild_required")
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
def clear_command(
  ctx: click.Context,
  model: str | None = typer.Option(
    None,
    "--model",
    help="Required embedding model selector as provider/model unless `--all` is passed.",
  ),
  clear_all: bool = typer.Option(False, "--all", help="Clear all namespaced index databases."),
) -> None:
  """Remove the local search index database when present."""
  runtime_settings = build_command_runtime_settings(ctx)
  cleared_paths = get_all_index_db_paths(runtime_settings.cache_dir) if clear_all else ()
  try:
    selected_model = validate_clear_selection(model, clear_all)
    cleared = clear_index(runtime_settings, model=selected_model, clear_all=clear_all)
  except ExplicitModelRequiredError as error:
    _exit_with_error(runtime_settings.json_output, "index", str(error), "explicit_model_required")
  except InvalidCommandSelectionError as error:
    _exit_with_error(runtime_settings.json_output, "index", str(error), "invalid_arguments")
  db_path = None if clear_all else get_index_db_path(runtime_settings.cache_dir, resolve_explicit_embedding_provider(None, selected_model))
  text_output = "Index cleared." if cleared else "No index found."
  payload: JsonObject = {
    "cleared": cleared,
    "command": "index",
    "subcommand": "clear",
  }
  if clear_all:
    payload["cleared_paths"] = cleared_paths
  else:
    payload["db_path"] = db_path
  typer.echo(render_output(text_output, payload, runtime_settings.json_output))


@beartype
def _exit_with_error(json_output: bool, command: str, message: str, error: str) -> None:
  """Render a CLI error and exit with a non-zero status."""
  if json_output:
    typer.echo(render_error(command, error, message))
  else:
    typer.echo(message)
  raise typer.Exit(code=1)
