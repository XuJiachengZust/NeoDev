"""C++ 语言解析测试。"""

import pytest

from gitnexus_parser.graph import generate_id
from gitnexus_parser.ingestion.parser import parse_files


def test_parse_cpp_class_and_methods():
    pytest.importorskip("tree_sitter_cpp")
    content = """
#include <iostream>

namespace Graphics {

class Shape {
public:
    void draw() {}
};

struct Point {
    int x, y;
};

enum Color { RED, GREEN, BLUE };

}

void render() {
    Graphics::Shape s;
}
""".strip()
    file_path = "graphics.cpp"
    result = parse_files([(file_path, content)])

    labels = {n.properties["name"]: n.label for n in result.nodes}
    assert labels.get("Shape") == "Class"
    assert labels.get("Point") == "Struct"
    assert labels.get("Color") == "Enum"
    assert labels.get("Graphics") == "Namespace"
    assert labels.get("render") == "Function"


def test_parse_cpp_heritage():
    pytest.importorskip("tree_sitter_cpp")
    content = """
class Base {};
class Derived : public Base {};
""".strip()
    result = parse_files([("heritage.cpp", content)])
    assert any(
        h.className == "Derived" and h.parentName == "Base" and h.kind == "extends"
        for h in result.heritage
    )


def test_parse_cpp_imports():
    pytest.importorskip("tree_sitter_cpp")
    content = '#include <vector>\n#include "myclass.h"\nvoid foo() {}\n'
    result = parse_files([("test.cpp", content)])
    raw_imports = [i.rawImportPath for i in result.imports]
    assert "vector" in raw_imports
    assert "myclass.h" in raw_imports


def test_parse_cpp_calls():
    pytest.importorskip("tree_sitter_cpp")
    content = """
void caller() {
    helper();
    obj.method();
}
""".strip()
    result = parse_files([("call.cpp", content)])
    called = {c.calledName for c in result.calls}
    assert "helper" in called
    assert "method" in called
