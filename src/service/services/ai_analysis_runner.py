"""AI 分析执行：分层并行生成 description，并同步写入 embedding。"""

import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable

from service.services.aggregation_sampling import build_aggregate_prompt, sample_children
from service.services.llm_client import chat_completion, embedding_completion, get_llm_config

# 合法 label 白名单（防 Cypher 注入）
VALID_LABELS: set[str] = {
    "Project", "Package", "Module", "Folder", "File",
    "Class", "Function", "Method", "Variable", "Interface", "Enum",
    "Decorator", "Import", "Type", "CodeElement", "Community", "Process",
    "Struct", "Macro", "Typedef", "Union", "Namespace", "Trait", "Impl",
    "TypeAlias", "Const", "Static", "Property", "Record", "Delegate",
    "Annotation", "Constructor", "Template",
}

# 处理优先级：值越小越先处理（叶子 → 容器 → 顶层）
_LABEL_PRIORITY: dict[str, int] = {
    "Function": 0, "Method": 0, "Constructor": 0,
    "Variable": 0, "Const": 0, "Static": 0, "Property": 0,
    "Enum": 0, "Decorator": 0, "Import": 0, "Type": 0,
    "TypeAlias": 0, "Macro": 0, "Typedef": 0, "Union": 0,
    "Delegate": 0, "Annotation": 0, "Template": 0, "Record": 0,
    "Interface": 1, "Trait": 1, "Struct": 1, "Impl": 1,
    "Class": 1,
    "File": 2, "CodeElement": 2,
    "Folder": 3, "Namespace": 3,
    "Module": 4, "Package": 4, "Community": 4, "Process": 4,
    "Project": 5,
}


def _sample_size() -> int:
    try:
        return max(1, int(os.environ.get("AGGREGATION_SAMPLE_SIZE", "3")))
    except ValueError:
        return 3


def _max_workers() -> int:
    try:
        return max(1, int(os.environ.get("AI_ANALYSIS_MAX_WORKERS", "4")))
    except ValueError:
        return 4


def _progress_interval() -> int:
    try:
        return max(1, int(os.environ.get("AI_ANALYSIS_PROGRESS_INTERVAL", "50")))
    except ValueError:
        return 50


def _embedding_similarity() -> str:
    value = (os.environ.get("AI_EMBEDDING_SIMILARITY", "cosine") or "cosine").strip().lower()
    if value not in {"cosine", "euclidean"}:
        return "cosine"
    return value


def _log_event(
    process_logs: list[dict[str, Any]],
    stage: str,
    message: str,
    **fields: Any,
) -> None:
    payload: dict[str, Any] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "message": message,
    }
    payload.update(fields)
    process_logs.append(payload)


def _sort_node_key(node: dict[str, Any]) -> tuple[int, str, str]:
    label = str(node.get("label") or "")
    name = str(node.get("name") or "")
    node_id = str(node.get("id") or "")
    return (_LABEL_PRIORITY.get(label, 2), name, node_id)


def _get_children(
    session, parent_id: str, branch: str, project_id: int
) -> list[dict]:
    """查询某节点的 CONTAINS / DEFINES 下级，返回 [{id, name, desc}, ...]。"""
    q = """
    MATCH (p {id: $parent_id, branch: $branch, project_id: $project_id})-[:CONTAINS|DEFINES]->(c)
    WHERE c.branch = $branch AND c.project_id = $project_id
    RETURN c.id AS id, c.name AS name, c.description AS description
    """
    result = session.run(q, parent_id=parent_id, branch=branch, project_id=project_id)
    return [
        {
            "id": r.get("id") or "",
            "name": r.get("name") or "",
            "desc": (r.get("description") or "") if r.get("description") else "",
        }
        for r in result
    ]


def _update_node_payload(
    session,
    label: str,
    node_id: str,
    branch: str,
    project_id: int,
    description: str,
    embedding: list[float],
    embedding_model: str,
) -> bool:
    """更新节点描述与向量属性。"""
    if label not in VALID_LABELS:
        return False
    q = f"""
    MATCH (n:{label} {{id: $id, branch: $branch, project_id: $project_id}})
    SET n.description = $description,
        n.enrichedBy = 'llm',
        n.embedding = $embedding,
        n.embeddingModel = $embedding_model,
        n.embeddingUpdatedAt = $embedding_updated_at
    """
    session.run(
        q,
        id=node_id,
        branch=branch,
        project_id=project_id,
        description=description,
        embedding=embedding,
        embedding_model=embedding_model,
        embedding_updated_at=datetime.now(timezone.utc).isoformat(),
    )
    return True


