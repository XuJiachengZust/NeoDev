"""FastAPI app for the NeoDev MVP API."""

import asyncio
import logging
import os
import sys
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from service.routers.api import router as api_router


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    from dotenv import load_dotenv

    root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(root / ".env")
except Exception:
    pass


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
    force=True,
)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(title="NeoDev MVP API", version="0.1.0")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
def log_unhandled_exception(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error(
        "Unhandled exception [%s %s] %s: %s\n%s",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc,
        tb,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


@app.on_event("startup")
async def startup():
    try:
        from service.migrate import run_migrations

        run_migrations()
    except Exception:
        logger.error("Automatic migration failed", exc_info=True)

    if not os.environ.get("REPO_CLONE_BASE", "").strip():
        neodev_root = Path(__file__).resolve().parent.parent.parent
        default_repos = neodev_root.parent / "repos"
        os.environ["REPO_CLONE_BASE"] = str(default_repos.resolve())
        logger.info("REPO_CLONE_BASE defaulted to: %s", os.environ["REPO_CLONE_BASE"])

    logging.getLogger("uvicorn.error").info(
        "NeoDev MVP API started -> http://127.0.0.1:8000"
    )


@app.on_event("shutdown")
async def shutdown():
    return None


_cors_origins = os.environ.get("CORS_ORIGINS", "").strip()
_allowed_origins = (
    [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]
    if _cors_origins
    else [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
        "http://127.0.0.1",
    ]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok", "profile": "mvp"}
