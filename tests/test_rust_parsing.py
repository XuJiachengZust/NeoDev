"""Rust 语言解析测试。"""

import pytest

from gitnexus_parser.graph import generate_id
from gitnexus_parser.ingestion.parser import parse_files


def test_parse_rust_function_struct_enum():
    pytest.importorskip("tree_sitter_rust")
    content = """
use std::fmt;

struct Point {
    x: f64,
    y: f64,
}

enum Color {
    Red,
    Green,
    Blue,
}

trait Drawable {
    fn draw(&self);
}

type Coordinate = (f64, f64);

fn distance(a: &Point, b: &Point) -> f64 {
    custom_calc(a.x, b.x)
}

fn main() {
    let p = Point { x: 1.0, y: 2.0 };
    distance(&p, &p);
}
""".strip()
    file_path = "shapes.rs"
    result = parse_files([(file_path, content)])

    labels = {n.properties["name"]: n.label for n in result.nodes}
    assert labels.get("Point") == "Struct"
    assert labels.get("Color") == "Enum"
    assert labels.get("Drawable") == "Trait"
    assert labels.get("Coordinate") == "TypeAlias"
    assert labels.get("distance") == "Function"
    assert labels.get("main") == "Function"


def test_parse_rust_impl_trait_heritage():
    pytest.importorskip("tree_sitter_rust")
    content = """
trait Display {
    fn display(&self);
}

struct Foo;

impl Display for Foo {
    fn display(&self) {}
}
""".strip()
    result = parse_files([("impl.rs", content)])
    assert any(
        h.className == "Foo" and h.parentName == "Display" and h.kind == "trait-impl"
        for h in result.heritage
    )


def test_parse_rust_imports():
    pytest.importorskip("tree_sitter_rust")
    content = """
use std::collections::HashMap;
use std::io;

fn main() {}
""".strip()
    result = parse_files([("main.rs", content)])
    raw_imports = [i.rawImportPath for i in result.imports]
    assert len(raw_imports) >= 2


def test_parse_rust_calls():
    pytest.importorskip("tree_sitter_rust")
    content = """
fn caller() {
    helper();
    obj.method();
}

fn helper() {}
""".strip()
    result = parse_files([("call.rs", content)])
    called = {c.calledName for c in result.calls}
    assert "helper" in called
    assert "method" in called


def test_parse_rust_call_source_id():
    pytest.importorskip("tree_sitter_rust")
    content = """
fn outer() {
    inner();
}

fn inner() {}
""".strip()
    file_path = "src.rs"
    result = parse_files([(file_path, content)])
    expected_source = generate_id("Function", f"{file_path}:outer")
    assert any(c.calledName == "inner" and c.sourceId == expected_source for c in result.calls)
