# Semantic search test fixtures.
# FEATURE: Shared file writers and fake embeddings for search regressions.
from pathlib import Path


def write_demo_files(root_dir: Path) -> None:
    app_dir = root_dir / "app"
    src_dir = root_dir / "src"
    app_dir.mkdir(parents=True)
    src_dir.mkdir(parents=True)
    (app_dir / "main.py").write_text(
        "# Main greeting module.\n# FEATURE: Search fixture.\ndef greet(person: str) -> str:\n    return f'Hello, {person}'\n\ndef make_message(person: str) -> str:\n    return greet(person)\n",
        encoding="utf-8",
    )
    (src_dir / "widget.ts").write_text(
        "// Widget helpers.\n// FEATURE: Search fixture.\nexport function buildWidget(id: string) {\n  return { id };\n}\n",
        encoding="utf-8",
    )


def write_broad_query_files(root_dir: Path) -> None:
    tools_dir = root_dir / "semctx" / "tools"
    core_dir = root_dir / "semctx" / "core"
    tools_dir.mkdir(parents=True)
    core_dir.mkdir(parents=True)
    (tools_dir / "index_status.py").write_text(
        "# SQLite index lifecycle status.\n# FEATURE: Refresh visibility.\ndef open_sqlite_store() -> str:\n    return 'sqlite store'\n\ndef refresh_index_state() -> str:\n    return 'index state'\n\ndef render_status_summary() -> str:\n    return 'ready'\n",
        encoding="utf-8",
    )
    (core_dir / "sqlite_cleanup.py").write_text(
        "# Cleanup helpers.\n# FEATURE: Remove stale embeddings.\ndef cleanup_sqlite_refresh_cache() -> str:\n    return 'cleanup cache'\n",
        encoding="utf-8",
    )


def write_intent_ranking_files(root_dir: Path) -> None:
    tools_dir = root_dir / "semctx" / "tools"
    core_dir = root_dir / "semctx" / "core"
    tools_dir.mkdir(parents=True)
    core_dir.mkdir(parents=True)
    (core_dir / "index_metadata.py").write_text(
        "# Metadata helpers.\n# FEATURE: Index records.\ndef build_index_metadata() -> str:\n    return 'metadata payload'\n",
        encoding="utf-8",
    )
    (tools_dir / "index_notes.py").write_text(
        "# Index metadata notes.\n# FEATURE: Planning text.\ndef describe_notes() -> str:\n    return 'index metadata overview'\n",
        encoding="utf-8",
    )
    (tools_dir / "how_refresh_works.py").write_text(
        "# How refresh works across the index workflow.\n# FEATURE: Refresh workflow steps.\ndef how_refresh_works() -> str:\n    return 'workflow status'\n",
        encoding="utf-8",
    )
    (core_dir / "cache_state.py").write_text(
        "# Cache storage.\n# FEATURE: Persist state values.\ndef cache_state_body() -> str:\n    return 'state cache values'\n",
        encoding="utf-8",
    )


def write_diversity_query_files(root_dir: Path) -> None:
    tools_dir = root_dir / "semctx" / "tools"
    tools_dir.mkdir(parents=True)
    (tools_dir / "index_refresh.py").write_text(
        "# SQLite index refresh flow.\n# FEATURE: Primary implementation.\nclass IndexRefreshEngine:\n    def refresh_sqlite_index(self) -> str:\n        return 'sqlite index refresh workflow'\n\ndef refresh_index_status() -> str:\n    return 'sqlite index refresh status'\n\ndef rebuild_sqlite_index() -> str:\n    return 'sqlite index refresh rebuild'\n",
        encoding="utf-8",
    )
    (tools_dir / "index_refresh_helper.py").write_text(
        "# SQLite index refresh helper.\n# FEATURE: Supporting helper.\ndef cleanup_sqlite_index_refresh() -> str:\n    return 'sqlite index refresh helper'\n",
        encoding="utf-8",
    )
    (tools_dir / "refresh_guidance.py").write_text(
        "# SQLite refresh guidance.\n# FEATURE: Supporting notes.\ndef summarize_index_workflow() -> str:\n    return 'sqlite refresh index workflow notes'\n",
        encoding="utf-8",
    )
    (tools_dir / "refresh_runner.py").write_text(
        "# Refresh runner.\n# FEATURE: Execute sqlite index refresh jobs.\ndef run_refresh_job() -> str:\n    return 'sqlite index refresh runner'\n",
        encoding="utf-8",
    )


def fake_fetch_embeddings(texts: list[str], model: object) -> list[list[float]]:
    del model
    return [vector_for_text(text) for text in texts]


def vector_for_text(text: str) -> list[float]:
    lowered_text = text.lower()
    return [
        1.0
        if any(
            token in lowered_text for token in ("greet", "greeting", "hello", "message")
        )
        else 0.0,
        1.0 if any(token in lowered_text for token in ("widget", "component")) else 0.0,
        1.0 if any(token in lowered_text for token in ("build", "builder")) else 0.0,
        1.0 if "sqlite" in lowered_text else 0.0,
        1.0 if "index" in lowered_text else 0.0,
        1.0 if "refresh" in lowered_text else 0.0,
    ]
