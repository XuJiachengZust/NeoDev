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
) -> None:
    """
    For each path, create Folder nodes for each path segment and a File node for the last.
    Add CONTAINS relationships. Paths use forward slashes.
    Aligned with structure-processor.ts.
    When branch is set, each node's properties include branch for Neo4j branch dimension.
    """
    for path in paths:
        parts = path.split("/")
        current_path = ""
        parent_id = ""
        for index, part in enumerate(parts):
            is_file = index == len(parts) - 1
            label: str = "File" if is_file else "Folder"
            current_path = f"{current_path}/{part}" if current_path else part
            node_id = generate_id(label, current_path)
            props: dict = {"name": part, "filePath": current_path}
            if branch is not None:
                props["branch"] = branch
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
