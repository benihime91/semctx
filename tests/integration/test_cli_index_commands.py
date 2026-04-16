# Index CLI integration tests.
# FEATURE: Index lifecycle command group.
from pathlib import Path

from typer.testing import CliRunner

from semctx.cli import app


def test_index_help_lists_init_status_refresh_and_clear() -> None:
  runner = CliRunner()
  result = runner.invoke(app, ["index", "--help"], prog_name="semctx")

  assert result.exit_code == 0
  assert "init" in result.stdout
  assert "status" in result.stdout
  assert "refresh" in result.stdout
  assert "clear" in result.stdout
  assert "--provider" not in result.stdout


def test_index_init_help_uses_target_dir_flag() -> None:
  runner = CliRunner()
  result = runner.invoke(app, ["index", "init", "--help"], prog_name="semctx")

  assert result.exit_code == 0
  assert "--target-dir" in result.stdout
  assert "--target-path" not in result.stdout


def test_index_commands_run_full_lifecycle(tmp_path: Path, monkeypatch) -> None:
  _write_project(tmp_path)
  monkeypatch.setattr(
    "semctx.tools.index_building.get_cached_embeddings",
    _fake_get_cached_embeddings,
  )
  runner = CliRunner()
  base_args = ["--cache-dir", str(tmp_path / ".semctx")]

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
  stale_free_status = runner.invoke(
    app,
    [*base_args, "index", "status", "--target-dir", str(tmp_path)],
    prog_name="semctx",
  )
  (tmp_path / "app" / "main.py").write_text(
    'class Greeter:\n    def greet(self) -> str:\n        return "hello"\n',
    encoding="utf-8",
  )
  stale_status = runner.invoke(
    app,
    [*base_args, "index", "status", "--target-dir", str(tmp_path)],
    prog_name="semctx",
  )
  refresh_result = runner.invoke(
    app,
    [*base_args, "index", "refresh", "--target-dir", str(tmp_path)],
    prog_name="semctx",
  )
  clear_result = runner.invoke(app, [*base_args, "index", "clear"], prog_name="semctx")

  assert init_result.exit_code == 0
  assert "Index initialized." in init_result.stdout
  assert "Indexed files: 2" in init_result.stdout
  assert "Code chunks: 4" in init_result.stdout
  assert stale_free_status.exit_code == 0
  assert "Status: ready" in stale_free_status.stdout
  assert "Indexed files: 2" in stale_free_status.stdout
  assert stale_status.exit_code == 0
  assert "Status: stale" in stale_status.stdout
  assert "Changed paths: app/main.py" in stale_status.stdout
  assert refresh_result.exit_code == 0
  assert "Index refreshed." in refresh_result.stdout
  assert clear_result.exit_code == 0
  assert "Index cleared." in clear_result.stdout


def test_index_init_rejects_removed_provider_flag(tmp_path: Path) -> None:
  _write_project(tmp_path)
  runner = CliRunner()
  result = runner.invoke(
    app,
    [
      "--cache-dir",
      str(tmp_path / ".semctx"),
      "index",
      "init",
      "--target-dir",
      str(tmp_path),
      "--provider",
      "ollama",
    ],
    prog_name="semctx",
  )

  assert result.exit_code == 2


def _write_project(root_dir: Path) -> None:
  (root_dir / "app").mkdir(parents=True)
  (root_dir / "docs").mkdir(parents=True)
  (root_dir / "app" / "main.py").write_text(
    'class Greeter:\n    def greet(self) -> str:\n        return "hi"\n',
    encoding="utf-8",
  )
  (root_dir / "docs" / "guide.md").write_text(
    "# Overview\nIntro section.\n## Details\nMore detail here.\n",
    encoding="utf-8",
  )


def _fake_get_cached_embeddings(cache_dir: Path, model: object, texts: list[str], fetcher: object = None) -> list[list[float]]:
  del cache_dir, model, fetcher
  return [[float(index + 1), float(len(text))] for index, text in enumerate(texts)]
