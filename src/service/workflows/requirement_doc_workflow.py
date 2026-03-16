"""需求文档生成工作流：LangGraph StateGraph，CollectContext → CodeSearch → GraphSearch → Synthesize → GenerateDoc → SaveDraft。"""

import asyncio
import os
import re
from collections.abc import AsyncIterator, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph, START

from service.agent_profiles import build_requirement_doc_prompt
from service.repositories import product_repository as product_repo
from service.repositories import product_requirement_repository as requirement_repo
from service.repositories import product_version_repository as version_repo
from service.services import requirement_doc_service as doc_service
from service.storage import RequirementDocStorage


# ── State ──


class DocWorkflowState(TypedDict, total=False):
    """工作流状态。"""

    requirement_id: int
    product_id: int
    level: str  # "epic" | "story" | "task"
    requirement_title: str
    requirement_description: str | None

    parent_doc_content: str | None
    generation_seed: str | None
    sibling_titles: list[str]
    product_name: str
    version_name: str | None
    project_repo_map: dict[str, str]  # 项目名 → 仓库路径

    code_search_results: str
    graph_search_results: str
    generated_content: str
    status: str  # "running" | "completed" | "failed"
    error: str | None

    # 注入依赖（由 runner 传入，节点只读）
    conn: Any
    storage: RequirementDocStorage


# ── 生成种子提取（从父文档拆分建议章节） ──


def _extract_split_section(content: str | None, section_marker: str) -> str:
    """从父文档中提取「Story 拆分建议」或「Task 拆分建议」章节正文。"""
    if not content or not section_marker:
        return ""
    pattern = rf"##\s*{re.escape(section_marker)}\s*\n(.*?)(?=\n##\s|\n#\s|\Z)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _match_generation_seed(section_text: str, child_title: str) -> str:
    """
    从拆分建议章节中选取与子需求标题最匹配的一条作为 generation_seed。
    步骤4 可用 LLM 替代；此处用简单规则：含标题关键词的首次出现行，否则首条。
    """
    if not section_text:
        return ""
    lines = [ln.strip() for ln in section_text.splitlines() if ln.strip()]
    if not lines:
        return ""
    # 去掉常见列表前缀
    def norm(s: str) -> str:
        s = re.sub(r"^[\s\-*•]\s*", "", s)
        return s.strip()

    for line in lines:
        clean = norm(line)
        if child_title and child_title in clean:
            return clean
    return norm(lines[0]) if lines else ""


def extract_generation_seed(
    parent_doc_content: str | None,
    level: str,
    child_title: str,
) -> str:
    """
    按层级从父文档提取本需求的生成种子。
    Epic 父文档 → 「Story 拆分建议」；Story 父文档 → 「Task 拆分建议」。
    """
    if not parent_doc_content or not child_title:
        return ""
    if level == "story":
        section = _extract_split_section(parent_doc_content, "Story 拆分建议")
    elif level == "task":
        section = _extract_split_section(parent_doc_content, "Task 拆分建议")
    else:
        return ""
    return _match_generation_seed(section, child_title)


# ── 节点 ──


def _collect_context(state: DocWorkflowState) -> dict[str, Any]:
    """收集上下文：需求信息、父文档、生成种子、兄弟标题、产品/版本/项目映射。"""
    conn = state["conn"]
    storage: RequirementDocStorage = state["storage"]
    product_id = state["product_id"]
    requirement_id = state["requirement_id"]

    ctx = doc_service.get_generation_context(conn, storage, product_id, requirement_id)
    if not ctx:
        return {
            "status": "failed",
            "error": "get_generation_context returned empty",
        }

    current = ctx["current_requirement"]
    parent_doc_content = ctx.get("parent_doc_content")
    siblings = ctx.get("sibling_requirements") or []
    product = ctx.get("product") or {}
    level = (current.get("level") or "story").lower()
    if level not in ("epic", "story", "task"):
        level = "story"

    # 生成种子（子需求时从父文档拆分建议提取）
    generation_seed = extract_generation_seed(
        parent_doc_content,
        level,
        current.get("title") or "",
    )

    # 项目名 → 仓库路径
    projects = product_repo.list_projects(conn, product_id)
    project_repo_map = {p["name"]: p["repo_path"] for p in projects if p.get("name") and p.get("repo_path")}

    version_id = current.get("version_id")
    version_name: str | None = None
    if version_id:
        ver = version_repo.find_by_id(conn, version_id)
        if ver:
            version_name = ver.get("version_name")

    return {
        "level": level,
        "requirement_title": current.get("title") or "",
        "requirement_description": current.get("description"),
        "parent_doc_content": parent_doc_content,
        "generation_seed": generation_seed or None,
        "sibling_titles": [s.get("title") or "" for s in siblings],
        "product_name": product.get("name") or "",
        "version_name": version_name,
        "project_repo_map": project_repo_map,
        "code_search_results": "",
        "graph_search_results": "",
        "status": "running",
    }


