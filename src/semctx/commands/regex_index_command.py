"""Regex-index command group."""

import click
import typer
from beartype import beartype

from semctx.commands.output_format import JsonObject, render_output
from semctx.commands.regex_index_command_support import exit_with_regex_index_error
from semctx.commands.runtime_context import build_command_runtime_settings
from semctx.tools.regex_index_lifecycle import (
  DEFAULT_REGEX_INDEX_DEPTH_LIMIT,
  clear_regex_index,
  init_regex_index,
  refresh_regex_index,
  status_regex_index,
)
from semctx.tools.regex_index_status import RegexIndexStatus, render_regex_index_status

regex_index_app = typer.Typer(
  help="Build and maintain the local regex candidate-prefilter index.",
  no_args_is_help=True,
)


@beartype
def register_regex_index_command(app: typer.Typer) -> None:
  """Register the regex-index command group on the root CLI."""
  app.add_typer(regex_index_app, name="regex-index")


@regex_index_app.command("init")
@beartype
def init_command(
  ctx: click.Context,
  target_dir: str | None = typer.Option(None, "--target-dir", help="Directory whose contents are indexed."),
  depth_limit: int = typer.Option(DEFAULT_REGEX_INDEX_DEPTH_LIMIT, "--depth-limit", min=0, help="Directory depth limit."),
) -> None:
  """Build a fresh regex candidate-prefilter index."""
  runtime_settings = build_command_runtime_settings(ctx, target_dir)
  try:
    status = init_regex_index(runtime_settings, depth_limit=depth_limit)
  except Exception as error:
    exit_with_regex_index_error(runtime_settings.json_output, str(error), "regex_index_error")
  typer.echo(render_output(f"Regex index initialized.\n{render_regex_index_status(status)}", _build_status_payload("init", status), runtime_settings.json_output))


@regex_index_app.command("status")
@beartype
def status_command(
  ctx: click.Context,
  target_dir: str | None = typer.Option(None, "--target-dir", help="Directory whose regex-index status to inspect."),
  depth_limit: int = typer.Option(DEFAULT_REGEX_INDEX_DEPTH_LIMIT, "--depth-limit", min=0, help="Directory depth limit."),
) -> None:
  """Show current regex-index status."""
  runtime_settings = build_command_runtime_settings(ctx, target_dir)
  try:
    status = status_regex_index(runtime_settings, depth_limit=depth_limit)
  except Exception as error:
    exit_with_regex_index_error(runtime_settings.json_output, str(error), "regex_index_error")
  typer.echo(render_output(render_regex_index_status(status), _build_status_payload("status", status), runtime_settings.json_output))


@regex_index_app.command("refresh")
@beartype
def refresh_command(
  ctx: click.Context,
  target_dir: str | None = typer.Option(None, "--target-dir", help="Directory whose contents are refreshed."),
  depth_limit: int = typer.Option(DEFAULT_REGEX_INDEX_DEPTH_LIMIT, "--depth-limit", min=0, help="Directory depth limit."),
  full: bool = typer.Option(False, "--full", help="Rebuild the regex index from scratch."),
) -> None:
  """Refresh the regex index incrementally or fully."""
  runtime_settings = build_command_runtime_settings(ctx, target_dir)
  try:
    status = refresh_regex_index(runtime_settings, depth_limit=depth_limit, full=full)
  except Exception as error:
    exit_with_regex_index_error(runtime_settings.json_output, str(error), "regex_index_error")
  label = "Regex index rebuilt." if full else "Regex index refreshed."
  typer.echo(render_output(f"{label}\n{render_regex_index_status(status)}", _build_status_payload("refresh", status), runtime_settings.json_output))


@regex_index_app.command("clear")
@beartype
def clear_command(
  ctx: click.Context,
  target_dir: str | None = typer.Option(None, "--target-dir", help="Directory whose regex index should be cleared."),
  depth_limit: int = typer.Option(DEFAULT_REGEX_INDEX_DEPTH_LIMIT, "--depth-limit", min=0, help="Directory depth limit."),
  clear_all: bool = typer.Option(False, "--all", help="Remove all regex-index artifacts under the cache root."),
) -> None:
  """Remove the regex index for this workspace or all regex-index artifacts."""
  del depth_limit
  runtime_settings = build_command_runtime_settings(ctx, target_dir)
  cleared = clear_regex_index(runtime_settings, clear_all=clear_all)
  text_output = "Regex index cleared." if cleared else "No regex index found."
  payload: JsonObject = {
    "command": "regex-index",
    "subcommand": "clear",
    "cleared": cleared,
    "clear_all": clear_all,
  }
  typer.echo(render_output(text_output, payload, runtime_settings.json_output))


@beartype
def _build_status_payload(subcommand: str, status: RegexIndexStatus) -> JsonObject:
  """Build the shared JSON payload for regex-index status commands."""
  return {
    "command": "regex-index",
    "subcommand": subcommand,
    "status": {
      "exists": status.exists,
      "indexed_file_count": status.indexed_file_count,
      "current_file_count": status.current_file_count,
      "stale_file_count": status.stale_file_count,
      "missing_from_index_count": status.missing_from_index_count,
      "missing_on_disk_count": status.missing_on_disk_count,
      "schema_version": status.schema_version,
      "stale": status.stale,
    },
  }
