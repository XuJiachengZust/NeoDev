"""Lua parser tests for module/member modeling (Plan A)."""

from pathlib import Path

import pytest

from gitnexus_parser.graph import generate_id
from gitnexus_parser.graph.graph import create_knowledge_graph
from gitnexus_parser.ingestion.parser import parse_files
from gitnexus_parser.ingestion.pipeline import run_pipeline


def test_parse_lua_module_member_function_extracts_module_and_function():
    pytest.importorskip("tree_sitter_lua")
    content = """
local _M = {}

function _M.stream_preread_phase()
    return true
end
""".strip()
    file_path = "apisix/init.lua"
    result = parse_files([(file_path, content)])

    function_id = generate_id("Function", f"{file_path}:_M.stream_preread_phase")
    module_id = generate_id("Module", f"{file_path}:_M")
    node_ids = {n.id for n in result.nodes}

    assert function_id in node_ids
    assert module_id in node_ids
    assert any(
        mm.functionNodeId == function_id and mm.moduleNodeId == module_id and mm.moduleName == "_M"
        for mm in result.moduleMembers
    )


def test_parse_plain_lua_function_does_not_create_module_member():
    pytest.importorskip("tree_sitter_lua")
    content = """
function foo()
    return 1
end
""".strip()
    file_path = "simple.lua"
    result = parse_files([(file_path, content)])

    function_id = generate_id("Function", f"{file_path}:foo")
    module_nodes = [n for n in result.nodes if n.label == "Module"]

    assert any(n.id == function_id for n in result.nodes)
    assert module_nodes == []
    assert result.moduleMembers == []


def test_parse_lua_method_definition_uses_full_name():
    pytest.importorskip("tree_sitter_lua")
    content = """
local obj = {}

function obj:run()
    return 1
end
""".strip()
    file_path = "obj.lua"
    result = parse_files([(file_path, content)])

    function_id = generate_id("Function", f"{file_path}:obj:run")
    assert any(n.id == function_id and n.label == "Function" for n in result.nodes)


def test_pipeline_adds_member_of_relationship_for_lua_module_member(monkeypatch, tmp_path: Path):
    pytest.importorskip("tree_sitter_lua")
    lua_file = tmp_path / "apisix" / "init.lua"
    lua_file.parent.mkdir(parents=True, exist_ok=True)
    lua_file.write_text(
        """
local _M = {}

function _M.stream_preread_phase()
    return true
end
""".strip(),
        encoding="utf-8",
    )

    captured_graph = create_knowledge_graph()
    monkeypatch.setattr(
        "gitnexus_parser.ingestion.pipeline.create_knowledge_graph",
        lambda: captured_graph,
    )

    run_pipeline(str(tmp_path), config={}, write_neo4j=False)

    function_id = generate_id("Function", "apisix/init.lua:_M.stream_preread_phase")
    module_id = generate_id("Module", "apisix/init.lua:_M")
    assert any(
        r.get("type") == "MEMBER_OF"
        and r.get("sourceId") == function_id
        and r.get("targetId") == module_id
        for r in captured_graph.iterRelationships()
    )
