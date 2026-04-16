"""Runtime settings models."""

from pathlib import Path

from beartype import beartype
from pydantic import BaseModel, ConfigDict


class RuntimeSettings(BaseModel):
    """Store immutable runtime settings for CLI commands."""

    model_config = ConfigDict(frozen=True)

    target_dir: Path
    cache_dir: Path
    json_output: bool

    @property
    def root_dir(self) -> Path:
        """Return the canonical target dir for compatibility."""
        return self.target_dir


@beartype
def build_runtime_settings(
    target_dir: Path | None = None,
    cache_dir: Path | None = None,
    json_output: bool = False,
    root_dir: Path | None = None,
) -> RuntimeSettings:
    """Build normalized runtime settings for the CLI."""
    resolved_target_dir = (target_dir or root_dir or Path.cwd()).resolve()
    resolved_cache_dir = (cache_dir or resolved_target_dir / ".semctx").resolve()
    return RuntimeSettings(
        target_dir=resolved_target_dir,
        cache_dir=resolved_cache_dir,
        json_output=json_output,
    )
