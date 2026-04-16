"""Blast-radius command helpers."""

import click
import typer
from beartype import beartype

from semctx.commands.output_format import JsonObject, render_output
from semctx.commands.runtime_context import get_runtime_settings
from semctx.config.runtime_settings import RuntimeSettings
from semctx.tools.blast_radius import get_blast_radius, trace_blast_radius


@beartype
def run_blast_radius_command(
  runtime_settings: RuntimeSettings,
  symbol_name: str,
  file_context: str,
  depth_limit: int = 99,
) -> str:
  """Run the blast-radius command and return text output."""
  return get_blast_radius(
    root_dir=runtime_settings.root_dir,
    symbol_name=symbol_name,
    file_context=file_context,
    depth_limit=depth_limit,
  )


@beartype
def build_blast_radius_payload(
  runtime_settings: RuntimeSettings,
  symbol_name: str,
  file_context: str,
  depth_limit: int = 99,
) -> JsonObject:
  """Build the JSON payload for a blast-radius run."""
  report = trace_blast_radius(
    root_dir=runtime_settings.root_dir,
    symbol_name=symbol_name,
    file_context=file_context,
    depth_limit=depth_limit,
  )
  return {
    "command": "blast-radius",
    "definition": report.definition,
    "depth_limit": depth_limit,
    "file_context": report.file_context,
    "symbol_name": report.symbol_name,
    "usages": report.usages,
  }


@beartype
def register_blast_radius_command(app: typer.Typer) -> None:
  """Register the blast-radius command on the root CLI."""

  @app.command("blast-radius")
  @beartype
  def blast_radius_command(
    ctx: click.Context,
    symbol_name: str = typer.Argument(..., help="Symbol name to trace."),
    file_context: str = typer.Argument(..., help="Relative defining file path."),
    depth_limit: int = typer.Option(99, "--depth-limit", min=0, help="Directory depth limit."),
  ) -> None:
    """Trace external usages of a symbol from one defining file."""
    runtime_settings = get_runtime_settings(ctx)
    typer.echo(
      render_output(
        text_output=run_blast_radius_command(
          runtime_settings=runtime_settings,
          symbol_name=symbol_name,
          file_context=file_context,
          depth_limit=depth_limit,
        ),
        payload=build_blast_radius_payload(
          runtime_settings=runtime_settings,
          symbol_name=symbol_name,
          file_context=file_context,
          depth_limit=depth_limit,
        ),
        json_output=runtime_settings.json_output,
      )
    )
