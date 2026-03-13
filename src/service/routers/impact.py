"""Impact analyses API: under /api/projects/{project_id}/impact-analyses + product-level reports."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from service.dependencies import get_db
from service.services import impact_analysis_service as service

router = APIRouter(prefix="", tags=["impact"])


class ImpactAnalysisCreate(BaseModel):
    commit_ids: list[int]


@router.post("/{project_id}/impact-analyses", status_code=201, response_model=dict)
def create_impact_analysis(
    project_id: int, body: ImpactAnalysisCreate, db=Depends(get_db)
):
    row, err = service.create_analysis(
        db, project_id, body.commit_ids, status="pending"
    )
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Project not found")
    if err == "empty_commits":
        raise HTTPException(
            status_code=400,
            detail="commit_ids must not be empty",
        )
    if err == "invalid_commits":
        raise HTTPException(
            status_code=400,
            detail="One or more commit_ids do not exist or do not belong to this project",
        )
    return row


@router.get("/{project_id}/impact-analyses", response_model=list)
def list_impact_analyses(project_id: int, db=Depends(get_db)):
    out = service.list_analyses(db, project_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return out


@router.get("/{project_id}/impact-analyses/{analysis_id}", response_model=dict)
def get_impact_analysis(
    project_id: int, analysis_id: int, db=Depends(get_db)
):
    out = service.get_analysis(db, project_id, analysis_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Impact analysis not found")
    return out


# 产品级报告路由（单独 router，挂载到 /api/products 前缀）
product_reports_router = APIRouter(prefix="", tags=["product-reports"])


@product_reports_router.get("/{product_id}/reports", response_model=list)
def list_product_reports(product_id: int, db=Depends(get_db)):
    return service.list_by_product(db, product_id)
