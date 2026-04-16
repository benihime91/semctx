# Context tree unit tests.
# FEATURE: Tree rendering.
from pathlib import Path

from semctx.tools.context_tree import get_context_tree

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "demo_project"


def test_get_context_tree_includes_headers_and_symbols() -> None:
  output = get_context_tree(root_dir=FIXTURE_ROOT, depth_limit=3, include_symbols=True)

  assert "demo_project/" in output
  assert "app/" in output
  assert "main.py" in output
  assert "header: Main application module. | FEATURE: Demo Fixture." in output
  assert "class Greeter [3-8]" in output
  assert "function make_message [11-13]" in output
  assert "ignored.py" not in output


def test_get_context_tree_prunes_symbols_when_token_budget_is_tight() -> None:
  output = get_context_tree(root_dir=FIXTURE_ROOT, depth_limit=3, include_symbols=True, max_tokens=8)

  assert "main.py" in output
  assert "class Greeter" not in output
  assert "header: Main application module. | FEATURE: Demo Fixture." not in output
