"""版本功能总结 API：列表、详情、手动触发。"""

from fastapi import APIRouter, Depends, HTTPException

from service.dependencies import get_db
from service.services import product_service
from service.services import product_version_service as pv_service
from service.services import version_feature_summary_service as summary_service
from service.repositories import version_feature_summary_repository as summary_repo

router = APIRouter(prefix="", tags=["feature-summaries"])


def _check_version(db, product_id: int, version_id: int) -> dict:
    """校验产品和版本存在且匹配。"""
    if not product_service.get_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    ver = pv_service.get_version(db, version_id)
    if not ver or ver["product_id"] != product_id:
        raise HTTPException(status_code=404, detail="Version not found")
    return ver


@router.get("/{product_id}/versions/{version_id}/feature-summaries")
def list_feature_summaries(product_id: int, version_id: int, db=Depends(get_db)):
    """列出该版本下所有项目的功能总结。"""
    _check_version(db, product_id, version_id)
    items = summary_service.list_summaries(db, version_id)
    return {"items": [_row_to_body(r) for r in items]}


@router.post("/{product_id}/versions/{version_id}/feature-summaries/trigger")
def trigger_feature_summaries(product_id: int, version_id: int, db=Depends(get_db)):
    """手动触发该版本下所有已映射分支的功能总结生成。"""
    _check_version(db, product_id, version_id)
    records = summary_service.trigger_for_version(db, version_id)
    if not records:
        return {"message": "该版本无已映射的项目分支", "triggered": 0}
    return {
        "message": f"已触发 {len(records)} 个项目的功能总结生成",
        "triggered": len(records),
        "items": records,
    }


@router.get("/{product_id}/versions/{version_id}/feature-summaries/{summary_id}")
def get_feature_summary(product_id: int, version_id: int, summary_id: int, db=Depends(get_db)):
    """获取单条功能总结详情。"""
    _check_version(db, product_id, version_id)
    row = summary_repo.find_by_id(db, summary_id)
    if not row or row["product_version_id"] != version_id:
        raise HTTPException(status_code=404, detail="Feature summary not found")
    return _row_to_body(row)


def _row_to_body(row: dict) -> dict:
    """DB 行转 API 返回体。"""
    return {
        "id": row["id"],
        "product_version_id": row["product_version_id"],
        "project_id": row["project_id"],
        "project_name": row.get("project_name"),
        "branch": row["branch"],
        "status": row["status"],
        "summary": row.get("summary"),
        "error_message": row.get("error_message"),
        "triggered_at": row["triggered_at"].isoformat() if row.get("triggered_at") else None,
        "finished_at": row["finished_at"].isoformat() if row.get("finished_at") else None,
    }
