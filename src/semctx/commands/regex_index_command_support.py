"""Shared CLI helpers for the regex-index command group."""

import typer
from beartype import beartype

from semctx.commands.output_format import render_error


@beartype
def exit_with_regex_index_error(
  json_output: bool,
  message: str,
  error: str,
) -> None:
  """Render a regex-index CLI error (`regex_index_error` or `invalid_arguments`) and exit non-zero."""
  if json_output:
    typer.echo(render_error("regex-index", error, message))
  else:
    typer.echo(message)
  raise typer.Exit(code=1)
