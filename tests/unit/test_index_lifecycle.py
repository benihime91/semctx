# Index lifecycle unit tests.
# FEATURE: Init, status, refresh, and clear workflows.
import sqlite3
from pathlib import Path

import pytest

from semctx.config.runtime_settings import build_runtime_settings
from semctx.core.index_schema import SCHEMA_VERSION
from semctx.core.index_store import IndexStore
from semctx.tools.index_lifecycle import (
  clear_index,
  get_requested_index_db_path,
  init_index,
  refresh_index,
  status_index,
)
from semctx.tools.index_status import IndexStatus, render_index_status

MODEL_SELECTOR = "ollama/test-model"


def test_index_lifecycle_init_status_refresh_and_clear(tmp_path: Path) -> None:
  _write_project(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )

  initial_status = init_index(
    runtime_settings,
    model=MODEL_SELECTOR,
    fetcher=_fake_fetch_embeddings,
  )

  assert initial_status.exists is True
  assert initial_status.stale is False
  assert initial_status.provider == "ollama"
  assert initial_status.indexed_file_count == 1
  assert initial_status.code_chunk_count == 2
  assert initial_status.identifier_doc_count == 2

  (tmp_path / "app" / "main.py").write_text(
    'class Greeter:\n    def greet(self) -> str:\n        return "hello"\n',
    encoding="utf-8",
  )

  stale_status = status_index(runtime_settings, model=MODEL_SELECTOR)

  assert stale_status.exists is True
  assert stale_status.stale is True
  assert stale_status.changed_paths == ("app/main.py",)

  refreshed_status = refresh_index(
    runtime_settings,
    model=MODEL_SELECTOR,
    fetcher=_fake_fetch_embeddings,
  )

  assert refreshed_status.exists is True
  assert refreshed_status.stale is False
  assert refreshed_status.changed_paths == ()
  assert clear_index(runtime_settings, model=MODEL_SELECTOR) is True
  assert status_index(runtime_settings, model=MODEL_SELECTOR).exists is False


def test_index_lifecycle_init_indexes_markdown_files(tmp_path: Path) -> None:
  _write_project(tmp_path)
  (tmp_path / "docs").mkdir(parents=True)
  (tmp_path / "docs" / "guide.md").write_text(
    "# Overview\nIntro section.\n## Details\nMore detail here.\n",
    encoding="utf-8",
  )
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )

  initial_status = init_index(runtime_settings, model=MODEL_SELECTOR, fetcher=_fake_fetch_embeddings)
  store = IndexStore(get_requested_index_db_path(runtime_settings.cache_dir, None, MODEL_SELECTOR))

  assert initial_status.indexed_file_count == 2
  assert initial_status.code_chunk_count == 4
  assert initial_status.identifier_doc_count == 2
  assert [record.relative_path for record in store.load_indexed_files()] == [
    "app/main.py",
    "docs/guide.md",
  ]
  assert [record.relative_path for record in store.load_code_chunks()] == [
    "app/main.py",
    "app/main.py",
    "docs/guide.md",
    "docs/guide.md",
  ]


def test_index_lifecycle_requires_full_rebuild_when_schema_changes(
  tmp_path: Path,
) -> None:
  _write_project(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )

  init_index(runtime_settings, model=MODEL_SELECTOR, fetcher=_fake_fetch_embeddings)
  store = IndexStore(get_requested_index_db_path(runtime_settings.cache_dir, None, MODEL_SELECTOR))
  metadata = store.load_metadata()

  assert metadata is not None
  assert metadata.schema_version == SCHEMA_VERSION

  _set_schema_version(get_requested_index_db_path(runtime_settings.cache_dir, None, MODEL_SELECTOR), "2")

  rebuild_status = status_index(runtime_settings, model=MODEL_SELECTOR)

  assert rebuild_status.exists is True
  assert rebuild_status.stale is True
  assert rebuild_status.rebuild_required is True
  assert rebuild_status.changed_paths == ("app/main.py",)
  assert render_index_status(rebuild_status).splitlines()[0] == "Status: rebuild required"
  with pytest.raises(ValueError, match="Full rebuild required"):
    refresh_index(runtime_settings, model=MODEL_SELECTOR, fetcher=_fake_fetch_embeddings)


def test_render_index_status_prefers_canonical_model_selector(tmp_path: Path) -> None:
  _write_project(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )

  status = init_index(
    runtime_settings,
    model="vertex_ai/gemini-embedding-2-preview",
    fetcher=_fake_fetch_embeddings,
  )
  rendered = render_index_status(status)

  assert "Model: vertex_ai/gemini-embedding-2-preview" in rendered
  assert "Provider:" not in rendered


def test_index_lifecycle_uses_canonical_target_dir_identity(tmp_path: Path) -> None:
  _write_target_dir_project(tmp_path)
  cache_dir = tmp_path / ".semctx"
  runtime_settings = build_runtime_settings(
    target_dir=tmp_path / "src",
    cache_dir=cache_dir,
  )

  init_index(runtime_settings, model=MODEL_SELECTOR, fetcher=_fake_fetch_embeddings)
  store = IndexStore(get_requested_index_db_path(cache_dir, None, MODEL_SELECTOR))
  metadata = store.load_metadata()

  assert metadata is not None
  assert metadata.target_dir_identity == str((tmp_path / "src").resolve())
  assert [record.relative_path for record in store.load_indexed_files()] == ["widget.ts"]
  assert status_index(build_runtime_settings(target_dir=tmp_path / "." / "src", cache_dir=cache_dir), model=MODEL_SELECTOR).rebuild_required is False


