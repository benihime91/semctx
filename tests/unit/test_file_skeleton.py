# File skeleton unit tests.
# FEATURE: Skeleton rendering.
from pathlib import Path

from semctx.tools.file_skeleton import get_file_skeleton

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "demo_project"


def test_get_file_skeleton_lists_headers_and_symbols() -> None:
    output = get_file_skeleton(root_dir=FIXTURE_ROOT, file_path="app/main.py")

    assert "file: app/main.py" in output
    assert "language: python" in output
    assert "  - Main application module." in output
    assert "  - FEATURE: Demo Fixture." in output
    assert "  - class Greeter [3-8] :: class Greeter:" in output
    assert (
        "  - function make_message [11-13] :: def make_message(person: str) -> str:"
        in output
    )
