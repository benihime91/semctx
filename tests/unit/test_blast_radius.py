# Blast radius unit tests.
# FEATURE: External symbol usage tracing.
from pathlib import Path

from semctx.tools.blast_radius import get_blast_radius


def test_get_blast_radius_reports_external_symbol_usages(tmp_path: Path) -> None:
    _write_blast_radius_fixture(tmp_path)

    result = get_blast_radius(
        root_dir=tmp_path,
        symbol_name="Greeter",
        file_context="app/main.py",
    )

    assert "symbol: Greeter" in result
    assert "file_context: app/main.py" in result
    assert "definition: class Greeter [3-8]" in result
    assert "usages: 3" in result
    assert "- app/consumer.py:1 :: from app.main import Greeter" in result
    assert "- app/consumer.py:4 :: greeter = Greeter(prefix)" in result
    assert '- src/widget.ts:2 :: export const greeterName = "Greeter";' in result
    assert "app/main.py" not in result.split("usages:", maxsplit=1)[1]


def test_get_blast_radius_reports_none_when_symbol_has_no_external_usage(
    tmp_path: Path,
) -> None:
    _write_blast_radius_fixture(tmp_path)

    result = get_blast_radius(
        root_dir=tmp_path,
        symbol_name="message_template",
        file_context="app/helpers.py",
    )

    assert "definition: function message_template [3-4]" in result
    assert result.endswith("usages: none")


def _write_blast_radius_fixture(root_dir: Path) -> None:
    app_dir = root_dir / "app"
    src_dir = root_dir / "src"
    app_dir.mkdir(parents=True)
    src_dir.mkdir(parents=True)
    (app_dir / "main.py").write_text(
        "# Main application module.\n"
        "# FEATURE: Blast radius fixture.\n"
        "class Greeter:\n"
        "    def __init__(self, prefix: str) -> None:\n"
        "        self.prefix = prefix\n\n"
        "    def greet(self, person: str) -> str:\n"
        "        return f'{self.prefix}, {person}!'\n"
    )
    (app_dir / "consumer.py").write_text(
        "from app.main import Greeter\n\n"
        "def build_message(prefix: str, name: str) -> str:\n"
        "    greeter = Greeter(prefix)\n"
        "    return greeter.greet(name)\n"
    )
    (app_dir / "helpers.py").write_text(
        "# Helper functions.\n"
        "# FEATURE: Blast radius fixture.\n"
        "def message_template() -> str:\n"
        "    return 'template'\n"
    )
    (src_dir / "widget.ts").write_text(
        '// Widget helpers.\nexport const greeterName = "Greeter";\n'
    )
