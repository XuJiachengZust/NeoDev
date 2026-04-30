from dataclasses import dataclass, field
from typing import Any

from service.repositories import graph_management_repository as repo
from service.repositories import code_fact_repository as code_fact_repo
from service.services import branch_snapshot_service

try:
    from service.services import manual_graph_sync_service
except Exception:  # pragma: no cover - optional Neo4j dependency path
    manual_graph_sync_service = None


IDENTITY_FIELDS = frozenset({"id", "project_id", "file_path", "content_hash", "node_id"})
EDGE_IDENTITY_FIELDS = frozenset(
    {"id", "project_id", "edge_id", "from_node_id", "to_node_id", "from_project_id", "to_project_id"}
)


@dataclass(slots=True)
class GraphManagementError(Exception):
    category: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


def create_node_type(
    conn,
    *,
    project_id: int,
    type_key: str,
    name: str,
    description: str | None = None,
) -> dict:
    return repo.upsert_node_type(
        conn,
        project_id=project_id,
        type_key=_required_text(type_key, "type_key"),
        name=_required_text(name, "name"),
        description=description,
    )


def list_node_types(conn, *, project_id: int) -> dict:
    rows = repo.list_node_types(conn, project_id)
    return {"node_types": rows, "count": len(rows)}


def archive_node_type(conn, *, project_id: int, type_key: str) -> dict:
    row = repo.archive_node_type(conn, project_id=project_id, type_key=_required_text(type_key, "type_key"))
    if not row:
        raise GraphManagementError(
            category="not_found",
            message="graph node type not found",
            details={"project_id": project_id, "type_key": type_key},
        )
    return row


def create_relation_type(
    conn,
    *,
    project_id: int,
    type_key: str,
    name: str,
    description: str | None = None,
    allowed_from_types: list[str] | None = None,
    allowed_to_types: list[str] | None = None,
    cross_project_allowed: bool = True,
) -> dict:
    normalized_from_types = _normalize_type_list(allowed_from_types)
    normalized_to_types = _normalize_type_list(allowed_to_types)
    _validate_registered_node_types(conn, project_id, normalized_from_types + normalized_to_types)
    return repo.upsert_relation_type(
        conn,
        project_id=project_id,
        type_key=_required_text(type_key, "type_key"),
        name=_required_text(name, "name"),
        description=description,
        allowed_from_types=normalized_from_types,
        allowed_to_types=normalized_to_types,
        cross_project_allowed=bool(cross_project_allowed),
    )


def list_relation_types(conn, *, project_id: int) -> dict:
    rows = repo.list_relation_types(conn, project_id)
    return {"edge_types": rows, "count": len(rows)}


def archive_relation_type(conn, *, project_id: int, type_key: str) -> dict:
    row = repo.archive_relation_type(conn, project_id=project_id, type_key=_required_text(type_key, "type_key"))
    if not row:
        raise GraphManagementError(
            category="not_found",
            message="graph relation type not found",
            details={"project_id": project_id, "type_key": type_key},
        )
    return row


def create_node(
    conn,
    *,
    project_id: int,
    branch: str | None = None,
    node_id: str,
    type_key: str,
    name: str,
    properties: dict | None = None,
) -> dict:
    normalized_type = _required_text(type_key, "type_key")
    _require_node_type(conn, project_id, normalized_type)
    node = repo.upsert_node(
        conn,
        project_id=project_id,
        node_id=_required_text(node_id, "node_id"),
        type_key=normalized_type,
        name=_required_text(name, "name"),
        properties=properties or {},
    )
    if branch:
        _project_node_to_current_snapshot(
            conn,
            project_id=project_id,
            branch=branch,
            node=node,
            operation="upsert",
            before=None,
        )
    return node


def get_node(conn, *, project_id: int, node_id: str) -> dict:
    row = repo.get_node(conn, project_id, _required_text(node_id, "node_id"))
    if not row:
        raise GraphManagementError(
            category="not_found",
            message="graph node not found",
            details={"project_id": project_id, "node_id": node_id},
        )
    return row


def list_nodes(conn, *, project_id: int, type_key: str | None = None) -> dict:
    rows = repo.list_nodes(conn, project_id, type_key=type_key)
    return {"nodes": rows, "count": len(rows)}