def _code_search(state: DocWorkflowState) -> dict[str, Any]:
    """
    按层级做代码检索：Epic 不检索；Story 可选轻量；Task 详细。
    当前为占位，步骤4 可接入 project-retriever 或等价工具。
    """
    level = (state.get("level") or "epic").lower()
    if level == "epic":
        return {"code_search_results": ""}
    if level == "story":
        # 可选轻量检索，占位
        return {"code_search_results": ""}
    # task: 详细 grep + read_file，占位
    return {"code_search_results": ""}


def _graph_search(state: DocWorkflowState) -> dict[str, Any]:
    """
    按层级做图谱检索：Epic 不检索或可选 overview；Story 主检索；Task 详细。
    当前为占位，步骤4 可接入 nexus_search / nexus_explore / nexus_impact。
    """
    level = (state.get("level") or "epic").lower()
    if level == "epic":
        return {"graph_search_results": ""}
    if level == "story":
        # 主检索，占位
        return {"graph_search_results": ""}
    return {"graph_search_results": ""}


def _synthesize(state: DocWorkflowState) -> dict[str, Any]:
    """合并检索结果与父文档种子，供生成使用。此处仅透传，实际合并在 GenerateDoc 的 prompt 中。"""
    return {}


def _generate_doc(state: DocWorkflowState) -> dict[str, Any]:
    """
    根据上下文与检索结果生成文档正文。
    使用 build_requirement_doc_prompt 三级模版 + LLM 生成；LLM 不可用时回退为占位模板。
    """
    title = state.get("requirement_title") or ""
    desc = state.get("requirement_description") or ""
    seed = state.get("generation_seed") or ""
    code = state.get("code_search_results") or ""
    graph = state.get("graph_search_results") or ""
    level = (state.get("level") or "story").lower()
    if level not in ("epic", "story", "task"):
        level = "story"

    prompt = build_requirement_doc_prompt(
        level=level,
        requirement_title=title,
        requirement_description=desc,
        parent_doc=state.get("parent_doc_content"),
        sibling_titles=state.get("sibling_titles") or [],
        product_name=state.get("product_name") or "",
        version_name=state.get("version_name"),
        code_context=code or None,
        graph_context=graph or None,
        existing_doc=None,
    )

    generated_content = _invoke_llm_for_doc(prompt, title)
    if generated_content is None:
        # 回退：占位模板
        parts = [
            f"# {title}",
            "",
            "## 概述",
            desc or "（待补充）",
            "",
        ]
        if seed:
            parts.extend(["## 父需求拆分指引", seed, ""])
        if code or graph:
            parts.append("## 代码与图谱检索")
            if code:
                parts.append(code)
            if graph:
                parts.append(graph)
            parts.append("")
        generated_content = "\n".join(parts).strip()

    return {"generated_content": generated_content}


def _invoke_llm_for_doc(system_prompt: str, title: str) -> str | None:
    """调用 LLM 生成文档正文；失败或未配置时返回 None。"""
    try:
        base = os.environ.get("OPENAI_BASE", "").strip()
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            return None
        for k, v in [("OPENAI_API_BASE", base), ("OPENAI_API_KEY", key)]:
            if v and k not in os.environ:
                os.environ[k] = v
        model_name = os.environ.get("OPENAI_MODEL_CHAT", "gpt-4o-mini")
        model_spec = f"openai:{model_name}"
        from langchain.chat_models import init_chat_model
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = init_chat_model(model_spec)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content="请根据以上上下文生成完整需求文档，只输出 Markdown 内容，不要附加解释。"),
        ])
        content = getattr(response, "content", None) or ""
        return content.strip() if content else None
    except Exception:
        return None


