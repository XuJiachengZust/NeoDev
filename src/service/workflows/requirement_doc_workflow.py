"""需求文档生成工作流：LangGraph StateGraph，CollectContext → CodeSearch → GraphSearch → Synthesize → GenerateDoc → SaveDraft。"""

import asyncio
import logging
import os
import re
import subprocess
import time
from collections.abc import AsyncIterator, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph, START

from service.agent_profiles import build_requirement_doc_prompt
from service.repositories import product_repository as product_repo
from service.repositories import product_requirement_repository as requirement_repo
from service.repositories import product_version_repository as version_repo
from service.services import requirement_doc_service as doc_service
from service.storage import RequirementDocStorage

logger = logging.getLogger(__name__)


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
    project_id_map: dict[str, int]    # 项目名 → 项目 ID
    user_overview: str | None

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

    # 项目名 → 仓库路径 / 项目 ID
    projects = product_repo.list_projects(conn, product_id)
    project_repo_map = {p["name"]: p["repo_path"] for p in projects if p.get("name") and p.get("repo_path")}
    project_id_map = {p["name"]: p["id"] for p in projects if p.get("name")}

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
        "project_id_map": project_id_map,
        "code_search_results": "",
        "graph_search_results": "",
        "status": "running",
    }


_STOP_WORDS = frozenset({
    "的", "了", "和", "是", "在", "与", "为", "对", "将", "从", "到", "中",
    "a", "an", "the", "and", "or", "in", "of", "to", "for", "with",
    "is", "be", "as", "by", "on", "at", "it", "this", "that",
    "管理", "系统", "功能", "模块", "实现", "支持", "需求", "优化", "新增", "修改",
})


def _extract_search_keywords(title: str, description: str | None) -> list[str]:
    """从需求标题和描述中提取搜索关键词（英文标识符 + 中文短语）。"""
    text = f"{title} {description or ''}"
    eng_words = re.findall(r'[A-Za-z_][A-Za-z0-9_]{2,}', text)
    cn_phrases = re.findall(r'[\u4e00-\u9fff]{2,6}', text)

    keywords: list[str] = []
    seen: set[str] = set()
    for w in eng_words:
        lower = w.lower()
        if lower not in _STOP_WORDS and lower not in seen:
            seen.add(lower)
            keywords.append(w)
    for p in cn_phrases:
        if p not in _STOP_WORDS and p not in seen:
            seen.add(p)
            keywords.append(p)
    return keywords