def update_node(conn, *, project_id: int, node_id: str, updates: dict, branch: str | None = None) -> dict:
    identity_updates = sorted(key for key in updates if key in IDENTITY_FIELDS)
    if identity_updates:
        raise GraphManagementError(
            category="invalid_argument",
            message="identity fields cannot be updated",
            details={"identity_fields": identity_updates},
        )
    normalized_updates = dict(updates)
    if "type_key" in normalized_updates:
        _require_node_type(conn, project_id, _required_text(normalized_updates["type_key"], "type_key"))
    before = repo.get_node(conn, project_id, _required_text(node_id, "node_id"))
    updated = repo.update_node(
        conn,
        project_id=project_id,
        node_id=_required_text(node_id, "node_id"),
        updates=normalized_updates,
    )
    if not updated:
        raise GraphManagementError(
            category="not_found",
            message="graph node not found",
            details={"project_id": project_id, "node_id": node_id},
        )
    if branch:
        _project_node_to_current_snapshot(
            conn,
            project_id=project_id,
            branch=branch,
            node=updated,
            operation="update",
            before=before,
        )
    return updated


def archive_node(conn, *, project_id: int, node_id: str, branch: str | None = None) -> dict:
    before = repo.get_node(conn, project_id, _required_text(node_id, "node_id"))
    row = repo.archive_node(conn, project_id=project_id, node_id=_required_text(node_id, "node_id"))
    if not row:
        raise GraphManagementError(
            category="not_found",
            message="graph node not found",
            details={"project_id": project_id, "node_id": node_id},
        )
    if branch:
        _archive_node_from_current_snapshot(
            conn,
            project_id=project_id,
            branch=branch,
            node=row,
            before=before,
        )
    return row


def create_edge(
    conn,
    *,
    project_id: int,
    branch: str | None = None,
    edge_id: str,
    from_node_id: str,
    to_node_id: str,
    type_key: str,
    from_project_id: int | None = None,
    to_project_id: int | None = None,
    properties: dict | None = None,
) -> dict:
    normalized_type = _required_text(type_key, "type_key")
    relation_type = repo.get_relation_type(conn, project_id, normalized_type)
    if not relation_type:
        raise GraphManagementError(
            category="invalid_type",
            message="graph relation type is not registered for project",
            details={"project_id": project_id, "type_key": normalized_type},
        )
    from_node = _require_node(conn, from_node_id, project_id=from_project_id)
    to_node = _require_node(conn, to_node_id, project_id=to_project_id)
    from_project_id = int(from_node["project_id"])
    to_project_id = int(to_node["project_id"])

    if project_id not in {from_project_id, to_project_id}:
        raise GraphManagementError(
            category="invalid_scope",
            message="edge owner project must match from or to node project",
            details={
                "project_id": project_id,
                "from_project_id": from_project_id,
                "to_project_id": to_project_id,
            },
        )
    if from_project_id != to_project_id and not relation_type.get("cross_project_allowed", True):
        raise GraphManagementError(
            category="invalid_scope",
            message="relation type does not allow cross-project edges",
            details={"type_key": normalized_type, "cross_project_allowed": False},
        )
    _validate_endpoint_type(
        relation_type,
        direction="from",
        actual_type=str(from_node.get("type_key") or ""),
    )
    _validate_endpoint_type(
        relation_type,
        direction="to",
        actual_type=str(to_node.get("type_key") or ""),
    )

    edge = repo.upsert_edge(
        conn,
        project_id=project_id,
        edge_id=_required_text(edge_id, "edge_id"),
        from_node_id=_required_text(from_node_id, "from_node_id"),
        to_node_id=_required_text(to_node_id, "to_node_id"),
        from_project_id=from_project_id,
        to_project_id=to_project_id,
        type_key=normalized_type,
        properties=properties or {},
    )
    if branch:
        _project_edge_to_current_snapshot(
            conn,
            project_id=project_id,
            branch=branch,
            edge=edge,
            operation="upsert",
            before=None,
        )
    return edge


def get_edge(conn, *, project_id: int, edge_id: str) -> dict:
    row = repo.get_edge(conn, project_id, _required_text(edge_id, "edge_id"))
    if not row:
        raise GraphManagementError(
            category="not_found",
            message="graph edge not found",
            details={"project_id": project_id, "edge_id": edge_id},
        )
    return row


def list_edges(
    conn,
    *,
    project_id: int,
    node_id: str | None = None,
    type_key: str | None = None,
) -> dict:
    rows = repo.list_edges(conn, project_id, node_id=node_id, type_key=type_key)
    return {"edges": rows, "count": len(rows)}