def _save_draft(state: DocWorkflowState) -> dict[str, Any]:
    """写入文件系统并更新元数据。"""
    conn = state["conn"]
    storage: RequirementDocStorage = state["storage"]
    product_id = state["product_id"]
    requirement_id = state["requirement_id"]
    content = state.get("generated_content") or ""

    try:
        doc_service.save_doc(
            conn, storage, product_id, requirement_id, content, generated_by="workflow"
        )
        return {"status": "completed", "error": None}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# ── 图构建 ──


def _after_collect_context(state: DocWorkflowState) -> str:
    """收集上下文失败则结束，否则进入代码检索。"""
    return "end" if state.get("status") == "failed" else "code_search"


def _build_graph() -> StateGraph:
    workflow = StateGraph(DocWorkflowState)

    workflow.add_node("collect_context", _collect_context)
    workflow.add_node("code_search", _code_search)
    workflow.add_node("graph_search", _graph_search)
    workflow.add_node("synthesize", _synthesize)
    workflow.add_node("generate_doc", _generate_doc)
    workflow.add_node("save_draft", _save_draft)

    workflow.add_edge(START, "collect_context")
    workflow.add_conditional_edges(
        "collect_context", _after_collect_context, {"end": END, "code_search": "code_search"}
    )
    workflow.add_edge("code_search", "graph_search")
    workflow.add_edge("graph_search", "synthesize")
    workflow.add_edge("synthesize", "generate_doc")
    workflow.add_edge("generate_doc", "save_draft")
    workflow.add_edge("save_draft", END)

    return workflow


_compiled_app = _build_graph().compile()


# ── 同步运行 ──


def run_doc_workflow(
    conn,
    storage: RequirementDocStorage,
    product_id: int,
    requirement_id: int,
) -> dict[str, Any]:
    """
    同步执行单需求文档生成工作流。
    返回最终状态（含 status / error / generated_content 等）。
    """
    initial: DocWorkflowState = {
        "conn": conn,
        "storage": storage,
        "product_id": product_id,
        "requirement_id": requirement_id,
    }
    final = None
    for chunk in _compiled_app.stream(initial):
        for _node_name, node_state in chunk.items():
            final = node_state
    return dict(final) if final else {}


# ── SSE 流式运行（单需求） ──


def run_doc_workflow_stream(
    conn,
    storage: RequirementDocStorage,
    product_id: int,
    requirement_id: int,
) -> Iterator[dict[str, Any]]:
    """
    流式执行单需求文档生成，产出 SSE 事件字典（同步生成器）。
    事件类型：workflow_step（step, status, detail?）, token（text）, workflow_done（requirement_id, version?）。
    """
    initial: DocWorkflowState = {
        "conn": conn,
        "storage": storage,
        "product_id": product_id,
        "requirement_id": requirement_id,
    }

    steps = [
        "collect_context",
        "code_search",
        "graph_search",
        "synthesize",
        "generate_doc",
        "save_draft",
    ]
    final: dict[str, Any] = {}

    try:
        for chunk in _compiled_app.stream(initial):
            for node_name, node_state in chunk.items():
                final.update(node_state)
                if node_name in steps:
                    yield {
                        "event": "workflow_step",
                        "data": {
                            "step": node_name,
                            "status": "running",
                        },
                    }
                    yield {
                        "event": "workflow_step",
                        "data": {
                            "step": node_name,
                            "status": "done",
                            "detail": None,
                        },
                    }
                if node_name == "generate_doc" and node_state.get("generated_content"):
                    # 步骤4 可改为逐 token 流式
                    yield {
                        "event": "token",
                        "data": {"text": node_state["generated_content"]},
                    }

        meta = None
        if final.get("status") == "completed":
            meta = doc_service.get_doc(conn, storage, product_id, requirement_id)
        yield {
            "event": "workflow_done",
            "data": {
                "requirement_id": requirement_id,
                "status": final.get("status", "unknown"),
                "error": final.get("error"),
                "version": meta.get("version") if meta else None,
            },
        }
    except Exception as e:
        yield {
            "event": "workflow_done",
            "data": {
                "requirement_id": requirement_id,
                "status": "failed",
                "error": str(e),
                "version": None,
            },
        }


# ── 批量生成子级：Step 0 解析 + 逐子需求工作流 ──


