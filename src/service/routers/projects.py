"""Projects API (Phase 3): CRUD under /api/projects."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from service.dependencies import get_db
from service.services import project_service as service

router = APIRouter(prefix="", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    repo_path: str
    watch_enabled: bool = False
    neo4j_database: str | None = None
    neo4j_identifier: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    repo_path: str | None = None
    watch_enabled: bool | None = None
    neo4j_database: str | None = None
    neo4j_identifier: str | None = None


@router.get("/", response_model=list)
def list_projects(db=Depends(get_db)):
    return service.list_projects(db)


@router.post("/", status_code=201, response_model=dict)
def create_project(body: ProjectCreate, db=Depends(get_db)):
    return service.create_project(
        db,
        name=body.name,
        repo_path=body.repo_path,
        watch_enabled=body.watch_enabled,
        neo4j_database=body.neo4j_database,
        neo4j_identifier=body.neo4j_identifier,
    )


@router.get("/{project_id}", response_model=dict)
def get_project(project_id: int, db=Depends(get_db)):
    out = service.get_project(db, project_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return out


@router.patch("/{project_id}", response_model=dict)
def update_project(project_id: int, body: ProjectUpdate, db=Depends(get_db)):
    out = service.update_project(
        db,
        project_id,
        name=body.name,
        repo_path=body.repo_path,
        watch_enabled=body.watch_enabled,
        neo4j_database=body.neo4j_database,
        neo4j_identifier=body.neo4j_identifier,
    )
    if out is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return out


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db=Depends(get_db)):
    if not service.delete_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
