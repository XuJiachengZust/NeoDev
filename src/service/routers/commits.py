"""Commits API (Phase 3): read-only under /api/projects/{project_id}/commits."""

from fastapi import APIRouter, Depends, HTTPException, Query

from service.dependencies import get_db
from service.services import commit_service as service

router = APIRouter(prefix="", tags=["commits"])


@router.get("/{project_id}/commits", response_model=list)
def list_commits(
    project_id: int,
    version_id: int | None = Query(None),
    requirement_id: int | None = Query(None),
    db=Depends(get_db),
):
    out = service.list_commits(
        db, project_id, version_id=version_id, requirement_id=requirement_id
    )
    if out is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return out


@router.get("/{project_id}/versions/{version_id}/commits", response_model=list)
def list_commits_by_version(
    project_id: int, version_id: int, db=Depends(get_db)
):
    out = service.list_commits_by_version(db, project_id, version_id)
    if out is None:
        raise HTTPException(
            status_code=404,
            detail="Project or version not found",
        )
    return out
