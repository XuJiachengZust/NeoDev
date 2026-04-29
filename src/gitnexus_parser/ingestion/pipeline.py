"""Full pipeline: walk -> structure -> parse -> symbol table -> import/call/heritage -> optional Neo4j write."""

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path

from gitnexus_parser.graph import create_knowledge_graph, generate_id
from gitnexus_parser.ingestion.facts import (
    build_file_fact_id,
    build_file_symbol_key,
    build_symbol_fact_id,
    build_symbol_fact_key,
    build_symbol_key,
)
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
    code_facts: list[dict] | None = None
    snapshot_hash: str | None = None


def _build_file_content_hashes(repo: Path, paths: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in paths:
        try:
            hashes[path] = hashlib.sha256((repo / path).read_bytes()).hexdigest()
        except OSError:
            continue
    return hashes


def _remap_parse_result_to_repository_facts(
    parse_result,
    *,
    project_id: int,
    file_content_hashes: dict[str, str],
    file_contents: dict[str, str] | None = None,
):
    file_contents = file_contents or {}
    file_ids_by_path = {
        file_path: build_file_fact_id(
            project_id=project_id,
            file_path=file_path,
            file_content_hash=file_content_hash,
        )
        for file_path, file_content_hash in file_content_hashes.items()
    }
    id_map = {
        generate_id("File", file_path): file_id
        for file_path, file_id in file_ids_by_path.items()
    }

    remapped_nodes = []
    for node in parse_result.nodes:
        props = dict(node.properties)
        file_path = props.get("filePath")
        file_content_hash = file_content_hashes.get(file_path or "")
        if file_path and file_content_hash:
            name = str(props.get("qualified_name") or props.get("qualifiedName") or props.get("name") or "")
            start_line = props.get("startLine")
            end_line = props.get("endLine")
            node_content_hash = _node_content_hash(
                file_contents.get(file_path or ""),
                start_line=start_line,
                end_line=end_line,
                fallback=file_content_hash,
            )
            fact_key = build_symbol_fact_key(
                project_id=project_id,
                label=node.label,
                file_path=file_path,
                name=name,
                start_line=start_line,
                end_line=end_line,
                file_content_hash=node_content_hash,
            )
            new_id = build_symbol_fact_id(
                project_id=project_id,
                label=node.label,
                file_path=file_path,
                name=name,
                start_line=start_line,
                end_line=end_line,
                file_content_hash=node_content_hash,
            )
            id_map[node.id] = new_id
            props["file_content_hash"] = file_content_hash
            props["content_hash"] = node_content_hash
            props["symbol_key"] = build_symbol_key(
                project_id=project_id,
                label=node.label,
                file_path=file_path,
                name=name,
            )
            props["fact_key"] = fact_key
            remapped_nodes.append(replace(node, id=new_id, properties=props))
        else:
            remapped_nodes.append(node)

    remapped_relationships = []
    for rel in parse_result.relationships:
        source_id = id_map.get(rel.sourceId, rel.sourceId)
        target_id = id_map.get(rel.targetId, rel.targetId)
        rel_id = generate_id(rel.type, f"{source_id}->{target_id}")
        remapped_relationships.append(
            replace(rel, id=rel_id, sourceId=source_id, targetId=target_id)
        )

    remapped_symbols = [
        replace(symbol, nodeId=id_map.get(symbol.nodeId, symbol.nodeId))
        for symbol in parse_result.symbols
    ]
    remapped_calls = [
        replace(call, sourceId=id_map.get(call.sourceId, call.sourceId))
        for call in parse_result.calls
    ]
    remapped_members = [
        replace(
            member,
            moduleNodeId=id_map.get(member.moduleNodeId, member.moduleNodeId),
            functionNodeId=id_map.get(member.functionNodeId, member.functionNodeId),
        )
        for member in parse_result.moduleMembers
    ]

    return replace(
        parse_result,
        nodes=remapped_nodes,
        relationships=remapped_relationships,
        symbols=remapped_symbols,
        calls=remapped_calls,
        moduleMembers=remapped_members,
    ), file_ids_by_path


def _node_content_hash(
    content: str | None,
    *,
    start_line: int | None,
    end_line: int | None,
    fallback: str,
) -> str:
    if not content or not start_line or not end_line or start_line > end_line:
        return fallback
    lines = content.splitlines()
    selected = lines[max(start_line - 1, 0) : min(end_line, len(lines))]
    normalized = "\n".join(line.strip() for line in selected if line.strip())
    if not normalized:
        return fallback
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


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
    Run full or incremental pipeline. Branch selects the Git ref and scan state only;
    Neo4j facts are repository-level and are not tagged by branch.

    When incremental=True (or since_commit is set): only parse files changed since base commit,
    write repository-level facts for changed content, and let branch snapshots switch visibility.
    Existing Neo4j facts are not deleted by branch.
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
    head_commit = (target_commit[:40] if target_commit else get_head_commit(str(repo))) if do_incremental else None
    base_commit = since_commit
    if do_incremental and base_commit is None and head_commit is not None:
        state = load_scan_state(state_path=state_path, repo_path=str(repo))
        base_commit = state.get(write_branch)

    entries = walk_repository_paths(str(repo))
    all_paths = [e.path for e in entries]
    all_file_paths = set(all_paths)
    file_content_hashes = _build_file_content_hashes(repo, all_paths)

    if do_incremental and head_commit is not None and base_commit is not None:
        changed_paths = get_changed_paths(
            str(repo),
            base_commit,
            target_commit or "HEAD",
            supported_extensions_only=True,
        )
        if not changed_paths:
            if write_neo4j and config.get("neo4j_uri"):
                save_scan_state(state_path=state_path, repo_path=str(repo), branch=write_branch, commit=head_commit)
            return PipelineResult(node_count=0, relationship_count=0, file_count=0)
        paths_to_scan = [p for p in all_paths if p in set(changed_paths)]
    else:
        paths_to_scan = all_paths

    graph = create_knowledge_graph()
    process_structure(
        graph,
        paths_to_scan,
        branch=use_branch,
        project_id=project_id,
        file_content_hashes=file_content_hashes,
    )

    files_with_content: list[tuple[str, str]] = []
    file_contents: dict[str, str] = {}
    for e in entries:
        if e.path not in paths_to_scan:
            continue
        full = repo / e.path
        try:
            content = full.read_text(encoding="utf-8", errors="replace")
            files_with_content.append((e.path, content))
            file_contents[e.path] = content
        except Exception:
            continue

    parse_result = parse_files(files_with_content)
    parse_result, file_ids_by_path = _remap_parse_result_to_repository_facts(
        parse_result,
        project_id=write_project_id,
        file_content_hashes=file_content_hashes,
        file_contents=file_contents,
    )
    symbol_table = create_symbol_table()

    for n in parse_result.nodes:
        props = dict(n.properties)
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
            target_id = file_ids_by_path.get(resolved) or generate_id("File", resolved)
            if graph.getNode(target_id) is None:
                stub_props = {"filePath": resolved, "name": resolved.split("/")[-1]}
                if resolved in file_content_hashes:
                    stub_props["file_content_hash"] = file_content_hashes[resolved]
                    stub_props["content_hash"] = file_content_hashes[resolved]
                    stub_props["symbol_key"] = build_file_symbol_key(
                        project_id=write_project_id,
                        file_path=resolved,
                    )
                if project_id is not None:
                    stub_props["project_id"] = project_id
                graph.addNode({"id": target_id, "label": "File", "properties": stub_props})

    process_imports(graph, parse_result.imports, all_file_paths, file_ids_by_path=file_ids_by_path)
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
                    ensure_constraints,
                    write_graph,
                )
                ensure_constraints(driver, database=config.get("neo4j_database"))
                db = config.get("neo4j_database")
                write_graph(graph, driver, project_id=write_project_id, database=db)
                if head_commit is not None:
                    save_scan_state(state_path=state_path, repo_path=str(repo), branch=write_branch, commit=head_commit)
            finally:
                driver.close()
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Neo4j 入库失败: %s", e)
            raise

    code_facts = _code_facts_from_graph(graph, project_id=write_project_id)
    snapshot_hash = _snapshot_hash(code_facts)

    return PipelineResult(
        node_count=graph.nodeCount,
        relationship_count=graph.relationshipCount,
        file_count=parse_result.fileCount,
        code_facts=code_facts,
        snapshot_hash=snapshot_hash,
    )


