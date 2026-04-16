# CLI JSON integration tests.
# FEATURE: JSON output for discovery, search, and index commands.
import json
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from semctx.cli import app
from semctx.tools.index_lifecycle import get_index_db_path
from semctx.commands import search_code_command, search_identifiers_command
from semctx.tools.index_status import IndexStatus
from semctx.tools.semantic_identifiers import IdentifierSearchMatch
from semctx.tools.semantic_search import CodeSearchMatch

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "demo_project"


def test_search_commands_emit_json(monkeypatch) -> None:
  monkeypatch.setattr(
    search_code_command,
    "ensure_search_ready_index",
    lambda **_: IndexStatus(
      exists=True,
      stale=False,
      rebuild_required=False,
      provider="ollama",
      model="test-model",
      indexed_file_count=2,
      code_chunk_count=3,
      identifier_doc_count=2,
      changed_paths=(),
      removed_paths=(),
      db_path=Path("/tmp/index.db"),
    ),
  )
  monkeypatch.setattr(
    search_code_command,
    "semantic_code_search",
    lambda **_: [
      CodeSearchMatch(
        relative_path=Path("app/main.py"),
        start_line=7,
        end_line=8,
        score=0.95,
        semantic_score=0.9,
        lexical_score=1.0,
        snippet="def make_message(person: str) -> str: return Greeter().greet(person)",
      ),
      CodeSearchMatch(
        relative_path=Path("app/greeter.py"),
        start_line=1,
        end_line=4,
        score=0.9,
        semantic_score=0.88,
        lexical_score=0.93,
        snippet='class Greeter:\n    def greet(self, person: str) -> str:\n        return f"Hello, {person}"',
      ),
    ],
  )
  monkeypatch.setattr(
    search_identifiers_command,
    "ensure_search_ready_index",
    lambda **_: IndexStatus(
      exists=True,
      stale=False,
      rebuild_required=False,
      provider="ollama",
      model="test-model",
      indexed_file_count=2,
      code_chunk_count=3,
      identifier_doc_count=2,
      changed_paths=(),
      removed_paths=(),
      db_path=Path("/tmp/index.db"),
    ),
  )
  monkeypatch.setattr(
    search_identifiers_command,
    "semantic_identifier_search",
    lambda **_: [
      IdentifierSearchMatch(
        relative_path=Path("src/widget.ts"),
        kind="function",
        name="buildWidget",
        signature="export function buildWidget(id: string): Widget",
        line_start=7,
        line_end=9,
        score=0.91,
        semantic_score=0.87,
        lexical_score=1.0,
      ),
      IdentifierSearchMatch(
        relative_path=Path("src/widget.ts"),
        kind="class",
        name="WidgetBuilder",
        signature="export class WidgetBuilder",
        line_start=1,
        line_end=5,
        score=0.83,
        semantic_score=0.8,
        lexical_score=0.9,
      ),
    ],
  )
  runner = CliRunner()
  code_result = runner.invoke(
    app,
    ["--json", "search-code", "greeting flow", "--model", "test-model"],
    prog_name="semctx",
  )
  identifiers_result = runner.invoke(
    app,
    ["--json", "search-identifiers", "build widget", "--model", "test-model"],
    prog_name="semctx",
  )

  code_payload = json.loads(code_result.stdout)
  identifiers_payload = json.loads(identifiers_result.stdout)

  assert code_result.exit_code == 0
  assert code_result.stderr == ""
  assert set(code_payload.keys()) == {
    "command",
    "depth_limit",
    "matches",
    "model",
    "provider",
    "query",
    "target_dir",
    "top_k",
  }
  assert {frozenset(match.keys()) for match in code_payload["matches"]} == {
    frozenset(
      {
        "end_line",
        "lexical_score",
        "relative_path",
        "score",
        "semantic_score",
        "snippet",
        "start_line",
      }
    )
  }
  assert code_payload["matches"]
  assert {frozenset(match.items()) for match in code_payload["matches"]} == {
    frozenset(
      {
        ("end_line", 8),
        ("lexical_score", 1.0),
        ("relative_path", "app/main.py"),
        ("score", 0.95),
        ("semantic_score", 0.9),
        (
          "snippet",
          "def make_message(person: str) -> str: return Greeter().greet(person)",
        ),
        ("start_line", 7),
      }
    ),
    frozenset(
      {
        ("end_line", 4),
        ("lexical_score", 0.93),
        ("relative_path", "app/greeter.py"),
        ("score", 0.9),
        ("semantic_score", 0.88),
        (
          "snippet",
          'class Greeter:\n    def greet(self, person: str) -> str:\n        return f"Hello, {person}"',
        ),
        ("start_line", 1),
      }
    ),
  }
  assert code_payload | {"matches": []} == {
    "command": "search-code",
    "depth_limit": 8,
    "matches": [],
    "model": "test-model",
    "provider": "ollama",
    "query": "greeting flow",
    "target_dir": ".",
    "top_k": 5,
  }
  assert identifiers_result.exit_code == 0
  assert identifiers_result.stderr == ""
  assert set(identifiers_payload.keys()) == {
    "command",
    "depth_limit",
    "matches",
    "model",
    "provider",
    "query",
    "target_dir",
    "top_k",
  }
  assert {frozenset(match.keys()) for match in identifiers_payload["matches"]} == {
    frozenset(
      {
        "kind",
        "lexical_score",
        "line_end",
        "line_start",
        "name",
        "relative_path",
        "score",
        "semantic_score",
        "signature",
      }
    )
  }
  assert identifiers_payload["matches"]
  assert {frozenset(match.items()) for match in identifiers_payload["matches"]} == {
    frozenset(
      {
        ("kind", "function"),
        ("lexical_score", 1.0),
        ("line_end", 9),
        ("line_start", 7),
        ("name", "buildWidget"),
        ("relative_path", "src/widget.ts"),
        ("score", 0.91),
        ("semantic_score", 0.87),
        ("signature", "export function buildWidget(id: string): Widget"),
      }
    ),
    frozenset(
      {
        ("kind", "class"),
        ("lexical_score", 0.9),
        ("line_end", 5),
        ("line_start", 1),
        ("name", "WidgetBuilder"),
        ("relative_path", "src/widget.ts"),
        ("score", 0.83),
        ("semantic_score", 0.8),
        ("signature", "export class WidgetBuilder"),
      }
    ),
  }
  assert identifiers_payload | {"matches": []} == {
    "command": "search-identifiers",
    "depth_limit": 8,
    "matches": [],
    "model": "test-model",
    "provider": "ollama",
    "query": "build widget",
    "target_dir": ".",
    "top_k": 5,
  }


