"""NexusToolsMiddleware 单元测试。

使用 mock Neo4j driver，不需要真实 Neo4j 实例。
deepagents.__init__ 会导入 langchain.agents.create_agent，
在没有完整 langchain 环境时会失败。尝试导入，不可用则跳过。
"""

from unittest.mock import MagicMock, patch

import pytest

# 尝试导入，不可用则跳过中间件测试
try:
    from deepagents.middleware.nexus_tools import (
        VALID_LABELS,
        NexusToolsMiddleware,
        _WRITE_PATTERN,
    )
    _HAS_MIDDLEWARE = True
except ImportError:
    _HAS_MIDDLEWARE = False

needs_middleware = pytest.mark.skipif(
    not _HAS_MIDDLEWARE,
    reason="deepagents middleware 依赖不可用（需要 langchain agents）",
)


def _make_middleware(**kwargs):
    """创建 NexusToolsMiddleware 实例，mock 掉 neo4j import。"""
    mw = NexusToolsMiddleware(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="pass",
        **kwargs,
    )
    return mw


# ── 工具构建 ──


@needs_middleware
class TestToolBuilding:
    def test_tool_names_default(self):
        """默认构建 5 个工具。"""
        mw = _make_middleware()
        names = {t.name for t in mw.tools}
        assert names == {
            "nexus_search", "nexus_cypher", "nexus_explore",
            "nexus_overview", "nexus_impact",
        }

    def test_tool_names_whitelist(self):
        """tools_whitelist 过滤工具。"""
        mw = _make_middleware(
            tools_whitelist=frozenset({"nexus_search", "nexus_cypher"}),
        )
        names = {t.name for t in mw.tools}
        assert names == {"nexus_search", "nexus_cypher"}


# ── project/branch 解析 ──


@needs_middleware
class TestProjectResolution:
    def test_resolve_project_empty(self):
        """无 project_id_map 时返回 (None, None)。"""
        mw = _make_middleware()
        pid, branch = mw._resolve_project(None)
        assert pid is None
        assert branch is None

    def test_resolve_project_single(self):
        """单项目时忽略 project 参数。"""
        mw = _make_middleware(
            project_id_map={"backend": 42},
            branch_map={"backend": "main"},
        )
        pid, branch = mw._resolve_project(None)
        assert pid == 42
        assert branch == "main"
        # 传了 project 参数也返回唯一的
        pid2, branch2 = mw._resolve_project("ignored")
        assert pid2 == 42

    def test_resolve_project_multi_missing(self):
        """多项目时未指定 project 应报错。"""
        mw = _make_middleware(
            project_id_map={"frontend": 1, "backend": 2},
            branch_map={"frontend": "dev", "backend": "main"},
        )
        with pytest.raises(ValueError, match="多项目"):
            mw._resolve_project(None)

    def test_resolve_project_multi_unknown(self):
        """多项目时指定未知 project 应报错。"""
        mw = _make_middleware(
            project_id_map={"frontend": 1, "backend": 2},
        )
        with pytest.raises(ValueError, match="未知项目"):
            mw._resolve_project("nonexistent")

    def test_resolve_project_multi_ok(self):
        """多项目时指定正确 project。"""
        mw = _make_middleware(
            project_id_map={"frontend": 1, "backend": 2},
            branch_map={"frontend": "dev", "backend": "main"},
        )
        pid, branch = mw._resolve_project("backend")
        assert pid == 2
        assert branch == "main"


# ── Cypher 安全检查 ──


@needs_middleware
class TestCypherSafety:
    def test_write_blocked(self):
        """_WRITE_PATTERN 应拦截写操作关键字。"""
        dangerous = [
            "CREATE (n:Node {name: 'x'})",
            "MATCH (n) DELETE n",
            "MATCH (n) DETACH DELETE n",
            "MATCH (n) SET n.name = 'x'",
            "MERGE (n:Node {name: 'x'})",
            "MATCH (n) REMOVE n.name",
            "DROP INDEX idx_test",
            "CALL { CREATE (n) }",
        ]
        for q in dangerous:
            assert _WRITE_PATTERN.search(q) is not None, f"应拦截: {q}"

    def test_read_allowed(self):
        """只读 Cypher 不应被拦截。"""
        safe = [
            "MATCH (n) RETURN n",
            "MATCH (n)-[r]->(m) RETURN n, type(r), m",
            "MATCH (n) WHERE n.name CONTAINS 'create' RETURN n",
            "MATCH (n) RETURN n.description AS desc",
        ]
        for q in safe:
            assert _WRITE_PATTERN.search(q) is None, f"不应拦截: {q}"


# ── label 白名单 ──


@needs_middleware
class TestValidLabels:
    def test_contains_core_types(self):
        for label in ["Function", "Class", "File", "Community", "Process", "Module"]:
            assert label in VALID_LABELS

    def test_rejects_invalid(self):
        assert "InvalidLabel" not in VALID_LABELS


# ── QUERY_VECTOR 占位符 ──


@needs_middleware
class TestQueryVectorPlaceholder:
    def test_replacement(self):
        """nexus_cypher 应将 {{QUERY_VECTOR}} 替换为 $query_vector。"""
        mw = _make_middleware(
            project_id_map={"proj": 1}, branch_map={"proj": "main"},
        )

        mock_session = MagicMock()
        mock_session.run.return_value = iter([])

        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(
            return_value=mock_session,
        )
        mock_driver.session.return_value.__exit__ = MagicMock(
            return_value=False,
        )
        mw._driver = mock_driver

        fake_vector = [0.1, 0.2, 0.3]

        with patch(
            "service.services.llm_client.embedding_completion",
            return_value=fake_vector,
        ):
            cypher_tool = next(
                t for t in mw.tools if t.name == "nexus_cypher"
            )
            cypher_tool.func(
                query="RETURN vector.similarity.cosine(n.embedding, {{QUERY_VECTOR}}) AS score",
                params={"query_text": "user login"},
            )

        call_args = mock_session.run.call_args
        actual_query = call_args[0][0]
        assert "{{QUERY_VECTOR}}" not in actual_query
        assert "$query_vector" in actual_query
        # params 中包含 query_vector
        actual_params = call_args[1]
        assert actual_params.get("query_vector") == fake_vector


# ── close ──


@needs_middleware
class TestClose:
    def test_close_driver(self):
        mw = _make_middleware()
        mock_driver = MagicMock()
        mw._driver = mock_driver

        mw.close()
        mock_driver.close.assert_called_once()
        assert mw._driver is None

        # 重复 close 不应报错
        mw.close()


# ── format_records ──


@needs_middleware
class TestFormatRecords:
    def test_empty(self):
        assert NexusToolsMiddleware._format_records([]) == "（无结果）"

    def test_normal(self):
        records = [
            {"id": "func:main", "name": "main", "label": "Function"},
            {"id": "cls:App", "name": "App", "label": "Class"},
        ]
        result = NexusToolsMiddleware._format_records(records)
        assert "共 2 条结果" in result
        assert "func:main" in result
        assert "cls:App" in result