def _load_nodes(neo4j_driver, project_id: int, branch: str, database: str | None) -> list[dict[str, Any]]:
    with neo4j_driver.session(database=database) as session:
        q = """
        MATCH (n)
        WHERE n.branch = $branch AND n.project_id = $project_id
        OPTIONAL MATCH (n)-[:CONTAINS|DEFINES]->(c)
        WHERE c.branch = $branch AND c.project_id = $project_id
        RETURN n.id AS id, labels(n)[0] AS label, n.name AS name,
               n.description AS description, count(c) AS child_count
        """
        result = session.run(q, branch=branch, project_id=project_id)
        return [dict(r) for r in result]


def _load_contains_edges(
    neo4j_driver, project_id: int, branch: str, database: str | None
) -> list[tuple[str, str]]:
    with neo4j_driver.session(database=database) as session:
        q = """
        MATCH (p)-[:CONTAINS|DEFINES]->(c)
        WHERE p.branch = $branch AND p.project_id = $project_id
          AND c.branch = $branch AND c.project_id = $project_id
        RETURN p.id AS parent_id, c.id AS child_id
        """
        result = session.run(q, branch=branch, project_id=project_id)
        return [(str(r.get("parent_id") or ""), str(r.get("child_id") or "")) for r in result]


def _build_container_levels(
    nodes: dict[str, dict[str, Any]],
    edges: list[tuple[str, str]],
) -> list[list[dict[str, Any]]]:
    node_ids = set(nodes.keys())
    children_map: dict[str, set[str]] = {nid: set() for nid in node_ids}
    for parent_id, child_id in edges:
        if parent_id in node_ids and child_id in node_ids and child_id != parent_id:
            children_map[parent_id].add(child_id)

    leaf_ids = {nid for nid, children in children_map.items() if not children}
    remaining = {nid for nid in node_ids if nid not in leaf_ids}
    processed = set(leaf_ids)
    levels: list[list[dict[str, Any]]] = []

    while remaining:
        current_ids = [
            nid for nid in remaining if children_map.get(nid) and children_map[nid].issubset(processed)
        ]
        if not current_ids:
            # 异常环路兜底：剩余节点按优先级作为最后一层处理
            fallback_nodes = sorted((nodes[nid] for nid in remaining), key=_sort_node_key)
            levels.append(fallback_nodes)
            break
        current_level = sorted((nodes[nid] for nid in current_ids), key=_sort_node_key)
        levels.append(current_level)
        processed.update(current_ids)
        remaining.difference_update(current_ids)

    return levels


def _ensure_vector_indexes(
    neo4j_driver,
    database: str | None,
    *,
    dimensions: int,
    process_logs: list[dict[str, Any]],
) -> None:
    similarity = _embedding_similarity()
    with neo4j_driver.session(database=database) as session:
        for label in sorted(VALID_LABELS):
            index_name = f"idx_{label.lower()}_embedding"
            q = f"""
            CREATE VECTOR INDEX {index_name} IF NOT EXISTS
            FOR (n:{label}) ON (n.embedding)
            OPTIONS {{
              indexConfig: {{
                `vector.dimensions`: $dimensions,
                `vector.similarity_function`: $similarity
              }}
            }}
            """
            try:
                session.run(q, dimensions=dimensions, similarity=similarity)
            except Exception as exc:  # noqa: BLE001
                _log_event(
                    process_logs,
                    stage="VECTOR_INDEX",
                    message=f"向量索引创建失败，已跳过 label={label}",
                    label=label,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )


def _leaf_prompt(label: str, name: str) -> str:
    return f"请用一句话描述以下代码元素的职责或作用：{label}「{name}」。"


def _process_node_common(
    neo4j_driver,
    node: dict[str, Any],
    branch: str,
    project_id: int,
    database: str | None,
    *,
    force: bool,
    prompt_builder: Callable[[dict[str, Any]], str],
    max_tokens: int,
) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    node_id = str(node.get("id") or "")
    label = str(node.get("label") or "")
    name = str(node.get("name") or node_id)
    existing = str(node.get("description") or "").strip()
    worker = threading.current_thread().name

    if not node_id or label not in VALID_LABELS:
        return {
            "status": "failed",
            "step": "validate",
            "node_id": node_id,
            "label": label,
            "name": name,
            "worker": worker,
            "error_type": "InvalidNode",
            "error_message": "node_id 为空或 label 非法",
            "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        }
    if not force and existing:
        return {
            "status": "skipped",
            "node_id": node_id,
            "label": label,
            "name": name,
            "worker": worker,
            "reason": "existing_description",
            "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        }

    try:
        prompt = prompt_builder(node)
        description = chat_completion(prompt, max_tokens=max_tokens)
        if not description:
            raise RuntimeError("LLM 返回空描述")
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "step": "desc",
            "node_id": node_id,
            "label": label,
            "name": name,
            "worker": worker,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        }

    try:
        embedding = embedding_completion(description)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "step": "embedding",
            "node_id": node_id,
            "label": label,
            "name": name,
            "worker": worker,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        }

    try:
        with neo4j_driver.session(database=database) as session:
            _update_node_payload(
                session=session,
                label=label,
                node_id=node_id,
                branch=branch,
                project_id=project_id,
                description=description,
                embedding=embedding,
                embedding_model=str(get_llm_config().get("model_embedding") or ""),
            )
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "step": "write",
            "node_id": node_id,
            "label": label,
            "name": name,
            "worker": worker,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        }

    return {
        "status": "saved",
        "node_id": node_id,
        "label": label,
        "name": name,
        "worker": worker,
        "embedding_dim": len(embedding),
        "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
    }


