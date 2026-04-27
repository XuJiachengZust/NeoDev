"""API router aggregator for the NeoDev MVP surface."""

from fastapi import APIRouter

from service.routers import (
    cli,
    commits,
    parse,
    preprocess,
    product_versions,
    products,
    projects,
    repos,
    sync,
    versions,
)

router = APIRouter(prefix="/api")

router.include_router(cli.router, prefix="/cli", tags=["cli"])
router.include_router(repos.router, prefix="/repos", tags=["repos"])
router.include_router(parse.router, prefix="/parse", tags=["parse"])
router.include_router(versions.router, prefix="/projects", tags=["versions"])
router.include_router(commits.router, prefix="/projects", tags=["commits"])
router.include_router(sync.router, prefix="/projects", tags=["sync"])
router.include_router(preprocess.router, prefix="/projects", tags=["preprocess"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(product_versions.router, prefix="/products", tags=["product-versions"])
router.include_router(products.router, prefix="/products", tags=["products"])
