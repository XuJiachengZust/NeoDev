"""Agent API: 会话管理、消息收发（含 SSE 流式）、上下文快照。"""

import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from service.agent_profiles import resolve_profile_name
from service.dependencies import get_db
from service.repositories import agent_repository as agent_repo
from service.repositories import product_repository
from service.repositories import product_version_repository
from service.repositories import project_repository as project_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["agent"])


# ── Pydantic Models ───────────────────────────────────────────────────


class ResolveSessionRequest(BaseModel):
    session_id: str
    route_context_key: str
    project_id: int | None = None
    product_id: int | None = None
    version_id: int | None = None
    agent_profile: str | None = None


class ResolveSessionResponse(BaseModel):
    conversation_id: int
    thread_id: str
    agent_profile: str
    route_context_key: str
    product_id: int | None = None
    version_id: int | None = None
    version_name: str | None = None
    product_name: str | None = None
    project_branches: list[dict] | None = None


class ChatRequest(BaseModel):
    conversation_id: int
    message: str
    stream: bool = True
    doc_context: dict | None = None  # {"requirement_id": int, "current_content": str}
    response_mode: str | None = None  # simple / medium / hard


class NewConversationRequest(BaseModel):
    session_id: str
    product_id: int
    route_context_key: str = "product_dashboard"
    version_id: int | None = None


class ActivateConversationRequest(BaseModel):
    session_id: str


class UpdateTitleRequest(BaseModel):
    title: str


class SnapshotRequest(BaseModel):
    conversation_id: int
    summary: str
    state_json: dict | None = None


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("/sessions/resolve")
def resolve_session(body: ResolveSessionRequest, db=Depends(get_db)):
    """解析会话：确保 session 存在，查找或创建对应 route+project 的 conversation。

    支持产品模式：当 product_id 存在时，使用产品级 profile。
    返回产品名、版本名、版本分支映射等上下文信息。
    """
    # 确保 session 存在
    agent_repo.upsert_session(db, body.session_id)

    # 校验 product_id 是否存在，不存在则忽略
    product_id = body.product_id
    product = None
    if product_id is not None:
        product = product_repository.find_by_id(db, product_id)
        if not product:
            product_id = None

    # 校验 version_id
    version_id = body.version_id
    version = None
    if version_id is not None:
        version = product_version_repository.find_by_id(db, version_id)
        if not version:
            version_id = None

    # 确定 profile：产品模式使用 "product" profile
    if product_id is not None:
        profile_name = body.agent_profile or "product"
    else:
        profile_name = body.agent_profile or resolve_profile_name(body.route_context_key)

    # 查找或创建 conversation
    conv = agent_repo.resolve_conversation(
        db,
        session_id=body.session_id,
        route_context_key=body.route_context_key,
        project_id=body.project_id,
        product_id=product_id,
        agent_profile=profile_name,
        version_id=version_id,
    )
    db.commit()

    # 构建版本分支映射
    project_branches = None
    if version_id:
        branches = product_version_repository.list_branches(db, version_id)
        if branches:
            project_branches = [
                {"project_id": b["project_id"], "project_name": b["project_name"], "branch": b["branch"]}
                for b in branches
            ]

    return ResolveSessionResponse(
        conversation_id=conv["id"],
        thread_id=conv["thread_id"],
        agent_profile=conv["agent_profile"],
        route_context_key=conv["route_context_key"],
        product_id=conv.get("product_id"),
        version_id=conv.get("version_id"),
        version_name=version["version_name"] if version else None,
        product_name=product["name"] if product else None,
        project_branches=project_branches,
    )


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    db=Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """分页获取对话消息。"""
    conv = agent_repo.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = agent_repo.list_messages(db, conversation_id, limit=limit, offset=offset)
    return {"messages": messages, "conversation_id": conversation_id}


