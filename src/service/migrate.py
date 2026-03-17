"""API 启动时自动执行数据库迁移（幂等）。"""

import logging
from pathlib import Path

import psycopg2

from service.dependencies import get_database_url

logger = logging.getLogger(__name__)

# 迁移目录：优先容器内 /app/docker/migrations，回退到源码相对路径
_MIGRATION_DIRS = [
    Path("/app/docker/migrations"),
    Path(__file__).resolve().parent.parent.parent / "docker" / "migrations",
]


def run_migrations() -> None:
    """连接数据库，按顺序执行所有 SQL 迁移文件（CREATE IF NOT EXISTS 保证幂等）。"""
    migration_dir = None
    for d in _MIGRATION_DIRS:
        if d.is_dir():
            migration_dir = d
            break
    if migration_dir is None:
        logger.warning("未找到迁移目录，跳过自动迁移")
        return

    sql_files = sorted(migration_dir.glob("*.sql"))
    if not sql_files:
        logger.info("迁移目录为空，跳过")
        return

    try:
        conn = psycopg2.connect(get_database_url())
    except Exception as e:
        logger.error("自动迁移：无法连接数据库: %s", e)
        return

    try:
        conn.autocommit = False
        conn.rollback()
        applied = 0
        for sql_path in sql_files:
            sql = sql_path.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                for stmt in sql.split(";"):
                    stmt = "\n".join(
                        line for line in stmt.splitlines()
                        if not line.strip().startswith("--")
                    ).strip()
                    if stmt:
                        try:
                            cur.execute(stmt)
                        except Exception as e:
                            # 跳过已存在等非致命错误，记录日志
                            conn.rollback()
                            logger.debug("迁移 %s 语句跳过: %s", sql_path.name, e)
                            break
                else:
                    applied += 1
            conn.commit()
        logger.info("自动迁移完成，处理 %d/%d 个文件", applied, len(sql_files))
    except Exception as e:
        conn.rollback()
        logger.error("自动迁移失败: %s", e)
    finally:
        conn.close()
