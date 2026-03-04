"""TDD tests for Phase 2: impact analysis PG schema (tables, constraints, insert chains)."""

import os
from datetime import datetime, timezone

import pytest


IMPACT_ANALYSIS_TABLES = [
    "projects",
    "versions",
    "requirements",
    "commits",
    "requirement_commits",
    "impact_analyses",
    "impact_analysis_commits",
]


def _get_test_repo_path():
    return os.environ.get("TEST_REPO_PATH", r"D:\PycharmProjects\codeAnalysis")


def _is_git_repo(path: str) -> bool:
    if not path or not os.path.isdir(path):
        return False
    return os.path.isdir(os.path.join(path, ".git"))


class TestTableExistence:
    """Step 2: Tables must exist after migration."""

    def test_all_seven_tables_exist(self, pg_conn):
        with pg_conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = ANY(%s)
                """,
                (IMPACT_ANALYSIS_TABLES,),
            )
            found = {row[0] for row in cur.fetchall()}
        missing = set(IMPACT_ANALYSIS_TABLES) - found
        assert not missing, f"Missing tables: {missing}"


class TestConstraintExistence:
    """Step 4: PK, unique and FK constraints must exist."""

    def test_versions_unique_project_branch(self, pg_conn):
        with pg_conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                WHERE t.relname = 'versions' AND c.contype = 'u'
                  AND pg_get_constraintdef(c.oid) LIKE '%%project_id%%' AND pg_get_constraintdef(c.oid) LIKE '%%branch%%'
                """
            )
            assert cur.fetchone() is not None, "versions(project_id, branch) unique constraint missing"

    def test_commits_unique_project_commit_sha(self, pg_conn):
        with pg_conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                WHERE t.relname = 'commits' AND c.contype = 'u'
                  AND pg_get_constraintdef(c.oid) LIKE '%%project_id%%' AND pg_get_constraintdef(c.oid) LIKE '%%commit_sha%%'
                """
            )
            assert cur.fetchone() is not None, "commits(project_id, commit_sha) unique constraint missing"

    def test_primary_keys_exist(self, pg_conn):
        tables_with_pk = ["projects", "versions", "requirements", "commits", "impact_analyses"]
        with pg_conn.cursor() as cur:
            for table in tables_with_pk:
                cur.execute(
                    """
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE table_schema = 'public' AND table_name = %s AND constraint_type = 'PRIMARY KEY'
                    """,
                    (table,),
                )
                assert cur.fetchone() is not None, f"PRIMARY KEY missing on {table}"

    def test_requirement_commits_primary_key(self, pg_conn):
        with pg_conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                WHERE t.relname = 'requirement_commits' AND c.contype = 'p'
                """
            )
            assert cur.fetchone() is not None, "requirement_commits PRIMARY KEY missing"

    def test_impact_analysis_commits_primary_key(self, pg_conn):
        with pg_conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                WHERE t.relname = 'impact_analysis_commits' AND c.contype = 'p'
                """
            )
            assert cur.fetchone() is not None, "impact_analysis_commits PRIMARY KEY missing"

    def test_foreign_keys_exist(self, pg_conn):
        # versions -> projects, commits -> projects + versions, etc.
        with pg_conn.cursor() as cur:
            cur.execute(
                """
                SELECT tc.table_name, kcu.column_name, ccu.table_name AS ref_table
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
                WHERE tc.table_schema = 'public' AND tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_name IN ('versions', 'requirements', 'commits', 'requirement_commits', 'impact_analyses', 'impact_analysis_commits')
                """
            )
            fks = {(r[0], r[1], r[2]) for r in cur.fetchall()}
        assert ("versions", "project_id", "projects") in fks
        assert ("commits", "project_id", "projects") in fks
        assert ("commits", "version_id", "versions") in fks
        assert ("impact_analyses", "project_id", "projects") in fks
        assert ("requirement_commits", "requirement_id", "requirements") in fks
        assert ("requirement_commits", "commit_id", "commits") in fks
        assert ("impact_analysis_commits", "impact_analysis_id", "impact_analyses") in fks
        assert ("impact_analysis_commits", "commit_id", "commits") in fks


class TestInsertChain:
    """Step 5: Insert project -> version -> commit, requirement_commits, impact_analysis + impact_analysis_commits."""

    @pytest.fixture
    def repo_path_for_insert(self, test_repo_path):
        path = test_repo_path
        if not _is_git_repo(path):
            pytest.skip("codeAnalysis repo not available (set TEST_REPO_PATH or use D:\\PycharmProjects\\codeAnalysis)")
        return path

    def test_insert_project_version_commit_chain(self, pg_conn, repo_path_for_insert):
        with pg_conn.cursor() as cur:
            pg_conn.rollback()
            cur.execute(
                """
                INSERT INTO projects (name, repo_path, created_at)
                VALUES (%s, %s, %s) RETURNING id
                """,
                ("test-project", repo_path_for_insert, datetime.now(timezone.utc)),
            )
            (project_id,) = cur.fetchone()
            cur.execute(
                """
                INSERT INTO versions (project_id, branch, created_at)
                VALUES (%s, %s, %s) RETURNING id
                """,
                (project_id, "main", datetime.now(timezone.utc)),
            )
            (version_id,) = cur.fetchone()
            commit_sha = "a" * 40
            cur.execute(
                """
                INSERT INTO commits (project_id, version_id, commit_sha, message, author, committed_at)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (project_id, version_id, commit_sha, "msg", "author", datetime.now(timezone.utc)),
            )
            (commit_id,) = cur.fetchone()
        pg_conn.rollback()
        assert project_id and version_id and commit_id

    def test_insert_requirement_and_requirement_commits(self, pg_conn, repo_path_for_insert):
        with pg_conn.cursor() as cur:
            pg_conn.rollback()
            cur.execute(
                "INSERT INTO projects (name, repo_path, created_at) VALUES (%s, %s, %s) RETURNING id",
                ("req-project", repo_path_for_insert, datetime.now(timezone.utc)),
            )
            (project_id,) = cur.fetchone()
            cur.execute(
                "INSERT INTO versions (project_id, branch, created_at) VALUES (%s, %s, %s) RETURNING id",
                (project_id, "main", datetime.now(timezone.utc)),
            )
            (version_id,) = cur.fetchone()
            cur.execute(
                """
                INSERT INTO commits (project_id, version_id, commit_sha, message, author, committed_at)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (project_id, version_id, "b" * 40, "m", "a", datetime.now(timezone.utc)),
            )
            (commit_id,) = cur.fetchone()
            cur.execute(
                "INSERT INTO requirements (project_id, title, created_at) VALUES (%s, %s, %s) RETURNING id",
                (project_id, "Req 1", datetime.now(timezone.utc)),
            )
            (requirement_id,) = cur.fetchone()
            cur.execute(
                "INSERT INTO requirement_commits (requirement_id, commit_id) VALUES (%s, %s)",
                (requirement_id, commit_id),
            )
        pg_conn.rollback()

    def test_insert_impact_analysis_and_commits(self, pg_conn, repo_path_for_insert):
        with pg_conn.cursor() as cur:
            pg_conn.rollback()
            cur.execute(
                "INSERT INTO projects (name, repo_path, created_at) VALUES (%s, %s, %s) RETURNING id",
                ("ia-project", repo_path_for_insert, datetime.now(timezone.utc)),
            )
            (project_id,) = cur.fetchone()
            cur.execute(
                "INSERT INTO versions (project_id, branch, created_at) VALUES (%s, %s, %s) RETURNING id",
                (project_id, "main", datetime.now(timezone.utc)),
            )
            (version_id,) = cur.fetchone()
            cur.execute(
                """
                INSERT INTO commits (project_id, version_id, commit_sha, message, author, committed_at)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (project_id, version_id, "c" * 40, "m", "a", datetime.now(timezone.utc)),
            )
            (commit_id,) = cur.fetchone()
            cur.execute(
                """
                INSERT INTO impact_analyses (project_id, status, triggered_at)
                VALUES (%s, %s, %s) RETURNING id
                """,
                (project_id, "completed", datetime.now(timezone.utc)),
            )
            (analysis_id,) = cur.fetchone()
            cur.execute(
                "INSERT INTO impact_analysis_commits (impact_analysis_id, commit_id) VALUES (%s, %s)",
                (analysis_id, commit_id),
            )
        pg_conn.rollback()


