# Semantic identifier test fixtures.
# FEATURE: Shared file writers and fake embeddings for identifier regressions.
from pathlib import Path


def write_demo_files(root_dir: Path) -> None:
    app_dir = root_dir / "app"
    src_dir = root_dir / "src"
    app_dir.mkdir(parents=True)
    src_dir.mkdir(parents=True)
    (app_dir / "main.py").write_text(
        "# Main greeting module.\n# FEATURE: Search fixture.\nclass Greeter:\n    def greet(self, person: str) -> str:\n        return f'Hello, {person}'\n\ndef make_message(person: str) -> str:\n    return Greeter().greet(person)\n",
        encoding="utf-8",
    )
    (src_dir / "widget.ts").write_text(
        "// Widget helpers.\n// FEATURE: Search fixture.\nexport interface Widget {\n  id: string;\n}\n\nexport function buildWidget(id: string): Widget {\n  return { id };\n}\n",
        encoding="utf-8",
    )
    (src_dir / "index_status.ts").write_text(
        "// Index status helpers.\n// FEATURE: Metadata search fixture.\nexport interface IndexMetadata {\n  status: string;\n}\n\nexport function buildIndexMetadata(status: string): IndexMetadata {\n  return { status };\n}\n\nexport function renderIndexStatus(status: string): string {\n  return status.toUpperCase();\n}\n\nexport function buildIndexView(status: string): string {\n  return `view:${status}`;\n}\n",
        encoding="utf-8",
    )


def write_identifier_intent_files(root_dir: Path) -> None:
    src_dir = root_dir / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "index_status.ts").write_text(
        "// SQLite index refresh helpers.\n// FEATURE: Index status workflow.\nexport function buildIndexMetadata(status: string): string {\n  return status;\n}\n\nexport function refreshSqliteIndexState(status: string): string {\n  return `refresh:${status}`;\n}\n\nexport function renderIndexStatus(status: string): string {\n  return status.toUpperCase();\n}\n",
        encoding="utf-8",
    )
    (src_dir / "refresh_workflow.ts").write_text(
        "// How refresh works across the index workflow.\n// FEATURE: Workflow search fixture.\nexport function howRefreshWorks(): string {\n  return 'workflow';\n}\n",
        encoding="utf-8",
    )
    (src_dir / "sqlite_cleanup.ts").write_text(
        "// SQLite cleanup helpers.\n// FEATURE: Clear stale cache state.\nexport function cleanupCacheState(): string {\n  return 'cleanup';\n}\n",
        encoding="utf-8",
    )


def write_direct_hit_identifier_files(root_dir: Path) -> None:
    src_dir = root_dir / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "index_metadata.ts").write_text(
        "// Index metadata helpers.\n// FEATURE: Direct identifier hits.\nexport function buildIndexMetadata(status: string): string {\n  return status;\n}\n\nexport function buildIndexMetadataView(status: string): string {\n  return `view:${status}`;\n}\n\nexport function buildIndexMetadataCache(status: string): string {\n  return `cache:${status}`;\n}\n",
        encoding="utf-8",
    )


def fake_fetch_embeddings(texts: list[str], model: object) -> list[list[float]]:
    del model
    return [vector_for_text(text) for text in texts]


def vector_for_text(text: str) -> list[float]:
    lowered_text = text.lower()
    return [
        1.0 if "widget" in lowered_text else 0.0,
        1.0 if any(token in lowered_text for token in ("build", "metadata")) else 0.0,
        1.0 if any(token in lowered_text for token in ("sqlite", "index")) else 0.0,
        1.0 if "refresh" in lowered_text else 0.0,
        1.0
        if any(token in lowered_text for token in ("how", "works", "workflow"))
        else 0.0,
    ]
