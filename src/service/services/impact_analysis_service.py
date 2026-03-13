"""影响面分析服务：完整流水线 — git diff + Neo4j 影响链 + LLM 报告生成。"""

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from service.repositories import commit_repository as commit_repo
from service.repositories import impact_analysis_repository as impact_repo
from service.repositories import project_repository as project_repo

logger = logging.getLogger(__name__)


# ── 查询类 ──

def list_analyses(conn, project_id: int) -> list[dict] | None:
    if project_repo.find_by_id(conn, project_id) is None:
        return None
    return impact_repo.list_by_project_id(conn, project_id)


def get_analysis(conn, project_id: int, analysis_id: int) -> dict | None:
    if project_repo.find_by_id(conn, project_id) is None:
        return None
    row = impact_repo.find_by_id(conn, analysis_id)
    if row is None or row.get("project_id") != project_id:
        return None
    row["commit_ids"] = impact_repo.get_commit_ids(conn, analysis_id)
    return row


def list_by_product(conn, product_id: int) -> list[dict]:
    return impact_repo.list_by_product(conn, product_id)


# ── 内部工具函数 ──

def _resolve_repo_path(project: dict) -> str | None:
    repo_path = (project.get("repo_path") or "").strip()
    if not repo_path:
        return None
    p = Path(repo_path)
    if not p.is_dir():
        clone_base = os.environ.get("REPO_CLONE_BASE", "")
        if clone_base:
            alt = Path(clone_base) / str(project["id"])
            if alt.is_dir():
                return str(alt)
        return None
    return repo_path


def _extract_commits_data(repo_path: str, commits: list[dict]) -> list[dict]:
    """并行 git show/diff 提取提交数据。"""
    from service.git_ops import show_commit, diff_commit

    def _get_one(c: dict) -> dict:
        sha = c["commit_sha"]
        stat = show_commit(repo_path, sha, stat_only=True) or ""
        diff = diff_commit(repo_path, sha) or ""
        # 截断过长 diff
        if len(diff) > 12000:
            diff = diff[:12000] + "\n... (diff truncated)"
        # 解析变更文件列表
        changed_files = []
        for line in stat.splitlines():
            line = line.strip()
            if "|" in line:
                fname = line.split("|")[0].strip()
                if fname:
                    changed_files.append(fname)
        return {
            "sha": sha,
            "message": c.get("message") or "",
            "author": c.get("author") or "",
            "committed_at": c.get("committed_at") or "",
            "stat": stat,
            "diff": diff,
            "changed_files": changed_files,
        }

    logger.info("[影响面分析] 开始提取 %d 个提交的 git diff 数据, repo=%s", len(commits), repo_path)
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(_get_one, c): c for c in commits}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:
                logger.warning("[影响面分析] 提取提交数据失败: %s", exc)
    logger.info("[影响面分析] git diff 提取完成, 成功 %d/%d", len(results), len(commits))
    return results


def _query_impact_chains(project: dict, project_id: int, files: list[str], branch: str | None) -> str:
    """Neo4j 3跳影响链查询，失败时 graceful fallback。"""
    from service.services.ai_preprocessor_service import _load_neo4j_config

    logger.info("[影响面分析] Neo4j 影响链查询开始, project_id=%d, files=%d, branch=%s", project_id, len(files), branch)
    neo4j_config, database = _load_neo4j_config(project)
    if not neo4j_config or not neo4j_config.get("neo4j_uri"):
        logger.info("[影响面分析] Neo4j 未配置，跳过影响链")
        return "(Neo4j 未配置，跳过影响链分析)"

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            neo4j_config["neo4j_uri"],
            auth=(neo4j_config.get("neo4j_user") or "neo4j",
                  neo4j_config.get("neo4j_password") or ""),
        )
    except Exception as exc:
        return f"(Neo4j 连接失败: {exc})"

    try:
        depth = 3
        params: dict = {"pid": project_id, "depth": depth}
        if branch:
            params["branch"] = branch

        branch_clause = "AND n.branch = $branch" if branch else ""

        # 按文件名匹配起始节点
        file_names = [Path(f).stem for f in files[:20]]
        if not file_names:
            return "(无变更文件，跳过影响链)"
        params["names"] = file_names

        q = (
            f"MATCH (n) WHERE n.project_id = $pid {branch_clause} "
            f"AND n.name IN $names "
            f"OPTIONAL MATCH (affected)-[:CALLS|IMPORTS*1..{depth}]->(n) "
            f"RETURN n.id AS source_id, n.name AS source_name, labels(n)[0] AS source_label, "
            f"collect(DISTINCT {{id: affected.id, name: affected.name, label: labels(affected)[0]}}) AS affected_nodes "
            f"LIMIT 200"
        )

        lines = []
        with driver.session(database=database) as session:
            result = session.run(q, params)
            for record in result:
                src = f"{record['source_label']}:{record['source_name']}"
                affected = [a for a in record["affected_nodes"] if a.get("id")]
                if affected:
                    for a in affected:
                        lines.append(f"  {src} → {a['label']}:{a['name']}")
                else:
                    lines.append(f"  {src} (无外部调用方)")

        driver.close()
        logger.info("[影响面分析] Neo4j 影响链查询完成, 结果行数=%d", len(lines))
        if not lines:
            return "(未找到影响链路)"
        return "影响链路:\n" + "\n".join(lines)
    except Exception as exc:
        try:
            driver.close()
        except Exception:
            pass
        return f"(Neo4j 查询失败: {exc})"


