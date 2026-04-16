# Search-code command unit tests.
# FEATURE: Search readiness keeps the canonical index scope.
from pathlib import Path
from typing import cast

import pytest

from semctx.commands import search_code_command
from semctx.config.runtime_settings import build_runtime_settings
from semctx.core.index_store import IndexStore
from semctx.tools.index_lifecycle import (
    ensure_search_ready_index,
    get_index_db_path,
    init_index,
    status_index,
)
from semctx.tools.semantic_search import CodeSearchMatch, semantic_code_search
from tests.unit.search_command_test_support import (
    fake_fetch_embeddings,
    use_real_index_recovery,
    write_project,
)


def test_search_code_auto_builds_missing_index(tmp_path: Path, monkeypatch) -> None:
    write_project(tmp_path)
    runtime_settings = build_runtime_settings(
        root_dir=tmp_path,
        cache_dir=tmp_path / ".semctx",
    )
    monkeypatch.setattr(search_code_command, "semantic_code_search", lambda **_: [])
    use_real_index_recovery(monkeypatch, search_code_command, ensure_search_ready_index)

    payload = search_code_command.build_search_code_payload(
        runtime_settings=runtime_settings,
        query="hello greeting",
        model="test-model",
    )

    status = status_index(runtime_settings, model="test-model")
    assert payload["provider"] == "ollama"
    assert payload["model"] == "test-model"
    assert status.exists is True
    assert status.stale is False


def test_search_code_auto_builds_from_provider_prefixed_model(
    tmp_path: Path,
    monkeypatch,
) -> None:
    write_project(tmp_path)
    runtime_settings = build_runtime_settings(
        root_dir=tmp_path,
        cache_dir=tmp_path / ".semctx",
    )
    monkeypatch.setattr(search_code_command, "semantic_code_search", lambda **_: [])
    use_real_index_recovery(monkeypatch, search_code_command, ensure_search_ready_index)

    payload = search_code_command.build_search_code_payload(
        runtime_settings=runtime_settings,
        query="hello greeting",
        model="vertex_ai/gemini-embedding-2-preview",
    )

    status = status_index(
        runtime_settings,
        model="vertex_ai/gemini-embedding-2-preview",
    )
    assert payload["provider"] == "vertex_ai"
    assert payload["model"] == "gemini-embedding-2-preview"
    assert status.provider == "vertex_ai"
    assert status.model == "gemini-embedding-2-preview"
    assert status.exists is True
    assert status.stale is False


def test_search_code_auto_refreshes_stale_index(tmp_path: Path, monkeypatch) -> None:
    write_project(tmp_path)
    runtime_settings = build_runtime_settings(
        root_dir=tmp_path,
        cache_dir=tmp_path / ".semctx",
    )
    init_index(runtime_settings, model="test-model", fetcher=fake_fetch_embeddings)
    (tmp_path / "app" / "main.py").write_text(
        'class Greeter:\n    def greet(self) -> str:\n        return "hello"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(search_code_command, "semantic_code_search", lambda **_: [])
    use_real_index_recovery(monkeypatch, search_code_command, ensure_search_ready_index)

    payload = search_code_command.build_search_code_payload(
        runtime_settings=runtime_settings,
        query="hello greeting",
        model="test-model",
    )

    status = status_index(runtime_settings, model="test-model")
    assert payload["model"] == "test-model"
    assert status.exists is True
    assert status.stale is False


def test_search_code_preserves_full_rebuild_required_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    write_project(tmp_path)
    runtime_settings = build_runtime_settings(
        root_dir=tmp_path,
        cache_dir=tmp_path / ".semctx",
    )
    init_index(runtime_settings, model="test-model", fetcher=fake_fetch_embeddings)
    monkeypatch.setattr(search_code_command, "semantic_code_search", lambda **_: [])

    with pytest.raises(ValueError, match="Full rebuild required"):
        search_code_command.build_search_code_payload(
            runtime_settings=runtime_settings,
            query="hello greeting",
            model="other-model",
        )


def test_search_code_refresh_keeps_files_outside_target_dir(
    tmp_path: Path, monkeypatch
) -> None:
    write_project(tmp_path)
    (tmp_path / "README.md").write_text("repository readme\n", encoding="utf-8")
    runtime_settings = build_runtime_settings(
        target_dir=tmp_path / "src",
        cache_dir=tmp_path / ".semctx",
    )
    init_index(runtime_settings, model="test-model", fetcher=fake_fetch_embeddings)
    (tmp_path / "src" / "widget.ts").write_text(
        "export function buildWidget(id: string): string {\n  return `${id}-updated`;\n}\n",
        encoding="utf-8",
    )
    assert status_index(runtime_settings).changed_paths == ("widget.ts",)
    monkeypatch.setattr(
        search_code_command,
        "semantic_code_search",
        lambda **kwargs: semantic_code_search(
            **kwargs,
            embedding_fetcher=fake_fetch_embeddings,
        ),
    )
    use_real_index_recovery(monkeypatch, search_code_command, ensure_search_ready_index)

    payload = search_code_command.build_search_code_payload(
        runtime_settings=runtime_settings,
        query="readme",
        model="test-model",
        target_dir="src",
    )

    indexed_paths = [
        record.relative_path
        for record in IndexStore(
            get_index_db_path(runtime_settings.cache_dir)
        ).load_indexed_files()
    ]
    matches = cast(list[CodeSearchMatch], payload["matches"])
    assert payload["target_dir"] == "src"
    assert [match.relative_path.as_posix() for match in matches] == ["widget.ts"]
    assert indexed_paths == ["widget.ts"]


def test_search_code_json_mode_keeps_payload_shape(tmp_path: Path, monkeypatch) -> None:
    write_project(tmp_path)
    runtime_settings = build_runtime_settings(
        root_dir=tmp_path,
        cache_dir=tmp_path / ".semctx",
        json_output=True,
    )
    monkeypatch.setattr(search_code_command, "semantic_code_search", lambda **_: [])
    monkeypatch.setattr(
        search_code_command,
        "ensure_search_ready_index",
        lambda **kwargs: ensure_search_ready_index(
            **kwargs,
            fetcher=fake_fetch_embeddings,
        ),
    )

    payload = search_code_command.build_search_code_payload(
        runtime_settings=runtime_settings,
        query="hello greeting",
        model="test-model",
    )

    assert payload["provider"] == "ollama"
    assert payload["model"] == "test-model"
