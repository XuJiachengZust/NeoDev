"""C 语言解析测试。"""

import pytest

from gitnexus_parser.graph import generate_id
from gitnexus_parser.ingestion.parser import parse_files


def test_parse_c_function_and_struct():
    pytest.importorskip("tree_sitter_c")
    content = """
#include <stdio.h>

typedef unsigned int uint;

struct Point {
    int x;
    int y;
};

enum Color { RED, GREEN, BLUE };

union Data {
    int i;
    float f;
};

#define MAX_SIZE 100

void draw(struct Point p) {
    custom_render(p.x, p.y);
}

int main() {
    struct Point p;
    draw(p);
    return 0;
}
""".strip()
    file_path = "graphics.c"
    result = parse_files([(file_path, content)])

    labels = {n.properties["name"]: n.label for n in result.nodes}
    assert labels.get("draw") == "Function"
    assert labels.get("main") == "Function"
    assert labels.get("Point") == "Struct"
    assert labels.get("Color") == "Enum"
    assert labels.get("Data") == "Union"
    assert labels.get("uint") == "Typedef"
    assert labels.get("MAX_SIZE") == "Macro"


def test_parse_c_imports():
    pytest.importorskip("tree_sitter_c")
    content = '#include <stdio.h>\n#include "myheader.h"\nvoid foo() {}\n'
    result = parse_files([("test.c", content)])
    raw_imports = [i.rawImportPath for i in result.imports]
    assert "stdio.h" in raw_imports
    assert "myheader.h" in raw_imports


def test_parse_c_calls():
    pytest.importorskip("tree_sitter_c")
    content = """
void caller() {
    helper();
    another();
}
""".strip()
    result = parse_files([("call.c", content)])
    called = {c.calledName for c in result.calls}
    assert "helper" in called
    assert "another" in called


def test_parse_c_call_source_id():
    pytest.importorskip("tree_sitter_c")
    content = """
void outer() {
    inner();
}
""".strip()
    file_path = "src.c"
    result = parse_files([(file_path, content)])
    expected_source = generate_id("Function", f"{file_path}:outer")
    assert any(c.calledName == "inner" and c.sourceId == expected_source for c in result.calls)
