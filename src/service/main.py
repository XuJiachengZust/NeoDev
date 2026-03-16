"""FastAPI app: project parsing management API.

Run from repo root:
  set PYTHONPATH=src && uvicorn service.main:app --reload
Or (Windows): PYTHONPATH=src python -m uvicorn service.main:app --reload

Environment: 从项目根目录加载 .env（OPENAI_API_KEY、OPENAI_BASE、OPENAI_MODEL_CHAT、NEO4J_* 等）。
"""

import os
from pathlib import Path

# 优先加载 .env，使 OPENAI_API_KEY 等对后续 import 可见（在项目根或 src 同级查找）
try:
    from dotenv import load_dotenv
    root = Path(__file__).resolve().parent.parent.parent  # service -> src -> repo root
    load_dotenv(root / ".env")
except Exception:
    pass

import logging
import sys
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic 请求验证错误：返回 422 + 详细字段信息。"""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


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
async def startup():
    # 未配置时自动设置 REPO_CLONE_BASE 为项目根的同级 repos 目录
    if not os.environ.get("REPO_CLONE_BASE", "").strip():
        neodev_root = Path(__file__).resolve().parent.parent.parent  # service -> src -> NeoDev
        default_repos = neodev_root.parent / "repos"
        os.environ["REPO_CLONE_BASE"] = str(default_repos.resolve())
        logger.info("REPO_CLONE_BASE 未配置，已设为默认: %s", os.environ["REPO_CLONE_BASE"])

    # 初始化 LangGraph Checkpointer（PostgreSQL 持久化）
    try:
        from service.checkpointer import init_checkpointer
        await init_checkpointer()
    except Exception:
        logger.error("LangGraph Checkpointer 初始化失败，Agent 将降级为内存 Checkpointer（重启后丢失上下文）", exc_info=True)

    log = logging.getLogger("uvicorn.error")
    log.info("NeoDev API 已启动 -> http://127.0.0.1:8000  docs -> http://127.0.0.1:8000/docs")


@app.on_event("shutdown")
async def shutdown():
    from service.checkpointer import close_checkpointer
    await close_checkpointer()

_cors_origins = os.environ.get("CORS_ORIGINS", "").strip()
_allowed_origins = (
    [o.strip() for o in _cors_origins.split(",") if o.strip()]
    if _cors_origins
    else ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost", "http://127.0.0.1"]
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
    from service.checkpointer import get_checkpointer
    cp = get_checkpointer()
    return {
        "status": "ok",
        "checkpointer": type(cp).__name__ if cp else "None (will fallback to MemorySaver)",
    }
