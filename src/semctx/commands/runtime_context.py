"""Runtime context helpers."""

from pathlib import Path

import click
import typer
from beartype import beartype

from semctx.config.runtime_settings import RuntimeSettings, build_runtime_settings


@beartype
def get_runtime_settings(ctx: click.Context) -> RuntimeSettings:
  """Return typed runtime settings from the active CLI context."""
  runtime_settings = ctx.obj
  if not isinstance(runtime_settings, RuntimeSettings):
    raise typer.Exit(code=1)
  return runtime_settings


@beartype
def build_command_runtime_settings(
  ctx: click.Context,
  target_dir: str | None = None,
) -> RuntimeSettings:
  """Return runtime settings with an optional command-level target dir."""
  runtime_settings = get_runtime_settings(ctx)
  if target_dir in {None, "."}:
    return runtime_settings
  resolved_target_dir = Path(target_dir)
  if not resolved_target_dir.is_absolute():
    resolved_target_dir = runtime_settings.target_dir / resolved_target_dir
  return build_runtime_settings(
    target_dir=resolved_target_dir,
    cache_dir=runtime_settings.cache_dir,
    json_output=runtime_settings.json_output,
  )


@beartype
def get_effective_target_dir_label(
  runtime_settings: RuntimeSettings,
  target_dir_override: str | None = None,
) -> str:
  """Return the normalized target-dir label for command payloads."""
  if target_dir_override is not None:
    return Path(target_dir_override).as_posix() or "."
  cwd = Path.cwd().resolve()
  try:
    relative_target_dir = runtime_settings.target_dir.relative_to(cwd)
  except ValueError:
    return runtime_settings.target_dir.as_posix()
  if relative_target_dir == Path("."):
    return "."
  return relative_target_dir.as_posix()
