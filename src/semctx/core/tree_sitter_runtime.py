"""Tree-sitter symbol extraction for supported languages."""

from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

import tree_sitter_go as tsgo
import tree_sitter_javascript as tsjavascript
import tree_sitter_kotlin as tskotlin
import tree_sitter_python as tspython
import tree_sitter_rust as tsrust
import tree_sitter_typescript as tstypescript
from beartype import beartype
from tree_sitter import Language, Node, Parser

@lru_cache(maxsize=1)
def _languages_by_suffix() -> dict[str, Language]:
    """Map file suffix to tree-sitter Language (lowercase suffix keys)."""
    return {
        ".py": Language(tspython.language()),
        ".js": Language(tsjavascript.language()),
        ".jsx": Language(tsjavascript.language()),
        ".ts": Language(tstypescript.language_typescript()),
        ".tsx": Language(tstypescript.language_tsx()),
        ".go": Language(tsgo.language()),
        ".rs": Language(tsrust.language()),
        ".kt": Language(tskotlin.language()),
        ".kts": Language(tskotlin.language()),
    }


def _get_language_for_suffix(suffix: str) -> Language | None:
    return _languages_by_suffix().get(suffix)


def _text(source: bytes, node: Node | None) -> str:
    if node is None:
        return ""
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _signature_first_line(source: bytes, node: Node) -> str:
    return _text(source, node).split("\n", 1)[0].strip()


def _symbol_dict(
    kind: str,
    name: str,
    source: bytes,
    node: Node,
) -> dict[str, object]:
    return {
        "kind": kind,
        "name": name,
        "signature": _signature_first_line(source, node),
        "line_start": node.start_point[0] + 1,
        "line_end": node.end_point[0] + 1,
    }


def _name_field(source: bytes, node: Node) -> str | None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    return _text(source, name_node).strip()


def _walk_children(node: Node, visit: Callable[[Node], None]) -> None:
    for i in range(node.child_count):
        child = node.child(i)
        if child is not None:
            visit(child)


def _extract_python(source: bytes, root: Node) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []

    def visit(node: Node) -> None:
        if node.type == "function_definition":
            name = _name_field(source, node)
            if name:
                out.append(_symbol_dict("function", name, source, node))
        elif node.type == "class_definition":
            name = _name_field(source, node)
            if name:
                out.append(_symbol_dict("class", name, source, node))
        _walk_children(node, visit)

    visit(root)
    return out


def _extract_javascript(source: bytes, root: Node) -> list[dict[str, object]]:
    return _extract_js_ts(source, root, include_ts_only=False)


def _extract_typescript(source: bytes, root: Node) -> list[dict[str, object]]:
    return _extract_js_ts(source, root, include_ts_only=True)


