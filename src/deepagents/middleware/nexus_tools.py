"""Middleware for providing Neo4j knowledge graph tools to an agent."""

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.tools import StructuredTool

from deepagents.backends.utils import truncate_if_too_long
from deepagents.middleware._utils import append_to_system_message

logger = logging.getLogger(__name__)

# 从 ai_analysis_runner 复用的合法 label 白名单
VALID_LABELS: frozenset[str] = frozenset({
    "Project", "Package", "Module", "Folder", "File",
    "Class", "Function", "Method", "Variable", "Interface", "Enum",
    "Decorator", "Import", "Type", "CodeElement", "Community", "Process",
    "Struct", "Macro", "Typedef", "Union", "Namespace", "Trait", "Impl",
    "TypeAlias", "Const", "Static", "Property", "Record", "Delegate",
    "Annotation", "Constructor", "Template",
})

# Cypher 写操作关键字检测（大小写不敏感）
_WRITE_PATTERN = re.compile(
    r"\b(CREATE|DELETE|DETACH\s+DELETE|SET|MERGE|REMOVE|DROP|CALL\s*\{)\b",
    re.IGNORECASE,
)

NEXUS_TOOLS_SYSTEM_PROMPT = (
    "## 知识图谱分析工具\n"
    "你可以使用以下工具查询 Neo4j 知识图谱：\n"
    "- nexus_search: 混合搜索节点（文本匹配 + 向量相似度）\n"
    "- nexus_cypher: 执行只读 Cypher 查询\n"
    "- nexus_explore: 查询节点的直接关联关系\n"
    "- nexus_overview: 获取代码库整体地图（Community/Process）\n"
    "- nexus_impact: 从指定节点做 N 跳影响分析\n"
    "\n"
    "### 图谱节点类型\n"
    "Project, Package, Module, Folder, File, Class, Function, Method, "
    "Variable, Interface, Enum, Community, Process 等\n"
    "\n"
    "### 主要关系类型\n"
    "CONTAINS, DEFINES, CALLS, IMPORTS, INHERITS, IMPLEMENTS, "
    "MEMBER_OF (Community), STEP_OF (Process)\n"
    "\n"
    "### 查询策略\n"
    "1. 先用 nexus_search 或 nexus_overview 定位目标节点\n"
    "2. 用 nexus_explore 查看节点的关联关系\n"
    "3. 用 nexus_cypher 做精确的自定义查询\n"
    "4. 用 nexus_impact 做变更影响分析\n"
    "\n"
    "⚠ 你没有文件系统工具，不能直接读取源码文件。"
    "需要查看源码时，请在回复中说明，由编排者另行调度 project-retriever。\n"
)