def update_edge(conn, *, project_id: int, edge_id: str, updates: dict, branch: str | None = None) -> dict:
    identity_updates = sorted(key for key in updates if key in EDGE_IDENTITY_FIELDS)
    if identity_updates:
        raise GraphManagementError(
            category="invalid_argument",
            message="identity fields cannot be updated",
            details={"identity_fields": identity_updates},
        )
    normalized_updates = dict(updates)
    if "type_key" in normalized_updates:
        relation_type = repo.get_relation_type(
            conn,
            project_id,
            _required_text(normalized_updates["type_key"], "type_key"),
        )
        if not relation_type:
            raise GraphManagementError(
                category="invalid_type",
                message="graph relation type is not registered for project",
                details={"project_id": project_id, "type_key": normalized_updates["type_key"]},
            )
        existing = get_edge(conn, project_id=project_id, edge_id=edge_id)
        from_node = _require_node(conn, existing["from_node_id"], project_id=existing["from_project_id"])
        to_node = _require_node(conn, existing["to_node_id"], project_id=existing["to_project_id"])
        _validate_endpoint_type(relation_type, direction="from", actual_type=str(from_node.get("type_key") or ""))
        _validate_endpoint_type(relation_type, direction="to", actual_type=str(to_node.get("type_key") or ""))
    before = repo.get_edge(conn, project_id, _required_text(edge_id, "edge_id"))
    updated = repo.update_edge(
        conn,
        project_id=project_id,
        edge_id=_required_text(edge_id, "edge_id"),
        updates=normalized_updates,
    )
    if not updated:
        raise GraphManagementError(
            category="not_found",
            message="graph edge not found",
            details={"project_id": project_id, "edge_id": edge_id},
        )
    if branch:
        _project_edge_to_current_snapshot(
            conn,
            project_id=project_id,
            branch=branch,
            edge=updated,
            operation="update",
            before=before,
        )
    return updated


def archive_edge(conn, *, project_id: int, edge_id: str, branch: str | None = None) -> dict:
    before = repo.get_edge(conn, project_id, _required_text(edge_id, "edge_id"))
    row = repo.archive_edge(conn, project_id=project_id, edge_id=_required_text(edge_id, "edge_id"))
    if not row:
        raise GraphManagementError(
            category="not_found",
            message="graph edge not found",
            details={"project_id": project_id, "edge_id": edge_id},
        )
    if branch:
        _project_edge_to_current_snapshot(
            conn,
            project_id=project_id,
            branch=branch,
            edge=row,
            operation="archive",
            before=before,
        )
    return row


def _project_node_to_current_snapshot(
    conn,
    *,
    project_id: int,
    branch: str,
    node: dict,
    operation: str,
    before: dict | None,
) -> None:
    snapshot = _require_current_snapshot(conn, project_id=project_id, branch=branch)
    log = repo.create_operation_log(
        conn,
        project_id=project_id,
        branch_name=(branch or "").strip(),
        snapshot_id=snapshot["id"],
        object_kind="node",
        object_id=node["node_id"],
        operation=operation,
        before_json=before or {},
        after_json=node,
        source="manual",
    )
    fact = _manual_node_fact(project_id=project_id, node=node, operation_id=log["id"])
    code_fact_repo.upsert_many(conn, [fact])
    branch_snapshot_service.add_fact(
        conn,
        snapshot_id=snapshot["id"],
        fact_id=fact["fact_id"],
    )
    if manual_graph_sync_service:
        manual_graph_sync_service.sync_node(conn, project_id=project_id, node=node, fact=fact)


def _archive_node_from_current_snapshot(
    conn,
    *,
    project_id: int,
    branch: str,
    node: dict,
    before: dict | None,
) -> None:
    snapshot = _require_current_snapshot(conn, project_id=project_id, branch=branch)
    fact_id = _manual_node_fact_id(project_id, node["node_id"])
    branch_snapshot_service.remove_fact(
        conn,
        snapshot_id=snapshot["id"],
        fact_id=fact_id,
    )
    repo.create_operation_log(
        conn,
        project_id=project_id,
        branch_name=(branch or "").strip(),
        snapshot_id=snapshot["id"],
        object_kind="node",
        object_id=node["node_id"],
        operation="archive",
        before_json=before or {},
        after_json=node,
        source="manual",
    )
    if manual_graph_sync_service:
        manual_graph_sync_service.archive_node(conn, project_id=project_id, node=node, fact_id=fact_id)