def _process_leaf_node(
    neo4j_driver,
    node: dict[str, Any],
    branch: str,
    project_id: int,
    database: str | None,
    force: bool,
) -> dict[str, Any]:
    return _process_node_common(
        neo4j_driver=neo4j_driver,
        node=node,
        branch=branch,
        project_id=project_id,
        database=database,
        force=force,
        prompt_builder=lambda n: _leaf_prompt(str(n.get("label") or ""), str(n.get("name") or n.get("id") or "")),
        max_tokens=200,
    )


def _process_container_node(
    neo4j_driver,
    node: dict[str, Any],
    branch: str,
    project_id: int,
    database: str | None,
    force: bool,
    sample_size: int,
) -> dict[str, Any]:
    def _build_prompt(n: dict[str, Any]) -> str:
        node_id = str(n.get("id") or "")
        with neo4j_driver.session(database=database) as session:
            children = _get_children(session, node_id, branch, project_id)
        total = len(children)
        sampled = sample_children(children, sample_size=sample_size, max_desc_chars=200)
        return build_aggregate_prompt(
            str(n.get("label") or ""),
            str(n.get("name") or node_id),
            sampled,
            total,
        )

    return _process_node_common(
        neo4j_driver=neo4j_driver,
        node=node,
        branch=branch,
        project_id=project_id,
        database=database,
        force=force,
        prompt_builder=_build_prompt,
        max_tokens=512,
    )


def _merge_stage_result(stats: dict[str, Any], result: dict[str, Any]) -> None:
    status = result.get("status")
    if status == "saved":
        stats["saved"] += 1
        stats["embedded"] += 1
        stats["durations_ms"].append(int(result.get("duration_ms") or 0))
        return
    if status == "skipped":
        stats["skipped"] += 1
        return
    stats["failed"] += 1
    step = str(result.get("step") or "")
    if step == "desc":
        stats["failed_desc"] += 1
    elif step == "embedding":
        stats["failed_embedding"] += 1
    elif step == "write":
        stats["failed_write"] += 1
    else:
        stats["failed_validate"] += 1
    stats["failures"].append(
        {
            "node_id": result.get("node_id"),
            "label": result.get("label"),
            "name": result.get("name"),
            "worker": result.get("worker"),
            "step": step,
            "error_type": result.get("error_type"),
            "error_message": result.get("error_message"),
        }
    )


def _run_parallel_stage(
    *,
    stage: str,
    nodes: list[dict[str, Any]],
    max_workers: int,
    process_logs: list[dict[str, Any]],
    worker_fn: Callable[[dict[str, Any]], dict[str, Any]],
    stats: dict[str, Any],
    progress_interval: int,
    ensure_index: Callable[[int], None],
) -> None:
    total = len(nodes)
    if total == 0:
        _log_event(process_logs, stage, "阶段无节点，已跳过", node_count=0)
        return
    _log_event(process_logs, stage, "阶段开始", node_count=total, max_workers=max_workers)

    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures: dict[Future[dict[str, Any]], dict[str, Any]] = {
            executor.submit(worker_fn, node): node for node in nodes
        }
        for future in as_completed(futures):
            done += 1
            result = future.result()
            if result.get("status") == "saved":
                dim = int(result.get("embedding_dim") or 0)
                if dim > 0:
                    ensure_index(dim)
            _merge_stage_result(stats, result)
            if result.get("status") == "failed":
                _log_event(
                    process_logs,
                    stage,
                    "节点处理失败",
                    node_id=result.get("node_id"),
                    label=result.get("label"),
                    step=result.get("step"),
                    error_type=result.get("error_type"),
                    error_message=result.get("error_message"),
                    worker=result.get("worker"),
                )
            if done % progress_interval == 0 or done == total:
                _log_event(
                    process_logs,
                    stage,
                    "阶段进度",
                    done=done,
                    total=total,
                    saved=stats["saved"],
                    skipped=stats["skipped"],
                    failed=stats["failed"],
                )


