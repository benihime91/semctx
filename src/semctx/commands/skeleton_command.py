"""Skeleton command helpers."""

import click
import typer
from beartype import beartype

from semctx.commands.output_format import JsonObject, render_output
from semctx.commands.runtime_context import get_runtime_settings
from semctx.config.runtime_settings import RuntimeSettings
from semctx.core.parser import analyze_file
from semctx.tools.file_skeleton import get_file_skeleton


@beartype
def run_skeleton_command(runtime_settings: RuntimeSettings, file_path: str) -> str:
  """Run the skeleton command and return text output."""
  return get_file_skeleton(root_dir=runtime_settings.root_dir, file_path=file_path)


@beartype
def build_skeleton_payload(runtime_settings: RuntimeSettings, file_path: str) -> JsonObject:
  """Build the JSON payload for a skeleton run."""
  analysis = analyze_file((runtime_settings.root_dir / file_path).resolve())
  return {
    "command": "skeleton",
    "file": {
      "header_lines": analysis.header_lines,
      "language": analysis.language,
      "path": analysis.file_path.relative_to(runtime_settings.root_dir),
      "symbols": analysis.symbols,
    },
  }


@beartype
def register_skeleton_command(app: typer.Typer) -> None:
  """Register the skeleton command on the root CLI."""

  @app.command("skeleton")
  @beartype
  def skeleton_command(
    ctx: click.Context,
    file_path: str = typer.Argument(..., help="Relative file path to inspect."),
  ) -> None:
    """Show parsed headers and symbols for one file."""
    runtime_settings = get_runtime_settings(ctx)
    typer.echo(
      render_output(
        text_output=run_skeleton_command(runtime_settings=runtime_settings, file_path=file_path),
        payload=build_skeleton_payload(runtime_settings=runtime_settings, file_path=file_path),
        json_output=runtime_settings.json_output,
      )
    )
