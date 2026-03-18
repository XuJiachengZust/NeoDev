"""API router aggregator: all business routes under /api."""

from fastapi import APIRouter

from service.routers import (
    agent,
    commits,
    feature_summaries,
    impact,
    parse,
    preprocess,
    product_bugs,
    product_requirements,
    product_versions,
    products,
    projects,
    repos,
    requirement_docs,
    sync,
    versions,
)

router = APIRouter(prefix="/api")

router.include_router(repos.router, prefix="/repos", tags=["repos"])
router.include_router(parse.router, prefix="/parse", tags=["parse"])
# Nested under /projects before projects so /projects/{id}/... is matched first
router.include_router(versions.router, prefix="/projects", tags=["versions"])
router.include_router(commits.router, prefix="/projects", tags=["commits"])
router.include_router(impact.router, prefix="/projects", tags=["impact"])
router.include_router(sync.router, prefix="/projects", tags=["sync"])
router.include_router(preprocess.router, prefix="/projects", tags=["preprocess"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(agent.router, prefix="/agent", tags=["agent"])
# 产品化路由
router.include_router(product_versions.router, prefix="/products", tags=["product-versions"])
router.include_router(product_requirements.router, prefix="/products", tags=["product-requirements"])
router.include_router(requirement_docs.router, prefix="/products")
router.include_router(product_bugs.router, prefix="/products", tags=["product-bugs"])
router.include_router(feature_summaries.router, prefix="/products", tags=["feature-summaries"])
router.include_router(impact.product_reports_router, prefix="/products", tags=["product-reports"])
router.include_router(products.router, prefix="/products", tags=["products"])