def run_ai_analysis(
    neo4j_driver,
    project_id: int,
    branch: str,
    force: bool,
    process_logs: list[dict[str, Any]],
    database: str | None = None,
) -> dict:
    """
    对 Neo4j 中 (project_id, branch) 的全部节点生成描述。
    过程日志追加到 process_logs；返回 {"saved": n, "skipped": m}。
    """
    llm_cfg = get_llm_config()
    if not llm_cfg["api_key"]:
        raise ValueError("OPENAI_API_KEY 未设置，无法执行 AI 分析")

    sample_size = _sample_size()
    workers = _max_workers()
    interval = _progress_interval()
    stats: dict[str, Any] = {
        "total": 0,
        "leaf_total": 0,
        "container_total": 0,
        "saved": 0,
        "embedded": 0,
        "skipped": 0,
        "failed": 0,
        "failed_desc": 0,
        "failed_embedding": 0,
        "failed_write": 0,
        "failed_validate": 0,
        "durations_ms": [],
        "failures": [],
    }
    _log_event(
        process_logs,
        "INIT",
        "开始 AI 分析",
        project_id=project_id,
        branch=branch,
        force=force,
        max_workers=workers,
        sample_size=sample_size,
        embedding_model=llm_cfg.get("model_embedding"),
    )

    nodes = _load_nodes(neo4j_driver, project_id, branch, database)
    node_by_id = {str(n.get("id") or ""): n for n in nodes if n.get("id")}
    edges = _load_contains_edges(neo4j_driver, project_id, branch, database)
    leaf_nodes = [n for n in node_by_id.values() if int(n.get("child_count") or 0) == 0]
    container_levels = _build_container_levels(node_by_id, edges)

    stats["total"] = len(node_by_id)
    stats["leaf_total"] = len(leaf_nodes)
    stats["container_total"] = sum(len(level) for level in container_levels)
    _log_event(
        process_logs,
        "FETCH_NODES",
        "图数据加载完成",
        total=stats["total"],
        leaf_total=stats["leaf_total"],
        container_total=stats["container_total"],
        edge_count=len(edges),
    )

    index_state: dict[str, Any] = {"ensured": False, "dimensions": 0}

    def ensure_index_once(dimensions: int) -> None:
        if index_state["ensured"]:
            return
        _ensure_vector_indexes(
            neo4j_driver=neo4j_driver,
            database=database,
            dimensions=dimensions,
            process_logs=process_logs,
        )
        index_state["ensured"] = True
        index_state["dimensions"] = dimensions
        _log_event(
            process_logs,
            "VECTOR_INDEX",
            "向量索引确保完成",
            dimensions=dimensions,
            similarity=_embedding_similarity(),
        )

    _run_parallel_stage(
        stage="LEAF_PARALLEL",
        nodes=sorted(leaf_nodes, key=_sort_node_key),
        max_workers=workers,
        process_logs=process_logs,
        worker_fn=lambda n: _process_leaf_node(
            neo4j_driver=neo4j_driver,
            node=n,
            branch=branch,
            project_id=project_id,
            database=database,
            force=force,
        ),
        stats=stats,
        progress_interval=interval,
        ensure_index=ensure_index_once,
    )

    for idx, level_nodes in enumerate(container_levels, start=1):
        stage = f"CONTAINER_LEVEL_{idx}"
        _run_parallel_stage(
            stage=stage,
            nodes=level_nodes,
            max_workers=workers,
            process_logs=process_logs,
            worker_fn=lambda n: _process_container_node(
                neo4j_driver=neo4j_driver,
                node=n,
                branch=branch,
                project_id=project_id,
                database=database,
                force=force,
                sample_size=sample_size,
            ),
            stats=stats,
            progress_interval=interval,
            ensure_index=ensure_index_once,
        )

    durations = stats.pop("durations_ms")
    if durations:
        durations_sorted = sorted(durations)
        stats["avg_latency_ms"] = int(sum(durations_sorted) / len(durations_sorted))
        p95_index = int((len(durations_sorted) - 1) * 0.95)
        stats["p95_latency_ms"] = durations_sorted[p95_index]
    else:
        stats["avg_latency_ms"] = 0
        stats["p95_latency_ms"] = 0

    _log_event(
        process_logs,
        "FINISH",
        "AI 分析完成",
        total=stats["total"],
        saved=stats["saved"],
        skipped=stats["skipped"],
        failed=stats["failed"],
        embedded=stats["embedded"],
        avg_latency_ms=stats["avg_latency_ms"],
        p95_latency_ms=stats["p95_latency_ms"],
        vector_index_dimensions=index_state["dimensions"],
    )
    return stats
