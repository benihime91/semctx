# Walker unit tests.
# FEATURE: Repository traversal.
from pathlib import Path

from semctx.core.walker import group_by_directory, walk_directory


def test_walk_directory_respects_gitignore(tmp_path: Path) -> None:
  project_dir = tmp_path / "project"
  project_dir.mkdir()
  (project_dir / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
  (project_dir / "kept.py").write_text("# Kept\n# FEATURE\n")
  (project_dir / "ignored.py").write_text("# Ignored\n# FEATURE\n")

  entries = walk_directory(root_dir=project_dir)

  relative_paths = [entry.relative_path.as_posix() for entry in entries]
  assert relative_paths == ["kept.py"]


def test_group_by_directory_returns_parent_buckets(tmp_path: Path) -> None:
  project_dir = tmp_path / "project"
  nested_dir = project_dir / "pkg"
  nested_dir.mkdir(parents=True)
  (project_dir / "root.py").write_text("# Root\n# FEATURE\n")
  (nested_dir / "child.py").write_text("# Child\n# FEATURE\n")

  grouped_entries = group_by_directory(walk_directory(root_dir=project_dir, depth_limit=2))

  assert sorted(path.as_posix() for path in grouped_entries) == [".", "pkg"]
  assert [entry.relative_path.as_posix() for entry in grouped_entries[Path("pkg")]] == ["pkg/child.py"]


def test_walk_directory_reincludes_gitignored_directory_with_root_ignore(
  tmp_path: Path,
) -> None:
  project_dir = tmp_path / "project"
  included_dir = project_dir / "node_modules" / "pkg"
  included_dir.mkdir(parents=True)
  (project_dir / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
  (project_dir / ".ignore").write_text("!node_modules/\n", encoding="utf-8")
  (included_dir / "index.js").write_text("export const value = 1;\n", encoding="utf-8")

  entries = walk_directory(root_dir=project_dir, depth_limit=3)

  relative_paths = [entry.relative_path.as_posix() for entry in entries]
  assert relative_paths == ["node_modules/pkg/index.js"]


def test_walk_directory_can_include_markdown_and_text_for_indexing(
  tmp_path: Path,
) -> None:
  project_dir = tmp_path / "project"
  docs_dir = project_dir / "docs"
  docs_dir.mkdir(parents=True)
  (project_dir / "app.py").write_text("# App\n# FEATURE\n", encoding="utf-8")
  (docs_dir / "guide.md").write_text("# Guide\nBody\n", encoding="utf-8")
  (docs_dir / "notes.txt").write_text("plain text notes\n", encoding="utf-8")

  code_entries = walk_directory(root_dir=project_dir, depth_limit=2)
  index_entries = walk_directory(
    root_dir=project_dir,
    depth_limit=2,
    include_index_text_files=True,
  )

  assert [entry.relative_path.as_posix() for entry in code_entries] == ["app.py"]
  assert [entry.relative_path.as_posix() for entry in index_entries] == [
    "app.py",
    "docs/guide.md",
    "docs/notes.txt",
  ]


def test_walk_directory_discovers_go_rust_kotlin_files(tmp_path: Path) -> None:
  project_dir = tmp_path / "project"
  project_dir.mkdir()
  (project_dir / "main.go").write_text("package main\n", encoding="utf-8")
  (project_dir / "lib.rs").write_text("fn main() {}\n", encoding="utf-8")
  (project_dir / "Demo.kt").write_text("fun main() {}\n", encoding="utf-8")

  entries = walk_directory(root_dir=project_dir, depth_limit=2)

  relative_paths = sorted(entry.relative_path.as_posix() for entry in entries)
  assert relative_paths == ["Demo.kt", "lib.rs", "main.go"]
