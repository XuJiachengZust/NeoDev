# NeoDev CLI 与元数据基础实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 NeoDev 建立可自动化调用的根级 CLI 壳层，并补齐后续 DocChange / 危险提交闭环所需的最小元数据表与仓储能力。

**Architecture:** 采用 `argparse` 构建薄 CLI 分发层，`neodev.py` 只转发到 `service.cli.main`。数据库层沿用现有增量 SQL 迁移和 repository 直写 SQL 风格，先增加 `doc_bindings`、`documents`、`doc_changes`、`code_change_links`、`dangerous_commit_records`，暂不新增独立 `BranchAnalysisTask` 表。

**Tech Stack:** Python 3.11、argparse、psycopg2、PostgreSQL、pytest、FastAPI 现有依赖
**Data Policy:** 用户已确认 metadata 旧数据无需迁移，允许直接彻底删除。为达成最终 schema 形状所需的破坏性清理在本切片内是允许的，包括 `DROP COLUMN change_summary`。

---

## 文件结构与职责

- `neodev.py`
  根级命令入口，只负责把 CLI 调用转发到 `service.cli.main`。
- `src/service/cli/main.py`
  顶层参数解析、子命令注册、统一异常收口与退出码返回。
- `src/service/cli/output.py`
  统一成功 / 失败 JSON 结构和文本输出渲染。
- `src/service/cli/errors.py`
  CLI 领域错误类型、错误分类和退出码映射。
- `src/service/cli/commands/__init__.py`
  命令注册入口。
- `src/service/cli/commands/cli.py`
  `cli version-check` 命令实现。
- `src/service/repositories/doc_binding_repository.py`
  文档仓库绑定的 CRUD / 查询。
- `src/service/repositories/document_repository.py`
  文档元数据的 CRUD / 查询。
- `src/service/repositories/doc_change_repository.py`
  `DocChange` 记录的 CRUD / 查询。
- `src/service/repositories/code_change_link_repository.py`
  代码提交与 `DocChange` 关联事实的创建 / 查询。
- `src/service/repositories/dangerous_commit_repository.py`
  危险提交记录的创建、列表、关闭。
- `docker/migrations/018_cli_metadata_foundation.sql`
  本轮新增元数据表、索引与约束。
- `tests/conftest.py`
  测试数据库连接、迁移加载、CLI 命令运行辅助。
- `tests/test_cli_contract.py`
  CLI 结果契约、错误码、入口一致性测试。
- `tests/test_metadata_repositories.py`
  新增元数据 repository 的持久化测试。
- `tests/test_metadata_migration.py`
  新增表、索引和约束是否可被迁移创建的测试。

## 任务拆分

### Task 1: 建立 CLI 结果协议与错误映射基础

**Files:**
- Create: `src/service/cli/output.py`
- Create: `src/service/cli/errors.py`
- Create: `tests/test_cli_contract.py`

- [ ] **Step 1: 先写失败测试，固定结果协议和退出码语义**

```python
from service.cli.errors import CliError, error_to_exit_code
from service.cli.output import build_error_payload, build_success_payload


def test_build_success_payload_contains_required_fields():
    payload = build_success_payload(
        command="cli version-check",
        data={"cli_version": "dev"},
    )
    assert payload["ok"] is True
    assert payload["command"] == "cli version-check"
    assert "timestamp" in payload
    assert payload["data"]["cli_version"] == "dev"
    assert payload["errors"] == []


def test_build_error_payload_contains_error_category():
    err = CliError(
        category="invalid_argument",
        message="missing --json",
        details={"arg": "--json"},
    )
    payload = build_error_payload(command="cli version-check", error=err)
    assert payload["ok"] is False
    assert payload["command"] == "cli version-check"
    assert payload["data"] is None
    assert payload["errors"] == [
        {
            "category": "invalid_argument",
            "message": "missing --json",
            "details": {"arg": "--json"},
        }
    ]


def test_error_to_exit_code_is_stable():
    assert error_to_exit_code(CliError("invalid_argument", "bad")) == 2
    assert error_to_exit_code(CliError("not_found", "missing")) == 3
    assert error_to_exit_code(CliError("conflict", "busy")) == 4
    assert error_to_exit_code(CliError("not_ready", "later")) == 5
    assert error_to_exit_code(CliError("version_mismatch", "mismatch")) == 6
    assert error_to_exit_code(CliError("internal_error", "boom")) == 10
```

- [ ] **Step 2: 运行测试，确认当前实现缺失导致失败**

Run: `pytest tests/test_cli_contract.py -v`

Expected: FAIL，报错 `ModuleNotFoundError: No module named 'service.cli'` 或导入符号不存在。

