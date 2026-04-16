"""Search-identifiers command helpers."""

import click
import typer
from beartype import beartype

from semctx.commands.output_format import JsonObject, render_error, render_output
from semctx.commands.runtime_context import (
    build_command_runtime_settings,
    get_effective_target_dir_label,
)
from semctx.config.runtime_settings import RuntimeSettings
from semctx.tools.index_lifecycle import ensure_search_ready_index
from semctx.tools.semantic_identifiers import (
    IdentifierSearchMatch,
    semantic_identifier_search,
)


@beartype
def run_search_identifiers_command(
    runtime_settings: RuntimeSettings,
    query: str,
    top_k: int = 5,
    model: str | None = None,
    target_dir: str | None = None,
    depth_limit: int = 8,
) -> str:
    """Run the identifier-search command and return text output."""
    return _build_search_identifier_outputs(
        runtime_settings, query, top_k, model, target_dir, depth_limit
    )[0]


@beartype
def build_search_identifiers_payload(
    runtime_settings: RuntimeSettings,
    query: str,
    top_k: int = 5,
    model: str | None = None,
    target_dir: str | None = None,
    depth_limit: int = 8,
) -> JsonObject:
    """Build the JSON payload for an identifier-search run."""
    return _build_search_identifier_outputs(
        runtime_settings, query, top_k, model, target_dir, depth_limit
    )[1]


@beartype
def register_search_identifiers_command(app: typer.Typer) -> None:
    """Register the search-identifiers command on the root CLI."""

    @app.command("search-identifiers")
    @beartype
    def search_identifiers_command(
        ctx: click.Context,
        query: str = typer.Argument(..., help="Semantic query to match identifiers."),
        top_k: int = typer.Option(
            5, "--top-k", min=1, help="Maximum number of matches to return."
        ),
        model: str | None = typer.Option(
            None,
            "--model",
            help="Embedding model override. Prefer provider/model for provider-aware search.",
        ),
        target_dir: str | None = typer.Option(
            None, "--target-dir", help="Directory whose contents are searched."
        ),
        depth_limit: int = typer.Option(
            8, "--depth-limit", min=0, help="Directory depth limit."
        ),
    ) -> None:
        """Search indexed identifiers with semantic and lexical ranking."""
        runtime_settings = build_command_runtime_settings(ctx, target_dir)
        try:
            text_output, payload = _build_search_identifier_outputs(
                runtime_settings, query, top_k, model, target_dir, depth_limit
            )
        except FileNotFoundError as error:
            _exit_with_error(
                runtime_settings.json_output,
                "search-identifiers",
                str(error),
                "index_not_found",
            )
        except ValueError as error:
            _exit_with_error(
                runtime_settings.json_output,
                "search-identifiers",
                str(error),
                "full_rebuild_required",
            )
        typer.echo(render_output(text_output, payload, runtime_settings.json_output))


@beartype
def _build_search_identifier_outputs(
    runtime_settings: RuntimeSettings,
    query: str,
    top_k: int,
    model: str | None,
    target_dir: str | None,
    depth_limit: int,
) -> tuple[str, JsonObject]:
    """Build both text and JSON outputs for identifier search."""
    status = ensure_search_ready_index(
        runtime_settings=runtime_settings,
        model=model,
    )
    matches = semantic_identifier_search(
        target_dir=runtime_settings.target_dir,
        cache_dir=runtime_settings.cache_dir,
        query=query,
        model=model,
        top_k=top_k,
        depth_limit=depth_limit,
    )
    payload: JsonObject = {
        "command": "search-identifiers",
        "depth_limit": depth_limit,
        "matches": matches,
        "model": status.model,
        "provider": status.provider,
        "query": query,
        "target_dir": get_effective_target_dir_label(runtime_settings, target_dir),
        "top_k": top_k,
    }
    return _render_search_identifier_matches(matches), payload


@beartype
def _render_search_identifier_matches(matches: list[IdentifierSearchMatch]) -> str:
    """Render ranked identifier-search matches as plain text."""
    if not matches:
        return "No identifier matches found."
    lines: list[str] = []
    for match in matches:
        lines.append(
            f"{match.relative_path.as_posix()}:{match.line_start}-{match.line_end} "
            f"{match.kind} {match.name} score={match.score:.4f} "
            f"semantic={match.semantic_score:.4f} lexical={match.lexical_score:.4f}"
        )
        lines.append(f"  signature: {match.signature}")
    return "\n".join(lines)


@beartype
def _exit_with_error(json_output: bool, command: str, message: str, error: str) -> None:
    """Render a CLI error and exit with a non-zero status."""
    if json_output:
        typer.echo(render_error(command, error, message))
    else:
        typer.echo(message)
    raise typer.Exit(code=1)
