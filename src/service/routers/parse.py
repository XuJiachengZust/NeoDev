"""Parse pipeline API."""

import logging
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from service.path_allowlist import ensure_path_allowed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["parse"])


class ParseRequest(BaseModel):
    repo_path: str
    branch: str | None = None
    incremental: bool = False
    since_commit: str | None = None


class ParseResponse(BaseModel):
    node_count: int
    relationship_count: int
    file_count: int


def _git_checkout(repo_path: str, branch: str) -> str | None:
    """Checkout branch in repo_path; return previous HEAD branch or None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        previous = result.stdout.strip() if result.returncode == 0 and result.stdout else None
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    repo = Path(request.repo_path).resolve()
    if not repo.is_dir():
        raise HTTPException(
            status_code=400,
            detail="repo_path must be an existing directory",
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
            config={},
            branch=request.branch or "main",
            write_neo4j=False,
            incremental=request.incremental,
            since_commit=request.since_commit,
        )
        return ParseResponse(
            node_count=result.node_count,
            relationship_count=result.relationship_count,
            file_count=result.file_count,
        )
    except Exception as exc:
        logger.exception("POST /api/parse failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
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
