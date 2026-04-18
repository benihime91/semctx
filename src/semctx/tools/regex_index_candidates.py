"""Extract mandatory literal trigrams from regex queries for candidate prefiltering."""

from beartype import beartype

from semctx.tools.regex_index_builder import TRIGRAM_LENGTH, extract_trigrams

REGEX_METACHARS = frozenset(".^$*+?()[]{}|\\")


@beartype
def extract_required_trigrams(
  pattern: str,
  fixed_strings: bool,
) -> tuple[str, ...] | None:
  """Return required trigrams for a query, or None when prefiltering is unsafe."""
  literal = pattern if fixed_strings else _extract_required_literal_run(pattern)
  if literal is None or len(literal) < TRIGRAM_LENGTH:
    return None
  trigrams = extract_trigrams(literal)
  if not trigrams:
    return None
  return tuple(sorted(trigrams))


@beartype
def _extract_required_literal_run(pattern: str) -> str | None:
  """Return the longest safe required literal run for a regex pattern."""
  if _contains_unsupported_regex_feature(pattern):
    return None
  return _longest_literal_run(pattern)


@beartype
def _contains_unsupported_regex_feature(pattern: str) -> bool:
  """Return whether the regex pattern uses unsupported branching constructs."""
  index = 0
  while index < len(pattern):
    char = pattern[index]
    if char == "\\":
      index += 2
      continue
    if char in {"|", "(", "["}:
      return True
    index += 1
  return False


@beartype
def _longest_literal_run(pattern: str) -> str | None:
  """Return the longest unescaped literal run in a regex pattern."""
  best_run = ""
  current_run = ""
  index = 0
  while index < len(pattern):
    char = pattern[index]
    if char == "\\":
      if len(current_run) >= len(best_run):
        best_run = current_run
      current_run = ""
      index += 2
      continue
    quantifier_length, optional = _quantifier_at(pattern, index + 1)
    if quantifier_length > 0:
      candidate_run = current_run if optional else current_run + char
      if len(candidate_run) >= len(best_run):
        best_run = candidate_run
      current_run = ""
      index += 1 + quantifier_length
      continue
    if char in REGEX_METACHARS:
      if len(current_run) >= len(best_run):
        best_run = current_run
      current_run = ""
      index += 1
      continue
    current_run += char
    index += 1
  if len(current_run) >= len(best_run):
    best_run = current_run
  return best_run or None


@beartype
def _quantifier_at(pattern: str, index: int) -> tuple[int, bool]:
  """Return the quantifier length and whether it makes the prior char optional."""
  if index >= len(pattern):
    return 0, False
  char = pattern[index]
  if char in {"?", "*"}:
    return 1, True
  if char != "{":
    return 0, False
  closing_index = pattern.find("}", index + 1)
  if closing_index < 0:
    return 0, False
  quantifier_body = pattern[index + 1 : closing_index]
  minimum = _parse_quantifier_minimum(quantifier_body)
  if minimum is None:
    return 0, False
  return closing_index - index + 1, minimum == 0


@beartype
def _parse_quantifier_minimum(quantifier_body: str) -> int | None:
  """Return the minimum repetition count for a counted quantifier."""
  minimum_text = quantifier_body.split(",", maxsplit=1)[0].strip()
  if not minimum_text.isdigit():
    return None
  return int(minimum_text)