def decompose_parent_doc(
    conn,
    storage: RequirementDocStorage,
    product_id: int,
    parent_requirement_id: int,
) -> list[dict[str, Any]]:
    """
    解析父文档拆分建议，与已有子需求匹配或创建新子需求，返回带 generation_seed、is_new 的列表。
    步骤4 可用 LLM 提取条目；此处用正则解析章节并与 list_by_product(parent_id) 匹配/创建。
    """
    parent_doc = storage.read(product_id, parent_requirement_id)
    parent_req = requirement_repo.find_by_id(conn, parent_requirement_id)
    if not parent_req:
        return []
    parent_level = (parent_req.get("level") or "story").lower()
    children = requirement_repo.list_by_product(
        conn, product_id, parent_id=parent_requirement_id
    )

    if parent_level == "epic":
        section = _extract_split_section(parent_doc, "Story 拆分建议")
        child_level = "story"
    elif parent_level == "story":
        section = _extract_split_section(parent_doc, "Task 拆分建议")
        child_level = "task"
    else:
        return []

    lines = [ln.strip() for ln in section.splitlines() if ln.strip()]
    def norm(s: str) -> str:
        return re.sub(r"^[\s\-*•]\s*", "", s).strip()

    result: list[dict[str, Any]] = []
    used_child_ids: set[int] = set()

    for line in lines:
        seed = norm(line)
        if not seed:
            continue
        # 尝试匹配已有子需求（标题包含种子关键词或种子包含标题）
        matched = None
        for c in children:
            if c["id"] in used_child_ids:
                continue
            title = (c.get("title") or "").strip()
            if title in seed or seed in title or (title and seed and title[:20] in seed):
                matched = c
                break
        if matched:
            used_child_ids.add(matched["id"])
            result.append({
                "requirement_id": matched["id"],
                "title": matched.get("title"),
                "generation_seed": seed,
                "is_new": False,
            })
        else:
            # 创建新子需求
            try:
                new_req = requirement_repo.create(
                    conn,
                    product_id=product_id,
                    title=seed[:200] if len(seed) > 200 else seed,
                    level=child_level,
                    parent_id=parent_requirement_id,
                )
                result.append({
                    "requirement_id": new_req["id"],
                    "title": new_req.get("title"),
                    "generation_seed": seed,
                    "is_new": True,
                })
            except Exception:
                continue

    # 未匹配到的已有子需求也加入，seed 为空
    for c in children:
        if c["id"] in used_child_ids:
            continue
        result.append({
            "requirement_id": c["id"],
            "title": c.get("title"),
            "generation_seed": "",
            "is_new": False,
        })

    return result


async def run_generate_children_stream(
    conn,
    storage: RequirementDocStorage,
    product_id: int,
    parent_requirement_id: int,
) -> AsyncIterator[dict[str, Any]]:
    """
    批量生成子级文档：先 decompose_parent_doc，再对每个子需求跑工作流，产出 SSE。
    事件：decompose_done（children）, child_done（requirement_id）, workflow_done（total）。
    """
    children_specs = decompose_parent_doc(
        conn, storage, product_id, parent_requirement_id
    )
    yield {
        "event": "decompose_done",
        "data": {
            "children": [
                {
                    "requirement_id": s["requirement_id"],
                    "title": s.get("title"),
                    "is_new": s.get("is_new", False),
                }
                for s in children_specs
            ],
        },
    }

    _executor = _get_executor()
    loop = asyncio.get_event_loop()

    for spec in children_specs:
        rid = spec["requirement_id"]
        gen = run_doc_workflow_stream(conn, storage, product_id, rid)
        while True:
            ev = await loop.run_in_executor(_executor, _next_or_stop, gen)
            if ev is _SENTINEL:
                break
            if ev.get("event") == "workflow_step":
                yield ev
            elif ev.get("event") == "token":
                yield ev
            elif ev.get("event") == "workflow_done":
                yield {"event": "child_done", "data": ev.get("data", {})}

    yield {
        "event": "workflow_done",
        "data": {"total": len(children_specs)},
    }


_SENTINEL = object()
_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="doc_workflow")
    return _executor


def _next_or_stop(gen: Iterator[dict[str, Any]]) -> dict[str, Any] | object:
    return next(gen, _SENTINEL)