- [ ] **Step 3: 用最小实现补齐 `output.py` 与 `errors.py`**

```python
# src/service/cli/errors.py
from dataclasses import dataclass, field


@dataclass(slots=True)
class CliError(Exception):
    category: str
    message: str
    details: dict | None = field(default=None)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "message": self.message,
            "details": self.details or {},
        }


_EXIT_CODES = {
    "invalid_argument": 2,
    "not_found": 3,
    "conflict": 4,
    "not_ready": 5,
    "version_mismatch": 6,
    "internal_error": 10,
}


def error_to_exit_code(error: CliError) -> int:
    return _EXIT_CODES.get(error.category, 10)
```

```python
# src/service/cli/output.py
from datetime import datetime, timezone

from service.cli.errors import CliError


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_success_payload(command: str, data: dict | None = None) -> dict:
    return {
        "ok": True,
        "command": command,
        "timestamp": _timestamp(),
        "data": data or {},
        "errors": [],
    }


def build_error_payload(command: str, error: CliError) -> dict:
    return {
        "ok": False,
        "command": command,
        "timestamp": _timestamp(),
        "data": None,
        "errors": [error.to_dict()],
    }
```

- [ ] **Step 4: 重新运行测试，确认协议层通过**

Run: `pytest tests/test_cli_contract.py -v`

Expected: PASS，3 个测试全部通过。

- [ ] **Step 5: 提交这一小步**

```bash
git add src/service/cli/output.py src/service/cli/errors.py tests/test_cli_contract.py
git commit -m "feat: add cli output contract foundation"
```

### Task 2: 接入 CLI 主入口、根级启动脚本与 `cli version-check`

**Files:**
- Create: `neodev.py`
- Create: `src/service/cli/main.py`
- Create: `src/service/cli/commands/__init__.py`
- Create: `src/service/cli/commands/cli.py`
- Modify: `tests/test_cli_contract.py`

- [ ] **Step 1: 先写失败测试，固定入口一致性和 `cli version-check` 输出**

```python
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_root_entrypoint_returns_version_check_json():
    proc = _run("neodev.py", "cli", "version-check", "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "cli version-check"
    assert payload["data"]["cli_version"]
    assert payload["data"]["compatible"] is True
    assert payload["data"]["update_available"] is False


def test_module_entrypoint_matches_root_entrypoint_shape():
    root_proc = _run("neodev.py", "cli", "version-check", "--json")
    mod_proc = _run("-m", "service.cli.main", "cli", "version-check", "--json")
    root_payload = json.loads(root_proc.stdout)
    mod_payload = json.loads(mod_proc.stdout)
    assert root_proc.returncode == 0
    assert mod_proc.returncode == 0
    assert root_payload["command"] == mod_payload["command"] == "cli version-check"
    assert root_payload["data"]["compatible"] == mod_payload["data"]["compatible"] is True
```

- [ ] **Step 2: 运行测试，确认入口尚未实现**

Run: `pytest tests/test_cli_contract.py -v`

Expected: FAIL，报错 `can't open file 'neodev.py'` 或 `No module named service.cli.main`。

- [ ] **Step 3: 编写最小 CLI 入口与 `cli version-check`**

```python
# neodev.py
from service.cli.main import main


if __name__ == "__main__":
    raise SystemExit(main())
```

```python
# src/service/cli/commands/cli.py
from service.cli.output import build_success_payload


def register(subparsers) -> None:
    cli_parser = subparsers.add_parser("cli")
    cli_subparsers = cli_parser.add_subparsers(dest="cli_command", required=True)

    version_parser = cli_subparsers.add_parser("version-check")
    version_parser.set_defaults(handler=handle_version_check, command_name="cli version-check")


def handle_version_check(args) -> dict:
    return build_success_payload(
        command=args.command_name,
        data={
            "cli_version": "dev",
            "plugin_version": None,
            "skill_version": None,
            "compatible": True,
            "update_available": False,
            "updated": False,
            "target_version": "dev",
            "message": "CLI 基础壳层已就绪，插件与 skill 版本联动待后续任务接入。",
        },
    )
```

```python
# src/service/cli/main.py
import argparse
import json

from service.cli.commands import register_commands
from service.cli.errors import CliError, error_to_exit_code
from service.cli.output import build_error_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="neodev")
    parser.add_argument("--json", action="store_true", dest="json_output")
    subparsers = parser.add_subparsers(dest="command_group", required=True)
    register_commands(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = args.handler(args)
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    except CliError as exc:
        payload = build_error_payload(getattr(args, "command_name", "unknown"), exc)
        print(json.dumps(payload, ensure_ascii=False))
        return error_to_exit_code(exc)
```

