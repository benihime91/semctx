# Index manifest unit tests.
# FEATURE: Metadata rebuild and refresh planning.
from pathlib import Path

from semctx.core.index_manifest import (
    build_index_metadata,
    build_indexed_file_record,
    needs_full_rebuild,
    plan_refresh,
)
from semctx.core.index_models import IndexMetadata, IndexedFileRecord
from semctx.core.index_schema import SCHEMA_VERSION


def test_needs_full_rebuild_when_provider_changes() -> None:
    old = IndexMetadata("1", "ollama", "model-a", "1", "1", "abc")
    new = IndexMetadata("1", "gemini", "model-a", "1", "1", "abc")

    assert needs_full_rebuild(old, new) is True


def test_build_index_metadata_uses_schema_version_defaults() -> None:
    metadata = build_index_metadata(
        provider="ollama",
        model="nomic-embed-text-v2-moe:latest",
        ignore_fingerprint="fingerprint-1",
    )

    assert metadata == IndexMetadata(
        SCHEMA_VERSION,
        "ollama",
        "nomic-embed-text-v2-moe:latest",
        "2",
        "2",
        "fingerprint-1",
    )


def test_build_indexed_file_record_uses_stat_and_hash(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text("print('hello')\n", encoding="utf-8")

    record = build_indexed_file_record(file_path, "src/sample.py")

    assert record.relative_path == "src/sample.py"
    assert record.size_bytes == file_path.stat().st_size
    assert record.mtime_ns == file_path.stat().st_mtime_ns
    assert len(record.content_hash) == 64


def test_plan_refresh_marks_changed_and_removed_paths() -> None:
    metadata = IndexMetadata("1", "ollama", "model-a", "1", "1", "abc")
    stored_files = (
        IndexedFileRecord("src/a.py", 10, 100, "hash-a"),
        IndexedFileRecord("src/b.py", 11, 110, "hash-b"),
    )
    current_files = (
        IndexedFileRecord("src/a.py", 10, 100, "hash-a"),
        IndexedFileRecord("src/c.py", 12, 120, "hash-c"),
    )

    plan = plan_refresh(metadata, metadata, stored_files, current_files)

    assert plan.rebuild_required is False
    assert plan.changed_paths == ("src/c.py",)
    assert plan.removed_paths == ("src/b.py",)


def test_plan_refresh_requires_rebuild_when_metadata_changes() -> None:
    stored_metadata = IndexMetadata("1", "ollama", "model-a", "1", "1", "abc")
    current_metadata = IndexMetadata("1", "ollama", "model-b", "1", "1", "abc")
    current_files = (IndexedFileRecord("src/a.py", 10, 100, "hash-a"),)

    plan = plan_refresh(stored_metadata, current_metadata, (), current_files)

    assert plan.rebuild_required is True
    assert plan.changed_paths == ("src/a.py",)
    assert plan.removed_paths == ()


def test_needs_full_rebuild_when_schema_version_changes() -> None:
    old = IndexMetadata("2", "ollama", "model-a", "1", "2", "abc")
    new = IndexMetadata(SCHEMA_VERSION, "ollama", "model-a", "1", "2", "abc")

    assert needs_full_rebuild(old, new) is True
