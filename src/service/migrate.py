"""Database initialization entrypoint for local/API startup."""

from __future__ import annotations

import logging
from pathlib import Path

import psycopg2

from service.dependencies import get_database_url

logger = logging.getLogger(__name__)

_INIT_SQL_PATHS = [
    Path("/app/docker/init.sql"),
    Path(__file__).resolve().parent.parent.parent / "docker" / "init.sql",
]
_INIT_LOCK_ID = 80430001


def _is_initialized(cur) -> bool:
    cur.execute(
        """
        SELECT to_regclass('public.branch_graphs') IS NOT NULL
           AND to_regclass('public.graph_refresh_runs') IS NOT NULL
           AND EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'doc_code_links'
                  AND column_name = 'code_locator_json'
           )
        """
    )
    return bool(cur.fetchone()[0])


def run_migrations() -> None:
    """Initialize the database from the single consolidated SQL file."""
    init_sql_path = next((path for path in _INIT_SQL_PATHS if path.is_file()), None)
    if init_sql_path is None:
        logger.warning("database init SQL not found")
        return

    try:
        conn = psycopg2.connect(get_database_url())
    except Exception as exc:
        logger.error("database initialization connection failed: %s", exc)
        return

    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (_INIT_LOCK_ID,))
            if _is_initialized(cur):
                _run_upgrade_sql(cur)
                conn.commit()
                logger.info("database initialization already applied; upgrade SQL checked")
                return
            cur.execute(init_sql_path.read_text(encoding="utf-8-sig"))
            _run_upgrade_sql(cur)
        conn.commit()
        logger.info("database initialization SQL applied: %s", init_sql_path)
    except Exception as exc:
        conn.rollback()
        logger.error("database initialization failed: %s", exc)
    finally:
        conn.close()


def _run_upgrade_sql(cur) -> None:
    """Apply additive metadata upgrades for databases initialized by older images."""
    cur.execute(
        """
        ALTER TABLE IF EXISTS doc_bindings
            ADD COLUMN IF NOT EXISTS product_version_id INTEGER REFERENCES product_versions(id) ON DELETE CASCADE,
            ADD COLUMN IF NOT EXISTS git_source_key TEXT NOT NULL DEFAULT '';
        ALTER TABLE IF EXISTS doc_bindings
            ALTER COLUMN product_version_id SET NOT NULL;

        ALTER TABLE IF EXISTS documents
            ADD COLUMN IF NOT EXISTS product_version_id INTEGER REFERENCES product_versions(id) ON DELETE CASCADE,
            ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS body_text TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64),
            ADD COLUMN IF NOT EXISTS graph_status VARCHAR(32) NOT NULL DEFAULT 'pending',
            ADD COLUMN IF NOT EXISTS chunk_status VARCHAR(32) NOT NULL DEFAULT 'pending',
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

        UPDATE documents AS d
           SET product_version_id = db.product_version_id
          FROM doc_bindings AS db
         WHERE d.doc_binding_id = db.id
           AND d.product_version_id IS DISTINCT FROM db.product_version_id;

        CREATE INDEX IF NOT EXISTS idx_doc_bindings_product_id
            ON doc_bindings(product_id);

        CREATE UNIQUE INDEX IF NOT EXISTS uq_products_name
            ON products(name);

        CREATE UNIQUE INDEX IF NOT EXISTS uq_projects_name
            ON projects(name);

        CREATE UNIQUE INDEX IF NOT EXISTS uq_product_versions_product_name
            ON product_versions(product_id, version_name);

        DROP INDEX IF EXISTS uq_pvb_project_branch;

        CREATE INDEX IF NOT EXISTS idx_product_version_branches_project_branch
            ON product_version_branches(project_id, branch_name);

        DROP INDEX IF EXISTS uq_doc_bindings_active_product;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_bindings_active_version
            ON doc_bindings(product_version_id)
            WHERE is_active = true;

        UPDATE doc_bindings
           SET git_source_key = COALESCE(
                NULLIF(
                    CASE
                        WHEN btrim(repo_url) <> '' THEN
                            regexp_replace(
                                regexp_replace(
                                    regexp_replace(
                                        lower(split_part(btrim(repo_url), '://', 1)) || '://' ||
                                        lower(split_part(split_part(btrim(repo_url), '://', 2), '/', 1)) ||
                                        CASE
                                            WHEN position('/' in split_part(btrim(repo_url), '://', 2)) > 0
                                            THEN substring(
                                                split_part(btrim(repo_url), '://', 2)
                                                FROM position('/' in split_part(btrim(repo_url), '://', 2))
                                            )
                                            ELSE ''
                                        END,
                                        '\\.git$',
                                        '',
                                        'i'
                                    ),
                                    '/+$',
                                    ''
                                ),
                               '\\\\',
                               '/',
                               'g'
                            ),
                        ELSE ''
                    END,
                   ''
               ),
               NULLIF(
                   regexp_replace(
                       regexp_replace(
                           regexp_replace(btrim(replace(repo_path, '\\', '/')), '\\.git$', '', 'i'),
                           '/+$',
                           ''
                       ),
                       '\\\\',
                       '/',
                       'g'
                   ),
                   ''
               ),
               ''
           )
         WHERE git_source_key = '';

        DROP INDEX IF EXISTS uq_doc_bindings_active_repo_url_source;
        DROP INDEX IF EXISTS uq_doc_bindings_active_repo_path_source;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_bindings_active_git_source_key
            ON doc_bindings(git_source_key, default_branch)
            WHERE is_active = true
              AND git_source_key <> '';

        DROP INDEX IF EXISTS uq_documents_doc_id;
        DROP INDEX IF EXISTS uq_documents_doc_version;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_doc_version
            ON documents(doc_id, product_version_id);

        CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_doc_id_legacy
            ON documents(doc_id)
            WHERE product_version_id IS NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_binding_path
            ON documents(doc_binding_id, relative_path);

        CREATE INDEX IF NOT EXISTS idx_documents_binding_deleted
            ON documents(doc_binding_id, deleted_at);
        """
    )
