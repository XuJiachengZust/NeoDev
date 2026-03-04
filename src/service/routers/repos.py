"""Repository resolve and ensure-from-URL API."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from service.path_allowlist import ensure_path_allowed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["repos"])


class ResolveRequest(BaseModel):
    path: str


class ResolveResponse(BaseModel):
    repo_root: str


class BranchesRequest(BaseModel):
    repo_url: str | None = None
    path: str | None = None
    username: str | None = None
    password: str | None = None


class BranchesResponse(BaseModel):
    branches: list[str]
    repo_root: str | None = None


class EnsureRequest(BaseModel):
    repo_url: str
    target_path: str
    branch: str | None = None
    username: str | None = None
    password: str | None = None


class EnsureResponse(BaseModel):
    repo_root: str


@router.post("/branches", response_model=BranchesResponse)
def list_branches(request: BranchesRequest) -> BranchesResponse:
    if request.path:
        ensure_path_allowed(request.path)
        try:
            from gitnexus_parser.ingestion.repo_resolve import (
                resolve_repo_root,
                list_local_branches,
            )
            root = resolve_repo_root(request.path)
            if root is None:
                raise HTTPException(
                    status_code=404,
                    detail="Not a Git repository or path invalid",
                )
            branches = list_local_branches(root)
            return BranchesResponse(branches=branches, repo_root=root)
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))
    if not request.repo_url:
        raise HTTPException(status_code=400, detail="Provide repo_url or path")
    try:
        from gitnexus_parser.ingestion.repo_resolve import list_remote_branches
        branches = list_remote_branches(
            request.repo_url,
            username=request.username,
            password=request.password,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return BranchesResponse(branches=branches)


@router.post("/resolve", response_model=ResolveResponse)
def resolve_repo(request: ResolveRequest) -> ResolveResponse:
    try:
        ensure_path_allowed(request.path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        from gitnexus_parser.ingestion.repo_resolve import resolve_repo_root
        root = resolve_repo_root(request.path)
    except Exception as e:
        logger.exception("POST /api/repos/resolve 失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    if root is None:
        raise HTTPException(
            status_code=404,
            detail="Not a Git repository or path invalid",
        )
    return ResolveResponse(repo_root=root)


@router.post("/ensure", response_model=EnsureResponse)
def ensure_repo(request: EnsureRequest) -> EnsureResponse:
    try:
        ensure_path_allowed(request.target_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        from gitnexus_parser.ingestion.repo_resolve import ensure_repo_from_url
        root = ensure_repo_from_url(
            request.repo_url,
            request.target_path,
            branch=request.branch,
            username=request.username,
            password=request.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return EnsureResponse(repo_root=root)
