"""Go 语言解析测试。"""

import pytest

from gitnexus_parser.graph import generate_id
from gitnexus_parser.ingestion.parser import parse_files


def test_parse_go_function_and_struct():
    pytest.importorskip("tree_sitter_go")
    content = """
package main

import "fmt"

type Point struct {
    X int
    Y int
}

type Stringer interface {
    String() string
}

func (p Point) String() string {
    return "point"
}

func main() {
    p := Point{1, 2}
    helper(p)
}

func helper(p Point) {
    custom(p)
}
""".strip()
    file_path = "main.go"
    result = parse_files([(file_path, content)])

    labels = {n.properties["name"]: n.label for n in result.nodes}
    assert labels.get("Point") == "Struct"
    assert labels.get("Stringer") == "Interface"
    assert labels.get("main") == "Function"
    assert labels.get("helper") == "Function"
    assert labels.get("String") == "Method"


def test_parse_go_exports():
    """Go: uppercase names are exported, lowercase are not."""
    pytest.importorskip("tree_sitter_go")
    content = """
package pkg

func Exported() {}
func unexported() {}
""".strip()
    result = parse_files([("pkg.go", content)])
    props = {n.properties["name"]: n.properties["isExported"] for n in result.nodes}
    assert props.get("Exported") is True
    assert props.get("unexported") is False


def test_parse_go_imports():
    pytest.importorskip("tree_sitter_go")
    content = """
package main

import (
    "fmt"
    "os"
)

func main() {}
""".strip()
    result = parse_files([("main.go", content)])
    raw_imports = [i.rawImportPath for i in result.imports]
    assert "fmt" in raw_imports
    assert "os" in raw_imports


def test_parse_go_calls():
    pytest.importorskip("tree_sitter_go")
    content = """
package main

func caller() {
    helper()
    obj.Method()
}

func helper() {}
""".strip()
    result = parse_files([("call.go", content)])
    called = {c.calledName for c in result.calls}
    assert "helper" in called
    assert "Method" in called


def test_parse_go_call_source_id():
    pytest.importorskip("tree_sitter_go")
    content = """
package main

func outer() {
    inner()
}

func inner() {}
""".strip()
    file_path = "src.go"
    result = parse_files([(file_path, content)])
    expected_source = generate_id("Function", f"{file_path}:outer")
    assert any(c.calledName == "inner" and c.sourceId == expected_source for c in result.calls)
