"""TypeScript 语言解析测试。"""

import pytest

from gitnexus_parser.graph import generate_id
from gitnexus_parser.ingestion.parser import parse_files


def test_parse_ts_function_class_interface():
    pytest.importorskip("tree_sitter_typescript")
    content = """
import { Component } from 'react';

interface Shape {
    area(): number;
}

enum Direction {
    Up,
    Down,
}

type Point = { x: number; y: number };

function calculate(s: Shape): number {
    return s.area();
}

class Circle {
    draw() {}
}

const add = (a: number, b: number): number => a + b;
""".strip()
    file_path = "shapes.ts"
    result = parse_files([(file_path, content)])

    labels = {n.properties["name"]: n.label for n in result.nodes}
    assert labels.get("Shape") == "Interface"
    assert labels.get("Direction") == "Enum"
    assert labels.get("Point") == "TypeAlias"
    assert labels.get("calculate") == "Function"
    assert labels.get("Circle") == "Class"
    assert labels.get("draw") == "Method"
    assert labels.get("add") == "Function"


def test_parse_ts_imports():
    pytest.importorskip("tree_sitter_typescript")
    content = "import { foo } from './foo';\nimport bar from 'bar';\n"
    result = parse_files([("app.ts", content)])
    raw_imports = [i.rawImportPath for i in result.imports]
    assert "./foo" in raw_imports
    assert "bar" in raw_imports


def test_parse_ts_heritage_extends():
    pytest.importorskip("tree_sitter_typescript")
    content = """
class Base {}
class Derived extends Base {}
""".strip()
    result = parse_files([("heritage.ts", content)])
    assert any(
        h.className == "Derived" and h.parentName == "Base" and h.kind == "extends"
        for h in result.heritage
    )


def test_parse_ts_heritage_implements():
    pytest.importorskip("tree_sitter_typescript")
    content = """
interface Drawable {
    draw(): void;
}
class Circle implements Drawable {
    draw() {}
}
""".strip()
    result = parse_files([("impl.ts", content)])
    assert any(
        h.className == "Circle" and h.parentName == "Drawable" and h.kind == "implements"
        for h in result.heritage
    )


def test_parse_tsx_file():
    """TSX files should use the tsx sub-language."""
    pytest.importorskip("tree_sitter_typescript")
    content = """
import React from 'react';

function App() {
    return <div>Hello</div>;
}
""".strip()
    result = parse_files([("App.tsx", content)])
    labels = {n.properties["name"]: n.label for n in result.nodes}
    assert labels.get("App") == "Function"


def test_parse_ts_calls():
    pytest.importorskip("tree_sitter_typescript")
    content = """
function main() {
    helper();
    obj.method();
}
""".strip()
    result = parse_files([("call.ts", content)])
    called = {c.calledName for c in result.calls}
    assert "helper" in called
    assert "method" in called