class NexusToolsMiddleware(AgentMiddleware):
    """为 agent 提供 Neo4j 知识图谱查询工具的中间件。"""

    TOOL_NAMES = (
        "nexus_search", "nexus_cypher", "nexus_explore",
        "nexus_overview", "nexus_impact",
    )

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str = "neo4j",
        neo4j_password: str = "",
        neo4j_database: str | None = None,
        project_id_map: dict[str, int] | None = None,
        branch_map: dict[str, str] | None = None,
        tools_whitelist: frozenset[str] | None = None,
    ):
        """
        Args:
            neo4j_uri: Neo4j bolt URI, 如 "bolt://localhost:7687"
            neo4j_user: Neo4j 用户名
            neo4j_password: Neo4j 密码
            neo4j_database: Neo4j 数据库名（None 则使用默认库）
            project_id_map: 项目名 → numeric project_id 映射
            branch_map: 项目名 → branch 映射
            tools_whitelist: 限制暴露的工具集，默认全部
        """
        self._neo4j_uri = neo4j_uri
        self._neo4j_user = neo4j_user
        self._neo4j_password = neo4j_password
        self._neo4j_database = neo4j_database
        self._project_id_map = project_id_map or {}
        self._branch_map = branch_map or {}
        self._tools_whitelist = tools_whitelist
        self._driver = None  # 惰性创建
        self.tools = self._build_tools()

    def _get_driver(self):
        """惰性创建 Neo4j driver。"""
        if self._driver is None:
            import neo4j
            self._driver = neo4j.GraphDatabase.driver(
                self._neo4j_uri,
                auth=(self._neo4j_user, self._neo4j_password),
            )
        return self._driver

    def close(self):
        """关闭 Neo4j driver。"""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def _resolve_project(
        self, project: str | None,
    ) -> tuple[int | None, str | None]:
        """解析 project 名称为 (project_id, branch)。

        单项目时 project 可省略；多项目时必填。
        """
        if not self._project_id_map:
            return None, None

        if len(self._project_id_map) == 1:
            name = next(iter(self._project_id_map))
            return self._project_id_map[name], self._branch_map.get(name)

        if not project:
            available = "、".join(self._project_id_map.keys())
            raise ValueError(
                f"多项目环境下必须指定 project 参数。可用项目: {available}"
            )

        if project not in self._project_id_map:
            available = "、".join(self._project_id_map.keys())
            raise ValueError(
                f"未知项目: {project!r}。可用项目: {available}"
            )
        return (
            self._project_id_map[project],
            self._branch_map.get(project),
        )

    def _run_cypher(
        self, query: str, params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """执行只读 Cypher 并返回结果列表。"""
        driver = self._get_driver()
        with driver.session(database=self._neo4j_database) as session:
            result = session.run(query, **(params or {}))
            return [dict(r) for r in result]

    @staticmethod
    def _format_records(records: list[dict[str, Any]], limit: int = 50) -> str:
        """将 Cypher 查询结果格式化为可读文本。"""
        if not records:
            return "（无结果）"
        lines = []
        for i, rec in enumerate(records[:limit]):
            parts = []
            for k, v in rec.items():
                parts.append(f"{k}: {v}")
            lines.append(f"  [{i+1}] {', '.join(parts)}")
        header = f"共 {len(records)} 条结果"
        if len(records) > limit:
            header += f"（显示前 {limit} 条）"
        return header + "\n" + "\n".join(lines)

    def _build_tools(self) -> list[StructuredTool]:
        """构建图谱工具列表。"""
        tools: list[StructuredTool] = []

        # ── nexus_search ──
        tools.append(self._make_nexus_search())
        # ── nexus_cypher ──
        tools.append(self._make_nexus_cypher())
        # ── nexus_explore ──
        tools.append(self._make_nexus_explore())
        # ── nexus_overview ──
        tools.append(self._make_nexus_overview())
        # ── nexus_impact ──
        tools.append(self._make_nexus_impact())

        # 过滤白名单
        if self._tools_whitelist:
            tools = [t for t in tools if t.name in self._tools_whitelist]
        return tools

    # ── 工具工厂方法（Phase 1B 实现）──

    def _make_nexus_search(self) -> StructuredTool:
        """构建 nexus_search 工具：混合搜索（文本 + 向量）。"""
        middleware = self

        def nexus_search(
            query: Annotated[str, "搜索关键词（节点名称、描述等）"],
            label_filter: Annotated[str | None, "按节点类型过滤，如 Function、Class"] = None,
            project: Annotated[str | None, "项目名称（多项目时必填）"] = None,
            limit: Annotated[int, "最大返回条数"] = 20,
        ) -> str:
            """在知识图谱中混合搜索节点（文本匹配 + 向量相似度），返回相关节点列表。"""
            if label_filter and label_filter not in VALID_LABELS:
                valid = ", ".join(sorted(VALID_LABELS))
                return f"错误: 无效的 label_filter {label_filter!r}。合法值: {valid}"
            try:
                project_id, branch = middleware._resolve_project(project)
            except ValueError as e:
                return f"错误: {e}"

            limit = max(1, min(limit, 100))

            # 构建 WHERE 条件
            where_parts = []
            params: dict[str, Any] = {"query_text": query, "limit": limit}
            if project_id is not None:
                where_parts.append("n.project_id = $project_id")
                params["project_id"] = project_id
            if branch:
                where_parts.append("n.branch = $branch")
                params["branch"] = branch

            # 尝试向量搜索
            vector = None
            try:
                from service.services.llm_client import embedding_completion
                vector = embedding_completion(query)
            except Exception:
                logger.debug("Embedding 不可用，退化为纯文本搜索")

            if vector and label_filter:
                # 向量搜索（指定 label）
                where_clause = (" AND " + " AND ".join(where_parts)) if where_parts else ""
                cypher = (
                    f"CALL db.index.vector.queryNodes("
                    f"'idx_{label_filter.lower()}_embedding', $limit, $vector"
                    f") YIELD node AS n, score "
                    f"WHERE (n.name CONTAINS $query_text OR n.description CONTAINS $query_text "
                    f"OR score > 0.5){where_clause} "
                    f"RETURN n.id AS id, labels(n)[0] AS label, n.name AS name, "
                    f"n.description AS description, score "
                    f"ORDER BY score DESC LIMIT $limit"
                )
                params["vector"] = vector
            elif vector:
                # 向量搜索（不指定 label，用文本匹配兜底）
                where_clause = (" AND " + " AND ".join(where_parts)) if where_parts else ""
                cypher = (
                    f"MATCH (n) "
                    f"WHERE (n.name CONTAINS $query_text "
                    f"OR n.description CONTAINS $query_text){where_clause} "
                    f"RETURN n.id AS id, labels(n)[0] AS label, n.name AS name, "
                    f"n.description AS description, 0.0 AS score "
                    f"ORDER BY n.name LIMIT $limit"
                )
            else:
                # 纯文本搜索
                label_match = f":{label_filter}" if label_filter else ""
                where_clause = (" AND " + " AND ".join(where_parts)) if where_parts else ""
                cypher = (
                    f"MATCH (n{label_match}) "
                    f"WHERE (n.name CONTAINS $query_text "
                    f"OR n.description CONTAINS $query_text){where_clause} "
                    f"RETURN n.id AS id, labels(n)[0] AS label, n.name AS name, "
                    f"n.description AS description, 0.0 AS score "
                    f"ORDER BY n.name LIMIT $limit"
                )

            try:
                records = middleware._run_cypher(cypher, params)
            except Exception as exc:
                return f"搜索失败: {exc}"
            return truncate_if_too_long(middleware._format_records(records, limit))

        return StructuredTool.from_function(
            func=nexus_search,
            name="nexus_search",
            description="在知识图谱中混合搜索节点（文本匹配 + 向量相似度），支持按类型过滤。",
        )

    def _make_nexus_cypher(self) -> StructuredTool:
        """构建 nexus_cypher 工具：只读 Cypher 执行。"""
        middleware = self

        def nexus_cypher(
            query: Annotated[str, "Cypher 查询语句（只读）"],
            params: Annotated[dict | None, "Cypher 参数字典"] = None,
            project: Annotated[str | None, "项目名称（多项目时必填）"] = None,
        ) -> str:
            """执行只读 Cypher 查询。自动注入 $project_id 和 $branch 参数。支持 {{QUERY_VECTOR}} 占位符（替换为查询文本的 embedding）。"""
            # 安全检查：禁止写操作
            if _WRITE_PATTERN.search(query):
                return "错误: 禁止执行写操作（CREATE/DELETE/SET/MERGE/REMOVE/DROP）"

            try:
                project_id, branch = middleware._resolve_project(project)
            except ValueError as e:
                return f"错误: {e}"

            cypher_params = dict(params or {})
            if project_id is not None:
                cypher_params.setdefault("project_id", project_id)
            if branch:
                cypher_params.setdefault("branch", branch)

            # 处理 {{QUERY_VECTOR}} 占位符
            if "{{QUERY_VECTOR}}" in query:
                try:
                    from service.services.llm_client import embedding_completion
                    # 从 params 中取 query_text，或用 query 本身
                    text = cypher_params.get("query_text", query)
                    vector = embedding_completion(str(text))
                    cypher_params["query_vector"] = vector
                    query = query.replace("{{QUERY_VECTOR}}", "$query_vector")
                except Exception as exc:
                    return f"错误: Embedding 生成失败: {exc}"

            try:
                records = middleware._run_cypher(query, cypher_params)
            except Exception as exc:
                return f"Cypher 执行失败: {exc}"
            return truncate_if_too_long(middleware._format_records(records))

        return StructuredTool.from_function(
            func=nexus_cypher,
            name="nexus_cypher",
            description="执行只读 Cypher 查询。自动注入 $project_id/$branch 参数，支持 {{QUERY_VECTOR}} 向量占位符。",
        )

    def _make_nexus_explore(self) -> StructuredTool:
        """构建 nexus_explore 工具：查询节点直接关联。"""
        middleware = self

        def nexus_explore(
            node_id: Annotated[str, "节点 ID（如 file:src/main.py 或 func:MyClass.run）"],
            project: Annotated[str | None, "项目名称（多项目时必填）"] = None,
            depth: Annotated[int, "关联深度（1-3）"] = 1,
        ) -> str:
            """查询指定节点的直接关联（入边、出边、所属 Community/Process），返回结构化关系列表。"""
            try:
                project_id, branch = middleware._resolve_project(project)
            except ValueError as e:
                return f"错误: {e}"

            depth = max(1, min(depth, 3))
            params: dict[str, Any] = {"node_id": node_id}
            if project_id is not None:
                params["project_id"] = project_id
            if branch:
                params["branch"] = branch

            # 构建 WHERE
            node_where = "n.id = $node_id"
            if project_id is not None:
                node_where += " AND n.project_id = $project_id"
            if branch:
                node_where += " AND n.branch = $branch"

            # 出边
            q_out = (
                f"MATCH (n)-[r]->(m) WHERE {node_where} "
                f"RETURN type(r) AS rel, m.id AS target_id, "
                f"labels(m)[0] AS target_label, m.name AS target_name "
                f"LIMIT 50"
            )
            # 入边
            q_in = (
                f"MATCH (m)-[r]->(n) WHERE {node_where} "
                f"RETURN type(r) AS rel, m.id AS source_id, "
                f"labels(m)[0] AS source_label, m.name AS source_name "
                f"LIMIT 50"
            )

            try:
                out_records = middleware._run_cypher(q_out, params)
                in_records = middleware._run_cypher(q_in, params)
            except Exception as exc:
                return f"查询失败: {exc}"

            lines = [f"节点 {node_id} 的关联关系："]
            if out_records:
                lines.append(f"\n出边（{len(out_records)} 条）：")
                for r in out_records:
                    lines.append(
                        f"  -[{r['rel']}]-> [{r.get('target_label','')}] "
                        f"{r.get('target_name','')} ({r.get('target_id','')})"
                    )
            else:
                lines.append("\n出边：无")

            if in_records:
                lines.append(f"\n入边（{len(in_records)} 条）：")
                for r in in_records:
                    lines.append(
                        f"  [{r.get('source_label','')}] "
                        f"{r.get('source_name','')} ({r.get('source_id','')}) "
                        f"-[{r['rel']}]->"
                    )
            else:
                lines.append("\n入边：无")

            return truncate_if_too_long("\n".join(lines))

        return StructuredTool.from_function(
            func=nexus_explore,
            name="nexus_explore",
            description="查询指定节点的直接关联（入边/出边/所属 Community/Process），返回结构化关系列表。",
        )

    def _make_nexus_overview(self) -> StructuredTool:
        """构建 nexus_overview 工具：代码库整体地图。"""
        middleware = self

        def nexus_overview(
            project: Annotated[str | None, "项目名称（多项目时必填）"] = None,
        ) -> str:
            """返回代码库整体地图：所有 Community 和 Process 节点列表，附带成员计数和描述摘要。"""
            try:
                project_id, branch = middleware._resolve_project(project)
            except ValueError as e:
                return f"错误: {e}"

            params: dict[str, Any] = {}
            where_parts = []
            if project_id is not None:
                where_parts.append("c.project_id = $project_id")
                params["project_id"] = project_id
            if branch:
                where_parts.append("c.branch = $branch")
                params["branch"] = branch
            where_clause = " WHERE " + " AND ".join(where_parts) if where_parts else ""

            # Community 节点
            q_community = (
                f"MATCH (c:Community){where_clause} "
                f"OPTIONAL MATCH (m)-[:MEMBER_OF]->(c) "
                f"RETURN c.id AS id, c.name AS name, "
                f"c.description AS description, count(m) AS member_count "
                f"ORDER BY member_count DESC"
            )
            # Process 节点
            q_process = (
                f"MATCH (c:Process){where_clause} "
                f"OPTIONAL MATCH (s)-[:STEP_OF]->(c) "
                f"RETURN c.id AS id, c.name AS name, "
                f"c.description AS description, count(s) AS step_count "
                f"ORDER BY step_count DESC"
            )

            try:
                communities = middleware._run_cypher(q_community, params)
                processes = middleware._run_cypher(q_process, params)
            except Exception as exc:
                return f"查询失败: {exc}"

            lines = ["## 代码库概览"]

            lines.append(f"\n### Community（{len(communities)} 个）")
            if communities:
                for c in communities:
                    desc = (c.get("description") or "")[:80]
                    lines.append(
                        f"  - {c['name']} (成员 {c.get('member_count', 0)})"
                        f"{': ' + desc if desc else ''}"
                    )
            else:
                lines.append("  （无）")

            lines.append(f"\n### Process（{len(processes)} 个）")
            if processes:
                for p in processes:
                    desc = (p.get("description") or "")[:80]
                    lines.append(
                        f"  - {p['name']} (步骤 {p.get('step_count', 0)})"
                        f"{': ' + desc if desc else ''}"
                    )
            else:
                lines.append("  （无）")

            return truncate_if_too_long("\n".join(lines))

        return StructuredTool.from_function(
            func=nexus_overview,
            name="nexus_overview",
            description="返回代码库整体地图：Community 和 Process 列表，附成员计数和描述。",
        )

    def _make_nexus_impact(self) -> StructuredTool:
        """构建 nexus_impact 工具：N 跳影响分析。"""
        middleware = self

        def nexus_impact(
            node_id: Annotated[str, "起始节点 ID"],
            project: Annotated[str | None, "项目名称（多项目时必填）"] = None,
            depth: Annotated[int, "传播深度（1-5）"] = 2,
        ) -> str:
            """从指定节点出发做 N 跳影响分析（沿 CALLS/IMPORTS 正向传播），返回受影响节点、流程和风险级别。"""
            try:
                project_id, branch = middleware._resolve_project(project)
            except ValueError as e:
                return f"错误: {e}"

            depth = max(1, min(depth, 5))
            params: dict[str, Any] = {"node_id": node_id, "depth": depth}

            node_where = "n.id = $node_id"
            if project_id is not None:
                node_where += " AND n.project_id = $project_id"
                params["project_id"] = project_id
            if branch:
                node_where += " AND n.branch = $branch"
                params["branch"] = branch

            # 沿 CALLS/IMPORTS 反向查找调用方（谁调用了/导入了该节点 → 受影响）
            q_affected = (
                f"MATCH (n) WHERE {node_where} "
                f"MATCH (affected)-[:CALLS|IMPORTS*1..{depth}]->(n) "
                f"RETURN DISTINCT affected.id AS id, labels(affected)[0] AS label, "
                f"affected.name AS name, "
                f"length(shortestPath((affected)-[:CALLS|IMPORTS*]->(n))) AS distance "
                f"ORDER BY distance, name LIMIT 100"
            )

            # 查找受影响的 Community / Process
            q_communities = (
                f"MATCH (n) WHERE {node_where} "
                f"MATCH (affected)-[:CALLS|IMPORTS*1..{depth}]->(n) "
                f"MATCH (affected)-[:MEMBER_OF]->(c:Community) "
                f"RETURN DISTINCT c.id AS id, c.name AS name, "
                f"count(affected) AS affected_members "
                f"ORDER BY affected_members DESC LIMIT 20"
            )

            try:
                affected = middleware._run_cypher(q_affected, params)
                communities = middleware._run_cypher(q_communities, params)
            except Exception as exc:
                return f"影响分析失败: {exc}"

            lines = [f"## 影响分析: {node_id}（深度 {depth}）"]

            # 直接受影响节点
            lines.append(f"\n### 受影响节点（{len(affected)} 个）")
            if affected:
                for a in affected:
                    dist = a.get("distance", "?")
                    lines.append(
                        f"  [{a.get('label','')}] {a.get('name','')} "
                        f"(距离 {dist}) — {a.get('id','')}"
                    )
            else:
                lines.append("  （无调用方/导入方）")

            # 受影响社区
            if communities:
                lines.append(f"\n### 受影响 Community（{len(communities)} 个）")
                for c in communities:
                    lines.append(
                        f"  - {c['name']} (受影响成员 {c.get('affected_members', 0)})"
                    )

            # 风险级别
            count = len(affected)
            if count == 0:
                risk = "低（无外部调用方）"
            elif count <= 5:
                risk = "低"
            elif count <= 20:
                risk = "中"
            else:
                risk = "高"
            lines.append(f"\n### 风险评估: {risk}（影响 {count} 个节点）")

            return truncate_if_too_long("\n".join(lines))

        return StructuredTool.from_function(
            func=nexus_impact,
            name="nexus_impact",
            description="从指定节点做 N 跳影响分析（沿 CALLS/IMPORTS 传播），返回受影响节点/流程/风险级别。",
        )

    # ── Model call wrappers（Phase 1C 实现）──

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        new_system_message = append_to_system_message(
            request.system_message, NEXUS_TOOLS_SYSTEM_PROMPT,
        )
        return handler(request.override(system_message=new_system_message))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        new_system_message = append_to_system_message(
            request.system_message, NEXUS_TOOLS_SYSTEM_PROMPT,
        )
        return await handler(request.override(system_message=new_system_message))
