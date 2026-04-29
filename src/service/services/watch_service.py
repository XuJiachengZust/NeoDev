"""Project watch service based on branch graph rebuilds."""

from __future__ import annotations

from typing import Any

from psycopg2.extras import RealDictCursor

from service.repositories import project_repository as project_repo


def run_once(
    conn,
    project_id: int,
    config: dict[str, Any] | None = None,
    *,
    pipeline_runner=None,
    neo4j_driver=None,
) -> dict | None:
    """Refresh all product-version branches bound to a watch-enabled project."""
    project = project_repo.find_by_id(conn, project_id)
    if not project:
        return None
    if not project.get("watch_enabled"):
        return {"project_id": project_id, "skipped": True, "reason": "watch_disabled"}

    branches = _list_bound_branches(conn, project_id)
    actions = []
    from service.services import sync_service

    for branch in branches:
        result = sync_service.refresh_graph_for_branch(conn, project_id, branch)
        if result is None:
            continue
        actions.append(
            {
                "branch": branch,
                "action": result.get("graph_action"),
                "snapshot_id": result.get("current_snapshot_id"),
            }
        )
    return {"project_id": project_id, "actions": actions}


def _list_bound_branches(conn, project_id: int) -> list[str]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT branch_name
            FROM product_version_branches
            WHERE project_id = %s
            ORDER BY branch_name
            """,
            (project_id,),
        )
        return [str(row["branch_name"]) for row in cur.fetchall()]
