"""Index-aware ignore helpers."""

from dataclasses import dataclass
from pathlib import Path

from beartype import beartype
from pathspec import PathSpec


@dataclass(frozen=True)
class OverrideRule:
    """Describe one root `.ignore` override rule."""

    excludes: bool
    spec: PathSpec


@dataclass(frozen=True)
class IndexIgnoreMatcher:
    """Check whether a path should be included in indexing."""

    baseline_spec: PathSpec
    override_rules: tuple[OverrideRule, ...]

    @beartype
    def includes(self, relative_path: str) -> bool:
        """Return whether a relative path should be indexed."""
        ignored = _matches(self.baseline_spec, relative_path)
        for rule in self.override_rules:
            if _matches(rule.spec, relative_path):
                ignored = rule.excludes
        return not ignored


@beartype
def build_index_ignore_matcher(root_dir: Path) -> IndexIgnoreMatcher:
    """Build the merged index ignore matcher for a repo root."""
    gitignore_patterns = _read_patterns(root_dir / ".gitignore")
    override_patterns = _read_patterns(root_dir / ".ignore")
    baseline_spec = PathSpec.from_lines("gitwildmatch", gitignore_patterns)
    override_rules = tuple(
        _build_override_rule(pattern) for pattern in override_patterns
    )
    return IndexIgnoreMatcher(
        baseline_spec=baseline_spec, override_rules=override_rules
    )


@beartype
def _build_override_rule(pattern: str) -> OverrideRule:
    """Build one override rule from a raw pattern line."""
    is_reinclude = pattern.startswith("!")
    normalized_pattern = pattern[1:] if is_reinclude else pattern
    return OverrideRule(
        excludes=not is_reinclude,
        spec=PathSpec.from_lines("gitwildmatch", [normalized_pattern]),
    )


@beartype
def _matches(spec: PathSpec, relative_path: str) -> bool:
    """Check whether a path or directory path matches a spec."""
    if spec.match_file(relative_path):
        return True
    return spec.match_file(f"{relative_path}/")


@beartype
def _read_patterns(file_path: Path) -> tuple[str, ...]:
    """Read ignore patterns from disk, skipping comments and blanks."""
    if not file_path.exists():
        return ()
    patterns: list[str] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue
        patterns.append(stripped_line)
    return tuple(patterns)
