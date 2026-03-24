"""AI 预处理服务：单分支触发、并发控制与状态收尾。

流程：预检 LLM API → 自动同步代码到图数据库 → 校验节点存在 → 并行 AI 分析。
"""

import logging
from datetime import datetime, timezone
from typing import Any

from service.repositories import ai_preprocess_status_repository as status_repo
from service.repositories import project_repository as project_repo

logger = logging.getLogger(__name__)


class ProjectBusyError(Exception):
    """项目正在处理中，应返回 409。"""
    def __init__(self, detail: str = "项目正在处理中，请稍后重试", code: str = "PROJECT_BUSY"):
        self.detail = detail
        self.code = code


def _log_step(process_logs: list[dict[str, Any]], message: str) -> None:
    """追加一条过程日志（带时间戳），并同步打 server 日志。"""
    now = datetime.now(timezone.utc).isoformat()
    process_logs.append({"at": now, "message": message})
    logger.info("[AI 分析] %s", message)


def _load_neo4j_config(project: dict) -> tuple[dict | None, str | None]:
    """加载 Neo4j 配置，合并项目的 neo4j_database。返回 (config, database)。"""
    import os
    from pathlib import Path

    config = {}
    try:
        from gitnexus_parser import load_config
        config = load_config()
        if not config.get("neo4j_uri"):
            src_dir = Path(__file__).resolve().parent.parent.parent
            for path in [src_dir / "config.json", src_dir / "config.example.json"]:
                if path.is_file():
                    try:
                        config = load_config(path)
                        if config.get("neo4j_uri"):
                            break
                    except Exception:
                        pass
    except Exception:
        pass
    if not config.get("neo4j_uri"):
        return None, None
    db = (project.get("neo4j_database") or "").strip() or config.get("neo4j_database")
    return config, (db if db else None)


def _preflight_check_llm(process_logs: list[dict[str, Any]]) -> bool:
    """预检 LLM：校验 API Key 存在、chat/embedding 接口可用。返回 True 表示通过。"""
    from service.services.llm_client import get_llm_config, probe_chat, probe_embedding

    cfg = get_llm_config()
    if not cfg["api_key"]:
        _log_step(process_logs, "[预检] 未配置 OPENAI_API_KEY，跳过 LLM 分析")
        return False

    chat_ok, chat_detail = probe_chat()
    _log_step(process_logs, f"[预检] Chat API: {chat_detail}")
    if not chat_ok:
        return False

    emb_ok, emb_detail = probe_embedding()
    _log_step(process_logs, f"[预检] Embedding API: {emb_detail}")
    if not emb_ok:
        return False

    return True


