"""JavaScript 语言解析测试。"""

import pytest

from gitnexus_parser.graph import generate_id
from gitnexus_parser.ingestion.parser import parse_files


def test_parse_js_function_and_class():
    pytest.importorskip("tree_sitter_javascript")
    content = """
import { helper } from './helper';

function greet(name) {
    return 'Hello ' + name;
}

const add = (a, b) => a + b;

class Animal {
    speak() {
        return 'sound';
    }
}
""".strip()
    file_path = "app.js"
    result = parse_files([(file_path, content)])

    labels = {n.properties["name"]: n.label for n in result.nodes}
    assert labels.get("greet") == "Function"
    assert labels.get("add") == "Function"
    assert labels.get("Animal") == "Class"
    assert labels.get("speak") == "Method"


def test_parse_js_imports():
    pytest.importorskip("tree_sitter_javascript")
    content = """
import React from 'react';
import { useState } from 'react';
const fs = require('fs');
""".strip()
    result = parse_files([("app.js", content)])
    raw_imports = [i.rawImportPath for i in result.imports]
    assert "react" in raw_imports
    assert "fs" in raw_imports


def test_parse_js_heritage():
    pytest.importorskip("tree_sitter_javascript")
    content = """
class Animal {}
class Dog extends Animal {
    bark() {}
}
""".strip()
    result = parse_files([("animals.js", content)])
    assert any(
        h.className == "Dog" and h.parentName == "Animal" and h.kind == "extends"
        for h in result.heritage
    )


def test_parse_js_calls():
    pytest.importorskip("tree_sitter_javascript")
    content = """
function main() {
    helper();
    obj.method();
}
""".strip()
    result = parse_files([("call.js", content)])
    called = {c.calledName for c in result.calls}
    assert "helper" in called
    assert "method" in called


def test_parse_js_call_source_id():
    pytest.importorskip("tree_sitter_javascript")
    content = """
function outer() {
    inner();
}
""".strip()
    file_path = "src.js"
    result = parse_files([(file_path, content)])
    expected_source = generate_id("Function", f"{file_path}:outer")
    assert any(c.calledName == "inner" and c.sourceId == expected_source for c in result.calls)
