"""Phase 4: sync-commits (Git to PG) and watch-status."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from service.dependencies import get_db
from service.repositories import project_repository as project_repo
from service.repositories import version_repository as version_repo
from service.services import sync_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["sync"])


@router.post("/{project_id}/versions/{version_id}/sync-commits")
def sync_commits_for_version(project_id: int, version_id: int, db=Depends(get_db)):
    """Sync commits and run graph pipeline for a single version (branch); returns summary."""
    try:
        result = sync_service.sync_commits_for_version(db, project_id, version_id)
    except (ValueError, RuntimeError) as e:
        logger.warning("sync-commits project_id=%s version_id=%s failed: %s", project_id, version_id, e)
        raise HTTPException(status_code=502, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Project or version not found")
    return result


@router.post("/{project_id}/sync-commits")
def sync_commits(project_id: int, db=Depends(get_db)):
    """Sync commits from project repo to PG for all versions; returns summary."""
    try:
        result = sync_service.sync_commits_for_project(db, project_id)
    except (ValueError, RuntimeError) as e:
        logger.warning("sync-commits project_id=%s failed: %s", project_id, e)
        raise HTTPException(status_code=502, detail=str(e))
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
