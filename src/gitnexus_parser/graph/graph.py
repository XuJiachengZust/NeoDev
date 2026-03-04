"""In-memory knowledge graph aligned with types.ts KnowledgeGraph interface."""

from typing import Callable, Iterator

from .types import GraphNode, GraphRelationship


def create_knowledge_graph() -> "KnowledgeGraph":
    """Create an empty in-memory knowledge graph."""
    return KnowledgeGraph()


class KnowledgeGraph:
    """In-memory graph: nodes and relationships with add/remove/get/iter."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._relationships: dict[str, GraphRelationship] = {}
        self._rel_ids_by_source: dict[str, list[str]] = {}
        self._rel_ids_by_target: dict[str, list[str]] = {}

    @property
    def nodes(self) -> list[GraphNode]:
        return list(self._nodes.values())

    @property
    def relationships(self) -> list[GraphRelationship]:
        return list(self._relationships.values())

    @property
    def nodeCount(self) -> int:
        return len(self._nodes)

    @property
    def relationshipCount(self) -> int:
        return len(self._relationships)

    def iterNodes(self) -> Iterator[GraphNode]:
        yield from self._nodes.values()

    def iterRelationships(self) -> Iterator[GraphRelationship]:
        yield from self._relationships.values()

    def forEachNode(self, fn: Callable[[GraphNode], None]) -> None:
        for n in self._nodes.values():
            fn(n)

    def forEachRelationship(self, fn: Callable[[GraphRelationship], None]) -> None:
        for r in self._relationships.values():
            fn(r)

    def getNode(self, id: str) -> GraphNode | None:
        return self._nodes.get(id)

    def addNode(self, node: GraphNode) -> None:
        self._nodes[node["id"]] = node

    def addRelationship(self, relationship: GraphRelationship) -> None:
        rid = relationship.get("id") or f"{relationship['sourceId']}->{relationship['targetId']}"
        rel: GraphRelationship = {**relationship, "id": rid}
        self._relationships[rid] = rel
        sid = rel["sourceId"]
        tid = rel["targetId"]
        self._rel_ids_by_source.setdefault(sid, []).append(rid)
        self._rel_ids_by_target.setdefault(tid, []).append(rid)

    def removeNode(self, nodeId: str) -> bool:
        if nodeId not in self._nodes:
            return False
        rids_to_remove: set[str] = set()
        rids_to_remove.update(self._rel_ids_by_source.get(nodeId, []))
        rids_to_remove.update(self._rel_ids_by_target.get(nodeId, []))
        for rid in rids_to_remove:
            r = self._relationships.pop(rid, None)
            if r:
                for nid in (r["sourceId"], r["targetId"]):
                    for d in (self._rel_ids_by_source, self._rel_ids_by_target):
                        if nid in d:
                            d[nid] = [x for x in d[nid] if x != rid]
        self._rel_ids_by_source.pop(nodeId, None)
        self._rel_ids_by_target.pop(nodeId, None)
        del self._nodes[nodeId]
        return True

    def removeNodesByFile(self, filePath: str) -> int:
        """Remove all nodes whose filePath matches, and their relationships. Returns count removed."""
        to_remove = [
            nid for nid, n in self._nodes.items()
            if n.get("properties", {}).get("filePath") == filePath
        ]
        for nid in to_remove:
            self.removeNode(nid)
        return len(to_remove)
