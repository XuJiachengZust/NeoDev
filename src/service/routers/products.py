"""Products API: CRUD under /api/products, including project binding."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from service.dependencies import get_db
from service.services import product_service as service

router = APIRouter(prefix="", tags=["products"])


class ProductCreate(BaseModel):
    name: str
    code: str | None = None
    description: str | None = None
    owner: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    owner: str | None = None
    status: str | None = None


class ProjectBindRequest(BaseModel):
    project_id: int


class ProjectCreateInProduct(BaseModel):
    name: str
    repo_path: str
    repo_username: str | None = None
    repo_password: str | None = None


@router.get("", response_model=list)
def list_products(status: str | None = Query(None), db=Depends(get_db)):
    return service.list_products(db, status=status)


@router.post("", status_code=201, response_model=dict)
def create_product(body: ProductCreate, db=Depends(get_db)):
    return service.create_product(
        db, name=body.name, code=body.code,
        description=body.description, owner=body.owner,
    )


@router.get("/{product_id}", response_model=dict)
def get_product(product_id: int, db=Depends(get_db)):
    out = service.get_product(db, product_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return out


@router.patch("/{product_id}", response_model=dict)
def update_product(product_id: int, body: ProductUpdate, db=Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    out = service.update_product(db, product_id, **data)
    if out is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return out


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db=Depends(get_db)):
    if not service.delete_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")


# ── 产品-项目关联 ──

@router.get("/{product_id}/projects", response_model=list)
def list_product_projects(product_id: int, db=Depends(get_db)):
    product = service.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return service.list_projects(db, product_id)


@router.post("/{product_id}/projects/create", status_code=201, response_model=dict)
def create_project_in_product(product_id: int, body: ProjectCreateInProduct, db=Depends(get_db)):
    product = service.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return service.create_project_in_product(
        db,
        product_id=product_id,
        name=body.name,
        repo_path=body.repo_path,
        repo_username=body.repo_username,
        repo_password=body.repo_password,
    )


@router.post("/{product_id}/projects", status_code=200)
def bind_project(product_id: int, body: ProjectBindRequest, db=Depends(get_db)):
    product = service.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    ok = service.bind_project(db, product_id, body.project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"product_id": product_id, "project_id": body.project_id, "bound": True}


@router.delete("/{product_id}/projects/{project_id}", status_code=200)
def unbind_project(product_id: int, project_id: int, db=Depends(get_db)):
    ok = service.unbind_project(db, product_id, project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Binding not found")
    return {"product_id": product_id, "project_id": project_id, "unbound": True}
