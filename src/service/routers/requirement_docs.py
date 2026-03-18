"""需求文档 API：文档 CRUD、版本、diff、生成上下文、工作流生成（SSE）、文档编辑 Agent 对话（SSE）。"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from service.dependencies import get_db, get_requirement_doc_storage
from service.repositories import product_repository
from service.repositories import product_version_repository
from service.services import product_service
from service.services import requirement_doc_service as doc_service
from service.services import product_requirement_service as requirement_service
from service.storage import RequirementDocStorage
from service.workflows import run_doc_workflow_stream, run_generate_children_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["requirement-docs"])


def _check_product_and_requirement(db, product_id: int, requirement_id: int) -> None:
    if not product_service.get_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    req = requirement_service.get_requirement(db, requirement_id)
    if not req or req["product_id"] != product_id:
        raise HTTPException(status_code=404, detail="Requirement not found")


# ── 文档 CRUD ──

@router.get("/{product_id}/requirements/{requirement_id}/doc")
def get_doc(
    product_id: int,
    requirement_id: int,
    db=Depends(get_db),
    storage: RequirementDocStorage = Depends(get_requirement_doc_storage),
):
    """获取当前需求文档内容及元数据。"""
    _check_product_and_requirement(db, product_id, requirement_id)
    out = doc_service.get_doc(db, storage, product_id, requirement_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return out


@router.put("/{product_id}/requirements/{requirement_id}/doc")
def save_doc(
    product_id: int,
    requirement_id: int,
    body: dict,
    db=Depends(get_db),
    storage: RequirementDocStorage = Depends(get_requirement_doc_storage),
):
    """保存文档。body: { content: string, generated_by?: 'manual'|'agent'|'workflow' }。"""
    _check_product_and_requirement(db, product_id, requirement_id)
    content = body.get("content")
    if content is None:
        raise HTTPException(status_code=400, detail="content is required")
    generated_by = body.get("generated_by")
    return doc_service.save_doc(
        db, storage, product_id, requirement_id, content, generated_by=generated_by
    )


# ── 版本 ──

@router.get("/{product_id}/requirements/{requirement_id}/doc/versions")
def list_versions(
    product_id: int,
    requirement_id: int,
    db=Depends(get_db),
    storage: RequirementDocStorage = Depends(get_requirement_doc_storage),
):
    """获取版本历史列表（版本号列表）。"""
    _check_product_and_requirement(db, product_id, requirement_id)
    return doc_service.list_versions(db, storage, product_id, requirement_id)


@router.get("/{product_id}/requirements/{requirement_id}/doc/versions/{version}")
def get_version_content(
    product_id: int,
    requirement_id: int,
    version: int,
    db=Depends(get_db),
    storage: RequirementDocStorage = Depends(get_requirement_doc_storage),
):
    """获取指定版本的文件内容。"""
    _check_product_and_requirement(db, product_id, requirement_id)
    content = doc_service.get_version_content(
        db, storage, product_id, requirement_id, version
    )
    if content is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"version": version, "content": content}


@router.get("/{product_id}/requirements/{requirement_id}/doc/diff")
def get_diff(
    product_id: int,
    requirement_id: int,
    v1: int = Query(..., description="Version 1"),
    v2: int = Query(..., description="Version 2"),
    db=Depends(get_db),
    storage: RequirementDocStorage = Depends(get_requirement_doc_storage),
):
    """返回两个版本的原始 content，供前端做 diff。"""
    _check_product_and_requirement(db, product_id, requirement_id)
    return doc_service.get_diff_contents(
        db, storage, product_id, requirement_id, v1, v2
    )


# ── 生成相关 ──

@router.get("/{product_id}/requirements/{requirement_id}/doc/can-generate-children")
def can_generate_children(
    product_id: int,
    requirement_id: int,
    db=Depends(get_db),
):
    """检查当前需求是否已有文档（有文档才可生成子级）。"""
    _check_product_and_requirement(db, product_id, requirement_id)
    return {"can_generate_children": doc_service.can_generate_children(db, requirement_id)}


@router.get("/{product_id}/requirements/{requirement_id}/doc/generation-context")
def get_generation_context(
    product_id: int,
    requirement_id: int,
    db=Depends(get_db),
    storage: RequirementDocStorage = Depends(get_requirement_doc_storage),
):
    """获取工作流/Agent 生成所需的上下文（产品、当前需求、父文档、兄弟需求）。"""
    _check_product_and_requirement(db, product_id, requirement_id)
    return doc_service.get_generation_context(db, storage, product_id, requirement_id)


@router.post("/{product_id}/requirements/{requirement_id}/doc/chat", deprecated=True)
async def doc_chat(
    product_id: int,
    requirement_id: int,
    body: dict,
    db=Depends(get_db),
    storage: RequirementDocStorage = Depends(get_requirement_doc_storage),
):
    """[已废弃] 文档编辑 Agent 流式对话。请改用 /api/agent/chat + doc_context。"""
    _check_product_and_requirement(db, product_id, requirement_id)
    message = (body or {}).get("message") or ""
    if not message.strip():
        raise HTTPException(status_code=400, detail="message is required")
    session_id = (body or {}).get("session_id") or "default"

    ctx = doc_service.get_generation_context(db, storage, product_id, requirement_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Requirement or product not found")

    product = ctx["product"]
    current = ctx["current_requirement"]
    parent_doc_content = ctx.get("parent_doc_content")
    sibling_requirements = ctx.get("sibling_requirements") or []
    # 优先使用前端传来的当前编辑器内容（可能有未保存改动），否则从存储读取
    current_content = (body or {}).get("current_content")
    existing_doc = current_content if current_content is not None else (storage.read(product_id, requirement_id) or "")

    product_name = product.get("name") or "Unknown"
    project_repo_map = {}
    projects = product_repository.list_projects(db, product_id)
    if projects:
        for p in projects:
            if p.get("repo_path"):
                project_repo_map[p["name"]] = p["repo_path"]
    project_id_map = {p["name"]: p["id"] for p in projects} if projects else None

    version_id = current.get("version_id")
    version_name = None
    branch_mappings = None
    if version_id:
        version = product_version_repository.find_by_id(db, version_id)
        if version:
            version_name = version.get("version_name")
        branches = product_version_repository.list_branches(db, version_id)
        if branches:
            branch_mappings = [{"project_name": b["project_name"], "branch": b["branch"]} for b in branches]

    doc_context = {
        "level": current.get("level") or "story",
        "requirement_title": current.get("title") or "",
        "requirement_description": current.get("description"),
        "parent_doc": parent_doc_content,
        "sibling_titles": [s.get("title") or "" for s in sibling_requirements],
        "product_name": product_name,
        "version_name": version_name,
        "existing_doc": existing_doc or None,
        "code_context": None,
        "graph_context": None,
    }

    thread_id = f"doc-{product_id}-{requirement_id}-{session_id}"

    async def event_stream():
        try:
            from service.agent_factory import run_product_agent_stream

            async for ev in run_product_agent_stream(
                product_name=product_name,
                thread_id=thread_id,
                user_message=message.strip(),
                session_id=session_id,
                project_repo_map=project_repo_map or None,
                version_name=version_name,
                branch_mappings=branch_mappings,
                project_id_map=project_id_map,
                doc_context=doc_context,
            ):
                event_type = ev.get("event", "message")
                data = ev.get("data", ev)
                if event_type == "token" and isinstance(data, str):
                    yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                else:
                    yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("Doc chat stream error")
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse_message(ev: dict) -> str:
    """将工作流事件转为 SSE 行：event: <type>\\ndata: <json>\\n\\n。"""
    event_type = ev.get("event", "message")
    data = ev.get("data", ev)
    data_str = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {data_str}\n\n"


@router.get("/{product_id}/requirements/{requirement_id}/doc/generation-status")
def get_generation_status(
    product_id: int,
    requirement_id: int,
    db=Depends(get_db),
):
    """获取文档生成状态。"""
    _check_product_and_requirement(db, product_id, requirement_id)
    try:
        from service.repositories import requirement_doc_repository as doc_repo
        status = doc_repo.get_generation_status(db, requirement_id)
        if not status:
            return {"generation_status": None, "generation_started_at": None, "generation_error": None}
        return status
    except Exception:
        logger.debug("get_generation_status failed, migration 016 may not be applied")
        db.rollback()
        return {"generation_status": None, "generation_started_at": None, "generation_error": None}


@router.post("/{product_id}/requirements/{requirement_id}/doc/pre-generate-chat")
async def pre_generate_chat(
    product_id: int,
    requirement_id: int,
    body: dict,
    db=Depends(get_db),
    storage: RequirementDocStorage = Depends(get_requirement_doc_storage),
):
    """Epic 预生成引导对话（SSE 流式）。body: { message: string, session_id?: string }。"""
    _check_product_and_requirement(db, product_id, requirement_id)
    message = (body or {}).get("message") or ""
    if not message.strip():
        raise HTTPException(status_code=400, detail="message is required")
    session_id = (body or {}).get("session_id") or "default"

    ctx = doc_service.get_generation_context(db, storage, product_id, requirement_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Requirement or product not found")

    product = ctx["product"]
    current = ctx["current_requirement"]
    parent_doc_content = ctx.get("parent_doc_content")
    sibling_requirements = ctx.get("sibling_requirements") or []

    doc_context = {
        "level": current.get("level") or "epic",
        "requirement_title": current.get("title") or "",
        "requirement_description": current.get("description"),
        "parent_doc": parent_doc_content,
        "sibling_titles": [s.get("title") or "" for s in sibling_requirements],
        "product_name": product.get("name") or "Unknown",
    }

    thread_id = f"pre-gen-{product_id}-{requirement_id}-{session_id}"

    async def event_stream():
        try:
            from service.agent_factory import run_pre_generate_agent_stream

            async for ev in run_pre_generate_agent_stream(
                thread_id=thread_id,
                user_message=message.strip(),
                doc_context=doc_context,
            ):
                event_type = ev.get("event", "message")
                data = ev.get("data", ev)
                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("Pre-generate chat stream error")
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{product_id}/requirements/{requirement_id}/doc/generate")
async def generate_doc(
    product_id: int,
    requirement_id: int,
    body: dict | None = None,
    db=Depends(get_db),
    storage: RequirementDocStorage = Depends(get_requirement_doc_storage),
):
    """触发工作流生成当前需求文档（SSE 流式）。body (optional): { user_overview?: string }。"""
    _check_product_and_requirement(db, product_id, requirement_id)
    user_overview = (body or {}).get("user_overview") if body else None

    try:
        from service.repositories import requirement_doc_repository as doc_repo
        doc_repo.update_generation_status(db, requirement_id, "running")
        db.commit()
    except Exception:
        logger.warning("Failed to persist generation_status=running (migration 016 may not be applied)", exc_info=True)
        db.rollback()

    async def event_stream():
        try:
            for ev in run_doc_workflow_stream(db, storage, product_id, requirement_id, user_overview=user_overview):
                yield _sse_message(ev)
        except Exception as e:
            logger.exception("generate_doc event_stream error")
            yield _sse_message({"event": "workflow_done", "data": {"requirement_id": requirement_id, "status": "failed", "error": str(e), "version": None}})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{product_id}/requirements/{requirement_id}/doc/generate-children")
async def generate_children_docs(
    product_id: int,
    requirement_id: int,
    db=Depends(get_db),
    storage: RequirementDocStorage = Depends(get_requirement_doc_storage),
):
    """触发批量生成子级文档工作流（SSE 流式）。"""
    _check_product_and_requirement(db, product_id, requirement_id)

    # 从父需求获取 version_id，传递给子需求创建
    parent_req = requirement_service.get_requirement(db, requirement_id)
    parent_version_id = parent_req.get("version_id") if parent_req else None

    async def event_stream():
        async for ev in run_generate_children_stream(
            db, storage, product_id, requirement_id, version_id=parent_version_id,
        ):
            yield _sse_message(ev)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