def _project_edge_to_current_snapshot(
    conn,
    *,
    project_id: int,
    branch: str,
    edge: dict,
    operation: str,
    before: dict | None,
) -> None:
    snapshot = _require_current_snapshot(conn, project_id=project_id, branch=branch)
    repo.create_operation_log(
        conn,
        project_id=project_id,
        branch_name=(branch or "").strip(),
        snapshot_id=snapshot["id"],
        object_kind="edge",
        object_id=edge["edge_id"],
        operation=operation,
        before_json=before or {},
        after_json=edge,
        source="manual",
    )
    if manual_graph_sync_service:
        if operation == "archive":
            manual_graph_sync_service.archive_edge(conn, project_id=project_id, edge=edge)
        else:
            manual_graph_sync_service.sync_edge(
                conn,
                project_id=project_id,
                branch=(branch or "").strip(),
                snapshot_id=snapshot["id"],
                edge=edge,
            )


def _require_current_snapshot(conn, *, project_id: int, branch: str) -> dict:
    normalized_branch = _required_text(branch, "branch")
    snapshot = branch_snapshot_service.get_current_snapshot(conn, project_id, normalized_branch)
    if not snapshot:
        raise GraphManagementError(
            category="invalid_scope",
            message="branch completed snapshot is required for manual graph edits",
            details={"project_id": project_id, "branch": normalized_branch},
        )
    return snapshot


def _manual_node_fact(*, project_id: int, node: dict, operation_id: int) -> dict:
    fact_id = _manual_node_fact_id(project_id, node["node_id"])
    type_key = str(node.get("type_key") or "")
    properties = dict(node.get("properties") or {})
    fact_node_type = properties.get("node_type") if properties.get("node_type") in _FACT_NODE_TYPES else "Function"
    return {
        "project_id": project_id,
        "fact_id": fact_id,
        "symbol_key": fact_id,
        "node_type": fact_node_type,
        "file_path": node.get("file_path"),
        "qualified_name": f"manual.{type_key}.{node['node_id']}",
        "name": node.get("name"),
        "metadata_json": {
            "source": "manual",
            "manual_node_id": node.get("node_id"),
            "type_key": type_key,
            "properties": properties,
            "operation_id": operation_id,
        },
        "status": node.get("status") or "active",
    }


def _manual_node_fact_id(project_id: int, node_id: str) -> str:
    return f"manual:{project_id}:node:{node_id}"


_FACT_NODE_TYPES = {
    "File",
    "Class",
    "Interface",
    "Enum",
    "Annotation",
    "Method",
    "Function",
    "Constructor",
}


def _require_node_type(conn, project_id: int, type_key: str) -> dict:
    node_type = repo.get_node_type(conn, project_id, type_key)
    if not node_type:
        raise GraphManagementError(
            category="invalid_type",
            message="graph node type is not registered for project",
            details={"project_id": project_id, "type_key": type_key},
        )
    return node_type


def _require_node(conn, node_id: str, project_id: int | None = None) -> dict:
    normalized_node_id = _required_text(node_id, "node_id")
    node = (
        repo.get_node(conn, project_id, normalized_node_id)
        if project_id is not None
        else repo.get_node_by_any_project(conn, normalized_node_id)
    )
    if not node:
        details = {"node_id": node_id}
        if project_id is not None:
            details["project_id"] = project_id
        raise GraphManagementError(
            category="not_found",
            message="graph node not found",
            details=details,
        )
    return node


def _normalize_type_list(values: list[str] | None) -> list[str]:
    seen = set()
    normalized = []
    for value in values or []:
        text = _required_text(value, "node_type")
        if text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _validate_registered_node_types(conn, project_id: int, type_keys: list[str]) -> None:
    missing = [type_key for type_key in type_keys if not repo.get_node_type(conn, project_id, type_key)]
    if missing:
        raise GraphManagementError(
            category="invalid_type",
            message="relation endpoint type must be registered in the owner project",
            details={"project_id": project_id, "missing_node_types": missing},
        )


def _validate_endpoint_type(relation_type: dict, *, direction: str, actual_type: str) -> None:
    field = "allowed_from_types" if direction == "from" else "allowed_to_types"
    allowed = relation_type.get(field) or []
    if allowed and actual_type not in allowed:
        raise GraphManagementError(
            category="invalid_type",
            message="relation endpoint node type is not allowed",
            details={
                "type_key": relation_type.get("type_key"),
                "direction": direction,
                "node_type": actual_type,
                "allowed_types": allowed,
            },
        )


def _required_text(value: str | None, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise GraphManagementError(
            category="invalid_argument",
            message=f"{field_name} is required",
            details={"field": field_name},
        )
    return text
