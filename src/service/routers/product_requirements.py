"""Product Requirements API: three-level requirements under /api/products/{product_id}/requirements."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from service.dependencies import get_db
from service.services import product_service
from service.services import product_requirement_service as service

router = APIRouter(prefix="", tags=["product-requirements"])


class RequirementCreate(BaseModel):
    title: str
    level: str = "story"
    parent_id: int | None = None
    description: str | None = None
    external_id: str | None = None
    status: str = "open"
    priority: str = "medium"
    assignee: str | None = None
    version_id: int
    sort_order: int = 0


class RequirementUpdate(BaseModel):
    title: str | None = None
    level: str | None = None
    parent_id: int | None = None
    description: str | None = None
    external_id: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee: str | None = None
    version_id: int | None = None
    sort_order: int | None = None


class CommitBindRequest(BaseModel):
    commit_ids: list[int]


def _check_product(db, product_id: int):
    if not product_service.get_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")


@router.get("/{product_id}/requirements", response_model=list)
def list_requirements(
    product_id: int,
    level: str | None = Query(None),
    parent_id: int | None = Query(None),
    status: str | None = Query(None),
    version_id: int | None = Query(None),
    db=Depends(get_db),
):
    _check_product(db, product_id)
    return service.list_requirements(
        db, product_id,
        level=level, parent_id=parent_id, status=status, version_id=version_id,
    )


@router.get("/{product_id}/requirements/tree", response_model=list)
def list_requirements_tree(
    product_id: int,
    version_id: int | None = Query(None),
    db=Depends(get_db),
):
    """返回平铺列表，前端根据 parent_id 构建树。"""
    _check_product(db, product_id)
    return service.list_tree(db, product_id, version_id=version_id)


@router.get("/{product_id}/requirements/tree_counts", response_model=list)
def list_requirements_tree_with_counts(
    product_id: int,
    version_id: int | None = Query(None),
    db=Depends(get_db),
):
    """返回平铺需求列表，附带每条需求已绑定提交数。"""
    _check_product(db, product_id)
    return service.list_tree_with_counts(db, product_id, version_id=version_id)


@router.post("/{product_id}/requirements", status_code=201, response_model=dict)
def create_requirement(product_id: int, body: RequirementCreate, db=Depends(get_db)):
    _check_product(db, product_id)
    return service.create_requirement(
        db, product_id, body.title,
        level=body.level, parent_id=body.parent_id,
        description=body.description, external_id=body.external_id,
        status=body.status, priority=body.priority,
        assignee=body.assignee, version_id=body.version_id,
        sort_order=body.sort_order,
    )


@router.get("/{product_id}/requirements/{requirement_id}", response_model=dict)
def get_requirement(product_id: int, requirement_id: int, db=Depends(get_db)):
    _check_product(db, product_id)
    req = service.get_requirement(db, requirement_id)
    if not req or req["product_id"] != product_id:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return req


@router.patch("/{product_id}/requirements/{requirement_id}", response_model=dict)
def update_requirement(product_id: int, requirement_id: int, body: RequirementUpdate, db=Depends(get_db)):
    _check_product(db, product_id)
    data = body.model_dump(exclude_unset=True)
    out = service.update_requirement(db, requirement_id, **data)
    if out is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return out


@router.delete("/{product_id}/requirements/{requirement_id}", status_code=204)
def delete_requirement(product_id: int, requirement_id: int, db=Depends(get_db)):
    _check_product(db, product_id)
    if not service.delete_requirement(db, requirement_id):
        raise HTTPException(status_code=404, detail="Requirement not found")


# ── 需求-提交关联 ──

@router.get("/{product_id}/requirements/{requirement_id}/commits", response_model=list)
def list_requirement_commits(product_id: int, requirement_id: int, db=Depends(get_db)):
    _check_product(db, product_id)
    return service.list_commits(db, requirement_id)


@router.post("/{product_id}/requirements/{requirement_id}/commits")
def bind_commits(product_id: int, requirement_id: int, body: CommitBindRequest, db=Depends(get_db)):
    _check_product(db, product_id)
    count = service.bind_commits(db, requirement_id, body.commit_ids)
    return {"bound": count}


@router.delete("/{product_id}/requirements/{requirement_id}/commits")
def unbind_commits(product_id: int, requirement_id: int, body: CommitBindRequest, db=Depends(get_db)):
    _check_product(db, product_id)
    count = service.unbind_commits(db, requirement_id, body.commit_ids)
    return {"unbound": count}