def test_search_commands_inherit_root_target_dir_in_json(monkeypatch) -> None:
  monkeypatch.setattr(
    search_code_command,
    "ensure_search_ready_index",
    lambda **_: IndexStatus(
      exists=True,
      stale=False,
      rebuild_required=False,
      provider="ollama",
      model="test-model",
      indexed_file_count=1,
      code_chunk_count=1,
      identifier_doc_count=1,
      changed_paths=(),
      removed_paths=(),
      db_path=Path("/tmp/index.db"),
    ),
  )
  monkeypatch.setattr(search_code_command, "semantic_code_search", lambda **_: [])
  runner = CliRunner()

  result = runner.invoke(
    app,
    [
      "--json",
      "--target-dir",
      "src/",
      "search-code",
      "greeting flow",
      "--model",
      "test-model",
    ],
    prog_name="semctx",
  )

  payload = json.loads(result.stdout)

  assert result.exit_code == 0
  assert payload["target_dir"] == "src"


def test_index_status_emits_rebuild_required_json(tmp_path: Path, monkeypatch) -> None:
  _write_index_fixture(tmp_path)
  monkeypatch.setattr(
    "semctx.tools.index_building.get_cached_embeddings",
    _fake_get_cached_embeddings,
  )
  runner = CliRunner()
  base_args = [
    "--json",
    "--cache-dir",
    str(tmp_path / ".semctx"),
  ]

  init_result = runner.invoke(
    app,
    [
      *base_args,
      "index",
      "init",
      "--target-dir",
      str(tmp_path),
      "--model",
      "ollama/nomic-embed-text-v2-moe:latest",
    ],
    prog_name="semctx",
  )
  _set_schema_version(get_index_db_path(tmp_path / ".semctx"), "2")
  status_result = runner.invoke(
    app,
    [*base_args, "index", "status", "--target-dir", str(tmp_path)],
    prog_name="semctx",
  )

  payload = json.loads(status_result.stdout)

  assert init_result.exit_code == 0
  assert init_result.stderr == ""
  assert status_result.exit_code == 0
  assert status_result.stderr == ""
  assert set(payload.keys()) == {"command", "status", "subcommand"}
  assert set(payload["status"].keys()) == {
    "changed_paths",
    "code_chunk_count",
    "db_path",
    "exists",
    "identifier_doc_count",
    "indexed_file_count",
    "model",
    "provider",
    "rebuild_required",
    "removed_paths",
    "stale",
  }
  assert payload["command"] == "index"
  assert payload["subcommand"] == "status"
  assert payload["status"]["rebuild_required"] is True
  assert payload["status"]["stale"] is True
  assert payload["status"]["changed_paths"] == ["app/main.py"]


def _write_index_fixture(root_dir: Path) -> None:
  (root_dir / "app").mkdir(parents=True)
  (root_dir / "app" / "main.py").write_text(
    'class Greeter:\n    def greet(self) -> str:\n        return "hi"\n',
    encoding="utf-8",
  )


def _set_schema_version(db_path: Path, schema_version: str) -> None:
  with sqlite3.connect(db_path) as connection:
    connection.execute(
      "UPDATE index_metadata SET value = ? WHERE key = ?",
      (schema_version, "schema_version"),
    )
    connection.commit()


def _fake_get_cached_embeddings(cache_dir: Path, model: object, texts: list[str], fetcher: object = None) -> list[list[float]]:
  del cache_dir, model, fetcher
  return [[float(index + 1), float(len(text))] for index, text in enumerate(texts)]
