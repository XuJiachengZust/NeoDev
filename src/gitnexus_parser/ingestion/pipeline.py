"""Full pipeline: walk -> structure -> parse -> symbol table -> import/call/heritage -> optional Neo4j write."""

from dataclasses import dataclass
from pathlib import Path

from gitnexus_parser.graph import create_knowledge_graph, generate_id
from gitnexus_parser.ingestion.walker import walk_repository_paths
from gitnexus_parser.ingestion.structure import process_structure
from gitnexus_parser.ingestion.parser import parse_files
from gitnexus_parser.ingestion.symbol_table import create_symbol_table
from gitnexus_parser.ingestion.import_resolver import process_imports, resolve_import_path
from gitnexus_parser.ingestion.call_resolver import process_calls
from gitnexus_parser.ingestion.heritage_resolver import process_heritage_from_extracted
from gitnexus_parser.ingestion.incremental import (
    get_changed_paths,
    get_head_commit,
    load_scan_state,
    save_scan_state,
)


@dataclass
class PipelineResult:
    node_count: int
    relationship_count: int
    file_count: int


def run_pipeline(
    repo_path: str,
    config: dict | None = None,
    *,
    branch: str | None = None,
    project_id: int | None = None,
    write_neo4j: bool = True,
    incremental: bool = False,
    since_commit: str | None = None,
) -> PipelineResult:
    """
    Run full or incremental pipeline. When write_neo4j and neo4j_uri are set, branch defaults to "main".
    All nodes are tagged with branch for (id, branch) uniqueness in Neo4j, and with project_id when provided.

    When incremental=True (or since_commit is set): only parse files changed since base commit,
    then delete those nodes in Neo4j and write the new subgraph; state is persisted for next run.
    Base commit = since_commit if given, else last scanned commit from scan_state_path (or repo .gitnexus/scan_state.json).
    """
    config = config or {}
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return PipelineResult(node_count=0, relationship_count=0, file_count=0)

    use_branch = branch if branch is not None else ("main" if (write_neo4j and config.get("neo4j_uri")) else None)
    write_branch = use_branch or "main"
    write_project_id = project_id if project_id is not None else 0
    state_path = config.get("scan_state_path")

    do_incremental = incremental or since_commit is not None
    head_commit = get_head_commit(str(repo)) if do_incremental else None
    base_commit = since_commit
    if do_incremental and base_commit is None and head_commit is not None:
        state = load_scan_state(state_path=state_path, repo_path=str(repo))
        base_commit = state.get(write_branch)

    entries = walk_repository_paths(str(repo))
    all_paths = [e.path for e in entries]
    all_file_paths = set(all_paths)

    if do_incremental and head_commit is not None and base_commit is not None:
        changed_paths = get_changed_paths(str(repo), base_commit, "HEAD", supported_extensions_only=True)
        if not changed_paths:
            if write_neo4j and config.get("neo4j_uri"):
                save_scan_state(state_path=state_path, repo_path=str(repo), branch=write_branch, commit=head_commit)
            return PipelineResult(node_count=0, relationship_count=0, file_count=0)
        paths_to_scan = [p for p in all_paths if p in set(changed_paths)]
    else:
        paths_to_scan = all_paths

    graph = create_knowledge_graph()
    process_structure(graph, paths_to_scan, branch=use_branch, project_id=project_id)

    files_with_content: list[tuple[str, str]] = []
    for e in entries:
        if e.path not in paths_to_scan:
            continue
        full = repo / e.path
        try:
            content = full.read_text(encoding="utf-8", errors="replace")
            files_with_content.append((e.path, content))
        except Exception:
            continue

    parse_result = parse_files(files_with_content)
    symbol_table = create_symbol_table()

    for n in parse_result.nodes:
        props = dict(n.properties)
        if use_branch is not None:
            props["branch"] = use_branch
        if project_id is not None:
            props["project_id"] = project_id
        graph.addNode({
            "id": n.id,
            "label": n.label,
            "properties": props,
        })
    for r in parse_result.relationships:
        graph.addRelationship({
            "id": r.id,
            "sourceId": r.sourceId,
            "targetId": r.targetId,
            "type": r.type,
            "confidence": r.confidence,
            "reason": r.reason,
        })
    for s in parse_result.symbols:
        symbol_table.add(s.filePath, s.name, s.nodeId, s.type)
    for mm in parse_result.moduleMembers:
        rel_id = generate_id("MEMBER_OF", f"{mm.functionNodeId}->{mm.moduleNodeId}")
        graph.addRelationship({
            "id": rel_id,
            "sourceId": mm.functionNodeId,
            "targetId": mm.moduleNodeId,
            "type": "MEMBER_OF",
            "confidence": 1.0,
            "reason": "lua-module-member",
        })

    if do_incremental and paths_to_scan != all_paths:
        for imp in parse_result.imports:
            resolved = resolve_import_path(imp.filePath, imp.rawImportPath, all_file_paths)
            if not resolved or resolved == imp.filePath:
                continue
            target_id = generate_id("File", resolved)
            if graph.getNode(target_id) is None:
                stub_props = {"filePath": resolved, "name": resolved.split("/")[-1]}
                if use_branch is not None:
                    stub_props["branch"] = use_branch
                if project_id is not None:
                    stub_props["project_id"] = project_id
                graph.addNode({"id": target_id, "label": "File", "properties": stub_props})

    process_imports(graph, parse_result.imports, all_file_paths)
    process_calls(graph, parse_result.calls, symbol_table)
    process_heritage_from_extracted(graph, parse_result.heritage, symbol_table)

    if write_neo4j and config.get("neo4j_uri"):
        try:
            from neo4j import GraphDatabase
            uri = config.get("neo4j_uri", "bolt://localhost:7687")
            user = config.get("neo4j_user", "neo4j")
            password = config.get("neo4j_password", "")
            driver = GraphDatabase.driver(uri, auth=(user, password))
            try:
                from gitnexus_parser.neo4j_writer import (
                    delete_branch,
                    delete_nodes_by_file_paths,
                    ensure_constraints,
                    write_graph,
                )
                ensure_constraints(driver, database=config.get("neo4j_database"))
                db = config.get("neo4j_database")
                if do_incremental and base_commit is not None and paths_to_scan != all_paths:
                    delete_nodes_by_file_paths(driver, write_branch, paths_to_scan, project_id=write_project_id, database=db)
                else:
                    delete_branch(driver, write_branch, project_id=write_project_id, database=db)
                write_graph(graph, driver, write_branch, project_id=write_project_id, database=db)
                if head_commit is not None:
                    save_scan_state(state_path=state_path, repo_path=str(repo), branch=write_branch, commit=head_commit)
            finally:
                driver.close()
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Neo4j 入库失败: %s", e)
            raise

    return PipelineResult(
        node_count=graph.nodeCount,
        relationship_count=graph.relationshipCount,
        file_count=parse_result.fileCount,
    )