_CODE_FACT_LABELS = {
    "File",
    "Class",
    "Interface",
    "Enum",
    "Annotation",
    "Method",
    "Function",
    "Constructor",
}


def _code_facts_from_graph(graph, *, project_id: int) -> list[dict]:
    parent_by_child: dict[str, str] = {}
    children_by_parent: dict[str, list[str]] = {}
    for rel in graph.iterRelationships():
        if rel.get("type") in {"CONTAINS", "DEFINES", "MEMBER_OF"}:
            parent_by_child[rel["targetId"]] = rel["sourceId"]
            children_by_parent.setdefault(rel["sourceId"], []).append(rel["targetId"])

    nodes_by_id = {node["id"]: node for node in graph.iterNodes()}
    structure_hashes: dict[str, str] = {}

    def structure_hash_for(node_id: str) -> str:
        if node_id in structure_hashes:
            return structure_hashes[node_id]
        node = nodes_by_id[node_id]
        label = str(node.get("label") or "")
        props = dict(node.get("properties") or {})
        file_path = props.get("filePath") or props.get("file_path")
        name = props.get("name") or file_path or node["id"]
        qualified_name = props.get("qualified_name") or props.get("qualifiedName") or name
        content_hash = props.get("content_hash") or props.get("file_content_hash") or ""
        signature_basis = f"{label}:{file_path or ''}:{qualified_name}:{props.get('startLine') or ''}:{props.get('endLine') or ''}"
        signature_hash = props.get("signature_hash") or hashlib.sha256(signature_basis.encode("utf-8")).hexdigest()
        child_hashes = sorted(
            structure_hash_for(child_id)
            for child_id in children_by_parent.get(node_id, [])
            if child_id in nodes_by_id and str(nodes_by_id[child_id].get("label") or "") in _CODE_FACT_LABELS
        )
        material = "\n".join([label, signature_hash, content_hash, *child_hashes])
        structure_hashes[node_id] = props.get("structure_hash") or hashlib.sha256(material.encode("utf-8")).hexdigest()
        return structure_hashes[node_id]

    facts: list[dict] = []
    for node in graph.iterNodes():
        label = str(node.get("label") or "")
        if label not in _CODE_FACT_LABELS:
            continue
        props = dict(node.get("properties") or {})
        file_path = props.get("filePath") or props.get("file_path")
        name = props.get("name") or file_path or node["id"]
        qualified_name = props.get("qualified_name") or props.get("qualifiedName") or name
        content_hash = props.get("content_hash") or props.get("file_content_hash") or ""
        signature_basis = f"{label}:{file_path or ''}:{qualified_name}:{props.get('startLine') or ''}:{props.get('endLine') or ''}"
        signature_hash = props.get("signature_hash") or hashlib.sha256(signature_basis.encode("utf-8")).hexdigest()
        structure_hash = structure_hash_for(node["id"])
        symbol_key = props.get("symbol_key")
        if not symbol_key:
            symbol_key = build_symbol_key(
                project_id=project_id,
                label=label,
                file_path=str(file_path or ""),
                name=str(qualified_name),
            )
        metadata = {
            key: value
            for key, value in props.items()
            if key not in {"sourceCode", "content", "repo_id"}
        }
        facts.append(
            {
                "project_id": project_id,
                "fact_id": node["id"],
                "symbol_key": symbol_key,
                "node_type": label,
                "file_path": file_path,
                "qualified_name": qualified_name,
                "name": name,
                "signature_hash": signature_hash,
                "content_hash": content_hash,
                "structure_hash": structure_hash,
                "parent_fact_id": parent_by_child.get(node["id"]),
                "start_line": props.get("startLine"),
                "end_line": props.get("endLine"),
                "metadata_json": metadata,
                "status": "active",
            }
        )
    return facts


def _snapshot_hash(code_facts: list[dict]) -> str:
    material = "\n".join(
        f"{fact['fact_id']}:{fact.get('structure_hash') or ''}"
        for fact in sorted(code_facts, key=lambda item: item["fact_id"])
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
