"""Search-code command helpers."""

import click
import typer
from beartype import beartype

from semctx.commands.model_selection_contract import ExplicitModelRequiredError, require_explicit_model
from semctx.commands.output_format import (
  JsonObject,
  render_error,
  render_output,
)
from semctx.commands.runtime_context import (
  build_command_runtime_settings,
  get_effective_target_dir_label,
)
from semctx.config.runtime_settings import RuntimeSettings
from semctx.core.embedding_provider import resolve_explicit_embedding_provider
from semctx.tools.index_lifecycle import ensure_search_ready_index
from semctx.tools.semantic_search import CodeSearchMatch, semantic_code_search


@beartype
def run_search_code_command(
  runtime_settings: RuntimeSettings,
  query: str,
  top_k: int = 5,
  model: str | None = None,
  target_dir: str | None = None,
  depth_limit: int = 8,
) -> str:
  """Run the code-search command and return text output."""
  return _build_search_code_outputs(runtime_settings, query, top_k, model, target_dir, depth_limit)[0]


@beartype
def build_search_code_payload(
  runtime_settings: RuntimeSettings,
  query: str,
  top_k: int = 5,
  model: str | None = None,
  target_dir: str | None = None,
  depth_limit: int = 8,
) -> JsonObject:
  """Build the JSON payload for a code-search run."""
  return _build_search_code_outputs(runtime_settings, query, top_k, model, target_dir, depth_limit)[1]


@beartype
def register_search_code_command(app: typer.Typer) -> None:
  """Register the search-code command on the root CLI."""

  @app.command("search-code")
  @beartype
  def search_code_command(
    ctx: click.Context,
    query: str = typer.Argument(..., help="Semantic query to match files."),
    top_k: int = typer.Option(5, "--top-k", min=1, help="Maximum number of matches to return."),
    model: str | None = typer.Option(
      None,
      "--model",
      help="Required embedding model selector as provider/model.",
    ),
    target_dir: str | None = typer.Option(None, "--target-dir", help="Directory whose contents are searched."),
    depth_limit: int = typer.Option(8, "--depth-limit", min=0, help="Directory depth limit."),
  ) -> None:
    """Search indexed code chunks with semantic and lexical ranking."""
    runtime_settings = build_command_runtime_settings(ctx, target_dir)
    try:
      text_output, payload = _build_search_code_outputs(runtime_settings, query, top_k, model, target_dir, depth_limit)
    except FileNotFoundError as error:
      _exit_with_error(
        runtime_settings.json_output,
        "search-code",
        str(error),
        "index_not_found",
      )
    except ExplicitModelRequiredError as error:
      _exit_with_error(
        runtime_settings.json_output,
        "search-code",
        str(error),
        "explicit_model_required",
      )
    except ValueError as error:
      _exit_with_error(
        runtime_settings.json_output,
        "search-code",
        str(error),
        "full_rebuild_required",
      )
    typer.echo(render_output(text_output, payload, runtime_settings.json_output))


@beartype
def _build_search_code_outputs(
  runtime_settings: RuntimeSettings,
  query: str,
  top_k: int,
  model: str | None,
  target_dir: str | None,
  depth_limit: int,
) -> tuple[str, JsonObject]:
  """Build both text and JSON outputs for code search."""
  resolved_model = require_explicit_model(model, "search-code")
  provider = resolve_explicit_embedding_provider(None, resolved_model)
  status = ensure_search_ready_index(
    runtime_settings=runtime_settings,
    model=resolved_model,
  )
  matches = semantic_code_search(
    target_dir=runtime_settings.target_dir,
    cache_dir=runtime_settings.cache_dir,
    query=query,
    provider=provider,
    top_k=top_k,
  )
  payload: JsonObject = {
    "command": "search-code",
    "depth_limit": depth_limit,
    "matches": matches,
    "model": status.model,
    "provider": status.provider,
    "query": query,
    "target_dir": get_effective_target_dir_label(runtime_settings, target_dir),
    "top_k": top_k,
  }
  return _render_search_code_matches(matches), payload


@beartype
def _render_search_code_matches(matches: list[CodeSearchMatch]) -> str:
  """Render ranked code-search matches as plain text."""
  if not matches:
    return "No code matches found."
  lines: list[str] = []
  for match in matches:
    lines.append(
      f"{match.relative_path.as_posix()}:{match.start_line}-{match.end_line} score={match.score:.4f} semantic={match.semantic_score:.4f} lexical={match.lexical_score:.4f}"
    )
    lines.append(f"  snippet: {match.snippet}")
  return "\n".join(lines)


@beartype
def _exit_with_error(json_output: bool, command: str, message: str, error: str) -> None:
  """Render a CLI error and exit with a non-zero status."""
  if json_output:
    typer.echo(render_error(command, error, message))
  else:
    typer.echo(message)
  raise typer.Exit(code=1)