class TestConstraintFailure:
    """Step 6: Constraint violations must raise."""

    def test_duplicate_project_branch_fails(self, pg_conn):
        with pg_conn.cursor() as cur:
            pg_conn.rollback()
            cur.execute(
                "INSERT INTO projects (name, repo_path, created_at) VALUES (%s, %s, %s) RETURNING id",
                ("dup-proj", "/tmp/repo", datetime.now(timezone.utc)),
            )
            (project_id,) = cur.fetchone()
            cur.execute(
                "INSERT INTO versions (project_id, branch, created_at) VALUES (%s, %s, %s)",
                (project_id, "main", datetime.now(timezone.utc)),
            )
            with pytest.raises(Exception):
                cur.execute(
                    "INSERT INTO versions (project_id, branch, created_at) VALUES (%s, %s, %s)",
                    (project_id, "main", datetime.now(timezone.utc)),
                )
                pg_conn.commit()
        pg_conn.rollback()

    def test_version_invalid_project_id_fails(self, pg_conn):
        with pg_conn.cursor() as cur:
            pg_conn.rollback()
            with pytest.raises(Exception):
                cur.execute(
                    "INSERT INTO versions (project_id, branch, created_at) VALUES (%s, %s, %s)",
                    (999999, "x", datetime.now(timezone.utc)),
                )
                pg_conn.commit()
        pg_conn.rollback()
