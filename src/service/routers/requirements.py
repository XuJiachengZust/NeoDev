"""Requirements API (Phase 3): under /api/projects/{project_id}/requirements."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from service.dependencies import get_db
from service.services import requirement_service as service

router = APIRouter(prefix="", tags=["requirements"])


class RequirementCreate(BaseModel):
    title: str
    description: str | None = None
    external_id: str | None = None


class RequirementUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    external_id: str | None = None


class CommitIdsBody(BaseModel):
    commit_ids: list[int]


@router.get("/{project_id}/requirements", response_model=list)
def list_requirements(project_id: int, db=Depends(get_db)):
    out = service.list_requirements(db, project_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return out


@router.post("/{project_id}/requirements", status_code=201, response_model=dict)
def create_requirement(project_id: int, body: RequirementCreate, db=Depends(get_db)):
    out = service.create_requirement(
        db, project_id, body.title, body.description, body.external_id
    )
    if out is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return out


@router.get("/{project_id}/requirements/{requirement_id}", response_model=dict)
def get_requirement(
    project_id: int, requirement_id: int, db=Depends(get_db)
):
    out = service.get_requirement(db, project_id, requirement_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return out


@router.patch("/{project_id}/requirements/{requirement_id}", response_model=dict)
def update_requirement(
    project_id: int,
    requirement_id: int,
    body: RequirementUpdate,
    db=Depends(get_db),
):
    out = service.update_requirement(
        db,
        project_id,
        requirement_id,
        body.title,
        body.description,
        body.external_id,
    )
    if out is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return out


@router.delete("/{project_id}/requirements/{requirement_id}", status_code=204)
def delete_requirement(
    project_id: int, requirement_id: int, db=Depends(get_db)
):
    if not service.delete_requirement(db, project_id, requirement_id):
        raise HTTPException(status_code=404, detail="Requirement not found")


@router.post(
    "/{project_id}/requirements/{requirement_id}/commits",
    status_code=204,
)
def bind_requirement_commits(
    project_id: int,
    requirement_id: int,
    body: CommitIdsBody,
    db=Depends(get_db),
):
    err = service.bind_requirement_commits(
        db, project_id, requirement_id, body.commit_ids
    )
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Requirement not found")
    if err == "invalid_commits":
        raise HTTPException(
            status_code=400,
            detail="One or more commit_ids do not exist or do not belong to this project",
        )


@router.delete(
    "/{project_id}/requirements/{requirement_id}/commits",
    status_code=204,
)
def unbind_requirement_commits(
    project_id: int,
    requirement_id: int,
    commit_ids: list[int] = Query(...),
    db=Depends(get_db),
):
    err = service.unbind_requirement_commits(
        db, project_id, requirement_id, commit_ids
    )
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Requirement not found")