def _extract_js_ts(
    source: bytes, root: Node, *, include_ts_only: bool
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []

    def visit(node: Node) -> None:
        if node.type == "function_declaration":
            name = _name_field(source, node)
            if name:
                out.append(_symbol_dict("function", name, source, node))
        elif node.type == "class_declaration":
            name = _name_field(source, node)
            if name:
                out.append(_symbol_dict("class", name, source, node))
        elif node.type == "lexical_declaration":
            # const x = ... (variable_declarator children)
            for i in range(node.child_count):
                child = node.child(i)
                if child is None or child.type != "variable_declarator":
                    continue
                name_node = child.child_by_field_name("name")
                if name_node is None:
                    continue
                name = _text(source, name_node).strip()
                if not name:
                    continue
                out.append(_symbol_dict("constant", name, source, child))
        elif include_ts_only:
            if node.type == "interface_declaration":
                name = _name_field(source, node)
                if name:
                    out.append(_symbol_dict("interface", name, source, node))
            elif node.type == "type_alias_declaration":
                name = _name_field(source, node)
                if name:
                    out.append(_symbol_dict("type", name, source, node))
            elif node.type == "enum_declaration":
                name = _name_field(source, node)
                if name:
                    out.append(_symbol_dict("enum", name, source, node))
        _walk_children(node, visit)

    visit(root)
    return out


def _go_type_kind(type_node: Node | None) -> str:
    if type_node is None:
        return "type"
    if type_node.type == "struct_type":
        return "struct"
    if type_node.type == "interface_type":
        return "interface"
    return "type"


def _extract_go(source: bytes, root: Node) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []

    def visit(node: Node) -> None:
        if node.type == "function_declaration":
            name = _name_field(source, node)
            if name:
                out.append(_symbol_dict("function", name, source, node))
        elif node.type == "method_declaration":
            name = _name_field(source, node)
            if name:
                out.append(_symbol_dict("function", name, source, node))
        elif node.type == "type_declaration":
            for i in range(node.child_count):
                child = node.child(i)
                if child is None or child.type != "type_spec":
                    continue
                name = _name_field(source, child)
                if not name:
                    continue
                type_inner = child.child_by_field_name("type")
                kind = _go_type_kind(type_inner)
                out.append(_symbol_dict(kind, name, source, child))
        _walk_children(node, visit)

    visit(root)
    return out


def _extract_rust(source: bytes, root: Node) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []

    _ITEM_KINDS = {
        "function_item": "function",
        "struct_item": "struct",
        "enum_item": "enum",
        "trait_item": "trait",
        "type_item": "type",
        "const_item": "constant",
        "mod_item": "module",
        "static_item": "static",
    }

    def visit(node: Node) -> None:
        if node.type in _ITEM_KINDS:
            name = _name_field(source, node)
            if name:
                out.append(_symbol_dict(_ITEM_KINDS[node.type], name, source, node))
        elif node.type == "impl_item":
            trait_node = node.child_by_field_name("trait")
            type_node = node.child_by_field_name("type")
            if trait_node is not None and type_node is not None:
                trait_name = _text(source, trait_node).strip()
                type_name = _text(source, type_node).strip()
                label = f"{trait_name} for {type_name}"
                out.append(_symbol_dict("impl", label, source, node))
            elif type_node is not None:
                type_name = _text(source, type_node).strip()
                out.append(_symbol_dict("impl", type_name, source, node))
        _walk_children(node, visit)

    visit(root)
    return out


def _kotlin_class_kind(source: bytes, node: Node) -> str:
    first = _signature_first_line(source, node)
    if first.startswith("interface "):
        return "interface"
    if first.startswith("object "):
        return "object"
    return "class"


def _extract_kotlin(source: bytes, root: Node) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []

    def visit(node: Node) -> None:
        if node.type == "function_declaration":
            name = _name_field(source, node)
            if name:
                out.append(_symbol_dict("function", name, source, node))
        elif node.type == "class_declaration":
            name = _name_field(source, node)
            if name:
                kind = _kotlin_class_kind(source, node)
                out.append(_symbol_dict(kind, name, source, node))
        elif node.type == "object_declaration":
            name = _name_field(source, node)
            if name:
                out.append(_symbol_dict("object", name, source, node))
        elif node.type == "property_declaration":
            name = _name_field(source, node)
            if name:
                out.append(_symbol_dict("property", name, source, node))
        _walk_children(node, visit)

    visit(root)
    return out


_Extractor = Callable[[bytes, Node], list[dict[str, object]]]

_EXTRACTORS: dict[str, _Extractor] = {
    "python": _extract_python,
    "javascript": _extract_javascript,
    "typescript": _extract_typescript,
    "go": _extract_go,
    "rust": _extract_rust,
    "kotlin": _extract_kotlin,
}


@beartype
def extract_symbols_with_tree_sitter(
    file_path: Path, language: str
) -> list[dict[str, object]]:
    """Parse a file with tree-sitter and return top-level symbol records."""
    if language == "text":
        return []
    suffix = file_path.suffix.lower()
    lang_obj = _get_language_for_suffix(suffix)
    if lang_obj is None:
        return []
    extractor = _EXTRACTORS.get(language)
    if extractor is None:
        return []
    try:
        source = file_path.read_bytes()
    except OSError:
        return []
    parser = Parser(lang_obj)
    tree = parser.parse(source)
    symbols: list[dict[str, object]] = extractor(source, tree.root_node)
    symbols.sort(key=lambda s: (s["line_start"], s["name"]))  # type: ignore[arg-type]
    return symbols