def _query_requirements(conn, commit_ids: list[int]) -> list[dict]:
    """查询关联的产品需求。"""
    if not commit_ids:
        return []
    try:
        from psycopg2.extras import RealDictCursor
        placeholders = ",".join(["%s"] * len(commit_ids))
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""SELECT DISTINCT pr.id, pr.title, pr.level, pr.status
                    FROM product_requirement_commits prc
                    JOIN product_requirements pr ON pr.id = prc.requirement_id
                    WHERE prc.commit_id IN ({placeholders})""",
                tuple(commit_ids),
            )
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return []


_SYSTEM_PROMPT = """你是一位资深软件工程师，擅长代码变更影响面分析。
请根据提供的 git 提交数据、影响链路和需求关联信息，生成一份详尽的中文 Markdown 影响面分析报告。

输出格式要求：
第一行必须是 TITLE: [模块/功能] 变更概述（不超过30字）
第二行必须是 ---
之后是报告正文。

报告结构要求：
1. 概述 — 用 mermaid pie 图展示作者占比和文件类型分布
2. 变更摘要 — 模块聚合表格 + mermaid gitGraph
3. 变更详情 — 关键 diff 代码块 + 文件统计表
4. 影响链路 — mermaid flowchart 拓扑图 + 分层表格 + pie 图（节点类型占比）
5. 风险评估 — 风险等级 + mermaid flowchart 高风险路径
6. 需求关联 — 覆盖表格
7. 测试建议 — 用例表格（场景|目标|关联变更|优先级）+ mermaid flowchart 测试路径