def test_index_lifecycle_requires_rebuild_for_legacy_scope_metadata(
  tmp_path: Path,
) -> None:
  _write_target_dir_project(tmp_path)
  cache_dir = tmp_path / ".semctx"
  runtime_settings = build_runtime_settings(
    target_dir=tmp_path / "src",
    cache_dir=cache_dir,
  )

  init_index(runtime_settings, model=MODEL_SELECTOR, fetcher=_fake_fetch_embeddings)
  _set_metadata_value(get_requested_index_db_path(cache_dir, None, MODEL_SELECTOR), "target_dir_identity", "")

  rebuild_status = status_index(runtime_settings, model=MODEL_SELECTOR)

  assert rebuild_status.exists is True
  assert rebuild_status.stale is True
  assert rebuild_status.rebuild_required is True
  assert rebuild_status.changed_paths == ("widget.ts",)


def test_index_lifecycle_requires_explicit_model_selection(tmp_path: Path) -> None:
  _write_project(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )

  with pytest.raises(ValueError, match="Embedding provider is required"):
    init_index(runtime_settings, fetcher=_fake_fetch_embeddings)
  with pytest.raises(ValueError, match="Embedding provider is required"):
    status_index(runtime_settings)
  with pytest.raises(ValueError, match="Embedding provider is required"):
    refresh_index(runtime_settings, fetcher=_fake_fetch_embeddings)
  with pytest.raises(ValueError, match="Embedding provider is required"):
    clear_index(runtime_settings)


def test_init_index_creates_namespaced_parent_before_rebuild(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  _write_project(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )
  db_path = get_requested_index_db_path(runtime_settings.cache_dir, None, MODEL_SELECTOR)
  observed_parent_exists: list[bool] = []

  def fake_rebuild_ready_index(*args: object) -> IndexStatus:
    rebuild_db_path = args[-1]
    assert isinstance(rebuild_db_path, Path)
    observed_parent_exists.append(rebuild_db_path.parent.exists())
    return IndexStatus(False, False, False, "ollama", "test-model", 0, 0, 0, (), (), rebuild_db_path)

  monkeypatch.setattr("semctx.tools.index_lifecycle.rebuild_ready_index", fake_rebuild_ready_index)

  status = init_index(runtime_settings, model=MODEL_SELECTOR, fetcher=_fake_fetch_embeddings)

  assert db_path.parent.exists() is True
  assert observed_parent_exists == [True]
  assert status.db_path == db_path


def test_refresh_index_creates_namespaced_parent_before_full_rebuild(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  _write_project(tmp_path)
  runtime_settings = build_runtime_settings(
    root_dir=tmp_path,
    cache_dir=tmp_path / ".semctx",
  )
  db_path = get_requested_index_db_path(runtime_settings.cache_dir, None, MODEL_SELECTOR)
  observed_parent_exists: list[bool] = []

  monkeypatch.setattr(
    "semctx.tools.index_lifecycle.status_index",
    lambda *args, **kwargs: IndexStatus(False, False, False, None, None, 0, 0, 0, (), (), db_path),
  )

  def fake_rebuild_ready_index(*args: object) -> IndexStatus:
    rebuild_db_path = args[-1]
    assert isinstance(rebuild_db_path, Path)
    observed_parent_exists.append(rebuild_db_path.parent.exists())
    return IndexStatus(False, False, False, "ollama", "test-model", 0, 0, 0, (), (), rebuild_db_path)

  monkeypatch.setattr("semctx.tools.index_lifecycle.rebuild_ready_index", fake_rebuild_ready_index)

  status = refresh_index(runtime_settings, model=MODEL_SELECTOR, full=True, fetcher=_fake_fetch_embeddings)

  assert db_path.parent.exists() is True
  assert observed_parent_exists == [True]
  assert status.db_path == db_path


def _write_project(root_dir: Path) -> None:
  (root_dir / "app").mkdir(parents=True)
  (root_dir / "app" / "main.py").write_text(
    'class Greeter:\n    def greet(self) -> str:\n        return "hi"\n',
    encoding="utf-8",
  )


def _write_target_dir_project(root_dir: Path) -> None:
  (root_dir / "src").mkdir(parents=True)
  (root_dir / "README.md").write_text("root docs\n", encoding="utf-8")
  (root_dir / ".gitignore").write_text("*.md\n", encoding="utf-8")
  (root_dir / "src" / "widget.ts").write_text(
    "export function buildWidget(id: string): string {\n  return id;\n}\n",
    encoding="utf-8",
  )


def _set_schema_version(db_path: Path, schema_version: str) -> None:
  _set_metadata_value(db_path, "schema_version", schema_version)


def _set_metadata_value(db_path: Path, key: str, value: str) -> None:
  with sqlite3.connect(db_path) as connection:
    connection.execute(
      "UPDATE index_metadata SET value = ? WHERE key = ?",
      (value, key),
    )
    connection.commit()


def _fake_fetch_embeddings(texts: list[str], model: object) -> list[list[float]]:
  del model
  return [[float(index + 1), float(len(text))] for index, text in enumerate(texts)]
