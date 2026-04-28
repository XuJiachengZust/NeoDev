"""Structure processing: build Folder/File nodes and CONTAINS edges from path list."""

from typing import TYPE_CHECKING, List

from gitnexus_parser.graph import generate_id
from gitnexus_parser.graph.types import GraphNode, GraphRelationship
from gitnexus_parser.ingestion.facts import build_file_fact_id, build_file_fact_key

if TYPE_CHECKING:
    from gitnexus_parser.graph.graph import KnowledgeGraph


def process_structure(
    graph: "KnowledgeGraph",
    paths: List[str],
    branch: str | None = None,
    project_id: int | None = None,
    repo_id: int | None = None,
    file_content_hashes: dict[str, str] | None = None,
) -> None:
    """
    For each path, create Folder nodes for each path segment and a File node for the last.
    Add CONTAINS relationships. Paths use forward slashes.
    Aligned with structure-processor.ts.
    branch is accepted for API compatibility but is not stored on graph facts.
    When project_id is set, each node's properties include project_id for PG project association.
    When repo_id and file_content_hashes are set, File nodes use repository fact identity.
    """
    file_content_hashes = file_content_hashes or {}
    for path in paths:
        parts = path.split("/")
        current_path = ""
        parent_id = ""
        for index, part in enumerate(parts):
            is_file = index == len(parts) - 1
            label: str = "File" if is_file else "Folder"
            current_path = f"{current_path}/{part}" if current_path else part
            props: dict = {"name": part, "filePath": current_path}
            content_hash = file_content_hashes.get(current_path) if is_file else None
            if is_file and repo_id is not None and content_hash:
                fact_key = build_file_fact_key(
                    repo_id=repo_id,
                    file_path=current_path,
                    file_content_hash=content_hash,
                )
                node_id = build_file_fact_id(
                    repo_id=repo_id,
                    file_path=current_path,
                    file_content_hash=content_hash,
                )
                props["repo_id"] = repo_id
                props["file_content_hash"] = content_hash
                props["content_hash"] = content_hash
                props["fact_key"] = fact_key
            elif not is_file and repo_id is not None:
                fact_key = f"repo:{repo_id}:folder:{current_path}"
                node_id = generate_id(label, fact_key)
                props["repo_id"] = repo_id
                props["fact_key"] = fact_key
            else:
                node_id = generate_id(label, current_path)
                if repo_id is not None:
                    props["repo_id"] = repo_id
            if project_id is not None:
                props["project_id"] = project_id
            node: GraphNode = {
                "id": node_id,
                "label": label,
                "properties": props,
            }
            graph.addNode(node)
            if parent_id:
                rel_id = generate_id("CONTAINS", f"{parent_id}->{node_id}")
                rel: GraphRelationship = {
                    "id": rel_id,
                    "sourceId": parent_id,
                    "targetId": node_id,
                    "type": "CONTAINS",
                    "confidence": 1.0,
                    "reason": "",
                }
                graph.addRelationship(rel)
            parent_id = node_id