要求至少包含 4 个 mermaid 图表。使用 ```mermaid 代码块。
报告应全面、专业、可操作。"""


def _generate_report(commits_data: list[dict], impact_text: str, requirements: list[dict]) -> tuple[str, str]:
    """调用 LLM 生成报告，返回 (title, markdown)。"""
    from service.services.llm_client import chat_completion

    # 构建 prompt
    parts = []
    parts.append(f"## 提交信息（共 {len(commits_data)} 个）\n")
    for cd in commits_data:
        parts.append(f"### {cd['sha'][:7]} — {cd['message']}")
        parts.append(f"作者: {cd['author']}  时间: {cd['committed_at']}")
        if cd["changed_files"]:
            parts.append(f"变更文件: {', '.join(cd['changed_files'])}")
        if cd["stat"]:
            parts.append(f"```\n{cd['stat'][:2000]}\n```")
        if cd["diff"]:
            parts.append(f"```diff\n{cd['diff'][:4000]}\n```")
        parts.append("")

    parts.append(f"## 影响链路\n{impact_text}\n")

    if requirements:
        parts.append("## 关联需求")
        for r in requirements:
            parts.append(f"- [{r['level']}] {r['title']} ({r['status']})")
        parts.append("")

    prompt = "\n".join(parts)
    # 截断过长 prompt
    if len(prompt) > 28000:
        prompt = prompt[:28000] + "\n... (内容过长已截断)"

    logger.info("[影响面分析] 调用 LLM 生成报告, prompt长度=%d", len(prompt))
    raw = chat_completion(prompt, system_prompt=_SYSTEM_PROMPT, max_tokens=8192)
    logger.info("[影响面分析] LLM 返回完成, 响应长度=%d", len(raw))

    # 解析 title
    title = "影响面分析报告"
    md = raw
    if raw.startswith("TITLE:"):
        lines = raw.split("\n", 2)
        title = lines[0].replace("TITLE:", "").strip()[:100]
        if len(lines) > 2:
            md = lines[2] if lines[1].strip() == "---" else "\n".join(lines[1:])
        elif len(lines) > 1:
            md = lines[1]

    return title, md


# ── 后台流水线 ──

def _run_pipeline(analysis_id: int, project: dict, project_id: int, commits: list[dict], commit_ids: list[int], version_id: int | None):
    """在后台线程中执行完整流水线，使用独立数据库连接。"""
    from service.dependencies import get_database_url
    import psycopg2

    conn = psycopg2.connect(get_database_url())
    conn.autocommit = False
    try:
        t_start = time.time()
        logger.info("[影响面分析] ===== 流水线启动 analysis_id=%d, commits=%d =====", analysis_id, len(commits))

        # Step 1: git diff
        t1 = time.time()
        logger.info("[影响面分析] [%d] Step 1/4 开始: 提取 git diff 数据", analysis_id)
        repo_path = _resolve_repo_path(project)
        commits_data = []
        if repo_path:
            logger.info("[影响面分析] [%d] 仓库路径: %s", analysis_id, repo_path)
            commits_data = _extract_commits_data(repo_path, commits)
        else:
            logger.warning("[影响面分析] [%d] 仓库路径无效，使用基础提交信息", analysis_id)
        if not commits_data:
            commits_data = [{
                "sha": c["commit_sha"], "message": c.get("message") or "",
                "author": c.get("author") or "", "committed_at": c.get("committed_at") or "",
                "stat": "", "diff": "", "changed_files": [],
            } for c in commits]
        all_files = list(set(f for cd in commits_data for f in (cd.get("changed_files") or [])))
        logger.info("[影响面分析] [%d] Step 1/4 完成: %d 个提交, %d 个变更文件 (%.1fs)",
                    analysis_id, len(commits_data), len(all_files), time.time() - t1)

        # Step 2: Neo4j 影响链
        t2 = time.time()
        logger.info("[影响面分析] [%d] Step 2/4 开始: 查询 Neo4j 影响链", analysis_id)
        branch = None
        if version_id:
            from service.repositories import version_repository as version_repo
            ver = version_repo.find_by_id(conn, version_id)
            if ver:
                branch = ver.get("branch")
        impact_text = _query_impact_chains(project, project_id, all_files, branch)
        logger.info("[影响面分析] [%d] Step 2/4 完成: 影响链 %d 字符 (%.1fs)",
                    analysis_id, len(impact_text), time.time() - t2)

        # Step 3: 需求关联
        t3 = time.time()
        logger.info("[影响面分析] [%d] Step 3/4 开始: 查询需求关联", analysis_id)
        requirements = _query_requirements(conn, commit_ids)
        logger.info("[影响面分析] [%d] Step 3/4 完成: 关联需求 %d 条 (%.1fs)",
                    analysis_id, len(requirements), time.time() - t3)

        # Step 4: LLM 报告
        t4 = time.time()
        logger.info("[影响面分析] [%d] Step 4/4 开始: LLM 生成报告", analysis_id)
        title, md = _generate_report(commits_data, impact_text, requirements)
        logger.info("[影响面分析] [%d] Step 4/4 完成: title=%s, 报告 %d 字符 (%.1fs)",
                    analysis_id, title, len(md), time.time() - t4)

        impact_repo.update_result(conn, analysis_id, "done", title=title, result_summary=md)
        conn.commit()
        logger.info("[影响面分析] ===== 流水线完成 analysis_id=%d, 总耗时 %.1fs =====",
                    analysis_id, time.time() - t_start)

    except Exception as exc:
        logger.exception("[影响面分析] 流水线失败 analysis_id=%d", analysis_id)
        try:
            conn.rollback()
            impact_repo.update_result(conn, analysis_id, "failed", title=None, result_summary=str(exc))
            conn.commit()
        except Exception:
            pass
    finally:
        conn.close()


# ── 主入口 ──

def create_analysis(
    conn, project_id: int, commit_ids: list[int], status: str = "pending"
) -> tuple[dict | None, str | None]:
    """创建影响面分析记录并启动后台流水线。立即返回 running 状态。"""
    project = project_repo.find_by_id(conn, project_id)
    if project is None:
        return None, "not_found"
    if not commit_ids:
        return None, "empty_commits"

    commits = []
    for cid in commit_ids:
        c = commit_repo.find_by_id(conn, cid)
        if c is None or c.get("project_id") != project_id:
            return None, "invalid_commits"
        commits.append(c)

    version_id = None
    for c in commits:
        if c.get("version_id"):
            version_id = c["version_id"]
            break

    row = impact_repo.create(conn, project_id, "running", version_id=version_id)
    impact_repo.add_commits(conn, row["id"], commit_ids)
    conn.commit()
    logger.info("[影响面分析] 记录已创建 analysis_id=%d, 启动后台流水线", row["id"])

    # 后台线程执行流水线
    t = threading.Thread(
        target=_run_pipeline,
        args=(row["id"], project, project_id, commits, commit_ids, version_id),
        daemon=True,
    )
    t.start()

    row["commit_ids"] = commit_ids
    return row, None
