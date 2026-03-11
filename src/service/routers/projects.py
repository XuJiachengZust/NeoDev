"""Projects API (Phase 3): CRUD under /api/projects."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from service.dependencies import get_db
from service.services import branch_service
from service.services import project_service as service

router = APIRouter(prefix="", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    repo_path: str
    watch_enabled: bool = False
    neo4j_database: str | None = None
    neo4j_identifier: str | None = None
    repo_username: str | None = None
    repo_password: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    repo_path: str | None = None
    watch_enabled: bool | None = None
    neo4j_database: str | None = None
    neo4j_identifier: str | None = None
    repo_username: str | None = None
    repo_password: str | None = None


@router.get("/", response_model=list)
def list_projects(db=Depends(get_db)):
    return service.list_projects(db)


@router.post("/", status_code=201, response_model=dict)
def create_project(body: ProjectCreate, db=Depends(get_db)):
    repo_url = body.repo_path if _is_remote_url(body.repo_path) else None
    return service.create_project(
        db,
        name=body.name,
        repo_path=body.repo_path,
        watch_enabled=body.watch_enabled,
        neo4j_database=body.neo4j_database,
        neo4j_identifier=body.neo4j_identifier,
        repo_username=body.repo_username,
        repo_password=body.repo_password,
        repo_url=repo_url,
    )


@router.get("/{project_id}", response_model=dict)
def get_project(project_id: int, db=Depends(get_db)):
    out = service.get_project(db, project_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return out


@router.get("/{project_id}/branches", response_model=list[str])
def list_project_branches(project_id: int, db=Depends(get_db)):
    """返回项目分支列表（持久化在 git_branches 表），用于版本绑定下拉。"""
    try:
        branches, err = branch_service.list_project_branches(db, project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Project not found")
    return branches or []


def _is_remote_url(path: str) -> bool:
    p = (path or "").strip()
    return p.startswith("http://") or p.startswith("https://") or p.startswith("git@")


@router.patch("/{project_id}", response_model=dict)
def update_project(project_id: int, body: ProjectUpdate, db=Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    # 当 repo_path 是远程 URL 时，同步保存到 repo_url
    if "repo_path" in data and _is_remote_url(data["repo_path"]):
        data["repo_url"] = data["repo_path"]
    out = service.update_project(db, project_id, **data)
    if out is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return out


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db=Depends(get_db)):
    if not service.delete_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
