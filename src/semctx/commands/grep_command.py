"""Grep command helpers."""

import click
import typer
from beartype import beartype

from semctx.commands.grep_command_support import (
  InvalidGrepArgumentsError,
  exit_with_error,
  render_grep_matches,
  validate_grep_arguments,
)
from semctx.commands.output_format import JsonObject, render_output
from semctx.commands.runtime_context import (
  build_command_runtime_settings,
  get_effective_target_dir_label,
)
from semctx.config.runtime_settings import RuntimeSettings
from semctx.tools.grep_search import DEFAULT_GREP_DEPTH_LIMIT, InvalidRegexPatternError, grep_search


@beartype
def run_grep_command(
  runtime_settings: RuntimeSettings,
  pattern: str,
  target_dir: str | None = None,
  depth_limit: int = DEFAULT_GREP_DEPTH_LIMIT,
  ignore_case: bool = False,
  fixed_strings: bool = False,
  max_count: int | None = None,
  before_context: int = 0,
  after_context: int = 0,
  context: int = 0,
  include: tuple[str, ...] = (),
  exclude: tuple[str, ...] = (),
  code_only: bool = False,
  text_only: bool = False,
  summary_only: bool = False,
) -> str:
  """Run the grep command and return text output."""
  return _build_grep_outputs(
    runtime_settings,
    pattern,
    target_dir,
    depth_limit,
    ignore_case,
    fixed_strings,
    max_count,
    before_context,
    after_context,
    context,
    include,
    exclude,
    code_only,
    text_only,
    summary_only,
  )[0]


@beartype
def build_grep_payload(
  runtime_settings: RuntimeSettings,
  pattern: str,
  target_dir: str | None = None,
  depth_limit: int = DEFAULT_GREP_DEPTH_LIMIT,
  ignore_case: bool = False,
  fixed_strings: bool = False,
  max_count: int | None = None,
  before_context: int = 0,
  after_context: int = 0,
  context: int = 0,
  include: tuple[str, ...] = (),
  exclude: tuple[str, ...] = (),
  code_only: bool = False,
  text_only: bool = False,
  summary_only: bool = False,
) -> JsonObject:
  """Build the JSON payload for a grep run."""
  return _build_grep_outputs(
    runtime_settings,
    pattern,
    target_dir,
    depth_limit,
    ignore_case,
    fixed_strings,
    max_count,
    before_context,
    after_context,
    context,
    include,
    exclude,
    code_only,
    text_only,
    summary_only,
  )[1]


@beartype
def register_grep_command(app: typer.Typer) -> None:
  """Register the grep command on the root CLI."""

  @app.command("grep")
  @beartype
  def grep_command(
    ctx: click.Context,
    pattern: str = typer.Argument(..., help="Regex pattern to search for."),
    target_dir: str | None = typer.Option(None, "--target-dir", help="Directory whose contents are searched."),
    depth_limit: int = typer.Option(DEFAULT_GREP_DEPTH_LIMIT, "--depth-limit", min=0, help="Directory depth limit."),
    ignore_case: bool = typer.Option(False, "--ignore-case", help="Match without case sensitivity."),
    fixed_strings: bool = typer.Option(False, "--fixed-strings", help="Treat the pattern as a literal string."),
    max_count: int | None = typer.Option(None, "--max-count", min=1, help="Maximum number of matching lines to return."),
    before_context: int = typer.Option(0, "--before-context", min=0, help="Lines of leading context per match."),
    after_context: int = typer.Option(0, "--after-context", min=0, help="Lines of trailing context per match."),
    context: int = typer.Option(0, "--context", min=0, help="Lines of leading and trailing context per match."),
    include: list[str] | None = typer.Option(None, "--include", help="Repeatable repo-relative glob filter to include."),
    exclude: list[str] | None = typer.Option(None, "--exclude", help="Repeatable repo-relative glob filter to exclude."),
    code_only: bool = typer.Option(False, "--code-only", help="Search only code files."),
    text_only: bool = typer.Option(False, "--text-only", help="Search only text-index files."),
    summary_only: bool = typer.Option(False, "--summary-only", help="Return totals without detailed match payloads."),
  ) -> None:
    """Search supported files with a regex pattern."""
    runtime_settings = build_command_runtime_settings(ctx, target_dir)
    try:
      text_output, payload = _build_grep_outputs(
        runtime_settings,
        pattern,
        target_dir,
        depth_limit,
        ignore_case,
        fixed_strings,
        max_count,
        before_context,
        after_context,
        context,
        tuple(include or ()),
        tuple(exclude or ()),
        code_only,
        text_only,
        summary_only,
      )
    except InvalidRegexPatternError as error:
      exit_with_error(runtime_settings.json_output, "grep", str(error), "invalid_regex")
    except InvalidGrepArgumentsError as error:
      exit_with_error(runtime_settings.json_output, "grep", str(error), "invalid_arguments", {"code_only": code_only, "text_only": text_only})
    except FileNotFoundError as error:
      exit_with_error(runtime_settings.json_output, "grep", str(error), "invalid_arguments")
    typer.echo(render_output(text_output, payload, runtime_settings.json_output))


@beartype
def _build_grep_outputs(
  runtime_settings: RuntimeSettings,
  pattern: str,
  target_dir: str | None,
  depth_limit: int,
  ignore_case: bool,
  fixed_strings: bool,
  max_count: int | None,
  before_context: int,
  after_context: int,
  context: int,
  include: tuple[str, ...],
  exclude: tuple[str, ...],
  code_only: bool,
  text_only: bool,
  summary_only: bool,
) -> tuple[str, JsonObject]:
  """Build both text and JSON outputs for grep."""
  validate_grep_arguments(code_only=code_only, text_only=text_only)
  resolved_before_context = max(before_context, context)
  resolved_after_context = max(after_context, context)
  result = grep_search(
    target_dir=runtime_settings.target_dir,
    pattern=pattern,
    depth_limit=depth_limit,
    ignore_case=ignore_case,
    fixed_strings=fixed_strings,
    max_count=max_count,
    before_context=resolved_before_context,
    after_context=resolved_after_context,
    include=include,
    exclude=exclude,
    code_only=code_only,
    text_only=text_only,
    cache_dir=runtime_settings.cache_dir,
  )
  matches = [] if summary_only else result.matches
  payload: JsonObject = {
    "command": "grep",
    "query": pattern,
    "target_dir": get_effective_target_dir_label(runtime_settings, target_dir),
    "depth_limit": depth_limit,
    "match_count": result.match_count,
    "returned_count": len(matches),
    "truncated": result.truncated,
    "matches": matches,
  }
  return render_grep_matches(result, summary_only), payload
