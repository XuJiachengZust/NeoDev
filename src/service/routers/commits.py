"""Commits API (Phase 3): read-only under /api/projects/{project_id}/commits. Nodes list under versions."""

from fastapi import APIRouter, Depends, HTTPException, Query

from service.dependencies import get_db
from service.services import commit_service as service
from service.services import node_service as node_service

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
    project_id: int,
    version_id: int,
    message: str | None = Query(None),
    committed_at_from: str | None = Query(None),
    committed_at_to: str | None = Query(None),
    commit_id: int | None = Query(None, alias="id"),
    sha: str | None = Query(None),
    db=Depends(get_db),
):
    out = service.list_commits_by_version(
        db,
        project_id,
        version_id,
        message=message,
        committed_at_from=committed_at_from,
        committed_at_to=committed_at_to,
        id=commit_id,
        sha=sha,
    )
    if out is None:
        raise HTTPException(
            status_code=404,
            detail="Project or version not found",
        )
    return out


@router.get("/{project_id}/versions/{version_id}/nodes", response_model=list)
def list_nodes_by_version(
    project_id: int,
    version_id: int,
    name: str | None = Query(None),
    type_filter: str | None = Query(None, alias="type"),
    db=Depends(get_db),
):
    """List graph nodes for a version; optional filters: name (substring), type (label)."""
    out = node_service.list_nodes_by_version(
        db, project_id, version_id, name=name, type_filter=type_filter
    )
    if out is None:
        raise HTTPException(
            status_code=404,
            detail="Project or version not found",
        )
    return out