def _grep_in_repo(repo_path: str, keyword: str, max_results: int = 5) -> str:
    """使用 git grep 在仓库中检索关键词，返回匹配行摘要。"""
    repo = Path(repo_path)
    if not repo.is_dir():
        return ""
    try:
        r = subprocess.run(
            ["git", "grep", "-n", "-I", "--max-count", str(max_results), keyword],
            cwd=repo, capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0 and r.stdout.strip():
            lines = r.stdout.strip().splitlines()[:max_results]
            return "\n".join(f"  {ln}" for ln in lines)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ""


def _code_search(state: DocWorkflowState) -> dict[str, Any]:
    """按层级做代码检索：Epic 不检索；Story 轻量检索；Task 详细检索。"""
    level = (state.get("level") or "epic").lower()
    if level == "epic":
        return {"code_search_results": ""}

    project_repo_map = state.get("project_repo_map") or {}
    if not project_repo_map:
        return {"code_search_results": ""}

    title = state.get("requirement_title") or ""
    desc = state.get("requirement_description") or ""
    keywords = _extract_search_keywords(title, desc)
    if not keywords:
        return {"code_search_results": ""}

    max_per_kw = 8 if level == "task" else 3
    max_keywords = 6 if level == "task" else 3
    results: list[str] = []

    for project_name, repo_path in project_repo_map.items():
        for kw in keywords[:max_keywords]:
            matches = _grep_in_repo(repo_path, kw, max_results=max_per_kw)
            if matches:
                results.append(f"### {project_name} — `{kw}`\n{matches}")

    if not results:
        return {"code_search_results": ""}
    return {"code_search_results": "\n\n".join(results)}


def _load_neo4j_config() -> dict[str, str] | None:
    """加载 Neo4j 连接配置，不可用时返回 None。"""
    try:
        from service.agent_factory import _load_nexus_neo4j_config
        return _load_nexus_neo4j_config()
    except Exception:
        return None


def _neo4j_search_nodes(
    keywords: list[str],
    project_id_map: dict[str, int] | None,
    include_overview: bool = False,
) -> str:
    """在 Neo4j 图谱中搜索与关键词相关的节点，返回格式化结果。"""
    neo4j_cfg = _load_neo4j_config()
    if not neo4j_cfg:
        return ""
    try:
        import neo4j as neo4j_lib
        driver = neo4j_lib.GraphDatabase.driver(
            neo4j_cfg["neo4j_uri"],
            auth=(neo4j_cfg["neo4j_user"], neo4j_cfg["neo4j_password"]),
        )
    except Exception:
        return ""

    db_name = neo4j_cfg.get("neo4j_database")
    project_ids = list(project_id_map.values()) if project_id_map else []
    results: list[str] = []

    try:
        with driver.session(database=db_name) as session:
            for kw in keywords[:5]:
                where_parts = ["(n.name CONTAINS $kw OR n.description CONTAINS $kw)"]
                params: dict[str, Any] = {"kw": kw, "limit": 10}
                if project_ids:
                    where_parts.append("n.project_id IN $pids")
                    params["pids"] = project_ids
                cypher = (
                    f"MATCH (n) WHERE {' AND '.join(where_parts)} "
                    f"RETURN labels(n)[0] AS label, n.name AS name, "
                    f"n.description AS description, n.id AS id "
                    f"ORDER BY n.name LIMIT $limit"
                )
                records = [dict(r) for r in session.run(cypher, params)]
                if records:
                    items = []
                    for rec in records:
                        desc = (rec.get("description") or "")[:80]
                        items.append(
                            f"  [{rec.get('label', '')}] {rec.get('name', '')}"
                            f"{' — ' + desc if desc else ''}"
                        )
                    results.append(f"### 关键字 `{kw}`\n" + "\n".join(items))

        if include_overview and project_ids:
            with driver.session(database=db_name) as session:
                overview = (
                    "MATCH (c:Community) WHERE c.project_id IN $pids "
                    "OPTIONAL MATCH (m)-[:MEMBER_OF]->(c) "
                    "RETURN c.name AS name, c.description AS description, "
                    "count(m) AS members ORDER BY members DESC LIMIT 10"
                )
                communities = [dict(r) for r in session.run(overview, {"pids": project_ids})]
                if communities:
                    items = []
                    for c in communities:
                        desc = (c.get("description") or "")[:60]
                        items.append(
                            f"  - {c['name']} (成员 {c.get('members', 0)})"
                            f"{': ' + desc if desc else ''}"
                        )
                    results.append("### 相关模块（Community）\n" + "\n".join(items))
    except Exception as e:
        logger.debug("Neo4j 图谱检索失败: %s", e)
        return ""
    finally:
        try:
            driver.close()
        except Exception:
            pass

    return "\n\n".join(results)


def _graph_search(state: DocWorkflowState) -> dict[str, Any]:
    """按层级做图谱检索：Epic 跳过；Story 检索相关模块概览；Task 详细检索节点。"""
    level = (state.get("level") or "epic").lower()
    if level == "epic":
        return {"graph_search_results": ""}

    project_id_map = state.get("project_id_map") or {}
    if not project_id_map:
        return {"graph_search_results": ""}

    title = state.get("requirement_title") or ""
    desc = state.get("requirement_description") or ""
    keywords = _extract_search_keywords(title, desc)
    if not keywords:
        return {"graph_search_results": ""}

    result = _neo4j_search_nodes(
        keywords,
        project_id_map,
        include_overview=(level == "story"),
    )
    return {"graph_search_results": result}


def _synthesize(state: DocWorkflowState) -> dict[str, Any]:
    """合并检索结果与父文档种子，供生成使用。此处仅透传，实际合并在 GenerateDoc 的 prompt 中。"""
    return {"status": state.get("status", "running")}


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


_LLM_USER_MESSAGE = "请根据以上上下文生成完整需求文档，只输出 Markdown 内容，不要附加解释。"
_LLM_MAX_RETRIES = 2


def _init_llm():
    """初始化 LLM，未配置时返回 None。"""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    from service.agent_factory import _create_chat_model
    return _create_chat_model()


def _build_llm_messages(system_prompt: str):
    from langchain_core.messages import HumanMessage, SystemMessage
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=_LLM_USER_MESSAGE),
    ]


def _invoke_llm_for_doc(system_prompt: str, title: str) -> str | None:
    """调用 LLM 生成文档正文；失败时重试，最终仍失败返回 None。"""
    try:
        llm = _init_llm()
        if not llm:
            return None
        messages = _build_llm_messages(system_prompt)

        last_error: Exception | None = None
        for attempt in range(_LLM_MAX_RETRIES + 1):
            try:
                response = llm.invoke(messages)
                content = getattr(response, "content", None) or ""
                if content.strip():
                    return content.strip()
            except Exception as e:
                last_error = e
                logger.warning("LLM 生成文档异常 (尝试 %d/%d): %s", attempt + 1, _LLM_MAX_RETRIES + 1, e, exc_info=True)
                if attempt < _LLM_MAX_RETRIES:
                    time.sleep(2 ** attempt)
        if last_error:
            logger.error("LLM 生成文档最终失败 (重试 %d 次): %s", _LLM_MAX_RETRIES, last_error)
        return None
    except Exception as e:
        logger.error("LLM 初始化或构建消息失败: %s", e, exc_info=True)
        return None


