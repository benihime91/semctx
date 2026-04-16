# Parser unit tests.
# FEATURE: Symbol extraction.
from pathlib import Path

from semctx.core.parser import analyze_file


def test_parse_python_symbols_returns_functions_and_classes(tmp_path: Path) -> None:
  file_path = tmp_path / "sample.py"
  file_path.write_text(
    "# Sample module.\n"
    "# FEATURE: Parser test.\n"
    "class Greeter:\n"
    "    def greet(self, person: str) -> str:\n"
    "        return person\n\n"
    "def build_message(person: str) -> str:\n"
    "    return person\n"
  )

  analysis = analyze_file(file_path)

  assert analysis.language == "python"
  assert analysis.header_lines == ("Sample module.", "FEATURE: Parser test.")
  assert [(symbol.kind, symbol.name) for symbol in analysis.symbols] == [
    ("class", "Greeter"),
    ("function", "greet"),
    ("function", "build_message"),
  ]
  assert analysis.symbols[-1].signature == "def build_message(person: str) -> str:"


def test_parse_typescript_symbols_returns_interfaces_and_functions(
  tmp_path: Path,
) -> None:
  file_path = tmp_path / "widget.ts"
  file_path.write_text(
    "// Widget helpers.\n// FEATURE: Parser test.\nexport interface Widget {\n  id: string;\n}\n\nexport function buildWidget(id: string): Widget {\n  return { id };\n}\n"
  )

  analysis = analyze_file(file_path)

  assert analysis.language == "typescript"
  assert analysis.header_lines == ("Widget helpers.", "FEATURE: Parser test.")
  assert [(symbol.kind, symbol.name) for symbol in analysis.symbols] == [
    ("interface", "Widget"),
    ("function", "buildWidget"),
  ]
  assert analysis.symbols[1].signature == "function buildWidget(id: string): Widget {"


def test_parse_javascript_symbols_uses_javascript_language(tmp_path: Path) -> None:
  file_path = tmp_path / "app.js"
  file_path.write_text("// JS module.\n// FEATURE: Parser test.\nexport const VERSION = '1';\nexport function run() {\n  return 1;\n}\n")

  analysis = analyze_file(file_path)

  assert analysis.language == "javascript"
  assert [(symbol.kind, symbol.name) for symbol in analysis.symbols] == [
    ("constant", "VERSION"),
    ("function", "run"),
  ]


def test_parse_go_symbols_returns_functions_and_types(tmp_path: Path) -> None:
  file_path = tmp_path / "main.go"
  file_path.write_text(
    "// Package main.\n"
    "// FEATURE: Parser test.\n"
    "package main\n\n"
    "type Server struct {\n\tName string\n}\n\n"
    "type Handler interface {\n\tServe()\n}\n\n"
    "func main() {\n}\n\n"
    "func (s *Server) Start() error {\n\treturn nil\n}\n"
  )

  analysis = analyze_file(file_path)

  assert analysis.language == "go"
  assert [(symbol.kind, symbol.name) for symbol in analysis.symbols] == [
    ("struct", "Server"),
    ("interface", "Handler"),
    ("function", "main"),
    ("function", "Start"),
  ]


def test_parse_rust_symbols_returns_functions_and_structs(tmp_path: Path) -> None:
  file_path = tmp_path / "lib.rs"
  file_path.write_text(
    "// Rust lib.\n// FEATURE: Parser test.\npub fn foo() {}\n\npub struct Config {\n    x: i32,\n}\n\npub enum E {\n    A,\n}\n\npub trait T {}\n\nimpl T for Config {}\n"
  )

  analysis = analyze_file(file_path)

  assert analysis.language == "rust"
  kinds_names = [(symbol.kind, symbol.name) for symbol in analysis.symbols]
  assert ("function", "foo") in kinds_names
  assert ("struct", "Config") in kinds_names
  assert ("enum", "E") in kinds_names
  assert ("trait", "T") in kinds_names
  assert ("impl", "T for Config") in kinds_names


def test_parse_kotlin_symbols_returns_functions_and_classes(tmp_path: Path) -> None:
  file_path = tmp_path / "Demo.kt"
  file_path.write_text(
    "// Kotlin demo.\n"
    "// FEATURE: Parser test.\n"
    "package demo\n\n"
    "fun greet(name: String): String {\n    return name\n}\n\n"
    "data class User(val name: String)\n\n"
    "interface Repository {\n    fun load(): User\n}\n\n"
    "object Singleton {\n    val x = 1\n}\n"
  )

  analysis = analyze_file(file_path)

  assert analysis.language == "kotlin"
  kinds_names = [(symbol.kind, symbol.name) for symbol in analysis.symbols]
  assert ("function", "greet") in kinds_names
  assert ("class", "User") in kinds_names
  assert ("interface", "Repository") in kinds_names
  assert ("function", "load") in kinds_names
  assert ("object", "Singleton") in kinds_names
