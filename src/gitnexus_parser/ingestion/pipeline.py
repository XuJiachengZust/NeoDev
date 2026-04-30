"""Basic parse pipeline: walk -> structure -> parse -> in-memory graph counts."""

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any

from gitnexus_parser.graph import create_knowledge_graph, generate_id
from gitnexus_parser.ingestion.call_resolver import process_calls
from gitnexus_parser.ingestion.heritage_resolver import process_heritage_from_extracted
from gitnexus_parser.ingestion.import_resolver import (
    build_import_resolver_index,
    process_imports,
    resolve_import_path,
)
from gitnexus_parser.ingestion.incremental import (
    get_changed_paths,
    get_head_commit,
    load_scan_state,
)
from gitnexus_parser.ingestion.parser import parse_files
from gitnexus_parser.ingestion.structure import process_structure
from gitnexus_parser.ingestion.symbol_table import create_symbol_table
from gitnexus_parser.ingestion.walker import walk_repository_paths


@dataclass
class PipelineResult:
    node_count: int
    relationship_count: int
    file_count: int
    graph: Any | None = None
    timings: dict[str, float] | None = None


def run_pipeline(
    repo_path: str,
    config: dict | None = None,
    *,
    branch: str | None = None,
    project_id: int | None = None,
    write_neo4j: bool = True,
    incremental: bool = False,
    since_commit: str | None = None,
    target_commit: str | None = None,
) -> PipelineResult:
    """
    Run the parser and build an in-memory graph.

    The pipeline itself does not write storage. When write_neo4j is true, the
    built graph is returned to the caller so the service layer can replace the
    project-branch graph in Neo4j in one transaction boundary.
    """
    config = config or {}
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return PipelineResult(node_count=0, relationship_count=0, file_count=0)
    timings: dict[str, float] = {}

    def timed(name: str, callback):
        started = time.perf_counter()
        value = callback()
        timings[name] = round(time.perf_counter() - started, 4)
        return value

    do_incremental = incremental or since_commit is not None
    head_commit = (target_commit[:40] if target_commit else get_head_commit(str(repo))) if do_incremental else None
    base_commit = since_commit
    if do_incremental and base_commit is None and head_commit is not None:
        state = load_scan_state(state_path=config.get("scan_state_path"), repo_path=str(repo))
        base_commit = state.get(branch or "main")

    entries = timed("walk_repository_paths", lambda: walk_repository_paths(str(repo)))
    all_paths = [entry.path for entry in entries]
    all_file_paths = set(all_paths)

    if do_incremental and head_commit is not None and base_commit is not None:
        changed_paths = get_changed_paths(
            str(repo),
            base_commit,
            target_commit or "HEAD",
            supported_extensions_only=True,
        )
        if not changed_paths:
            return PipelineResult(node_count=0, relationship_count=0, file_count=0)
        paths_to_scan = [path for path in all_paths if path in set(changed_paths)]
    else:
        paths_to_scan = all_paths

    graph = create_knowledge_graph()
    timed(
        "process_structure",
        lambda: process_structure(
            graph,
            paths_to_scan,
            branch=branch,
            project_id=project_id,
        ),
    )

    def read_files() -> list[tuple[str, str]]:
        files: list[tuple[str, str]] = []
        for entry in entries:
            if entry.path not in paths_to_scan:
                continue
            full_path = repo / entry.path
            try:
                files.append(
                    (entry.path, full_path.read_text(encoding="utf-8", errors="replace"))
                )
            except Exception:
                continue
        return files

    files_with_content = timed("read_files", read_files)
    parse_result = timed("parse_files_ast", lambda: parse_files(files_with_content))
    symbol_table = create_symbol_table()

    def materialize_ast_to_graph() -> None:
        for node in parse_result.nodes:
            props = dict(node.properties)
            if project_id is not None:
                props["project_id"] = project_id
            graph.addNode(
                {
                    "id": node.id,
                    "label": node.label,
                    "properties": props,
                }
            )
        for relationship in parse_result.relationships:
            graph.addRelationship(
                {
                    "id": relationship.id,
                    "sourceId": relationship.sourceId,
                    "targetId": relationship.targetId,
                    "type": relationship.type,
                    "confidence": relationship.confidence,
                    "reason": relationship.reason,
                }
            )
        for symbol in parse_result.symbols:
            symbol_table.add(symbol.filePath, symbol.name, symbol.nodeId, symbol.type)
        for member in parse_result.moduleMembers:
            rel_id = generate_id("MEMBER_OF", f"{member.functionNodeId}->{member.moduleNodeId}")
            graph.addRelationship(
                {
                    "id": rel_id,
                    "sourceId": member.functionNodeId,
                    "targetId": member.moduleNodeId,
                    "type": "MEMBER_OF",
                    "confidence": 1.0,
                    "reason": "lua-module-member",
                }
            )

    timed("materialize_ast_to_graph", materialize_ast_to_graph)

    if do_incremental and paths_to_scan != all_paths:
        def add_incremental_import_stubs() -> None:
            resolver_index = build_import_resolver_index(all_file_paths)
            for imported in parse_result.imports:
                resolved = resolve_import_path(
                    imported.filePath,
                    imported.rawImportPath,
                    all_file_paths,
                    resolver_index=resolver_index,
                )
                if not resolved or resolved == imported.filePath:
                    continue
                target_id = generate_id("File", resolved)
                if graph.getNode(target_id) is None:
                    stub_props = {"filePath": resolved, "name": resolved.split("/")[-1]}
                    if project_id is not None:
                        stub_props["project_id"] = project_id
                    graph.addNode({"id": target_id, "label": "File", "properties": stub_props})

        timed("resolve_import_stubs", add_incremental_import_stubs)

    timed("process_import_relationships", lambda: process_imports(graph, parse_result.imports, all_file_paths))
    timed("process_call_relationships", lambda: process_calls(graph, parse_result.calls, symbol_table))
    timed(
        "process_heritage_relationships",
        lambda: process_heritage_from_extracted(graph, parse_result.heritage, symbol_table),
    )
    timings["total_pipeline"] = round(sum(timings.values()), 4)

    return PipelineResult(
        node_count=graph.nodeCount,
        relationship_count=graph.relationshipCount,
        file_count=parse_result.fileCount,
        graph=graph if write_neo4j else None,
        timings=timings,
    )