- [ ] **Step 4: 运行测试，确认两个入口一致通过**

Run: `pytest tests/test_cli_contract.py -v`

Expected: PASS，入口一致性与 `cli version-check` 输出测试通过。

- [ ] **Step 5: 提交这一小步**

```bash
git add neodev.py src/service/cli/main.py src/service/cli/commands/__init__.py src/service/cli/commands/cli.py tests/test_cli_contract.py
git commit -m "feat: add neodev cli entrypoint and version check"
```

### Task 3: 增加元数据迁移并验证表结构

**Files:**
- Create: `docker/migrations/018_cli_metadata_foundation.sql`
- Create: `tests/test_metadata_migration.py`

- [ ] **Step 1: 先写失败测试，固定新增表、唯一约束和索引存在**

```python
def test_cli_metadata_tables_exist(pg_conn):
    pg_conn.rollback()
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT to_regclass('public.doc_bindings'),
                   to_regclass('public.documents'),
                   to_regclass('public.doc_changes'),
                   to_regclass('public.code_change_links'),
                   to_regclass('public.dangerous_commit_records')
            """
        )
        row = cur.fetchone()
    assert row == (
        "doc_bindings",
        "documents",
        "doc_changes",
        "code_change_links",
        "dangerous_commit_records",
    )


def test_doc_changes_has_unique_doc_change_id(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'doc_changes'
            """
        )
        indexes = {name for (name,) in cur.fetchall()}
    assert any("doc_change_id" in name for name in indexes)
```

- [ ] **Step 2: 运行测试，确认迁移文件尚不存在导致失败**

Run: `pytest tests/test_metadata_migration.py -v`

Expected: FAIL，新增表不存在。

- [ ] **Step 3: 写增量迁移 SQL**

```sql
CREATE TABLE IF NOT EXISTS doc_bindings (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    repo_path       VARCHAR(512) NOT NULL,
    repo_url        VARCHAR(512),
    default_branch  VARCHAR(255),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_bindings_active_product
ON doc_bindings(product_id)
WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS documents (
    id                 SERIAL PRIMARY KEY,
    doc_binding_id     INTEGER NOT NULL REFERENCES doc_bindings(id) ON DELETE CASCADE,
    doc_id             VARCHAR(128) NOT NULL,
    doc_type           VARCHAR(64) NOT NULL,
    relative_path      VARCHAR(512) NOT NULL,
    title              VARCHAR(512),
    front_matter_json  JSONB NOT NULL DEFAULT '{}'::jsonb,
    relations_json     JSONB NOT NULL DEFAULT '[]'::jsonb,
    status             VARCHAR(64) NOT NULL DEFAULT 'active',
    last_seen_commit   VARCHAR(40),
    last_scanned_at    TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_documents_doc_id UNIQUE (doc_id),
    CONSTRAINT uq_documents_binding_path UNIQUE (doc_binding_id, relative_path)
);
```

- [ ] **Step 4: 继续补全迁移并重跑测试**

```sql
CREATE TABLE IF NOT EXISTS doc_changes (
    id               SERIAL PRIMARY KEY,
    doc_change_id    VARCHAR(64) NOT NULL UNIQUE,
    document_id      INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    status           VARCHAR(64) NOT NULL,
    source_commit    VARCHAR(40),
    summary          TEXT,
    details_json     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by       VARCHAR(255),
    implemented_at   TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_doc_changes_status CHECK (status IN ('pending_implementation', 'in_implementation', 'implemented'))
);

CREATE TABLE IF NOT EXISTS code_change_links (
    id              SERIAL PRIMARY KEY,
    doc_change_id   INTEGER NOT NULL REFERENCES doc_changes(id) ON DELETE CASCADE,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch          VARCHAR(255) NOT NULL,
    commit_sha      VARCHAR(40) NOT NULL,
    commit_message  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_code_change_links_project_branch_commit
ON code_change_links(project_id, branch, commit_sha);

CREATE TABLE IF NOT EXISTS dangerous_commit_records (
    id             SERIAL PRIMARY KEY,
    project_id     INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch         VARCHAR(255) NOT NULL,
    commit_sha     VARCHAR(40) NOT NULL,
    risk_level     VARCHAR(32) NOT NULL,
    reason         TEXT NOT NULL,
    status         VARCHAR(32) NOT NULL DEFAULT 'open',
    resolved_by    VARCHAR(255),
    resolved_at    TIMESTAMPTZ,
    extra_json     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_dangerous_commit_status CHECK (status IN ('open', 'resolved'))
);

CREATE INDEX IF NOT EXISTS idx_dangerous_commit_records_project_status_created
ON dangerous_commit_records(project_id, status, created_at DESC);
```

