"""Project graph refresh API."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from service.dependencies import get_db
from service.repositories import project_repository as project_repo
from service.services import sync_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["sync"])


@router.post("/{project_id}/refresh-graph")
def refresh_project_branch_graph(
    project_id: int,
    branch: str = Query(...),
    db=Depends(get_db),
):
    """Rebuild graph facts for one project branch."""
    try:
        result = sync_service.refresh_graph_for_branch(db, project_id, branch)
    except (ValueError, RuntimeError) as e:
        logger.warning("refresh-graph project_id=%s branch=%s failed: %s", project_id, branch, e)
        raise HTTPException(status_code=502, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Project or branch not found")
    return result


@router.get("/{project_id}/watch-status")
def watch_status(project_id: int, db=Depends(get_db)):
    """Return project watch state."""
    project = project_repo.find_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "project_id": project_id,
        "watch_enabled": project.get("watch_enabled", False),
    }
