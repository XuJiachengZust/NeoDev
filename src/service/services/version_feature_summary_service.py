"""版本功能总结服务：从 Neo4j 提取顶层节点描述，通过迭代压缩生成项目功能概述。

流程：反查关联产品版本 → 创建 running 记录 → 后台线程执行 pipeline → 完成/失败写回。
"""

import logging
import os
import threading
from typing import Any

import psycopg2

from service.dependencies import get_database_url
from service.repositories import version_feature_summary_repository as summary_repo
from service.repositories import project_repository as project_repo

logger = logging.getLogger(__name__)

# 触发压缩的字符阈值（累积 + 当前批次超过此值时压缩）
FEATURE_SUMMARY_CHAR_THRESHOLD = int(
    os.environ.get("FEATURE_SUMMARY_CHAR_THRESHOLD", "8000")
)

# 顶层节点的 label 白名单，按优先级排列
_TOP_LEVEL_LABELS = ["Project", "Module", "Package", "Folder", "File"]

# label 排序优先级（值越小越优先）
_LABEL_PRIORITY = {label: i for i, label in enumerate(_TOP_LEVEL_LABELS)}


# ── 公开接口 ──


def trigger_for_project_branch(conn, project_id: int, branch: str) -> list[dict]:
    """AI 预处理完成后调用：反查所有关联产品版本，为每个创建 running 记录并启动后台线程。

    返回已创建的 summary 记录列表。
    """
    versions = summary_repo.find_versions_for_project_branch(conn, project_id, branch)
    if not versions:
        logger.info("[功能总结] project_id=%s branch=%s 无关联产品版本，跳过", project_id, branch)
        return []

    project = project_repo.find_by_id(conn, project_id)
    if not project:
        logger.warning("[功能总结] project_id=%s 不存在", project_id)
        return []

    records = []
    for v in versions:
        pv_id = v["product_version_id"]
        row = summary_repo.upsert_running(conn, pv_id, project_id, branch)
        conn.commit()
        records.append(row)
        # 启动后台线程执行 pipeline
        t = threading.Thread(
            target=_run_summary_pipeline,
            args=(row["id"], project_id, branch, project),
            daemon=True,
        )
        t.start()
        logger.info("[功能总结] 已启动后台线程 summary_id=%s pv_id=%s", row["id"], pv_id)

    return records


def trigger_for_version(conn, product_version_id: int) -> list[dict]:
    """手动触发：为该版本下所有已映射分支生成总结。"""
    from service.repositories import product_version_repository as pv_repo

    branches = pv_repo.list_branches(conn, product_version_id)
    if not branches:
        return []

    records = []
    for b in branches:
        proj_id = b["project_id"]
        branch = b["branch"]
        project = project_repo.find_by_id(conn, proj_id)
        if not project:
            continue
        row = summary_repo.upsert_running(conn, product_version_id, proj_id, branch)
        conn.commit()
        records.append(row)
        t = threading.Thread(
            target=_run_summary_pipeline,
            args=(row["id"], proj_id, branch, project),
            daemon=True,
        )
        t.start()
        logger.info("[功能总结] 已启动后台线程 summary_id=%s project_id=%s", row["id"], proj_id)

    return records


def list_summaries(conn, product_version_id: int) -> list[dict]:
    """查询某版本的功能总结列表。"""
    return summary_repo.list_by_version(conn, product_version_id)


# ── 核心 pipeline（后台线程） ──


