"""Versions API (Phase 3): under /api/projects/{project_id}/versions."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from service.dependencies import get_db
from service.services import version_service as service

router = APIRouter(prefix="", tags=["versions"])


class VersionCreate(BaseModel):
    branch: str | None = None
    version_name: str | None = None


@router.get("/{project_id}/versions", response_model=list)
def list_versions(project_id: int, db=Depends(get_db)):
    out = service.list_versions(db, project_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return out


@router.post("/{project_id}/versions", status_code=201, response_model=dict)
def create_version(project_id: int, body: VersionCreate, db=Depends(get_db)):
    branch = (body.branch or "").strip() or None
    version_name = (body.version_name or "").strip() or None
    if not branch and not version_name:
        raise HTTPException(
            status_code=400,
            detail="At least one of branch or version_name is required",
        )
    row, err = service.create_version(
        db, project_id, branch, version_name
    )
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Project not found")
    if err == "duplicate_branch":
        raise HTTPException(
            status_code=409,
            detail="Version with this branch already exists for this project",
        )
    return row


@router.delete("/{project_id}/versions/{version_id}", status_code=204)
def delete_version(project_id: int, version_id: int, db=Depends(get_db)):
    err = service.delete_version(db, project_id, version_id)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Version or project not found")
