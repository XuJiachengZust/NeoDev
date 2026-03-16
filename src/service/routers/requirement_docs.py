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


@router.post("/{product_id}/requirements/{requirement_id}/doc/chat")
async def doc_chat(
    product_id: int,
    requirement_id: int,
    body: dict,
    db=Depends(get_db),
    storage: RequirementDocStorage = Depends(get_requirement_doc_storage),
):
    """文档编辑 Agent 流式对话（SSE）。body: { message: string }。"""
    _check_product_and_requirement(db, product_id, requirement_id)
    message = (body or {}).get("message") or ""
    if not message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    ctx = doc_service.get_generation_context(db, storage, product_id, requirement_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Requirement or product not found")

    product = ctx["product"]
    current = ctx["current_requirement"]
    parent_doc_content = ctx.get("parent_doc_content")
    sibling_requirements = ctx.get("sibling_requirements") or []
    existing_doc = storage.read(product_id, requirement_id) or ""

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

    thread_id = f"doc-{product_id}-{requirement_id}"

    async def event_stream():
        try:
            from service.agent_factory import run_doc_editor_agent_stream

            async for ev in run_doc_editor_agent_stream(
                thread_id=thread_id,
                user_message=message.strip(),
                doc_context=doc_context,
                session_id=None,
                project_repo_map=project_repo_map or None,
                project_id_map=project_id_map,
                version_name=version_name,
                branch_mappings=branch_mappings,
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


@router.post("/{product_id}/requirements/{requirement_id}/doc/generate")
def generate_doc(
    product_id: int,
    requirement_id: int,
    db=Depends(get_db),
    storage: RequirementDocStorage = Depends(get_requirement_doc_storage),
):
    """触发工作流生成当前需求文档（SSE 流式）。"""
    _check_product_and_requirement(db, product_id, requirement_id)

    def event_stream():
        for ev in run_doc_workflow_stream(db, storage, product_id, requirement_id):
            yield _sse_message(ev)

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

    async def event_stream():
        async for ev in run_generate_children_stream(db, storage, product_id, requirement_id):
            yield _sse_message(ev)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