def _run_summary_pipeline(
    summary_id: int,
    project_id: int,
    branch: str,
    project: dict,
) -> None:
    """后台线程：连接 Neo4j → 查顶层节点 → 迭代压缩 → 生成最终总结 → 写回 DB。"""
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())

        # 1. 加载 Neo4j 配置
        from service.services.ai_preprocessor_service import _load_neo4j_config
        neo4j_config, database = _load_neo4j_config(project)
        if not neo4j_config or not neo4j_config.get("neo4j_uri"):
            raise RuntimeError("未配置 Neo4j，无法生成功能总结")

        # 2. 连接 Neo4j 查询顶层节点
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            neo4j_config["neo4j_uri"],
            auth=(neo4j_config.get("neo4j_user") or "neo4j", neo4j_config.get("neo4j_password") or ""),
        )
        try:
            nodes = _fetch_top_level_nodes(driver, project_id, branch, database)
        finally:
            driver.close()

        if not nodes:
            raise RuntimeError(f"Neo4j 中未找到 project_id={project_id} branch={branch} 的顶层节点描述")

        logger.info("[功能总结] summary_id=%s 共获取 %d 个顶层节点", summary_id, len(nodes))

        # 3. 迭代压缩
        accumulated, remaining = _iterative_compress(nodes)

        # 4. 生成最终总结
        project_name = project.get("name") or f"Project-{project_id}"
        final_summary = _generate_final_summary(accumulated, remaining, project_name)

        # 5. 写回
        summary_repo.set_completed(conn, summary_id, final_summary)
        conn.commit()
        logger.info("[功能总结] summary_id=%s 完成", summary_id)

    except Exception as e:
        logger.exception("[功能总结] summary_id=%s 失败", summary_id)
        if conn:
            try:
                conn.rollback()
                summary_repo.set_failed(conn, summary_id, str(e))
                conn.commit()
            except Exception:
                logger.exception("[功能总结] summary_id=%s 写回失败状态时出错", summary_id)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _fetch_top_level_nodes(
    driver: Any,
    project_id: int,
    branch: str,
    database: str | None,
) -> list[dict]:
    """从 Neo4j 查询有 LLM 描述的顶层节点。

    返回 [{label, name, description}, ...] 按 label 优先级 + name 排序。
    """
    label_list = _TOP_LEVEL_LABELS
    # 构造 Cypher：匹配指定 label、有 enrichedBy='llm' 的节点
    cypher = """
        MATCH (n)
        WHERE n.project_id = $pid
          AND n.branch = $branch
          AND n.enrichedBy = 'llm'
          AND n.description IS NOT NULL
          AND n.description <> ''
          AND any(lbl IN labels(n) WHERE lbl IN $labels)
        RETURN labels(n) AS node_labels, n.name AS name, n.description AS description
    """
    with driver.session(database=database) as session:
        result = session.run(cypher, pid=project_id, branch=branch, labels=label_list)
        raw = list(result)

    nodes = []
    for record in raw:
        node_labels = record["node_labels"]
        # 取优先级最高的 label
        best_label = "File"
        best_priority = 999
        for lbl in node_labels:
            p = _LABEL_PRIORITY.get(lbl, 999)
            if p < best_priority:
                best_priority = p
                best_label = lbl
        nodes.append({
            "label": best_label,
            "name": record["name"] or "",
            "description": record["description"] or "",
        })

    # 按 label 优先级 + name 排序
    nodes.sort(key=lambda n: (_LABEL_PRIORITY.get(n["label"], 999), n["name"]))
    return nodes


def _iterative_compress(nodes: list[dict]) -> tuple[str, str]:
    """迭代压缩：累积节点描述，超过阈值时调用 LLM 压缩。

    返回 (accumulated_text, remaining_batch_text)。
    """
    from service.services.llm_client import chat_completion

    accumulated = ""
    batch = ""

    for node in nodes:
        line = f"- {node['label']} {node['name']}: {node['description']}\n"
        batch += line

        if len(accumulated) + len(batch) > FEATURE_SUMMARY_CHAR_THRESHOLD:
            # 触发压缩
            accumulated = _llm_compress(chat_completion, accumulated, batch)
            batch = ""

    return accumulated, batch


def _llm_compress(chat_fn, accumulated: str, batch: str) -> str:
    """调用 LLM 将 accumulated + batch 压缩为结构化概要。"""
    content = ""
    if accumulated:
        content += f"【已有概要】\n{accumulated}\n\n"
    content += f"【新增模块描述】\n{batch}"

    result = chat_fn(
        prompt=(
            "以下是项目部分模块的功能描述，请提炼压缩为结构化概要，"
            "保留所有关键功能点，去除冗余细节，维持清晰的层级结构：\n\n"
            + content
        ),
        system_prompt="你是代码项目分析助手，擅长归纳总结代码模块功能。",
        max_tokens=2048,
    )
    return result


def _generate_final_summary(accumulated: str, remaining_batch: str, project_name: str) -> str:
    """将最终的 accumulated + 剩余 batch 交给 LLM 生成 Markdown 功能总结。"""
    from service.services.llm_client import chat_completion

    content = ""
    if accumulated:
        content += f"{accumulated}\n\n"
    if remaining_batch:
        content += f"【补充模块描述】\n{remaining_batch}"

    if not content.strip():
        return f"# {project_name}\n\n暂无功能描述。"

    result = chat_completion(
        prompt=(
            f"以下是项目「{project_name}」各模块功能的概要描述。"
            "请基于这些信息生成一份完整的项目功能总结，使用 Markdown 格式，"
            "包含项目概述和主要功能模块介绍。\n\n"
            + content
        ),
        system_prompt=(
            "你是代码项目分析助手。请生成结构清晰、内容精炼的 Markdown 项目功能总结。"
            "重点描述项目的核心功能、模块划分和技术架构。不要编造信息，只基于提供的描述进行总结。"
        ),
        max_tokens=2048,
    )
    return result