def _invoke_llm_for_doc_stream(system_prompt: str) -> Iterator[str]:
    """流式调用 LLM 生成文档，逐 token yield；全部失败时不产出任何内容。"""
    try:
        llm = _init_llm()
        if not llm:
            return
        messages = _build_llm_messages(system_prompt)

        for attempt in range(_LLM_MAX_RETRIES + 1):
            try:
                has_content = False
                for chunk in llm.stream(messages):
                    text = getattr(chunk, "content", None) or ""
                    if text:
                        has_content = True
                        yield text
                if has_content:
                    return
            except Exception as e:
                logger.warning("LLM 流式生成异常 (尝试 %d/%d): %s", attempt + 1, _LLM_MAX_RETRIES + 1, e, exc_info=True)
                if attempt < _LLM_MAX_RETRIES:
                    time.sleep(2 ** attempt)
                else:
                    logger.error("LLM 流式生成最终失败 (重试 %d 次): %s", _LLM_MAX_RETRIES, e)
    except Exception as e:
        logger.error("LLM 流式初始化或构建消息失败: %s", e, exc_info=True)


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
        try:
            from service.repositories import requirement_doc_repository as doc_repo
            doc_repo.update_generation_status(conn, requirement_id, "completed")
        except Exception:
            logger.debug("update_generation_status(completed) failed, migration 016 may not be applied")
        conn.commit()
        return {"status": "completed", "error": None}
    except Exception as e:
        logger.error("保存草稿失败 (requirement_id=%s): %s", requirement_id, e, exc_info=True)
        try:
            conn.rollback()
            from service.repositories import requirement_doc_repository as doc_repo
            doc_repo.update_generation_status(conn, requirement_id, "failed", error=str(e))
            conn.commit()
        except Exception as inner_e:
            logger.error("更新失败状态时异常 (requirement_id=%s): %s", requirement_id, inner_e, exc_info=True)
            try:
                conn.rollback()
            except Exception:
                pass
        return {"status": "failed", "error": str(e)}


# ── 图构建 ──


def _after_collect_context(state: DocWorkflowState) -> str:
    """收集上下文失败则结束，否则进入代码检索。"""
    return "end" if state.get("status") == "failed" else "code_search"


def _build_fallback_template(state: dict[str, Any]) -> str:
    """LLM 不可用时的回退占位模板。"""
    title = state.get("requirement_title") or ""
    desc = state.get("requirement_description") or ""
    seed = state.get("generation_seed") or ""
    code = state.get("code_search_results") or ""
    graph = state.get("graph_search_results") or ""

    parts = [f"# {title}", "", "## 概述", desc or "（待补充）", ""]
    if seed:
        parts.extend(["## 父需求拆分指引", seed, ""])
    if code or graph:
        parts.append("## 代码与图谱检索")
        if code:
            parts.append(code)
        if graph:
            parts.append(graph)
        parts.append("")
    return "\n".join(parts).strip()


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


def _build_pre_generation_graph() -> StateGraph:
    """预生成图：仅执行上下文收集和检索，不含文档生成与保存（供流式生成使用）。"""
    workflow = StateGraph(DocWorkflowState)

    workflow.add_node("collect_context", _collect_context)
    workflow.add_node("code_search", _code_search)
    workflow.add_node("graph_search", _graph_search)
    workflow.add_node("synthesize", _synthesize)

    workflow.add_edge(START, "collect_context")
    workflow.add_conditional_edges(
        "collect_context", _after_collect_context, {"end": END, "code_search": "code_search"}
    )
    workflow.add_edge("code_search", "graph_search")
    workflow.add_edge("graph_search", "synthesize")
    workflow.add_edge("synthesize", END)

    return workflow


_compiled_app = _build_graph().compile()
_pre_generation_app = _build_pre_generation_graph().compile()


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
            if node_state is not None:
                final = node_state
    return dict(final) if final else {}


# ── SSE 流式运行（单需求） ──


