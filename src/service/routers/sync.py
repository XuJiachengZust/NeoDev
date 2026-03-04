"""Phase 4: sync-commits (Git to PG) and watch-status."""

from fastapi import APIRouter, Depends, HTTPException

from service.dependencies import get_db
from service.repositories import project_repository as project_repo
from service.repositories import version_repository as version_repo
from service.services import sync_service

router = APIRouter(prefix="", tags=["sync"])


@router.post("/{project_id}/sync-commits")
def sync_commits(project_id: int, db=Depends(get_db)):
    """Sync commits from project repo to PG for all versions; returns summary."""
    result = sync_service.sync_commits_for_project(db, project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.get("/{project_id}/watch-status")
def watch_status(project_id: int, db=Depends(get_db)):
    """Return project watch state and versions with last_parsed_commit (Phase 3)."""
    proj = project_repo.find_by_id(db, project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    versions = version_repo.list_by_project_id(db, project_id)
    return {
        "project_id": project_id,
        "watch_enabled": proj.get("watch_enabled", False),
        "versions": [
            {
                "id": v["id"],
                "branch": v["branch"],
                "last_parsed_commit": v.get("last_parsed_commit"),
            }
            for v in versions
        ],
    }
