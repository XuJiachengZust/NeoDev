"""预处理 API：单分支触发与状态查询。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from service.dependencies import get_db
from service.repositories import ai_preprocess_status_repository as status_repo
from service.repositories import project_repository as project_repo
from service.services.ai_preprocessor_service import (
    ProjectBusyError,
    run_preprocess,
)

router = APIRouter(prefix="", tags=["preprocess"])


@router.post("/{project_id}/preprocess")
def post_preprocess(
    project_id: int,
    db=Depends(get_db),
    branch: str = Query("main", description="本次只处理该分支"),
    force: bool = Query(False, description="强制重算"),
):
    """触发 AI 预处理（单分支）；同一项目同时仅允许一个任务。"""
    try:
        body = run_preprocess(db, project_id, branch=branch, force=force)
        return body
    except ProjectBusyError as e:
        return JSONResponse(
            status_code=409,
            content={"detail": e.detail, "code": e.code},
        )
    except HTTPException:
        raise


@router.get("/{project_id}/preprocess/status")
def get_preprocess_status(
    project_id: int,
    db=Depends(get_db),
    branch: str | None = Query(None, description="不传则返回该项目下所有 branch 状态"),
):
    """查询预处理状态：单 branch 返回单对象，不传 branch 返回 items 列表。"""
    proj = project_repo.find_by_id(db, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    rows = status_repo.get_status(db, project_id, branch)
    if branch is not None:
        if not rows:
            raise HTTPException(status_code=404, detail="No preprocess status for this branch")
        row = rows[0]
        return _row_to_status_body(row)
    return {"items": [_row_to_status_body(r) for r in rows]}


def _row_to_status_body(row: dict) -> dict:
    """把 DB 行转为 API 返回体（含 project_id, branch, status, started_at, finished_at, extra 等）。"""
    return {
        "project_id": row["project_id"],
        "branch": row["branch"],
        "status": row["status"],
        "started_at": row["started_at"].isoformat() if row.get("started_at") else None,
        "finished_at": row["finished_at"].isoformat() if row.get("finished_at") else None,
        "error_message": row.get("error_message"),
        "extra": row.get("extra"),
    }
