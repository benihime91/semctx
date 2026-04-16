# Search-identifiers command unit tests.
# FEATURE: Search readiness keeps the canonical index scope.
from pathlib import Path
from typing import cast

import pytest

from semctx.commands import search_identifiers_command
from semctx.config.runtime_settings import build_runtime_settings
from semctx.core.index_store import IndexStore
from semctx.tools.index_lifecycle import (
    ensure_search_ready_index,
    get_index_db_path,
    init_index,
    status_index,
)
from semctx.tools.semantic_identifiers import (
    IdentifierSearchMatch,
    semantic_identifier_search,
)
from tests.unit.search_command_test_support import (
    fake_fetch_embeddings,
    use_real_index_recovery,
    write_project,
)


def test_search_identifiers_auto_builds_missing_index(
    tmp_path: Path,
    monkeypatch,
) -> None:
    write_project(tmp_path)
    runtime_settings = build_runtime_settings(
        root_dir=tmp_path,
        cache_dir=tmp_path / ".semctx",
    )
    monkeypatch.setattr(
        search_identifiers_command, "semantic_identifier_search", lambda **_: []
    )
    use_real_index_recovery(
        monkeypatch,
        search_identifiers_command,
        ensure_search_ready_index,
    )

    payload = search_identifiers_command.build_search_identifiers_payload(
        runtime_settings=runtime_settings,
        query="widget builder",
        model="test-model",
    )

    status = status_index(runtime_settings, model="test-model")
    assert payload["provider"] == "ollama"
    assert payload["model"] == "test-model"
    assert status.exists is True
    assert status.stale is False


def test_search_identifiers_auto_builds_from_provider_prefixed_model(
    tmp_path: Path,
    monkeypatch,
) -> None:
    write_project(tmp_path)
    runtime_settings = build_runtime_settings(
        root_dir=tmp_path,
        cache_dir=tmp_path / ".semctx",
    )
    monkeypatch.setattr(
        search_identifiers_command, "semantic_identifier_search", lambda **_: []
    )
    use_real_index_recovery(
        monkeypatch,
        search_identifiers_command,
        ensure_search_ready_index,
    )

    payload = search_identifiers_command.build_search_identifiers_payload(
        runtime_settings=runtime_settings,
        query="widget builder",
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


def test_search_identifiers_auto_refreshes_stale_index(
    tmp_path: Path,
    monkeypatch,
) -> None:
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
    monkeypatch.setattr(
        search_identifiers_command, "semantic_identifier_search", lambda **_: []
    )
    use_real_index_recovery(
        monkeypatch,
        search_identifiers_command,
        ensure_search_ready_index,
    )

    payload = search_identifiers_command.build_search_identifiers_payload(
        runtime_settings=runtime_settings,
        query="widget builder",
        model="test-model",
    )

    status = status_index(runtime_settings, model="test-model")
    assert payload["model"] == "test-model"
    assert status.exists is True
    assert status.stale is False


def test_search_identifiers_preserves_full_rebuild_required_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    write_project(tmp_path)
    runtime_settings = build_runtime_settings(
        root_dir=tmp_path,
        cache_dir=tmp_path / ".semctx",
    )
    init_index(runtime_settings, model="test-model", fetcher=fake_fetch_embeddings)
    monkeypatch.setattr(
        search_identifiers_command, "semantic_identifier_search", lambda **_: []
    )

    with pytest.raises(ValueError, match="Full rebuild required"):
        search_identifiers_command.build_search_identifiers_payload(
            runtime_settings=runtime_settings,
            query="widget builder",
            model="other-model",
        )


def test_search_identifiers_refresh_keeps_files_outside_query_depth(
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
        search_identifiers_command,
        "semantic_identifier_search",
        lambda **kwargs: semantic_identifier_search(
            **kwargs,
            embedding_fetcher=fake_fetch_embeddings,
        ),
    )
    use_real_index_recovery(
        monkeypatch,
        search_identifiers_command,
        ensure_search_ready_index,
    )

    payload = search_identifiers_command.build_search_identifiers_payload(
        runtime_settings=runtime_settings,
        query="widget builder",
        model="test-model",
        depth_limit=0,
        target_dir="src",
    )

    indexed_paths = [
        record.relative_path
        for record in IndexStore(
            get_index_db_path(runtime_settings.cache_dir)
        ).load_indexed_files()
    ]
    matches = cast(list[IdentifierSearchMatch], payload["matches"])
    assert payload["depth_limit"] == 0
    assert payload["target_dir"] == "src"
    assert [match.relative_path.as_posix() for match in matches] == ["widget.ts"]
    assert indexed_paths == ["widget.ts"]
