"""Product Versions API: CRUD under /api/products/{product_id}/versions."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from service.dependencies import get_db
from service.services import product_service
from service.services import product_version_service as service

router = APIRouter(prefix="", tags=["product-versions"])


class VersionCreate(BaseModel):
    version_name: str
    description: str | None = None
    status: str = "planning"
    release_date: str | None = None


class VersionUpdate(BaseModel):
    version_name: str | None = None
    description: str | None = None
    status: str | None = None
    release_date: str | None = None


class BranchSetRequest(BaseModel):
    project_id: int
    branch: str


def _check_product(db, product_id: int):
    if not product_service.get_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")


@router.get("/{product_id}/versions", response_model=list)
def list_versions(
    product_id: int,
    status: str | None = Query(None),
    db=Depends(get_db),
):
    _check_product(db, product_id)
    return service.list_versions(db, product_id, status=status)


@router.post("/{product_id}/versions", status_code=201, response_model=dict)
def create_version(product_id: int, body: VersionCreate, db=Depends(get_db)):
    _check_product(db, product_id)
    return service.create_version(
        db, product_id, body.version_name,
        description=body.description, status=body.status, release_date=body.release_date,
    )


@router.get("/{product_id}/versions/{version_id}", response_model=dict)
def get_version(product_id: int, version_id: int, db=Depends(get_db)):
    _check_product(db, product_id)
    ver = service.get_version(db, version_id)
    if not ver or ver["product_id"] != product_id:
        raise HTTPException(status_code=404, detail="Version not found")
    return ver


@router.patch("/{product_id}/versions/{version_id}", response_model=dict)
def update_version(product_id: int, version_id: int, body: VersionUpdate, db=Depends(get_db)):
    _check_product(db, product_id)
    ver = service.get_version(db, version_id)
    if not ver or ver["product_id"] != product_id:
        raise HTTPException(status_code=404, detail="Version not found")
    data = body.model_dump(exclude_unset=True)
    out = service.update_version(db, version_id, **data)
    if out is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return out


@router.delete("/{product_id}/versions/{version_id}", status_code=204)
def delete_version(product_id: int, version_id: int, db=Depends(get_db)):
    _check_product(db, product_id)
    # 检查是否有关联的需求或 Bug，有则拒绝删除
    from psycopg2.extras import RealDictCursor
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT count(*) AS cnt FROM product_requirements WHERE version_id = %s", (version_id,))
        req_count = cur.fetchone()["cnt"]
        cur.execute("SELECT count(*) AS cnt FROM product_bugs WHERE version_id = %s", (version_id,))
        bug_count = cur.fetchone()["cnt"]
    if req_count > 0 or bug_count > 0:
        parts = []
        if req_count > 0:
            parts.append(f"{req_count} 条需求")
        if bug_count > 0:
            parts.append(f"{bug_count} 个Bug")
        raise HTTPException(
            status_code=409,
            detail=f"该版本下仍有{'、'.join(parts)}，请先删除或迁移后再删除版本",
        )
    if not service.delete_version(db, version_id):
        raise HTTPException(status_code=404, detail="Version not found")


# ── 分支映射 ──

@router.get("/{product_id}/versions/{version_id}/branches", response_model=list)
def list_version_branches(product_id: int, version_id: int, db=Depends(get_db)):
    _check_product(db, product_id)
    return service.list_branches(db, version_id)


@router.post("/{product_id}/versions/{version_id}/branches", response_model=dict)
def set_version_branch(product_id: int, version_id: int, body: BranchSetRequest, db=Depends(get_db)):
    _check_product(db, product_id)
    return service.set_branch(db, version_id, body.project_id, body.branch)


@router.delete("/{product_id}/versions/{version_id}/branches/{project_id}", status_code=200)
def remove_version_branch(product_id: int, version_id: int, project_id: int, db=Depends(get_db)):
    _check_product(db, product_id)
    if not service.remove_branch(db, version_id, project_id):
        raise HTTPException(status_code=404, detail="Branch mapping not found")
    return {"removed": True}
