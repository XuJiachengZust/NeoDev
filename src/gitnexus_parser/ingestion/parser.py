"""Tree-sitter parsing: single- and multi-language, output aligned with ParseWorkerResult."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional
from fnmatch import fnmatch

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

C_BUILT_INS = frozenset({
    "printf", "scanf", "malloc", "free", "sizeof", "memcpy", "memset", "strlen",
    "strcmp", "strcpy", "strncpy", "strcat", "fopen", "fclose", "fprintf", "sprintf",
    "snprintf", "exit", "abort", "calloc", "realloc", "fread", "fwrite", "fgets",
    "fputs", "atoi", "atof", "strtol", "strtod", "NULL",
})

CPP_BUILT_INS = C_BUILT_INS | frozenset({
    "cout", "cin", "cerr", "endl", "std", "vector", "string", "map", "set",
    "make_shared", "make_unique", "move", "forward", "static_cast", "dynamic_cast",
    "const_cast", "reinterpret_cast", "begin", "end", "push_back", "emplace_back",
    "size", "empty", "find", "insert", "erase",
})

JS_BUILT_INS = frozenset({
    "console", "log", "require", "setTimeout", "setInterval", "clearTimeout",
    "clearInterval", "parseInt", "parseFloat", "JSON", "Math", "Array", "Object",
    "String", "Number", "Boolean", "Promise", "Symbol", "Map", "Set", "WeakMap",
    "WeakSet", "Error", "TypeError", "Date", "RegExp", "isNaN", "isFinite",
    "encodeURIComponent", "decodeURIComponent", "fetch", "alert", "confirm",
})

TS_BUILT_INS = JS_BUILT_INS

GO_BUILT_INS = frozenset({
    "fmt", "println", "Println", "Printf", "Sprintf", "Fprintf", "len", "cap",
    "make", "new", "append", "copy", "delete", "close", "panic", "recover",
    "print", "error", "Error", "Errorf", "String",
})

RUST_BUILT_INS = frozenset({
    "println", "eprintln", "format", "vec", "Box", "Rc", "Arc", "Some", "None",
    "Ok", "Err", "todo", "unimplemented", "unreachable", "assert", "assert_eq",
    "assert_ne", "dbg", "cfg", "include", "String", "Vec", "HashMap", "HashSet",
    "Option", "Result", "drop", "clone", "default",
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
class ExtractedModuleMember:
    filePath: str
    moduleName: str
    moduleNodeId: str
    functionNodeId: str


@dataclass
class ParseResult:
    nodes: list[ParsedNode] = field(default_factory=list)
    relationships: list[ParsedRelationship] = field(default_factory=list)
    symbols: list[ParsedSymbol] = field(default_factory=list)
    imports: list[ExtractedImport] = field(default_factory=list)
    calls: list[ExtractedCall] = field(default_factory=list)
    heritage: list[ExtractedHeritage] = field(default_factory=list)
    moduleMembers: list[ExtractedModuleMember] = field(default_factory=list)
    fileCount: int = 0


SOURCE_STORAGE_POLICY: dict[str, Any] = {
    "default": {
        "include_labels": {"Function", "Method", "Constructor"},
        "exclude_labels": {"Project", "Community", "Process", "Folder"},
    },
    "lua": {
        "include_labels": {"Function", "Method", "Constructor", "Module"},
        "exclude_labels": {"Project", "Community", "Process", "Folder"},
        "path_patterns": [
            {"include_if_path_matches": "*/models/*.lua"},
            {"include_if_name_matches": "*Model"},
        ],
    },
}


def _match_any_pattern(patterns: list[dict[str, str]] | None, file_path: str, name: str) -> bool:
    if not patterns:
        return False
    for rule in patterns:
        path_pat = rule.get("include_if_path_matches")
        if path_pat and fnmatch(file_path, path_pat):
            return True
        name_pat = rule.get("include_if_name_matches")
        if name_pat and fnmatch(name, name_pat):
            return True
    return False


def should_store_source(language: str, label: str, *, file_path: str, name: str) -> bool:
    """
    Decide whether to store sourceCode for a node based on language, label and basic metadata.
    """
    base = SOURCE_STORAGE_POLICY.get("default", {})
    lang_policy = SOURCE_STORAGE_POLICY.get(language, {})

    include_labels = set(base.get("include_labels", set()))
    include_labels.update(lang_policy.get("include_labels", []))

    exclude_labels = set(base.get("exclude_labels", set()))
    exclude_labels.update(lang_policy.get("exclude_labels", []))

    if label in exclude_labels:
        return False

    if _match_any_pattern(lang_policy.get("path_patterns"), file_path, name):
        return True

    if label in include_labels:
        return True

    return False

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
    if capture_map.get("definition.struct"):
        return "Struct"
    if capture_map.get("definition.namespace"):
        return "Namespace"
    if capture_map.get("definition.trait"):
        return "Trait"
    if capture_map.get("definition.impl"):
        return "Impl"
    if capture_map.get("definition.type_alias"):
        return "TypeAlias"
    if capture_map.get("definition.macro"):
        return "Macro"
    if capture_map.get("definition.typedef"):
        return "Typedef"
    if capture_map.get("definition.union"):
        return "Union"
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


def _extract_c_function_name(declarator_node: Node, source_bytes: bytes) -> Optional[str]:
    """Extract function name from a C/C++ declarator node."""
    if declarator_node.type == "function_declarator":
        inner = declarator_node.child_by_field_name("declarator")
        if inner:
            return _node_text(inner, source_bytes)
    elif declarator_node.type == "pointer_declarator":
        inner = declarator_node.child_by_field_name("declarator")
        if inner:
            return _extract_c_function_name(inner, source_bytes)
    return None


def _find_enclosing_function_id_c(node: Node, file_path: str, source_bytes: bytes) -> Optional[str]:
    """Walk up AST to find enclosing function (C)."""
    try:
        current = node.parent
    except Exception:
        return None
    while current:
        if current.type == "function_definition":
            decl = current.child_by_field_name("declarator")
            if decl:
                name = _extract_c_function_name(decl, source_bytes)
                if name:
                    return generate_id("Function", f"{file_path}:{name}")
        current = getattr(current, "parent", None)
    return None


def _find_enclosing_function_id_cpp(node: Node, file_path: str, source_bytes: bytes) -> Optional[str]:
    """Walk up AST to find enclosing function/method (C++)."""
    try:
        current = node.parent
    except Exception:
        return None
    while current:
        if current.type == "function_definition":
            decl = current.child_by_field_name("declarator")
            if decl:
                name = _extract_c_function_name(decl, source_bytes)
                if name:
                    label = "Function"
                    if decl.type == "function_declarator":
                        inner = decl.child_by_field_name("declarator")
                        if inner and inner.type == "qualified_identifier":
                            label = "Method"
                    return generate_id(label, f"{file_path}:{name}")
        current = getattr(current, "parent", None)
    return None


def _find_enclosing_function_id_js(node: Node, file_path: str, source_bytes: bytes) -> Optional[str]:
    """Walk up AST to find enclosing function/method (JavaScript)."""
    try:
        current = node.parent
    except Exception:
        return None
    while current:
        if current.type == "function_declaration":
            name_node = current.child_by_field_name("name")
            if name_node:
                return generate_id("Function", f"{file_path}:{_node_text(name_node, source_bytes)}")
        elif current.type == "method_definition":
            name_node = current.child_by_field_name("name")
            if name_node:
                return generate_id("Method", f"{file_path}:{_node_text(name_node, source_bytes)}")
        elif current.type == "arrow_function":
            parent = getattr(current, "parent", None)
            if parent and parent.type == "variable_declarator":
                name_node = parent.child_by_field_name("name")
                if name_node:
                    return generate_id("Function", f"{file_path}:{_node_text(name_node, source_bytes)}")
        current = getattr(current, "parent", None)
    return None


def _find_enclosing_function_id_go(node: Node, file_path: str, source_bytes: bytes) -> Optional[str]:
    """Walk up AST to find enclosing function/method (Go)."""
    try:
        current = node.parent
    except Exception:
        return None
    while current:
        if current.type == "function_declaration":
            name_node = current.child_by_field_name("name")
            if name_node:
                return generate_id("Function", f"{file_path}:{_node_text(name_node, source_bytes)}")
        elif current.type == "method_declaration":
            name_node = current.child_by_field_name("name")
            if name_node:
                return generate_id("Method", f"{file_path}:{_node_text(name_node, source_bytes)}")
        current = getattr(current, "parent", None)
    return None


def _find_enclosing_function_id_rust(node: Node, file_path: str, source_bytes: bytes) -> Optional[str]:
    """Walk up AST to find enclosing function (Rust)."""
    try:
        current = node.parent
    except Exception:
        return None
    while current:
        if current.type == "function_item":
            name_node = current.child_by_field_name("name")
            if name_node:
                return generate_id("Function", f"{file_path}:{_node_text(name_node, source_bytes)}")
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
        source_code: Optional[str] = None
        if should_store_source(language, node_label, file_path=file_path, name=node_name):
            definition_node = (
                capture_map.get("definition.function")
                or capture_map.get("definition.class")
                or capture_map.get("definition.method")
                or capture_map.get("definition.constructor")
            )
            target_node = definition_node or name_node
            source_code = _node_text(target_node, source_bytes)
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
                    "sourceCode": source_code,
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
        source_code: Optional[str] = None
        if should_store_source(language, node_label, file_path=file_path, name=node_name):
            definition_node = (
                capture_map.get("definition.class")
                or capture_map.get("definition.method")
                or capture_map.get("definition.constructor")
            )
            target_node = definition_node or name_node
            source_code = _node_text(target_node, source_bytes)
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
                    "sourceCode": source_code,
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
    module_node_ids: set[str] = set()
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
        full_name_node = capture_map.get("function.full")
        node_name = _node_text(full_name_node, source_bytes) if full_name_node else _node_text(name_node, source_bytes)
        node_id = generate_id(node_label, f"{file_path}:{node_name}")
        start_line = name_node.start_point[0] + 1
        end_line = name_node.end_point[0] + 1
        source_code: Optional[str] = None
        if should_store_source(language, node_label, file_path=file_path, name=node_name):
            definition_node = capture_map.get("definition.function")
            target_node = definition_node or name_node
            source_code = _node_text(target_node, source_bytes)
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
                    "sourceCode": source_code,
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
        module_name_node = capture_map.get("module.name")
        if node_label != "Function" or not module_name_node:
            continue
        module_name = _node_text(module_name_node, source_bytes).strip()
        if not module_name:
            continue
        module_id = generate_id("Module", f"{file_path}:{module_name}")
        if module_id not in module_node_ids:
            module_node_ids.add(module_id)
            module_start_line = module_name_node.start_point[0] + 1
            module_end_line = module_name_node.end_point[0] + 1
            result.nodes.append(
                ParsedNode(
                    id=module_id,
                    label="Module",
                    properties={
                        "name": module_name,
                        "filePath": file_path,
                        "startLine": module_start_line,
                        "endLine": module_end_line,
                        "language": language,
                        "isExported": True,
                    },
                )
            )
            result.symbols.append(
                ParsedSymbol(filePath=file_path, name=module_name, nodeId=module_id, type="Module")
            )
            module_rel_id = generate_id("DEFINES", f"{file_id}->{module_id}")
            result.relationships.append(
                ParsedRelationship(
                    id=module_rel_id,
                    sourceId=file_id,
                    targetId=module_id,
                    type="DEFINES",
                    confidence=1.0,
                    reason="",
                )
            )
        result.moduleMembers.append(
            ExtractedModuleMember(
                filePath=file_path,
                moduleName=module_name,
                moduleNodeId=module_id,
                functionNodeId=node_id,
            )
        )


def _generic_parse_file(
    file_path: str,
    content: str,
    language: str,
    result: ParseResult,
    lang_obj: Any,
    built_ins: frozenset,
    enclosing_fn,
    is_exported_fn=None,
    heritage_kind: str = "extends",
) -> None:
    """Generic parse logic shared by C/C++/JS/TS/Go/Rust."""
    parser = Parser(lang_obj)
    query_str = LANGUAGE_QUERIES.get(language)
    if not query_str:
        return
    try:
        query = Query(lang_obj, query_str)
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

        # Imports
        if "import" in capture_map and "import.source" in capture_map:
            # Skip require()-as-import that isn't actually require (JS)
            if "import.require" in capture_map:
                if _node_text(capture_map["import.require"], source_bytes) != "require":
                    continue
            raw = _parse_import_source_text(capture_map["import.source"], source_bytes)
            if raw:
                result.imports.append(
                    ExtractedImport(filePath=file_path, rawImportPath=raw, language=language)
                )
            continue

        # Calls
        if "call" in capture_map and "call.name" in capture_map:
            called_name = _node_text(capture_map["call.name"], source_bytes)
            if called_name not in built_ins:
                call_node = capture_map["call"]
                source_id = enclosing_fn(call_node, file_path, source_bytes) or file_id
                result.calls.append(
                    ExtractedCall(filePath=file_path, calledName=called_name, sourceId=source_id)
                )
            continue

        # Heritage
        if "heritage.class" in capture_map:
            class_name = _node_text(capture_map["heritage.class"], source_bytes)
            if "heritage.extends" in capture_map:
                parent_name = _node_text(capture_map["heritage.extends"], source_bytes)
                kind = heritage_kind
                # Rust impl Trait for Struct → trait-impl
                if language == "rust":
                    kind = "trait-impl"
                result.heritage.append(
                    ExtractedHeritage(filePath=file_path, className=class_name, parentName=parent_name, kind=kind)
                )
            if "heritage.implements" in capture_map:
                parent_name = _node_text(capture_map["heritage.implements"], source_bytes)
                result.heritage.append(
                    ExtractedHeritage(filePath=file_path, className=class_name, parentName=parent_name, kind="implements")
                )
            continue

        # Definitions
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
        source_code: Optional[str] = None
        if should_store_source(language, node_label, file_path=file_path, name=node_name):
            definition_node = (
                capture_map.get("definition.function")
                or capture_map.get("definition.method")
                or capture_map.get("definition.constructor")
                or capture_map.get("definition.class")
                or capture_map.get("definition.interface")
                or capture_map.get("definition.enum")
            )
            target_node = definition_node or name_node
            source_code = _node_text(target_node, source_bytes)
        is_exported = is_exported_fn(node_name) if is_exported_fn else True
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
                    "sourceCode": source_code,
                },
            )
        )
        result.symbols.append(
            ParsedSymbol(filePath=file_path, name=node_name, nodeId=node_id, type=node_label)
        )
        rel_id = generate_id("DEFINES", f"{file_id}->{node_id}")
        result.relationships.append(
            ParsedRelationship(
                id=rel_id, sourceId=file_id, targetId=node_id, type="DEFINES", confidence=1.0, reason="",
            )
        )


def _parse_c_file(file_path: str, content: str, language: str, result: ParseResult) -> None:
    try:
        import tree_sitter_c
    except ImportError:
        return
    lang = Language(tree_sitter_c.language())
    _generic_parse_file(file_path, content, language, result, lang, C_BUILT_INS, _find_enclosing_function_id_c)


def _parse_cpp_file(file_path: str, content: str, language: str, result: ParseResult) -> None:
    try:
        import tree_sitter_cpp
    except ImportError:
        return
    lang = Language(tree_sitter_cpp.language())
    _generic_parse_file(file_path, content, language, result, lang, CPP_BUILT_INS, _find_enclosing_function_id_cpp)


def _parse_javascript_file(file_path: str, content: str, language: str, result: ParseResult) -> None:
    try:
        import tree_sitter_javascript
    except ImportError:
        return
    lang = Language(tree_sitter_javascript.language())
    _generic_parse_file(file_path, content, language, result, lang, JS_BUILT_INS, _find_enclosing_function_id_js)


def _parse_typescript_file(file_path: str, content: str, language: str, result: ParseResult) -> None:
    try:
        import tree_sitter_typescript
    except ImportError:
        return
    if file_path.endswith(".tsx") or file_path.endswith(".jsx"):
        lang = Language(tree_sitter_typescript.language_tsx())
    else:
        lang = Language(tree_sitter_typescript.language_typescript())
    _generic_parse_file(file_path, content, language, result, lang, TS_BUILT_INS, _find_enclosing_function_id_js)


def _parse_go_file(file_path: str, content: str, language: str, result: ParseResult) -> None:
    try:
        import tree_sitter_go
    except ImportError:
        return
    lang = Language(tree_sitter_go.language())
    _generic_parse_file(
        file_path, content, language, result, lang, GO_BUILT_INS, _find_enclosing_function_id_go,
        is_exported_fn=lambda name: name[0].isupper() if name else False,
    )


def _parse_rust_file(file_path: str, content: str, language: str, result: ParseResult) -> None:
    try:
        import tree_sitter_rust
    except ImportError:
        return
    lang = Language(tree_sitter_rust.language())
    _generic_parse_file(
        file_path, content, language, result, lang, RUST_BUILT_INS, _find_enclosing_function_id_rust,
        is_exported_fn=lambda name: True,
        heritage_kind="trait-impl",
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
        elif language == "c":
            for path, content in group:
                _parse_c_file(path, content, language, result)
        elif language == "cpp":
            for path, content in group:
                _parse_cpp_file(path, content, language, result)
        elif language == "javascript":
            for path, content in group:
                _parse_javascript_file(path, content, language, result)
        elif language == "typescript":
            for path, content in group:
                _parse_typescript_file(path, content, language, result)
        elif language == "go":
            for path, content in group:
                _parse_go_file(path, content, language, result)
        elif language == "rust":
            for path, content in group:
                _parse_rust_file(path, content, language, result)
    return result
