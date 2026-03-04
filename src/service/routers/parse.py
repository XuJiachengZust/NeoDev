"""Parse pipeline API."""

import logging
import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from service.path_allowlist import ensure_path_allowed

logger = logging.getLogger(__name__)


def _get_neo4j_config(request: "ParseRequest") -> dict:
    """Build config from request, then env, then default config file so 入库 works."""
    from gitnexus_parser import load_config

    config: dict = {}
    if request.neo4j_uri is not None:
        config["neo4j_uri"] = request.neo4j_uri
    if request.neo4j_user is not None:
        config["neo4j_user"] = request.neo4j_user
    if request.neo4j_password is not None:
        config["neo4j_password"] = request.neo4j_password
    if config.get("neo4j_uri"):
        return config
    try:
        config = load_config()
    except Exception as e:
        logger.debug("load_config() failed: %s", e)
    if config.get("neo4j_uri"):
        return config
    for path in _default_config_paths():
        try:
            config = load_config(path)
            if config.get("neo4j_uri"):
                logger.info("Loaded Neo4j config from %s", path)
                return config
        except Exception as e:
            logger.debug("load_config(%s) failed: %s", path, e)
    return config


def _default_config_paths() -> list[Path]:
    """Config file paths to try when env/config not set (so 扫描后能入库)."""
    env_path = os.environ.get("CONFIG_PATH")
    if env_path:
        return [Path(env_path)]
    # __file__ = .../src/service/routers/parse.py -> parent*3 = src
    src_dir = Path(__file__).resolve().parent.parent.parent
    return [
        src_dir / "config.json",
        src_dir / "config.example.json",
    ]

router = APIRouter(prefix="", tags=["parse"])


class ParseRequest(BaseModel):
    repo_path: str
    branch: str | None = None
    write_neo4j: bool = True
    incremental: bool = False
    since_commit: str | None = None
    neo4j_uri: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = None


class ParseResponse(BaseModel):
    node_count: int
    relationship_count: int
    file_count: int


def _git_checkout(repo_path: str, branch: str) -> str | None:
    """Checkout branch in repo_path; return previous HEAD branch or None."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        previous = r.stdout.strip() if r.returncode == 0 and r.stdout else None
        subprocess.run(
            ["git", "checkout", branch],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return previous
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


@router.post("/", response_model=ParseResponse)
def run_parse(request: ParseRequest) -> ParseResponse:
    try:
        ensure_path_allowed(request.repo_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    repo = Path(request.repo_path).resolve()
    if not repo.is_dir():
        raise HTTPException(
            status_code=400,
            detail="repo_path must be an existing directory",
        )
    config = _get_neo4j_config(request)
    if request.write_neo4j and not config.get("neo4j_uri"):
        logger.warning(
            "write_neo4j=True but no neo4j_uri in config (env NEO4J_URI or config file)"
        )

    branch = request.branch
    previous_branch: str | None = None
    if branch:
        previous_branch = _git_checkout(request.repo_path, branch)
        if previous_branch is None:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to checkout branch: {branch}",
            )
    try:
        from gitnexus_parser.ingestion.pipeline import run_pipeline
        result = run_pipeline(
            request.repo_path,
            config=config or None,
            branch=request.branch or "main",
            write_neo4j=request.write_neo4j,
            incremental=request.incremental,
            since_commit=request.since_commit,
        )
        return ParseResponse(
            node_count=result.node_count,
            relationship_count=result.relationship_count,
            file_count=result.file_count,
        )
    except Exception as e:
        logger.exception("POST /api/parse 失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if branch and previous_branch and previous_branch != branch:
            try:
                subprocess.run(
                    ["git", "checkout", previous_branch],
                    cwd=request.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except Exception:
                pass
