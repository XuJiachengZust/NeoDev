from gitnexus_parser.graph import create_knowledge_graph, generate_id
from gitnexus_parser.ingestion.facts import build_file_fact_id, build_symbol_fact_id
from gitnexus_parser.ingestion.import_resolver import process_imports
from gitnexus_parser.ingestion.parser import (
    ExtractedCall,
    ParseResult,
    ParsedNode,
    ParsedRelationship,
    ParsedSymbol,
)
from gitnexus_parser.ingestion.pipeline import _remap_parse_result_to_repository_facts
from gitnexus_parser.ingestion.structure import process_structure


def test_file_fact_id_includes_repo_path_and_content_hash():
    graph = create_knowledge_graph()

    process_structure(
        graph,
        ["src/a.py"],
        branch="feature/a",
        project_id=7,
        repo_id=7,
        file_content_hashes={"src/a.py": "abc123"},
    )

    file_nodes = [node for node in graph.iterNodes() if node["label"] == "File"]
    assert len(file_nodes) == 1
    node = file_nodes[0]
    expected_id = generate_id("File", "repo:7:file:src/a.py:hash:abc123")
    assert node["id"] == expected_id
    assert node["properties"]["repo_id"] == 7
    assert node["properties"]["file_content_hash"] == "abc123"
    assert node["properties"]["content_hash"] == "abc123"
    assert node["properties"]["fact_key"] == "repo:7:file:src/a.py:hash:abc123"
    assert "branch" not in node["properties"]

    folder_nodes = [node for node in graph.iterNodes() if node["label"] == "Folder"]
    assert len(folder_nodes) == 1
    assert folder_nodes[0]["id"] == generate_id("Folder", "repo:7:folder:src")
    assert folder_nodes[0]["properties"]["fact_key"] == "repo:7:folder:src"


def test_parse_result_ids_are_remapped_to_repository_fact_ids():
    old_file_id = generate_id("File", "src/a.py")
    old_func_id = generate_id("Function", "src/a.py:handle")
    parse_result = ParseResult(
        nodes=[
            ParsedNode(
                id=old_func_id,
                label="Function",
                properties={
                    "filePath": "src/a.py",
                    "name": "handle",
                    "startLine": 2,
                    "endLine": 4,
                },
            )
        ],
        relationships=[
            ParsedRelationship(
                id=generate_id("DEFINES", f"{old_file_id}->{old_func_id}"),
                sourceId=old_file_id,
                targetId=old_func_id,
                type="DEFINES",
                confidence=1.0,
                reason="",
            )
        ],
        symbols=[
            ParsedSymbol(
                filePath="src/a.py",
                name="handle",
                nodeId=old_func_id,
                type="Function",
            )
        ],
        calls=[
            ExtractedCall(
                filePath="src/a.py",
                calledName="handle",
                sourceId=old_func_id,
            )
        ],
    )

    remapped, file_ids = _remap_parse_result_to_repository_facts(
        parse_result,
        repo_id=7,
        file_content_hashes={"src/a.py": "abc123"},
    )

    expected_file_id = build_file_fact_id(
        repo_id=7,
        file_path="src/a.py",
        file_content_hash="abc123",
    )
    expected_func_id = build_symbol_fact_id(
        repo_id=7,
        label="Function",
        file_path="src/a.py",
        name="handle",
        start_line=2,
        end_line=4,
        file_content_hash="abc123",
    )
    assert file_ids == {"src/a.py": expected_file_id}
    assert remapped.nodes[0].id == expected_func_id
    assert remapped.nodes[0].properties["repo_id"] == 7
    assert remapped.nodes[0].properties["file_content_hash"] == "abc123"
    assert remapped.relationships[0].sourceId == expected_file_id
    assert remapped.relationships[0].targetId == expected_func_id
    assert remapped.symbols[0].nodeId == expected_func_id
    assert remapped.calls[0].sourceId == expected_func_id


def test_import_relationship_id_uses_repository_fact_endpoint_ids():
    graph = create_knowledge_graph()
    source_id = build_file_fact_id(repo_id=7, file_path="src/a.py", file_content_hash="h1")
    target_id = build_file_fact_id(repo_id=7, file_path="src/b.py", file_content_hash="h2")
    graph.addNode({"id": source_id, "label": "File", "properties": {"filePath": "src/a.py"}})
    graph.addNode({"id": target_id, "label": "File", "properties": {"filePath": "src/b.py"}})

    class Import:
        filePath = "src/a.py"
        rawImportPath = "./b"

    process_imports(
        graph,
        [Import()],
        {"src/a.py", "src/b.py"},
        file_ids_by_path={"src/a.py": source_id, "src/b.py": target_id},
    )

    relationships = list(graph.iterRelationships())
    assert relationships == [
        {
            "id": generate_id("IMPORTS", f"{source_id}->{target_id}"),
            "sourceId": source_id,
            "targetId": target_id,
            "type": "IMPORTS",
            "confidence": 1.0,
            "reason": "",
        }
    ]