Run: `pytest tests/test_metadata_migration.py -v`

Expected: PASS，新增表与索引检查通过。

- [ ] **Step 5: 提交这一小步**

```bash
git add docker/migrations/018_cli_metadata_foundation.sql tests/test_metadata_migration.py
git commit -m "feat: add cli metadata foundation migration"
```

### Task 4: 补齐元数据 repositories 并用持久化测试锁定行为

**Files:**
- Create: `src/service/repositories/doc_binding_repository.py`
- Create: `src/service/repositories/document_repository.py`
- Create: `src/service/repositories/doc_change_repository.py`
- Create: `src/service/repositories/code_change_link_repository.py`
- Create: `src/service/repositories/dangerous_commit_repository.py`
- Create: `tests/test_metadata_repositories.py`

- [ ] **Step 1: 先写失败测试，固定最小 CRUD 和关闭行为**

```python
from service.repositories import (
    code_change_link_repository,
    dangerous_commit_repository,
    doc_binding_repository,
    doc_change_repository,
    document_repository,
)


def test_doc_binding_create_and_get(pg_conn):
    product_id = _make_product(pg_conn)
    created = doc_binding_repository.create(
        pg_conn,
        product_id=product_id,
        repo_path="/repos/docs",
        repo_url="https://example.com/docs.git",
        default_branch="main",
    )
    pg_conn.commit()
    fetched = doc_binding_repository.find_by_id(pg_conn, created["id"])
    assert fetched["product_id"] == product_id
    assert fetched["repo_path"] == "/repos/docs"
    assert fetched["is_active"] is True


def test_doc_change_requires_unique_doc_change_id(pg_conn):
    document_id = _make_document(pg_conn)
    doc_change_repository.create(
        pg_conn,
        doc_change_id="DC-001",
        document_id=document_id,
        status="pending_implementation",
    )
    pg_conn.commit()
    with pytest.raises(Exception):
        doc_change_repository.create(
            pg_conn,
            doc_change_id="DC-001",
            document_id=document_id,
            status="pending_implementation",
        )


def test_resolve_dangerous_commit_updates_resolver_fields(pg_conn):
    project_id = _make_project(pg_conn)
    record = dangerous_commit_repository.create(
        pg_conn,
        project_id=project_id,
        branch="main",
        commit_sha="a" * 40,
        risk_level="high",
        reason="doc change missing",
    )
    pg_conn.commit()
    resolved = dangerous_commit_repository.resolve(
        pg_conn,
        record_id=record["id"],
        resolved_by="codex",
    )
    pg_conn.commit()
    assert resolved["status"] == "resolved"
    assert resolved["resolved_by"] == "codex"
    assert resolved["resolved_at"] is not None
```

- [ ] **Step 2: 运行测试，确认 repository 还不存在**

Run: `pytest tests/test_metadata_repositories.py -v`

Expected: FAIL，报错 repository 模块缺失。

- [ ] **Step 3: 先实现绑定、文档与 `DocChange` repositories**

```python
# src/service/repositories/doc_binding_repository.py
from psycopg2.extras import RealDictCursor


_COLUMNS = "id, product_id, repo_path, repo_url, default_branch, is_active, created_at, updated_at"


def create(conn, product_id: int, repo_path: str, repo_url: str | None = None, default_branch: str | None = None) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO doc_bindings (product_id, repo_path, repo_url, default_branch)
                VALUES (%s, %s, %s, %s)
                RETURNING {_COLUMNS}""",
            (product_id, repo_path, repo_url, default_branch),
        )
        return dict(cur.fetchone())
```

```python
# src/service/repositories/doc_change_repository.py
from psycopg2.extras import Json, RealDictCursor


_COLUMNS = "id, doc_change_id, document_id, status, source_commit, summary, details_json, created_by, implemented_at, created_at, updated_at"


def create(conn, doc_change_id: str, document_id: int, status: str, source_commit: str | None = None) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO doc_changes (doc_change_id, document_id, status, source_commit)
                VALUES (%s, %s, %s, %s)
                RETURNING {_COLUMNS}""",
            (doc_change_id, document_id, status, source_commit),
        )
        return dict(cur.fetchone())
```

- [ ] **Step 4: 再实现提交关联与危险提交 repositories，并跑通测试**