@router.post("/chat")
async def chat(body: ChatRequest, db=Depends(get_db)):
    """发送消息并获取 AI 回复。支持 SSE 流式（默认）和非流式模式。

    产品级会话自动使用产品 Agent（动态 prompt + 产品上下文）。
    """
    conv = agent_repo.get_conversation(db, body.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    profile_name = conv["agent_profile"]
    thread_id = conv["thread_id"]
    session_id = conv["session_id"]

    # 解析项目路径（如果有 project_id）
    project_path = None
    project_id = conv.get("project_id")
    if project_id:
        project = project_repo.find_by_id(db, project_id)
        if project and project.get("repo_path"):
            project_path = project["repo_path"]

    # 写入用户消息
    agent_repo.insert_message(db, body.conversation_id, role="user", content=body.message)
    db.commit()

    # 判断是否是产品级会话
    is_product = conv.get("product_id") is not None

    if body.stream:
        if is_product:
            gen = _stream_product_chat(
                db, body.conversation_id, conv["product_id"],
                conv.get("route_context_key", ""),
                thread_id, body.message, session_id=session_id,
                version_id=conv.get("version_id"),
                doc_context_input=body.doc_context,
                response_mode=body.response_mode,
            )
        else:
            gen = _stream_chat(
                db, body.conversation_id, profile_name, thread_id, body.message,
                session_id=session_id, project_path=project_path,
                project_id=project_id,
                response_mode=body.response_mode,
            )
        return StreamingResponse(
            gen,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        return await _invoke_chat(
            db, body.conversation_id, profile_name, thread_id, body.message,
            session_id=session_id, project_path=project_path,
            project_id=project_id,
            response_mode=body.response_mode,
        )


async def _stream_chat(
    db, conversation_id: int, profile_name: str, thread_id: str, message: str,
    session_id: str | None = None, project_path: str | None = None,
    project_id: int | None = None,
    response_mode: str | None = None,
):
    """SSE 流式生成器。"""
    from service.agent_factory import run_agent_stream

    start_time = time.time()

    try:
        async for event in run_agent_stream(
            profile_name, thread_id, message,
            session_id=session_id, project_path=project_path,
            project_id=project_id,
            response_mode=response_mode,
        ):
            sse_data = json.dumps(event, ensure_ascii=False)
            yield f"data: {sse_data}\n\n"

            # 流结束后写入完整消息
            if event["event"] == "done":
                latency_ms = int((time.time() - start_time) * 1000)
                data = event["data"]
                agent_repo.insert_message(
                    db,
                    conversation_id,
                    role="assistant",
                    content=data.get("content", ""),
                    token_in=data.get("token_in"),
                    token_out=data.get("token_out"),
                    latency_ms=latency_ms,
                    model=profile_name,
                )
                db.commit()

            elif event["event"] == "recursion_limit":
                latency_ms = int((time.time() - start_time) * 1000)
                data = event["data"]
                agent_repo.insert_message(
                    db,
                    conversation_id,
                    role="assistant",
                    content=data.get("content", ""),
                    token_in=data.get("token_in"),
                    token_out=data.get("token_out"),
                    latency_ms=latency_ms,
                    model=profile_name,
                )
                db.commit()

            elif event["event"] == "error":
                latency_ms = int((time.time() - start_time) * 1000)
                agent_repo.insert_message(
                    db,
                    conversation_id,
                    role="assistant",
                    content=f"[错误] {event['data'].get('message', '未知错误')}",
                    latency_ms=latency_ms,
                )
                db.commit()

    except Exception as e:
        logger.exception("SSE stream error")
        error_event = {"event": "error", "data": {"message": str(e)}}
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"


async def _stream_product_chat(
    db, conversation_id: int, product_id: int, route_context_key: str,
    thread_id: str, message: str, session_id: str | None = None,
    version_id: int | None = None,
    doc_context_input: dict | None = None,
    response_mode: str | None = None,
):
    """产品级 SSE 流式生成器。

    当 doc_context_input 存在时（含 requirement_id + current_content），
    自动构建完整 doc_context 传给 run_product_agent_stream 进入文档编辑模式。
    """
    from service.agent_factory import run_product_agent_stream

    # 获取产品信息
    product = product_repository.find_by_id(db, product_id)
    product_name = product["name"] if product else "Unknown"
    project_names = None
    project_repo_map: dict[str, str] = {}
    projects = None
    if product:
        projects = product_repository.list_projects(db, product_id)
        if projects:
            project_names = [p["name"] for p in projects]
            for p in projects:
                if p.get("repo_path"):
                    project_repo_map[p["name"]] = p["repo_path"]

    # 获取版本分支映射
    version_name = None
    branch_mappings = None
    if version_id:
        version = product_version_repository.find_by_id(db, version_id)
        if version:
            version_name = version["version_name"]
        branches = product_version_repository.list_branches(db, version_id)
        if branches:
            branch_mappings = [
                {"project_name": b["project_name"], "branch": b["branch"]}
                for b in branches
            ]

    # 构建项目名 → ID 映射（供 nexus 子智能体使用，复用上面的 projects 查询结果）
    project_id_map: dict[str, int] | None = None
    if product and projects:
        project_id_map = {p["name"]: p["id"] for p in projects}

    # 构建文档编辑 doc_context（如有）
    doc_context = None
    if doc_context_input and doc_context_input.get("requirement_id"):
        try:
            from service.services import requirement_doc_service as doc_service
            from service.services import product_requirement_service as requirement_service
            from service.dependencies import get_requirement_doc_storage

            requirement_id = int(doc_context_input["requirement_id"])
            current_content = doc_context_input.get("current_content") or ""

            req = requirement_service.get_requirement(db, requirement_id)
            if req and req.get("product_id") == product_id:
                storage = get_requirement_doc_storage()
                ctx = doc_service.get_generation_context(db, storage, product_id, requirement_id)
                if ctx:
                    current_req = ctx["current_requirement"]
                    parent_doc_content = ctx.get("parent_doc_content")
                    sibling_requirements = ctx.get("sibling_requirements") or []

                    # 如有版本 ID，从需求中获取
                    req_version_id = current_req.get("version_id")
                    req_version_name = version_name
                    if req_version_id and not version_id:
                        v = product_version_repository.find_by_id(db, req_version_id)
                        if v:
                            req_version_name = v.get("version_name")

                    doc_context = {
                        "level": current_req.get("level") or "story",
                        "requirement_title": current_req.get("title") or "",
                        "requirement_description": current_req.get("description"),
                        "parent_doc": parent_doc_content,
                        "sibling_titles": [s.get("title") or "" for s in sibling_requirements],
                        "product_name": product_name,
                        "version_name": req_version_name,
                        "existing_doc": current_content or None,
                        "code_context": None,
                        "graph_context": None,
                    }
        except Exception:
            logger.warning("构建 doc_context 失败", exc_info=True)

    start_time = time.time()

    try:
        async for event in run_product_agent_stream(
            product_name, thread_id, message,
            project_names=project_names,
            route_hint=route_context_key,
            session_id=session_id,
            project_repo_map=project_repo_map or None,
            version_name=version_name,
            branch_mappings=branch_mappings,
            project_id_map=project_id_map,
            doc_context=doc_context,
            response_mode=response_mode,
        ):
            sse_data = json.dumps(event, ensure_ascii=False)
            yield f"data: {sse_data}\n\n"

            if event["event"] == "done":
                latency_ms = int((time.time() - start_time) * 1000)
                data = event["data"]
                agent_repo.insert_message(
                    db, conversation_id, role="assistant",
                    content=data.get("content", ""),
                    token_in=data.get("token_in"),
                    token_out=data.get("token_out"),
                    latency_ms=latency_ms,
                    model="product",
                )
                db.commit()

            elif event["event"] == "recursion_limit":
                latency_ms = int((time.time() - start_time) * 1000)
                data = event["data"]
                agent_repo.insert_message(
                    db, conversation_id, role="assistant",
                    content=data.get("content", ""),
                    token_in=data.get("token_in"),
                    token_out=data.get("token_out"),
                    latency_ms=latency_ms,
                    model="product",
                )
                db.commit()

            elif event["event"] == "error":
                latency_ms = int((time.time() - start_time) * 1000)
                agent_repo.insert_message(
                    db, conversation_id, role="assistant",
                    content=f"[错误] {event['data'].get('message', '未知错误')}",
                    latency_ms=latency_ms,
                )
                db.commit()

    except Exception as e:
        logger.exception("Product SSE stream error")
        error_event = {"event": "error", "data": {"message": str(e)}}
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"


async def _invoke_chat(
    db, conversation_id: int, profile_name: str, thread_id: str, message: str,
    session_id: str | None = None, project_path: str | None = None,
    project_id: int | None = None,
    response_mode: str | None = None,
):
    """非流式调用。"""
    from service.agent_factory import run_agent_invoke

    start_time = time.time()
    result = await run_agent_invoke(
        profile_name, thread_id, message,
        session_id=session_id, project_path=project_path,
        project_id=project_id,
        response_mode=response_mode,
    )
    latency_ms = int((time.time() - start_time) * 1000)

    msg = agent_repo.insert_message(
        db,
        conversation_id,
        role="assistant",
        content=result.get("content", ""),
        token_in=result.get("token_in"),
        token_out=result.get("token_out"),
        latency_ms=latency_ms,
        model=profile_name,
    )

    return {
        "role": "assistant",
        "content": result.get("content", ""),
        "message_id": msg["id"],
        "token_in": result.get("token_in"),
        "token_out": result.get("token_out"),
        "latency_ms": latency_ms,
    }


@router.get("/conversations")
def list_conversations(
    session_id: str = Query(...),
    product_id: int = Query(...),
    db=Depends(get_db),
):
    """列出 session+product 的所有对话。"""
    return {"conversations": agent_repo.list_conversations(db, session_id, product_id)}


@router.post("/conversations/new")
def create_conversation(body: NewConversationRequest, db=Depends(get_db)):
    """新建对话：旧激活对话 deactivate，创建新激活对话。清除旧 agent 缓存。"""
    from service.agent_factory import evict_agent

    agent_repo.upsert_session(db, body.session_id)

    # 在创建新对话前，获取旧激活对话的 thread_id 并清除 agent 缓存
    old_convs = agent_repo.list_conversations(db, body.session_id, body.product_id)
    for c in old_convs:
        if c.get("is_active"):
            old_thread = agent_repo.get_conversation(db, c["id"])
            if old_thread and old_thread.get("thread_id"):
                evict_agent(old_thread["thread_id"])

    conv = agent_repo.create_new_conversation(
        db,
        session_id=body.session_id,
        product_id=body.product_id,
        route_context_key=body.route_context_key,
        version_id=body.version_id,
    )
    db.commit()
    return conv


@router.post("/conversations/{conversation_id}/activate")
def activate_conversation(
    conversation_id: int, body: ActivateConversationRequest, db=Depends(get_db),
):
    """切换激活对话。"""
    conv = agent_repo.activate_conversation(db, conversation_id, body.session_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or not owned by session")
    db.commit()
    return conv


@router.patch("/conversations/{conversation_id}/title")
def update_title(conversation_id: int, body: UpdateTitleRequest, db=Depends(get_db)):
    """更新对话标题。"""
    conv = agent_repo.update_conversation_title(db, conversation_id, body.title)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.commit()
    return conv


@router.post("/context/snapshot")
def create_snapshot(body: SnapshotRequest, db=Depends(get_db)):
    """手动创建上下文快照。"""
    conv = agent_repo.get_conversation(db, body.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 获取最新消息 ID
    messages = agent_repo.list_messages(db, body.conversation_id, limit=1, offset=0)
    last_msg_id = messages[-1]["id"] if messages else None

    snapshot = agent_repo.save_context_snapshot(
        db,
        conversation_id=body.conversation_id,
        summary=body.summary,
        state_json=body.state_json,
        last_message_id=last_msg_id,
    )
    return snapshot


# ── Sandbox Lifecycle ─────────────────────────────────────────────────


class SandboxRecycleRequest(BaseModel):
    session_id: str


class SandboxMountRequest(BaseModel):
    session_id: str
    project_id: int


@router.post("/sandbox/recycle")
def recycle_sandbox(body: SandboxRecycleRequest, db=Depends(get_db)):
    """回收会话沙箱。"""
    from service.sandbox_manager import recycle_sandbox as do_recycle

    success = do_recycle(body.session_id)
    if success:
        agent_repo.upsert_sandbox(db, body.session_id, body.session_id, status="recycled")
    return {"session_id": body.session_id, "recycled": success}


@router.post("/sandbox/mount-project")
def mount_project(body: SandboxMountRequest, db=Depends(get_db)):
    """手动挂载项目到沙箱。"""
    project = project_repo.find_by_id(db, body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from service.sandbox_manager import ensure_sandbox, get_sandbox_path

    ensure_sandbox(body.session_id)
    sandbox_path = str(get_sandbox_path(body.session_id))

    agent_repo.upsert_sandbox(
        db, body.session_id, body.session_id,
        status="active",
        workspace_path=sandbox_path,
        mounted_project_id=body.project_id,
    )

    return {
        "session_id": body.session_id,
        "project_id": body.project_id,
        "workspace_path": sandbox_path,
        "mounted": True,
    }


@router.get("/sandbox/mount-status")
def get_mount_status(session_id: str = Query(...), db=Depends(get_db)):
    """查询沙箱挂载状态。"""
    sandbox = agent_repo.get_active_sandbox(db, session_id)
    if not sandbox:
        return {"session_id": session_id, "mounted": False}
    return {
        "session_id": session_id,
        "mounted": True,
        "sandbox_id": sandbox["sandbox_id"],
        "status": sandbox["status"],
        "workspace_path": sandbox.get("workspace_path"),
        "mounted_project_id": sandbox.get("mounted_project_id"),
    }
