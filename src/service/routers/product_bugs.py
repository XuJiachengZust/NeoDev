"""Product Bugs API: CRUD under /api/products/{product_id}/bugs."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from service.dependencies import get_db
from service.services import product_service
from service.services import product_bug_service as service

router = APIRouter(prefix="", tags=["product-bugs"])


class BugCreate(BaseModel):
    title: str
    description: str | None = None
    external_id: str | None = None
    severity: str = "minor"
    status: str = "open"
    priority: str = "medium"
    assignee: str | None = None
    reporter: str | None = None
    version_id: int
    fix_version_id: int | None = None
    requirement_id: int | None = None


class BugUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    external_id: str | None = None
    severity: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee: str | None = None
    reporter: str | None = None
    version_id: int | None = None
    fix_version_id: int | None = None
    requirement_id: int | None = None


class CommitBindRequest(BaseModel):
    commit_ids: list[int]


def _check_product(db, product_id: int):
    if not product_service.get_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")


@router.get("/{product_id}/bugs", response_model=list)
def list_bugs(
    product_id: int,
    status: str | None = Query(None),
    severity: str | None = Query(None),
    version_id: int | None = Query(None),
    db=Depends(get_db),
):
    _check_product(db, product_id)
    return service.list_bugs(
        db, product_id, status=status, severity=severity, version_id=version_id,
    )


@router.post("/{product_id}/bugs", status_code=201, response_model=dict)
def create_bug(product_id: int, body: BugCreate, db=Depends(get_db)):
    _check_product(db, product_id)
    return service.create_bug(
        db, product_id, body.title,
        description=body.description, external_id=body.external_id,
        severity=body.severity, status=body.status, priority=body.priority,
        assignee=body.assignee, reporter=body.reporter,
        version_id=body.version_id, fix_version_id=body.fix_version_id,
        requirement_id=body.requirement_id,
    )


@router.get("/{product_id}/bugs/{bug_id}", response_model=dict)
def get_bug(product_id: int, bug_id: int, db=Depends(get_db)):
    _check_product(db, product_id)
    bug = service.get_bug(db, bug_id)
    if not bug or bug["product_id"] != product_id:
        raise HTTPException(status_code=404, detail="Bug not found")
    return bug


@router.patch("/{product_id}/bugs/{bug_id}", response_model=dict)
def update_bug(product_id: int, bug_id: int, body: BugUpdate, db=Depends(get_db)):
    _check_product(db, product_id)
    data = body.model_dump(exclude_unset=True)
    out = service.update_bug(db, bug_id, **data)
    if out is None:
        raise HTTPException(status_code=404, detail="Bug not found")
    return out


@router.delete("/{product_id}/bugs/{bug_id}", status_code=204)
def delete_bug(product_id: int, bug_id: int, db=Depends(get_db)):
    _check_product(db, product_id)
    if not service.delete_bug(db, bug_id):
        raise HTTPException(status_code=404, detail="Bug not found")


# ── Bug-提交关联 ──

@router.get("/{product_id}/bugs/{bug_id}/commits", response_model=list)
def list_bug_commits(product_id: int, bug_id: int, db=Depends(get_db)):
    _check_product(db, product_id)
    return service.list_commits(db, bug_id)


@router.post("/{product_id}/bugs/{bug_id}/commits")
def bind_commits(product_id: int, bug_id: int, body: CommitBindRequest, db=Depends(get_db)):
    _check_product(db, product_id)
    count = service.bind_commits(db, bug_id, body.commit_ids)
    return {"bound": count}


@router.delete("/{product_id}/bugs/{bug_id}/commits")
def unbind_commits(product_id: int, bug_id: int, body: CommitBindRequest, db=Depends(get_db)):
    _check_product(db, product_id)
    count = service.unbind_commits(db, bug_id, body.commit_ids)
    return {"unbound": count}
