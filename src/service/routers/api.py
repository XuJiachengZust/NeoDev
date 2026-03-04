"""API router aggregator: all business routes under /api."""

from fastapi import APIRouter

from service.routers import (
    commits,
    impact,
    parse,
    projects,
    repos,
    requirements,
    sync,
    versions,
)

router = APIRouter(prefix="/api")

router.include_router(repos.router, prefix="/repos", tags=["repos"])
router.include_router(parse.router, prefix="/parse", tags=["parse"])
# Nested under /projects before projects so /projects/{id}/... is matched first
router.include_router(versions.router, prefix="/projects", tags=["versions"])
router.include_router(requirements.router, prefix="/projects", tags=["requirements"])
router.include_router(commits.router, prefix="/projects", tags=["commits"])
router.include_router(impact.router, prefix="/projects", tags=["impact"])
router.include_router(sync.router, prefix="/projects", tags=["sync"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