def run_doc_workflow_stream(
    conn,
    storage: RequirementDocStorage,
    product_id: int,
    requirement_id: int,
    user_overview: str | None = None,
) -> Iterator[dict[str, Any]]:
    """
    流式执行单需求文档生成，产出 SSE 事件字典（同步生成器）。
    事件类型：workflow_step（step, status, detail?）, token（text）, workflow_done（requirement_id, version?）。

    流程：预生成图（collect_context → code_search → graph_search → synthesize）
         → 流式 LLM 生成 → save_draft。
    """
    initial: DocWorkflowState = {
        "conn": conn,
        "storage": storage,
        "product_id": product_id,
        "requirement_id": requirement_id,
        "user_overview": user_overview,
    }

    pre_steps = {"collect_context", "code_search", "graph_search", "synthesize"}
    state: dict[str, Any] = dict(initial)

    try:
        # ── Phase 1: 预生成（上下文 + 检索） ──
        for chunk in _pre_generation_app.stream(initial):
            for node_name, node_state in chunk.items():
                if node_state is None:
                    continue
                state.update(node_state)
                if node_name in pre_steps:
                    yield {
                        "event": "workflow_step",
                        "data": {"step": node_name, "status": "running"},
                    }
                    yield {
                        "event": "workflow_step",
                        "data": {"step": node_name, "status": "done", "detail": None},
                    }

        if state.get("status") == "failed":
            yield {
                "event": "workflow_done",
                "data": {
                    "requirement_id": requirement_id,
                    "status": "failed",
                    "error": state.get("error"),
                    "version": None,
                },
            }
            return

        # ── Phase 2: 流式 LLM 生成 ──
        yield {"event": "workflow_step", "data": {"step": "generate_doc", "status": "running"}}

        level = (state.get("level") or "story").lower()
        if level not in ("epic", "story", "task"):
            level = "story"
        prompt = build_requirement_doc_prompt(
            level=level,
            requirement_title=state.get("requirement_title") or "",
            requirement_description=state.get("requirement_description"),
            parent_doc=state.get("parent_doc_content"),
            sibling_titles=state.get("sibling_titles") or [],
            product_name=state.get("product_name") or "",
            version_name=state.get("version_name"),
            code_context=state.get("code_search_results") or None,
            graph_context=state.get("graph_search_results") or None,
            existing_doc=None,
            user_overview=state.get("user_overview"),
        )

        content_parts: list[str] = []
        for token in _invoke_llm_for_doc_stream(prompt):
            content_parts.append(token)
            yield {"event": "token", "data": {"text": token}}

        generated_content = "".join(content_parts).strip()
        if not generated_content:
            generated_content = _build_fallback_template(state)
            yield {"event": "token", "data": {"text": generated_content}}

        yield {"event": "workflow_step", "data": {"step": "generate_doc", "status": "done", "detail": None}}

        # ── Phase 3: 保存草稿 ──
        yield {"event": "workflow_step", "data": {"step": "save_draft", "status": "running"}}

        save_state = {**state, "generated_content": generated_content}
        save_result = _save_draft(save_state)
        state.update(save_result)

        yield {"event": "workflow_step", "data": {"step": "save_draft", "status": "done", "detail": None}}

        meta = None
        if state.get("status") == "completed":
            meta = doc_service.get_doc(conn, storage, product_id, requirement_id)
        yield {
            "event": "workflow_done",
            "data": {
                "requirement_id": requirement_id,
                "status": state.get("status", "completed"),
                "error": state.get("error"),
                "version": meta.get("version") if meta else None,
            },
        }
    except Exception as e:
        logger.error("文档生成工作流异常 (requirement_id=%s): %s", requirement_id, e, exc_info=True)
        try:
            from service.repositories import requirement_doc_repository as doc_repo
            doc_repo.update_generation_status(conn, requirement_id, "failed", error=str(e))
            conn.commit()
        except Exception as inner_e:
            logger.error("更新失败状态时异常 (requirement_id=%s): %s", requirement_id, inner_e, exc_info=True)
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
    version_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    解析父文档拆分建议，与已有子需求匹配或创建新子需求，返回带 generation_seed、is_new 的列表。
    步骤4 可用 LLM 提取条目；此处用正则解析章节并与 list_by_product(parent_id) 匹配/创建。
    """
    parent_doc = storage.read(product_id, parent_requirement_id)
    parent_req = requirement_repo.find_by_id(conn, parent_requirement_id)
    if not parent_req:
        return []
    # version_id 优先使用参数传入，否则继承父需求的 version_id
    if version_id is None:
        version_id = parent_req.get("version_id")
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
                    version_id=version_id,
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
    version_id: int | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """
    批量生成子级文档：先 decompose_parent_doc，再对每个子需求跑工作流，产出 SSE。
    事件：decompose_done（children）, child_done（requirement_id）, workflow_done（total）。
    """
    children_specs = decompose_parent_doc(
        conn, storage, product_id, parent_requirement_id, version_id=version_id,
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
