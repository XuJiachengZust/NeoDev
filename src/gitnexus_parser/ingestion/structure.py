"""Structure processing: build Folder/File nodes and CONTAINS edges from path list."""

from typing import TYPE_CHECKING, List

from gitnexus_parser.graph import generate_id
from gitnexus_parser.graph.types import GraphNode, GraphRelationship

if TYPE_CHECKING:
    from gitnexus_parser.graph.graph import KnowledgeGraph


def process_structure(
    graph: "KnowledgeGraph",
    paths: List[str],
    branch: str | None = None,
    project_id: int | None = None,
    file_content_hashes: dict[str, str] | None = None,
) -> None:
    """
    For each path, create Folder nodes for each path segment and a File node for the last.
    Add CONTAINS relationships. Paths use forward slashes.
    Aligned with structure-processor.ts.
    branch is accepted for API compatibility but is not stored on graph facts.
    When project_id is set, each node's properties include project_id for PG project association.
    file_content_hashes is accepted for compatibility and ignored.
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
            node_id = generate_id(label, current_path)
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
