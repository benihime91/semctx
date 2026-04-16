"""Output formatting helpers."""

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

from beartype import beartype

JsonValue = object
JsonObject = dict[str, object]


@beartype
def render_output(text_output: str, payload: JsonObject, json_output: bool) -> str:
  """Render either plain text or normalized JSON output."""
  if not json_output:
    return text_output
  return json.dumps(_normalize_json(payload), indent=2, sort_keys=True)


@beartype
def render_error(
  command: str,
  error: str,
  message: str,
  details: JsonValue | None = None,
) -> str:
  """Render a structured error payload as JSON."""
  payload: JsonObject = {"command": command, "error": error, "message": message}
  if details is not None:
    payload["details"] = details
  return json.dumps(_normalize_json(payload), indent=2, sort_keys=True)


def _normalize_json(value: object) -> JsonValue:
  """Normalize arbitrary values into JSON-serializable data."""
  if value is None or isinstance(value, bool | int | float | str):
    return value
  if isinstance(value, Path):
    return value.as_posix()
  if is_dataclass(value) and not isinstance(value, type):
    return _normalize_json(asdict(value))
  if isinstance(value, dict):
    return {str(key): _normalize_json(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
  if isinstance(value, list | tuple):
    return [_normalize_json(item) for item in value]
  return str(value)
