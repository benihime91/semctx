"""Command-surface validation for explicit model selection."""

from beartype import beartype


class CommandContractError(ValueError):
  """Base error for invalid command-surface arguments."""


class ExplicitModelRequiredError(CommandContractError):
  """Raised when a DB-touching command omits the required model selector."""


class InvalidCommandSelectionError(CommandContractError):
  """Raised when a command receives an invalid selector combination."""


@beartype
def require_explicit_model(model: str | None, command_name: str) -> str:
  """Return the required model selector or fail with a command-level error."""
  normalized_model = model.strip() if isinstance(model, str) else ""
  if not normalized_model:
    raise ExplicitModelRequiredError(f"--model provider/model is required for `{command_name}`.")
  return normalized_model


@beartype
def validate_clear_selection(model: str | None, clear_all: bool) -> str | None:
  """Validate clear-command selection and return the explicit model when used."""
  normalized_model = model.strip() if isinstance(model, str) else ""
  if clear_all and normalized_model:
    raise InvalidCommandSelectionError("Pass either `--model provider/model` or `--all`, not both.")
  if clear_all:
    return None
  if not normalized_model:
    raise ExplicitModelRequiredError("`index clear` requires `--model provider/model` or explicit `--all`.")
  return normalized_model