def _ensure_graph_fresh(
    conn,
    project: dict,
    project_id: int,
    branch: str,
    process_logs: list[dict[str, Any]],
) -> tuple[bool, Any, str | None]:
    """确保图数据最新：找版本 → 同步代码/图 → 校验 Neo4j 有节点。

    返回 (通过, neo4j_driver | None, database)。
    调用方负责关闭 driver。
    """
    from service.repositories import version_repository as version_repo

    # ── 1. 找到该 branch 对应的 version 记录 ──
    versions = version_repo.list_by_project_id(conn, project_id)
    version = next((v for v in versions if (v.get("branch") or "").strip() == branch), None)
    if not version:
        _log_step(process_logs, f"[预检] 未找到 branch={branch} 的版本记录，请先创建版本")
        return False, None, None

    # ── 2. 触发 sync-commits（fetch + 增量/全量图解析 → Neo4j） ──
    from service.services.sync_service import sync_commits_for_version

    _log_step(process_logs, f"[预检] 同步代码到图数据库 (version_id={version['id']}, branch={branch})")
    # 心跳：更新 updated_at，防止 git fetch 超时误判
    status_repo.update_heartbeat(conn, project_id, branch)
    conn.commit()

    try:
        sync_result = sync_commits_for_version(conn, project_id, version["id"])
    except Exception as exc:  # noqa: BLE001
        _log_step(process_logs, f"[预检] 代码同步失败: {exc}")
        return False, None, None

    if sync_result is None:
        _log_step(process_logs, "[预检] 代码同步返回空（项目或版本异常）")
        return False, None, None

    graph_action = sync_result.get("graph_action") or "skipped"
    _log_step(
        process_logs,
        f"[预检] 同步完成: commits_synced={sync_result.get('commits_synced', 0)}, "
        f"graph_action={graph_action}",
    )
    for err in sync_result.get("graph_errors") or []:
        _log_step(process_logs, f"[预检] 图解析警告: {err}")

    # ── 3. 连接 Neo4j，校验节点是否存在 ──
    neo4j_config, database = _load_neo4j_config(project)
    if not neo4j_config or not neo4j_config.get("neo4j_uri"):
        _log_step(process_logs, "[预检] 未配置 Neo4j (NEO4J_URI)，跳过图读取")
        return False, None, None

    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        neo4j_config["neo4j_uri"],
        auth=(neo4j_config.get("neo4j_user") or "neo4j", neo4j_config.get("neo4j_password") or ""),
    )

    try:
        with driver.session(database=database) as session:
            result = session.run(
                "MATCH (n) WHERE n.branch = $branch AND n.project_id = $pid RETURN count(n) AS cnt",
                branch=branch, pid=project_id,
            )
            cnt = result.single()["cnt"]
    except Exception as exc:  # noqa: BLE001
        _log_step(process_logs, f"[预检] Neo4j 连接失败: {exc}")
        driver.close()
        return False, None, None

    # ── 4. 增量同步后无节点 → 清除 last_parsed_commit 强制全量重扫 ──
    if cnt == 0 and graph_action == "incremental":
        _log_step(process_logs, "[预检] 增量同步后无节点，回退为全量扫描")
        driver.close()
        version_repo.update_last_parsed_commit(conn, version["id"], None)
        conn.commit()
        try:
            sync_result2 = sync_commits_for_version(conn, project_id, version["id"])
        except Exception as exc:  # noqa: BLE001
            _log_step(process_logs, f"[预检] 全量扫描失败: {exc}")
            return False, None, None
        if sync_result2:
            action2 = sync_result2.get("graph_action") or "skipped"
            _log_step(process_logs, f"[预检] 全量扫描完成: graph_action={action2}")
            for err in sync_result2.get("graph_errors") or []:
                _log_step(process_logs, f"[预检] 图解析警告: {err}")

        driver = GraphDatabase.driver(
            neo4j_config["neo4j_uri"],
            auth=(neo4j_config.get("neo4j_user") or "neo4j", neo4j_config.get("neo4j_password") or ""),
        )
        try:
            with driver.session(database=database) as session:
                result = session.run(
                    "MATCH (n) WHERE n.branch = $branch AND n.project_id = $pid RETURN count(n) AS cnt",
                    branch=branch, pid=project_id,
                )
                cnt = result.single()["cnt"]
        except Exception as exc:  # noqa: BLE001
            _log_step(process_logs, f"[预检] Neo4j 连接失败: {exc}")
            driver.close()
            return False, None, None

    if cnt == 0:
        _log_step(
            process_logs,
            f"[预检] 全量扫描后 Neo4j 仍无 project_id={project_id}, branch={branch} 的代码节点，"
            "可能是空仓库或解析未产出节点",
        )
        driver.close()
        return False, None, None

    _log_step(process_logs, f"[预检] 图数据就绪 (节点数={cnt})")
    return True, driver, database


