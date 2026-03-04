"""Tree-sitter parsing: single- and multi-language, output aligned with ParseWorkerResult."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from tree_sitter import Language, Node, Parser, Query, QueryCursor

from gitnexus_parser.graph import generate_id

from .tree_sitter_queries import LANGUAGE_QUERIES
from .utils import get_language_from_filename

# Max file size to parse (bytes); skip larger files
MAX_FILE_BYTES = 512 * 1024

BUILT_INS = frozenset({
    "print", "len", "range", "str", "int", "float", "list", "dict", "set", "tuple",
    "open", "read", "write", "close", "append", "extend", "update",
    "super", "type", "isinstance", "issubclass", "getattr", "setattr", "hasattr",
    "enumerate", "zip", "sorted", "reversed", "min", "max", "sum", "abs",
    "True", "False", "None", "Exception", "object",
})

JAVA_BUILT_INS = frozenset({
    "System", "out", "println", "print", "equals", "hashCode", "toString",
    "length", "size", "get", "set", "add", "put", "main", "valueOf",
    "parseInt", "parseDouble", "format", "List", "Map", "Set", "Optional",
})

LUA_BUILT_INS = frozenset({
    "print", "pairs", "ipairs", "next", "type", "tostring", "tonumber",
    "require", "assert", "error", "pcall", "xpcall", "select", "unpack", "table",
    "string", "math", "io", "os", "debug", "coroutine", "package", "rawget", "rawset",
    "getmetatable", "setmetatable", "rawequal", "load", "loadfile",
})


@dataclass
class ParsedNode:
    id: str
    label: str
    properties: dict[str, Any]


@dataclass
class ParsedRelationship:
    id: str
    sourceId: str
    targetId: str
    type: str
    confidence: float
    reason: str


@dataclass
class ParsedSymbol:
    filePath: str
    name: str
    nodeId: str
    type: str


@dataclass
class ExtractedImport:
    filePath: str
    rawImportPath: str
    language: str


@dataclass
class ExtractedCall:
    filePath: str
    calledName: str
    sourceId: str


@dataclass
class ExtractedHeritage:
    filePath: str
    className: str
    parentName: str
    kind: str  # 'extends' | 'implements' | 'trait-impl'


@dataclass
class ParseResult:
    nodes: list[ParsedNode] = field(default_factory=list)
    relationships: list[ParsedRelationship] = field(default_factory=list)
    symbols: list[ParsedSymbol] = field(default_factory=list)
    imports: list[ExtractedImport] = field(default_factory=list)
    calls: list[ExtractedCall] = field(default_factory=list)
    heritage: list[ExtractedHeritage] = field(default_factory=list)
    fileCount: int = 0


def _node_text(node: Node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _get_label_from_captures(capture_map: dict[str, Node]) -> Optional[str]:
    if capture_map.get("import") or capture_map.get("call"):
        return None
    if not capture_map.get("name"):
        return None
    if capture_map.get("definition.function"):
        return "Function"
    if capture_map.get("definition.class"):
        return "Class"
    if capture_map.get("definition.interface"):
        return "Interface"
    if capture_map.get("definition.method"):
        return "Method"
    if capture_map.get("definition.constructor"):
        return "Constructor"
    if capture_map.get("definition.enum"):
        return "Enum"
    if capture_map.get("definition.annotation"):
        return "Annotation"
    return "CodeElement"


def _is_node_exported_python(name: str) -> bool:
    """Python: names not starting with _ are considered exported."""
    return not name.startswith("_")


def _find_enclosing_function_id(node: Node, file_path: str, source_bytes: bytes) -> Optional[str]:
    """Walk up AST to find enclosing function, return its generateId or None for top-level (Python)."""
    try:
        current = node.parent
    except Exception:
        return None
    while current:
        if current.type == "function_definition":
            name_node = current.child_by_field_name("name")
            if name_node:
                func_name = _node_text(name_node, source_bytes)
                return generate_id("Function", f"{file_path}:{func_name}")
        current = getattr(current, "parent", None)
    return None


def _find_enclosing_function_id_java(node: Node, file_path: str, source_bytes: bytes) -> Optional[str]:
    """Walk up AST to find enclosing method/constructor (Java)."""
    try:
        current = node.parent
    except Exception:
        return None
    while current:
        if current.type == "method_declaration":
            name_node = current.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node, source_bytes)
                return generate_id("Method", f"{file_path}:{name}")
        elif current.type == "constructor_declaration":
            name_node = current.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node, source_bytes)
                return generate_id("Constructor", f"{file_path}:{name}")
        current = getattr(current, "parent", None)
    return None


def _find_enclosing_function_id_lua(node: Node, file_path: str, source_bytes: bytes) -> Optional[str]:
    """Walk up AST to find enclosing function (Lua)."""
    try:
        current = node.parent
    except Exception:
        return None
    while current:
        if current.type == "function_declaration":
            name_node = current.child_by_field_name("name")
            if not name_node:
                for child in current.children:
                    if child.type == "identifier":
                        name_node = child
                        break
            if name_node:
                name = _node_text(name_node, source_bytes)
                return generate_id("Function", f"{file_path}:{name}")
        current = getattr(current, "parent", None)
    return None


def _parse_import_source_text(node: Node, source_bytes: bytes) -> str:
    text = _node_text(node, source_bytes)
    return re.sub(r"['\"<>]", "", text)


def _parse_python_file(
    file_path: str,
    content: str,
    language: str,
    result: ParseResult,
) -> None:
    try:
        import tree_sitter_python
    except ImportError:
        return
    lang = Language(tree_sitter_python.language())
    parser = Parser(lang)
    query_str = LANGUAGE_QUERIES.get(language)
    if not query_str:
        return
    try:
        query = Query(lang, query_str)
    except Exception:
        return
    source_bytes = content.encode("utf-8")
    if len(source_bytes) > MAX_FILE_BYTES:
        return
    try:
        tree = parser.parse(source_bytes)
    except Exception:
        return
    if not tree or not tree.root_node:
        return
    result.fileCount += 1
    cursor = QueryCursor(query)
    try:
        matches = cursor.matches(tree.root_node)
    except Exception:
        return
    file_id = generate_id("File", file_path)
    for match in matches:
        try:
            pattern_idx, captures = match
            # captures: dict[str, list[Node]] -> map to first node
            capture_map = {name: nodes[0] for name, nodes in captures.items() if nodes}
        except (TypeError, ValueError):
            continue

        # Imports
        if "import" in capture_map and "import.source" in capture_map:
            raw = _parse_import_source_text(capture_map["import.source"], source_bytes)
            result.imports.append(
                ExtractedImport(filePath=file_path, rawImportPath=raw, language=language)
            )
            continue

        # Calls
        if "call" in capture_map and "call.name" in capture_map:
            call_name_node = capture_map["call.name"]
            called_name = _node_text(call_name_node, source_bytes)
            if called_name not in BUILT_INS:
                call_node = capture_map["call"]
                source_id = _find_enclosing_function_id(call_node, file_path, source_bytes) or file_id
                result.calls.append(
                    ExtractedCall(filePath=file_path, calledName=called_name, sourceId=source_id)
                )
            continue

        # Heritage
        if "heritage.class" in capture_map:
            class_node = capture_map["heritage.class"]
            class_name = _node_text(class_node, source_bytes)
            if "heritage.extends" in capture_map:
                parent_name = _node_text(capture_map["heritage.extends"], source_bytes)
                result.heritage.append(
                    ExtractedHeritage(
                        filePath=file_path,
                        className=class_name,
                        parentName=parent_name,
                        kind="extends",
                    )
                )
            continue

        # Definition nodes
        node_label = _get_label_from_captures(capture_map)
        if not node_label:
            continue
        name_node = capture_map.get("name")
        if not name_node:
            continue
        node_name = _node_text(name_node, source_bytes)
        node_id = generate_id(node_label, f"{file_path}:{node_name}")
        start_line = name_node.start_point[0] + 1
        end_line = name_node.end_point[0] + 1
        is_exported = _is_node_exported_python(node_name)
        result.nodes.append(
            ParsedNode(
                id=node_id,
                label=node_label,
                properties={
                    "name": node_name,
                    "filePath": file_path,
                    "startLine": start_line,
                    "endLine": end_line,
                    "language": language,
                    "isExported": is_exported,
                },
            )
        )
        result.symbols.append(
            ParsedSymbol(filePath=file_path, name=node_name, nodeId=node_id, type=node_label)
        )
        rel_id = generate_id("DEFINES", f"{file_id}->{node_id}")
        result.relationships.append(
            ParsedRelationship(
                id=rel_id,
                sourceId=file_id,
                targetId=node_id,
                type="DEFINES",
                confidence=1.0,
                reason="",
            )
        )


def _parse_java_file(
    file_path: str,
    content: str,
    language: str,
    result: ParseResult,
) -> None:
    try:
        import tree_sitter_java
    except ImportError:
        return
    lang = Language(tree_sitter_java.language())
    parser = Parser(lang)
    query_str = LANGUAGE_QUERIES.get(language)
    if not query_str:
        return
    try:
        query = Query(lang, query_str)
    except Exception:
        return
    source_bytes = content.encode("utf-8")
    if len(source_bytes) > MAX_FILE_BYTES:
        return
    try:
        tree = parser.parse(source_bytes)
    except Exception:
        return
    if not tree or not tree.root_node:
        return
    result.fileCount += 1
    cursor = QueryCursor(query)
    try:
        matches = cursor.matches(tree.root_node)
    except Exception:
        return
    file_id = generate_id("File", file_path)
    for match in matches:
        try:
            pattern_idx, captures = match
            capture_map = {name: nodes[0] for name, nodes in captures.items() if nodes}
        except (TypeError, ValueError):
            continue

        if "import" in capture_map and "import.source" in capture_map:
            raw = _node_text(capture_map["import.source"], source_bytes)
            raw = re.sub(r"^\s*static\s+", "", raw).strip().rstrip(";").strip()
            if raw:
                result.imports.append(
                    ExtractedImport(filePath=file_path, rawImportPath=raw, language=language)
                )
            continue

        if "call" in capture_map and "call.name" in capture_map:
            call_name_node = capture_map["call.name"]
            called_name = _node_text(call_name_node, source_bytes)
            if called_name not in JAVA_BUILT_INS:
                call_node = capture_map["call"]
                source_id = _find_enclosing_function_id_java(call_node, file_path, source_bytes) or file_id
                result.calls.append(
                    ExtractedCall(filePath=file_path, calledName=called_name, sourceId=source_id)
                )
            continue

        if "heritage.class" in capture_map:
            class_node = capture_map["heritage.class"]
            class_name = _node_text(class_node, source_bytes)
            if "heritage.extends" in capture_map:
                parent_name = _node_text(capture_map["heritage.extends"], source_bytes)
                result.heritage.append(
                    ExtractedHeritage(
                        filePath=file_path,
                        className=class_name,
                        parentName=parent_name,
                        kind="extends",
                    )
                )
            if "heritage.implements" in capture_map:
                parent_name = _node_text(capture_map["heritage.implements"], source_bytes)
                result.heritage.append(
                    ExtractedHeritage(
                        filePath=file_path,
                        className=class_name,
                        parentName=parent_name,
                        kind="implements",
                    )
                )
            continue

        node_label = _get_label_from_captures(capture_map)
        if not node_label:
            continue
        name_node = capture_map.get("name")
        if not name_node:
            continue
        node_name = _node_text(name_node, source_bytes)
        node_id = generate_id(node_label, f"{file_path}:{node_name}")
        start_line = name_node.start_point[0] + 1
        end_line = name_node.end_point[0] + 1
        result.nodes.append(
            ParsedNode(
                id=node_id,
                label=node_label,
                properties={
                    "name": node_name,
                    "filePath": file_path,
                    "startLine": start_line,
                    "endLine": end_line,
                    "language": language,
                    "isExported": True,
                },
            )
        )
        result.symbols.append(
            ParsedSymbol(filePath=file_path, name=node_name, nodeId=node_id, type=node_label)
        )
        rel_id = generate_id("DEFINES", f"{file_id}->{node_id}")
        result.relationships.append(
            ParsedRelationship(
                id=rel_id,
                sourceId=file_id,
                targetId=node_id,
                type="DEFINES",
                confidence=1.0,
                reason="",
            )
        )


def _parse_lua_file(
    file_path: str,
    content: str,
    language: str,
    result: ParseResult,
) -> None:
    try:
        import tree_sitter_lua
    except ImportError:
        return
    lang = Language(tree_sitter_lua.language())
    parser = Parser(lang)
    query_str = LANGUAGE_QUERIES.get(language)
    if not query_str:
        return
    try:
        query = Query(lang, query_str)
    except Exception:
        return
    source_bytes = content.encode("utf-8")
    if len(source_bytes) > MAX_FILE_BYTES:
        return
    try:
        tree = parser.parse(source_bytes)
    except Exception:
        return
    if not tree or not tree.root_node:
        return
    result.fileCount += 1
    cursor = QueryCursor(query)
    try:
        matches = cursor.matches(tree.root_node)
    except Exception:
        return
    file_id = generate_id("File", file_path)
    for match in matches:
        try:
            pattern_idx, captures = match
            capture_map = {name: nodes[0] for name, nodes in captures.items() if nodes}
        except (TypeError, ValueError):
            continue

        # require("module") as import
        if "import" in capture_map and "import.source" in capture_map and "import.require" in capture_map:
            if _node_text(capture_map["import.require"], source_bytes) == "require":
                raw = _parse_import_source_text(capture_map["import.source"], source_bytes)
                if raw:
                    result.imports.append(
                        ExtractedImport(filePath=file_path, rawImportPath=raw, language=language)
                    )
            continue

        # Calls
        if "call" in capture_map and "call.name" in capture_map:
            call_name_node = capture_map["call.name"]
            called_name = _node_text(call_name_node, source_bytes)
            if called_name not in LUA_BUILT_INS:
                call_node = capture_map["call"]
                source_id = _find_enclosing_function_id_lua(call_node, file_path, source_bytes) or file_id
                result.calls.append(
                    ExtractedCall(filePath=file_path, calledName=called_name, sourceId=source_id)
                )
            continue

        # Definition nodes (function only; Lua has no class/interface)
        node_label = _get_label_from_captures(capture_map)
        if not node_label:
            continue
        name_node = capture_map.get("name")
        if not name_node:
            continue
        node_name = _node_text(name_node, source_bytes)
        node_id = generate_id(node_label, f"{file_path}:{node_name}")
        start_line = name_node.start_point[0] + 1
        end_line = name_node.end_point[0] + 1
        result.nodes.append(
            ParsedNode(
                id=node_id,
                label=node_label,
                properties={
                    "name": node_name,
                    "filePath": file_path,
                    "startLine": start_line,
                    "endLine": end_line,
                    "language": language,
                    "isExported": True,
                },
            )
        )
        result.symbols.append(
            ParsedSymbol(filePath=file_path, name=node_name, nodeId=node_id, type=node_label)
        )
        rel_id = generate_id("DEFINES", f"{file_id}->{node_id}")
        result.relationships.append(
            ParsedRelationship(
                id=rel_id,
                sourceId=file_id,
                targetId=node_id,
                type="DEFINES",
                confidence=1.0,
                reason="",
            )
        )


def parse_files(
    files: list[tuple[str, str]],
) -> ParseResult:
    """
    Parse a list of (file_path, content) for supported languages.
    Returns ParseResult with nodes, relationships, symbols, imports, calls, heritage.
    """
    result = ParseResult()
    by_lang: dict[str, list[tuple[str, str]]] = {}
    for path, content in files:
        lang = get_language_from_filename(path)
        if not lang:
            continue
        by_lang.setdefault(lang, []).append((path, content))
    for language, group in by_lang.items():
        if language == "python":
            for path, content in group:
                _parse_python_file(path, content, language, result)
        elif language == "java":
            for path, content in group:
                _parse_java_file(path, content, language, result)
        elif language == "lua":
            for path, content in group:
                _parse_lua_file(path, content, language, result)
    return result
