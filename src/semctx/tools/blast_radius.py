"""Blast radius helpers."""

import re
from dataclasses import dataclass
from pathlib import Path

from beartype import beartype

from semctx.core.parser import analyze_file
from semctx.core.parser_models import SymbolInfo
from semctx.core.walker import FileEntry, walk_directory

DEFAULT_DEPTH_LIMIT = 99


@dataclass(frozen=True)
class BlastRadiusUsage:
  """Describe one external symbol usage line."""

  relative_path: Path
  line_number: int
  line_text: str


@dataclass(frozen=True)
class BlastRadiusReport:
  """Describe one traced symbol and its external usages."""

  symbol_name: str
  file_context: Path
  definition: SymbolInfo | None
  usages: tuple[BlastRadiusUsage, ...]


@beartype
def get_blast_radius(
  root_dir: Path,
  symbol_name: str,
  file_context: str,
  depth_limit: int = DEFAULT_DEPTH_LIMIT,
) -> str:
  """Return a rendered blast-radius report."""
  report = trace_blast_radius(
    root_dir=root_dir,
    symbol_name=symbol_name,
    file_context=file_context,
    depth_limit=depth_limit,
  )
  return render_blast_radius(report)


@beartype
def trace_blast_radius(
  root_dir: Path,
  symbol_name: str,
  file_context: str,
  depth_limit: int = DEFAULT_DEPTH_LIMIT,
) -> BlastRadiusReport:
  """Trace external usages for a symbol within the repo."""
  resolved_root_dir = root_dir.resolve()
  file_context_path = _resolve_file_context(resolved_root_dir, file_context)
  definition = _find_definition(file_context_path, symbol_name)
  entries = walk_directory(root_dir=resolved_root_dir, target_path=".", depth_limit=depth_limit)
  usages = _collect_usages(entries, file_context_path, symbol_name)
  return BlastRadiusReport(
    symbol_name=symbol_name,
    file_context=file_context_path.relative_to(resolved_root_dir),
    definition=definition,
    usages=tuple(usages),
  )


@beartype
def render_blast_radius(report: BlastRadiusReport) -> str:
  """Render a blast-radius report as plain text."""
  lines = [
    f"symbol: {report.symbol_name}",
    f"file_context: {report.file_context.as_posix()}",
    f"definition: {_format_definition(report.definition)}",
  ]
  if not report.usages:
    lines.append("usages: none")
    return "\n".join(lines)
  lines.append(f"usages: {len(report.usages)}")
  lines.extend(f"- {usage.relative_path.as_posix()}:{usage.line_number} :: {usage.line_text}" for usage in report.usages)
  return "\n".join(lines)


@beartype
def _resolve_file_context(root_dir: Path, file_context: str) -> Path:
  """Resolve and validate the defining file path."""
  resolved_path = (root_dir / file_context).resolve()
  if not resolved_path.exists() or not resolved_path.is_file():
    raise FileNotFoundError(f"File context does not exist: {resolved_path}")
  if root_dir not in {resolved_path, *resolved_path.parents}:
    raise ValueError(f"File context must stay within root_dir: {resolved_path}")
  return resolved_path


@beartype
def _find_definition(file_path: Path, symbol_name: str) -> SymbolInfo | None:
  """Find the symbol definition inside the context file."""
  analysis = analyze_file(file_path)
  for symbol in analysis.symbols:
    if symbol.name == symbol_name:
      return symbol
  return None


@beartype
def _collect_usages(entries: list[FileEntry], file_context_path: Path, symbol_name: str) -> list[BlastRadiusUsage]:
  """Collect external symbol usages across discovered files."""
  pattern = re.compile(rf"(?<![\w$]){re.escape(symbol_name)}(?![\w$])")
  usages: list[BlastRadiusUsage] = []
  for entry in entries:
    if entry.absolute_path == file_context_path:
      continue
    usages.extend(_collect_entry_usages(entry, symbol_name, pattern))
  return usages


@beartype
def _collect_entry_usages(entry: FileEntry, symbol_name: str, pattern: re.Pattern[str]) -> list[BlastRadiusUsage]:
  """Collect symbol usages from one file entry."""
  analysis = analyze_file(entry.absolute_path)
  definition_lines = {symbol.line_start for symbol in analysis.symbols if symbol.name == symbol_name}
  usages: list[BlastRadiusUsage] = []
  for line_number, line in enumerate(entry.absolute_path.read_text().splitlines(), start=1):
    if line_number in definition_lines or not pattern.search(line):
      continue
    usages.append(
      BlastRadiusUsage(
        relative_path=entry.relative_path,
        line_number=line_number,
        line_text=line.strip(),
      )
    )
  return usages


@beartype
def _format_definition(definition: SymbolInfo | None) -> str:
  """Render one definition summary for plain-text output."""
  if definition is None:
    return "not found"
  return f"{definition.kind} {definition.name} [{definition.line_start}-{definition.line_end}]"
