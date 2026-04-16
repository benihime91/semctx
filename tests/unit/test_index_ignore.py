# Index ignore unit tests.
# FEATURE: Merged ignore precedence.
from pathlib import Path

from semctx.core.index_ignore import build_index_ignore_matcher


def test_ignore_matcher_reincludes_gitignored_path(tmp_path: Path) -> None:
  (tmp_path / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
  (tmp_path / ".ignore").write_text("!node_modules/\n", encoding="utf-8")

  matcher = build_index_ignore_matcher(tmp_path)

  assert matcher.includes("node_modules/pkg/index.js") is True


def test_ignore_matcher_applies_root_ignore_exclusion(tmp_path: Path) -> None:
  (tmp_path / ".ignore").write_text("dist/\n", encoding="utf-8")

  matcher = build_index_ignore_matcher(tmp_path)

  assert matcher.includes("dist/app.js") is False


def test_ignore_matcher_preserves_override_order(tmp_path: Path) -> None:
  (tmp_path / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
  (tmp_path / ".ignore").write_text("!node_modules/\nnode_modules/private/\n", encoding="utf-8")

  matcher = build_index_ignore_matcher(tmp_path)

  assert matcher.includes("node_modules/public/index.js") is True
  assert matcher.includes("node_modules/private/index.js") is False