```python
# src/service/repositories/dangerous_commit_repository.py
from psycopg2.extras import Json, RealDictCursor


_COLUMNS = "id, project_id, branch, commit_sha, risk_level, reason, status, resolved_by, resolved_at, extra_json, created_at, updated_at"


def create(conn, project_id: int, branch: str, commit_sha: str, risk_level: str, reason: str, extra_json: dict | None = None) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO dangerous_commit_records (project_id, branch, commit_sha, risk_level, reason, extra_json)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING {_COLUMNS}""",
            (project_id, branch, commit_sha[:40], risk_level, reason, Json(extra_json or {})),
        )
        return dict(cur.fetchone())


def resolve(conn, record_id: int, resolved_by: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""UPDATE dangerous_commit_records
                SET status = 'resolved', resolved_by = %s, resolved_at = now(), updated_at = now()
                WHERE id = %s
                RETURNING {_COLUMNS}""",
            (resolved_by, record_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
```

Run: `pytest tests/test_metadata_repositories.py -v`

Expected: PASS，新增 repository 行为测试通过。

- [ ] **Step 5: 提交这一小步**

```bash
git add src/service/repositories/doc_binding_repository.py src/service/repositories/document_repository.py src/service/repositories/doc_change_repository.py src/service/repositories/code_change_link_repository.py src/service/repositories/dangerous_commit_repository.py tests/test_metadata_repositories.py
git commit -m "feat: add metadata repositories for cli foundation"
```

### Task 5: 做 CLI 集成验证并补最终回归测试

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/test_cli_contract.py`
- Modify: `tests/test_metadata_migration.py`
- Modify: `tests/test_metadata_repositories.py`

- [ ] **Step 1: 补测试夹具，确保测试库缺表时会自动应用最新迁移**

```python
def _run_migration_if_needed(conn) -> None:
    migration_dir = Path(__file__).resolve().parent.parent / "docker" / "migrations"
    if not migration_dir.is_dir():
        return
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT to_regclass('public.projects'), to_regclass('public.dangerous_commit_records')"
        )
        projects_table, latest_table = cur.fetchone()
    if projects_table and latest_table:
        return
    for migration_path in sorted(migration_dir.glob('*.sql')):
        sql = migration_path.read_text(encoding='utf-8')
        with conn.cursor() as cur:
            normalized_sql = "\n".join(
                line for line in sql.splitlines() if not line.strip().startswith("--")
            ).strip()
            if not normalized_sql:
                continue
            for stmt in normalized_sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
    conn.commit()
```

- [ ] **Step 2: 增加真实 CLI 验收测试**

```python
def test_version_check_json_is_machine_readable():
    proc = _run("neodev.py", "cli", "version-check", "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert set(payload.keys()) == {"ok", "command", "timestamp", "data", "errors"}
    assert payload["data"]["message"]
```

- [ ] **Step 3: 跑完整测试集，确认 `T001 + T002` 回归稳定**

Run: `pytest tests/test_cli_contract.py tests/test_metadata_migration.py tests/test_metadata_repositories.py -v`

Expected: PASS，所有本轮新增测试通过。

- [ ] **Step 4: 运行真实命令做最终证据收口**

Run: `python neodev.py cli version-check --json`

Expected:

```json
{
  "ok": true,
  "command": "cli version-check",
  "timestamp": "...",
  "data": {
    "cli_version": "dev",
    "plugin_version": null,
    "skill_version": null,
    "compatible": true,
    "update_available": false,
    "updated": false,
    "target_version": "dev",
    "message": "CLI 基础壳层已就绪，插件与 skill 版本联动待后续任务接入。"
  },
  "errors": []
}
```

- [ ] **Step 5: 提交最终收口**

```bash
git add tests/conftest.py tests/test_cli_contract.py tests/test_metadata_migration.py tests/test_metadata_repositories.py
git commit -m "test: verify cli foundation and metadata persistence"
```

## 自检结果

### 1. Spec 覆盖检查

- CLI 根级入口、模块入口、统一结果协议、错误码映射：由 Task 1 和 Task 2 覆盖
- `cli version-check`：由 Task 2 和 Task 5 覆盖
- 元数据表与迁移：由 Task 3 覆盖
- 元数据 repository 持久化：由 Task 4 覆盖
- 自动化测试与真实命令验收：由 Task 5 覆盖

无缺口。

### 2. 占位符扫描

已避免使用 `TBD`、`TODO`、`implement later`、`write tests for above` 这类占位表述。

### 3. 类型与命名一致性

- CLI 错误类型统一使用 `CliError`
- 统一成功结构构造器为 `build_success_payload`
- 统一失败结构构造器为 `build_error_payload`
- 危险提交关闭方法统一命名为 `resolve`

任务间命名一致。