def _run_ai_preprocess(
    conn,
    project_id: int,
    branch: str,
    force: bool,
    process_logs: list[dict[str, Any]],
    project: dict,
) -> dict:
    """
    AI 分析：预检（LLM 可用 + 同步代码 + 图数据就绪）→ 分层并行生成描述 → 写回 Neo4j。
    过程步骤通过 process_logs 追加。
    """
    _log_step(process_logs, f"开始 AI 分析 (project_id={project_id}, branch={branch}, force={force})")

    # ── Step 1: LLM API 探活 ──
    if not _preflight_check_llm(process_logs):
        return {"saved": 0, "skipped": 0}

    # ── Step 2: 同步代码 + 图数据校验 ──
    graph_ok, driver, database = _ensure_graph_fresh(conn, project, project_id, branch, process_logs)
    if not graph_ok:
        return {"saved": 0, "skipped": 0}

    # ── Step 3: 执行 AI 分析 ──
    _log_step(process_logs, "预检通过，开始执行聚合描述生成")
    try:
        from service.services.ai_analysis_runner import run_ai_analysis
        from service.repositories import ai_preprocess_status_repository as status_repo

        def _on_progress(payload: dict) -> None:
            # payload: {stage, done, total, saved, skipped, failed, cache_hit}
            progress = {
                "stage": payload.get("stage"),
                "done": int(payload.get("done") or 0),
                "total": int(payload.get("total") or 0),
                "saved": int(payload.get("saved") or 0),
                "skipped": int(payload.get("skipped") or 0),
                "failed": int(payload.get("failed") or 0),
                "cache_hit": int(payload.get("cache_hit") or 0),
            }
            try:
                status_repo.update_progress(conn, project_id, branch, progress)
                conn.commit()
            except Exception:
                # 进度更新失败不影响主流程
                logger.warning(
                    "[AI 分析] 更新进度失败（忽略，不影响主流程）",
                    exc_info=True,
                )

        stats = run_ai_analysis(
            driver,
            project_id,
            branch,
            force,
            process_logs,
            database=database,
            on_progress=_on_progress,
            pg_conn=conn,
        )
        _log_step(
            process_logs,
            "完成："
            f"总节点 {stats.get('total', 0)}，"
            f"已更新 {stats.get('saved', 0)}，"
            f"缓存命中 {stats.get('cache_hit', 0)}，"
            f"向量化 {stats.get('embedded', 0)}，"
            f"跳过 {stats.get('skipped', 0)}，"
            f"失败 {stats.get('failed', 0)}",
        )
        return stats
    finally:
        driver.close()


def run_preprocess(conn, project_id: int, branch: str = "main", force: bool = False) -> dict:
    """
    执行 AI 预处理：校验项目存在、占位 running、执行 AI 分析（含过程日志）、收尾状态。
    成功返回 body dict；若项目不存在或项目忙则抛出 HTTPException（由 router 捕获）。
    过程日志写入 extra.logs，供 GET preprocess/status 返回。
    """
    from fastapi import HTTPException

    process_logs: list[dict[str, Any]] = []

    proj = project_repo.find_by_id(conn, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    _log_step(process_logs, "校验项目与并发状态")
    if status_repo.has_running(conn, project_id):
        raise ProjectBusyError()
    if not status_repo.set_running(conn, project_id, branch):
        raise ProjectBusyError()
    conn.commit()
    _log_step(process_logs, "已占位 running，开始执行分析")

    try:
        stats = _run_ai_preprocess(conn, project_id, branch, force, process_logs, proj)
        stats["logs"] = process_logs
        status_repo.set_completed(conn, project_id, branch, extra=stats)
        conn.commit()

        # 自动触发版本功能总结
        try:
            from service.services.version_feature_summary_service import trigger_for_project_branch
            trigger_for_project_branch(conn, project_id, branch)
        except Exception:
            logger.warning("[AI 分析] 触发版本功能总结失败（不影响主流程）", exc_info=True)

        return {
            "status": "completed",
            "project_id": project_id,
            "branch": branch,
            "message": "任务已完成",
            "extra": stats,
        }
    except (ProjectBusyError, HTTPException):
        raise
    except Exception as e:
        _log_step(process_logs, f"失败: {e}")
        logger.exception("AI preprocess failed for project_id=%s branch=%s", project_id, branch)
        conn.rollback()
        status_repo.set_failed(
            conn, project_id, branch, error_message=str(e), extra={"logs": process_logs}
        )
        conn.commit()
        raise
