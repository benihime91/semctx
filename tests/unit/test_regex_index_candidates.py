# Regex index candidate extraction unit tests.
from semctx.tools.regex_index_candidates import extract_required_trigrams


def test_extract_required_trigrams_handles_fixed_string_queries() -> None:
  assert extract_required_trigrams(pattern="ab", fixed_strings=True) is None
  assert extract_required_trigrams(pattern="hello", fixed_strings=True) == ("ell", "hel", "llo")


def test_extract_required_trigrams_returns_none_without_long_enough_literal_run() -> None:
  assert extract_required_trigrams(pattern="a.b", fixed_strings=False) is None


def test_extract_required_trigrams_uses_the_longest_literal_run() -> None:
  assert extract_required_trigrams(pattern="abc.*xyz_longer", fixed_strings=False) == (
    "_lo",
    "ger",
    "lon",
    "nge",
    "ong",
    "xyz",
    "yz_",
    "z_l",
  )


def test_extract_required_trigrams_treats_escaped_metacharacters_as_run_breaks() -> None:
  assert extract_required_trigrams(pattern=r"hello\.world", fixed_strings=False) == ("orl", "rld", "wor")


def test_extract_required_trigrams_returns_none_for_alternation() -> None:
  assert extract_required_trigrams(pattern="abc|xyz_longer", fixed_strings=False) is None


def test_extract_required_trigrams_does_not_treat_optional_chars_as_required() -> None:
  trigrams = extract_required_trigrams(pattern="colou?r", fixed_strings=False)

  assert trigrams is not None
  assert "lou" not in trigrams


def test_extract_required_trigrams_returns_none_for_groups() -> None:
  assert extract_required_trigrams(pattern="(abc)", fixed_strings=False) is None


def test_extract_required_trigrams_returns_none_for_character_classes() -> None:
  assert extract_required_trigrams(pattern="[abc]xyz_longer", fixed_strings=False) is None
