"""Repository walking helpers."""

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from beartype import beartype

from semctx.core.index_ignore import IndexIgnoreMatcher, build_index_ignore_matcher

IGNORED_DIRECTORY_NAMES = {".git", ".semctx", "__pycache__"}
CODE_SUFFIXES = frozenset(
    {".go", ".js", ".jsx", ".kt", ".kts", ".py", ".rs", ".ts", ".tsx"}
)
INDEX_TEXT_SUFFIXES = frozenset({".markdown", ".md", ".mdx", ".txt"})
INDEXABLE_SUFFIXES = CODE_SUFFIXES | INDEX_TEXT_SUFFIXES


@dataclass(frozen=True)
class FileEntry:
    """Describe one discovered file in the repo walk."""

    absolute_path: Path
    relative_path: Path
    depth: int


@beartype
def walk_directory(
    root_dir: Path,
    target_path: str | None = None,
    depth_limit: int = 2,
    include_index_text_files: bool = False,
) -> list[FileEntry]:
    """Walk the repo and return supported files within scope."""
    resolved_root_dir = root_dir.resolve()
    resolved_target_path = _resolve_target_path(resolved_root_dir, target_path)
    ignore_matcher = build_index_ignore_matcher(resolved_root_dir)
    if resolved_target_path.is_file():
        relative_path = resolved_target_path.relative_to(resolved_root_dir)
        if _is_ignored(relative_path, ignore_matcher):
            return []
        return [
            FileEntry(
                absolute_path=resolved_target_path, relative_path=relative_path, depth=0
            )
        ]
    entries: list[FileEntry] = []
    _collect_entries(
        root_dir=resolved_root_dir,
        current_dir=resolved_target_path,
        current_depth=0,
        depth_limit=max(depth_limit, 0),
        supported_suffixes=(
            INDEXABLE_SUFFIXES if include_index_text_files else CODE_SUFFIXES
        ),
        ignore_matcher=ignore_matcher,
        entries=entries,
    )
    return sorted(entries, key=lambda entry: entry.relative_path.as_posix())


@beartype
def walk_target_directory(
    target_dir: Path,
    depth_limit: int = 2,
    include_index_text_files: bool = False,
) -> list[FileEntry]:
    """Walk one canonical target directory and scope paths to it."""
    resolved_target_dir = target_dir.resolve()
    ignore_matcher = build_index_ignore_matcher(resolved_target_dir)
    if resolved_target_dir.is_file():
        relative_path = Path(resolved_target_dir.name)
        if _is_ignored(relative_path, ignore_matcher):
            return []
        return [
            FileEntry(
                absolute_path=resolved_target_dir,
                relative_path=relative_path,
                depth=0,
            )
        ]
    entries: list[FileEntry] = []
    _collect_entries(
        root_dir=resolved_target_dir,
        current_dir=resolved_target_dir,
        current_depth=0,
        depth_limit=max(depth_limit, 0),
        supported_suffixes=(
            INDEXABLE_SUFFIXES if include_index_text_files else CODE_SUFFIXES
        ),
        ignore_matcher=ignore_matcher,
        entries=entries,
    )
    return sorted(entries, key=lambda entry: entry.relative_path.as_posix())


@beartype
def group_by_directory(entries: list[FileEntry]) -> dict[Path, list[FileEntry]]:
    """Group discovered file entries by parent directory."""
    grouped_entries: dict[Path, list[FileEntry]] = defaultdict(list)
    for entry in entries:
        grouped_entries[entry.relative_path.parent].append(entry)
    return dict(sorted(grouped_entries.items(), key=lambda item: item[0].as_posix()))


@beartype
def _resolve_target_path(root_dir: Path, target_path: str | None) -> Path:
    """Resolve and validate the requested walk target path."""
    candidate_path = (root_dir / (target_path or ".")).resolve()
    if not candidate_path.exists():
        raise FileNotFoundError(f"Target path does not exist: {candidate_path}")
    if root_dir not in {candidate_path, *candidate_path.parents}:
        raise ValueError(f"Target path must stay within root_dir: {candidate_path}")
    return candidate_path


@beartype
def _collect_entries(
    root_dir: Path,
    current_dir: Path,
    current_depth: int,
    depth_limit: int,
    supported_suffixes: frozenset[str],
    ignore_matcher: IndexIgnoreMatcher,
    entries: list[FileEntry],
) -> None:
    """Collect supported file entries recursively."""
    for child_path in sorted(
        current_dir.iterdir(), key=lambda path: (path.is_file(), path.name.lower())
    ):
        relative_path = child_path.relative_to(root_dir)
        if _is_ignored(relative_path, ignore_matcher):
            continue
        if child_path.is_dir():
            if (
                child_path.name in IGNORED_DIRECTORY_NAMES
                or current_depth >= depth_limit
            ):
                continue
            _collect_entries(
                root_dir,
                child_path,
                current_depth + 1,
                depth_limit,
                supported_suffixes,
                ignore_matcher,
                entries,
            )
            continue
        if child_path.suffix.lower() not in supported_suffixes:
            continue
        entries.append(
            FileEntry(
                absolute_path=child_path,
                relative_path=relative_path,
                depth=current_depth,
            )
        )


@beartype
def _is_ignored(relative_path: Path, ignore_matcher: IndexIgnoreMatcher) -> bool:
    """Check whether a path should be skipped during walking."""
    if any(part in IGNORED_DIRECTORY_NAMES for part in relative_path.parts):
        return True
    return not ignore_matcher.includes(relative_path.as_posix())
