# Search command target-dir runtime tests.
# FEATURE: Command payloads use canonical target_dir scope.
from pathlib import Path

import click

from semctx.commands import search_identifiers_command
from semctx.commands.runtime_context import (
    build_command_runtime_settings,
    get_effective_target_dir_label,
)
from semctx.config.runtime_settings import build_runtime_settings
from semctx.tools.index_lifecycle import ensure_search_ready_index
from tests.unit.search_command_test_support import fake_fetch_embeddings, write_project


def test_build_command_runtime_settings_overrides_target_dir(tmp_path: Path) -> None:
    runtime_settings = build_runtime_settings(
        root_dir=tmp_path,
        cache_dir=tmp_path / ".semctx",
    )
    ctx = click.Context(click.Command("search-code"), obj=runtime_settings)

    command_settings = build_command_runtime_settings(ctx, "app")

    assert command_settings.target_dir == (tmp_path / "app").resolve()
    assert command_settings.cache_dir == (tmp_path / ".semctx").resolve()
    assert command_settings.root_dir == command_settings.target_dir


def test_effective_target_dir_label_inherits_root_scope(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    runtime_settings = build_runtime_settings(
        target_dir=tmp_path / "src",
        cache_dir=tmp_path / ".semctx",
    )

    assert get_effective_target_dir_label(runtime_settings) == "src"


def test_effective_target_dir_label_preserves_explicit_override(tmp_path: Path) -> None:
    runtime_settings = build_runtime_settings(
        target_dir=tmp_path / "src",
        cache_dir=tmp_path / ".semctx",
    )

    assert get_effective_target_dir_label(runtime_settings, "nested") == "nested"


def test_search_identifiers_json_mode_keeps_payload_shape(
    tmp_path: Path,
    monkeypatch,
) -> None:
    write_project(tmp_path)
    runtime_settings = build_runtime_settings(
        root_dir=tmp_path,
        cache_dir=tmp_path / ".semctx",
        json_output=True,
    )
    monkeypatch.setattr(
        search_identifiers_command, "semantic_identifier_search", lambda **_: []
    )
    monkeypatch.setattr(
        search_identifiers_command,
        "ensure_search_ready_index",
        lambda **kwargs: ensure_search_ready_index(
            **kwargs,
            fetcher=fake_fetch_embeddings,
        ),
    )

    payload = search_identifiers_command.build_search_identifiers_payload(
        runtime_settings=runtime_settings,
        query="widget builder",
        model="test-model",
    )

    assert payload["provider"] == "ollama"
    assert payload["model"] == "test-model"
