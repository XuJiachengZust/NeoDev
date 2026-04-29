"""Product version API for the NeoDev MVP surface."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from service.dependencies import get_db
from service.services import doc_code_link_service
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


class DocCodeLinkCreate(BaseModel):
    doc_id: str
    doc_node_id: str | None = None
    code_project_id: int
    symbol_key: str
    relation_type: str
    source: str = "manual"
    confidence: float | None = None
    metadata_json: dict | None = None


def _check_product(db, product_id: int):
    if not product_service.get_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")


def _check_version_for_product(db, product_id: int, version_id: int) -> dict:
    _check_product(db, product_id)
    ver = service.get_version(db, version_id)
    if not ver or ver["product_id"] != product_id:
        raise HTTPException(status_code=404, detail="Version not found")
    return ver


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
        db,
        product_id,
        body.version_name,
        description=body.description,
        status=body.status,
        release_date=body.release_date,
    )


@router.get("/{product_id}/versions/{version_id}", response_model=dict)
def get_version(product_id: int, version_id: int, db=Depends(get_db)):
    return _check_version_for_product(db, product_id, version_id)


@router.patch("/{product_id}/versions/{version_id}", response_model=dict)
def update_version(product_id: int, version_id: int, body: VersionUpdate, db=Depends(get_db)):
    _check_version_for_product(db, product_id, version_id)
    data = body.model_dump(exclude_unset=True)
    out = service.update_version(db, version_id, **data)
    if out is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return out


@router.delete("/{product_id}/versions/{version_id}", status_code=204)
def delete_version(product_id: int, version_id: int, db=Depends(get_db)):
    _check_product(db, product_id)
    if not service.delete_version(db, version_id):
        raise HTTPException(status_code=404, detail="Version not found")


@router.get("/{product_id}/versions/{version_id}/branches", response_model=list)
def list_version_branches(product_id: int, version_id: int, db=Depends(get_db)):
    _check_version_for_product(db, product_id, version_id)
    return service.list_branches(db, version_id)


@router.post("/{product_id}/versions/{version_id}/branches", response_model=dict)
def set_version_branch(product_id: int, version_id: int, body: BranchSetRequest, db=Depends(get_db)):
    _check_version_for_product(db, product_id, version_id)
    return service.set_branch(db, version_id, body.project_id, body.branch)


@router.delete("/{product_id}/versions/{version_id}/branches/{project_id}", status_code=200)
def remove_version_branch(product_id: int, version_id: int, project_id: int, db=Depends(get_db)):
    _check_version_for_product(db, product_id, version_id)
    if not service.remove_branch(db, version_id, project_id):
        raise HTTPException(status_code=404, detail="Branch mapping not found")
    return {"removed": True}


@router.get("/{product_id}/versions/{version_id}/code-facts", response_model=list)
def list_version_code_facts(
    product_id: int,
    version_id: int,
    node_type: list[str] | None = Query(None),
    db=Depends(get_db),
):
    _check_version_for_product(db, product_id, version_id)
    return service.list_code_facts(db, version_id, node_types=node_type)


@router.post("/{product_id}/versions/{version_id}/doc-code-links", response_model=dict)
def create_doc_code_link(
    product_id: int,
    version_id: int,
    body: DocCodeLinkCreate,
    db=Depends(get_db),
):
    _check_version_for_product(db, product_id, version_id)
    return doc_code_link_service.create_link(
        db,
        product_id=product_id,
        product_version_id=version_id,
        doc_id=body.doc_id,
        doc_node_id=body.doc_node_id,
        code_project_id=body.code_project_id,
        symbol_key=body.symbol_key,
        relation_type=body.relation_type,
        source=body.source,
        confidence=body.confidence,
        metadata_json=body.metadata_json,
    )


@router.get("/{product_id}/versions/{version_id}/docs/{doc_id}/code-facts", response_model=dict)
def list_doc_code_facts(
    product_id: int,
    version_id: int,
    doc_id: str,
    db=Depends(get_db),
):
    _check_version_for_product(db, product_id, version_id)
    return doc_code_link_service.list_code_facts_for_doc(
        db,
        product_version_id=version_id,
        doc_id=doc_id,
    )
