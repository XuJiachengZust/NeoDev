"""FastAPI app: project parsing management API.

Run from repo root:
  set PYTHONPATH=src && uvicorn service.main:app --reload
Or (Windows): PYTHONPATH=src python -m uvicorn service.main:app --reload
"""

import logging
import sys
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from service.routers.api import router as api_router

# 配置日志：输出到终端，便于开发时查看
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
    force=True,
)
# uvicorn 的访问日志（请求记录）使用 INFO
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(title="NeoDev Parser API", version="0.1.0")


@app.exception_handler(Exception)
def log_unhandled_exception(request: Request, exc: Exception):
    """将未捕获异常以完整 traceback 输出到终端。"""
    tb = traceback.format_exc()
    logger.error(
        "未捕获异常 [%s %s] %s: %s\n%s",
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
def startup():
    logger = logging.getLogger("uvicorn.error")
    logger.info("NeoDev API 已启动 -> http://127.0.0.1:8000  docs -> http://127.0.0.1:8000/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
