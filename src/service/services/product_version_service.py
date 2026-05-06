"""Product version service."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from service.repositories import branch_graph_repository
from service.repositories import doc_code_link_repository
from service.repositories import product_version_repository as repo


class ProductVersionError(Exception):
    def __init__(self, category: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.category = category
        self.message = message
        self.details = details or {}


def list_versions(conn, product_id: int, status: str | None = None) -> list[dict]:
    return repo.list_by_product(conn, product_id, status=status)


def get_version(conn, version_id: int) -> dict | None:
    return repo.find_by_id(conn, version_id)


def get_version_by_name(conn, product_id: int, version_name: str) -> dict | None:
    return repo.find_by_product_and_name(conn, product_id, version_name)


def create_version(
    conn,
    product_id: int,
    version_name: str,
    description: str | None = None,
    status: str = "planning",
    release_date: str | None = None,
) -> dict:
    return repo.create(
        conn,
        product_id,
        version_name,
        description=description,
        status=status,
        release_date=release_date,
    )


def update_version(conn, version_id: int, **kwargs) -> dict | None:
    return repo.update(conn, version_id, **kwargs)


def delete_version(conn, version_id: int) -> bool:
    return repo.delete(conn, version_id)


def list_branches(conn, version_id: int) -> list[dict]:
    return repo.list_branches(conn, version_id)


def set_branch(conn, version_id: int, project_id: int, branch: str) -> dict:
    return repo.set_branch(conn, version_id, project_id, (branch or "").strip())


def remove_branch(conn, version_id: int, project_id: int) -> bool:
    return repo.remove_branch(conn, version_id, project_id)


def get_bound_branch(conn, product_version_id: int, project_id: int) -> dict:
    return _require_bound_branch(conn, product_version_id, project_id)


def bind_code_link(
    conn,
    *,
    product_version_id: int,
    project_id: int,
    doc_id: str,
    doc_node_id: str | None,
    relation_type: str,
    code_locator: dict[str, Any],
    source: str = "manual",
    confidence: float | None = None,
) -> dict:
    branch = _require_bound_branch(conn, product_version_id, project_id)
    locator_hash = _locator_hash(code_locator)
    graph = branch_graph_repository.get_by_project_branch(conn, project_id, branch["branch_name"])
    resolved_node_id = code_locator.get("code_node_id")
    resolution_status = "resolved" if graph and graph.get("status") == "ready" and resolved_node_id else "pending"
    return doc_code_link_repository.upsert_active(
        conn,
        product_version_id=product_version_id,
        project_id=project_id,
        branch_name=branch["branch_name"],
        doc_id=doc_id,
        doc_node_id=doc_node_id,
        relation_type=relation_type or "LINKS_TO_CODE",
        code_locator_json=code_locator,
        code_locator_hash=locator_hash,
        resolved_graph_id=(graph or {}).get("id"),
        resolved_node_id=resolved_node_id,
        resolution_status=resolution_status,
        source=source,
        confidence=confidence,
    )


def unbind_code_link(conn, *, link_id: int, product_version_id: int | None = None) -> dict | None:
    return doc_code_link_repository.mark_inactive(
        conn,
        link_id=link_id,
        product_version_id=product_version_id,
    )


def _require_bound_branch(conn, product_version_id: int, project_id: int) -> dict:
    branches = repo.list_branches(conn, product_version_id)
    for branch in branches:
        if int(branch["project_id"]) == int(project_id):
            return branch
    raise ProductVersionError(
        category="invalid_scope",
        message="project branch is not bound to product version",
        details={"product_version_id": product_version_id, "project_id": project_id},
    )


def _locator_hash(locator: dict[str, Any]) -> str:
    payload = json.dumps(locator, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
