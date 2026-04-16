"""Identifier-search support helpers."""

from beartype import beartype


@beartype
def matches_identifier_target_path(relative_path: str, target_path: str) -> bool:
  """Check whether an identifier path falls inside the requested scope."""
  normalized_target = target_path.strip().strip("/")
  if not normalized_target or normalized_target == ".":
    return True
  return relative_path == normalized_target or relative_path.startswith(f"{normalized_target}/")


@beartype
def dedupe_search_terms(terms: tuple[str, ...]) -> tuple[str, ...]:
  """Preserve search term order while removing duplicates."""
  return tuple(dict.fromkeys(terms))


@beartype
def infer_identifier_kind(signature: str) -> str:
  """Infer a stable identifier kind from its signature text."""
  lowered_signature = signature.lower()
  if lowered_signature.startswith("class ") or " class " in lowered_signature:
    return "class"
  if " interface " in f" {lowered_signature} ":
    return "interface"
  if " enum " in f" {lowered_signature} ":
    return "enum"
  if lowered_signature.startswith("type ") or " type " in f" {lowered_signature} ":
    return "type"
  if lowered_signature.startswith("async def ") or lowered_signature.startswith("def "):
    return "function"
  if " function " in f" {lowered_signature} ":
    return "function"
  if any(keyword in lowered_signature for keyword in ("const ", "let ", "var ")):
    return "variable"
  return "identifier"
