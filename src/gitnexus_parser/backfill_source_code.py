"""Backfill sourceCode for existing Neo4j nodes using local repo files.

用法示例（在 NeoDev 容器内执行）：

  python -m gitnexus_parser.backfill_source_code \\
    --repo-path /workspace/repo \\
    --project-id 1 \\
    --branch main

依赖环境变量（可选，沿用解析管线配置）：
  NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

from gitnexus_parser.config import load_config
from gitnexus_parser.ingestion.parser import should_store_source

logger = logging.getLogger(__name__)


def _safe_label(label: str) -> str:
    """Very small whitelist: 仅允许字母组成的 label，避免 Cypher 注入。"""
    value = "".join(ch for ch in (label or "") if ch.isalpha())
    if not value:
        raise ValueError(f"Invalid label for Cypher: {label!r}")
    return value


def _load_nodes_without_source(
    driver,
    *,
    project_id: int,
    branch: str,
    database: str | None,
    batch_size: int,
) -> list[dict[str, Any]]:
    """从 Neo4j 批量拉取缺失 sourceCode 的节点。"""
    with driver.session(database=database) as session:
        q = """
        MATCH (n)
        WHERE n.project_id = $project_id
          AND n.branch = $branch
          AND n.filePath IS NOT NULL
          AND n.startLine IS NOT NULL
          AND n.endLine IS NOT NULL
          AND (n.sourceCode IS NULL OR n.sourceCode = "")
        RETURN n.id AS id,
               labels(n)[0] AS label,
               n.name AS name,
               n.filePath AS filePath,
               n.startLine AS startLine,
               n.endLine AS endLine,
               n.language AS language
        LIMIT $limit
        """
        result = session.run(
            q,
            project_id=project_id,
            branch=branch,
            limit=batch_size,
        )
        return [dict(r) for r in result]


def _read_source_snippet(
    repo_root: Path,
    file_path: str,
    start_line: int,
    end_line: int,
    *,
    context: int = 20,
) -> str | None:
    """根据起止行号，从文件中截取一段源码片段（前后各带少量上下文）。"""
    full_path = (repo_root / file_path).resolve()
    try:
        text = full_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("无法读取文件 %s: %s", full_path, exc)
        return None

    lines = text.splitlines()
    if not lines:
        return ""
    start_idx = max(0, start_line - 1 - context)
    end_idx = min(len(lines), end_line + context)
    snippet = "\n".join(lines[start_idx:end_idx])
    return snippet


def _update_node_source(
    driver,
    *,
    node_id: str,
    label: str,
    branch: str,
    project_id: int,
    source_code: str,
    database: str | None,
) -> None:
    """更新单个节点的 sourceCode 字段。"""
    safe = _safe_label(label)
    with driver.session(database=database) as session:
        q = f"""
        MATCH (n:{safe} {{id: $id, branch: $branch, project_id: $project_id}})
        SET n.sourceCode = $sourceCode
        """
        session.run(
            q,
            id=node_id,
            branch=branch,
            project_id=project_id,
            sourceCode=source_code,
        )


def backfill_source_code(
    repo_path: str,
    *,
    project_id: int,
    branch: str,
    batch_size: int = 500,
) -> None:
    """主入口：为现有图中节点按策略补全 sourceCode。"""
    repo_root = Path(repo_path).resolve()
    if not repo_root.is_dir():
        raise ValueError(f"repo_path 不存在或不是目录: {repo_root}")

    cfg = load_config(None)
    uri = cfg.get("neo4j_uri") or os.environ.get("NEO4J_URI") or "bolt://localhost:7687"
    user = cfg.get("neo4j_user") or os.environ.get("NEO4J_USER") or "neo4j"
    password = cfg.get("neo4j_password") or os.environ.get("NEO4J_PASSWORD") or ""
    database = cfg.get("neo4j_database") or os.environ.get("NEO4J_DATABASE")

    logger.info(
        "开始补全 sourceCode：repo=%s project_id=%s branch=%s uri=%s db=%s",
        repo_root,
        project_id,
        branch,
        uri,
        database or "(default)",
    )

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        total_updated = 0
        total_skipped = 0
        while True:
            nodes = _load_nodes_without_source(
                driver,
                project_id=project_id,
                branch=branch,
                database=database,
                batch_size=batch_size,
            )
            if not nodes:
                break

            logger.info("本批待处理节点数：%d", len(nodes))
            for node in nodes:
                node_id = str(node.get("id") or "")
                label = str(node.get("label") or "")
                name = str(node.get("name") or "")
                file_path = str(node.get("filePath") or "")
                language = str(node.get("language") or "")
                start_line = int(node.get("startLine") or 0)
                end_line = int(node.get("endLine") or 0)

                if not node_id or not label or not file_path or start_line <= 0 or end_line <= 0:
                    total_skipped += 1
                    continue

                # 按策略判断是否需要存源码
                try:
                    if not should_store_source(language, label, file_path=file_path, name=name):
                        total_skipped += 1
                        continue
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "should_store_source 失败，跳过节点 %s (%s): %s",
                        node_id,
                        label,
                        exc,
                    )
                    total_skipped += 1
                    continue

                snippet = _read_source_snippet(
                    repo_root,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                )
                if snippet is None:
                    total_skipped += 1
                    continue
                snippet = snippet.strip()
                if not snippet:
                    total_skipped += 1
                    continue

                try:
                    _update_node_source(
                        driver,
                        node_id=node_id,
                        label=label,
                        branch=branch,
                        project_id=project_id,
                        source_code=snippet,
                        database=database,
                    )
                    total_updated += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "更新节点 %s (%s) sourceCode 失败: %s",
                        node_id,
                        label,
                        exc,
                    )
                    total_skipped += 1

        logger.info(
            "补全 sourceCode 完成：更新 %d 个节点，跳过 %d 个节点",
            total_updated,
            total_skipped,
        )
    finally:
        driver.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill sourceCode for existing Neo4j nodes.")
    parser.add_argument(
        "--repo-path",
        required=True,
        help="源码所在仓库根目录（容器内路径，例如 /workspace/repo）",
    )
    parser.add_argument(
        "--project-id",
        type=int,
        required=True,
        help="Neo4j 中的 project_id",
    )
    parser.add_argument(
        "--branch",
        required=True,
        help="Neo4j 中的 branch 名称（如 main）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="每批从 Neo4j 拉取的最大节点数（默认 500）",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    backfill_source_code(
        repo_path=args.repo_path,
        project_id=args.project_id,
        branch=args.branch,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()

