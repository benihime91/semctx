"""Support helpers for grep command validation and rendering."""

import typer
from beartype import beartype

from semctx.commands.output_format import JsonValue, render_error
from semctx.tools.grep_search import GrepMatch, GrepSearchResult


class InvalidGrepArgumentsError(ValueError):
  """Raised when grep receives an invalid option combination."""


@beartype
def validate_grep_arguments(*, code_only: bool, text_only: bool) -> None:
  """Validate grep-specific argument combinations."""
  if code_only and text_only:
    raise InvalidGrepArgumentsError("`--code-only` and `--text-only` cannot be used together.")


@beartype
def render_grep_matches(result: GrepSearchResult, summary_only: bool) -> str:
  """Render grep matches as plain text."""
  if result.match_count == 0:
    return "No matches found."
  if summary_only:
    return f"{result.match_count} match(es) found."
  return "\n".join(_render_grep_match(match) for match in result.matches)


def _render_grep_match(match: GrepMatch) -> str:
  """Render one grep match as plain text."""
  lines = [f"{match.relative_path.as_posix()}:{match.line_number} :: {match.line_text}"]
  for line in match.context_before:
    lines.append(f"  before: {line}")
  for line in match.context_after:
    lines.append(f"  after: {line}")
  return "\n".join(lines)


@beartype
def exit_with_error(
  json_output: bool,
  command: str,
  message: str,
  error: str,
  details: JsonValue | None = None,
) -> None:
  """Render a CLI error and exit with a non-zero status."""
  if json_output:
    typer.echo(render_error(command, error, message, details=details))
  else:
    typer.echo(message)
  raise typer.Exit(code=1)
