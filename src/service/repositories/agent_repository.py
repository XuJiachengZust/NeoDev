"""AI Agent 会话与消息仓储：会话管理、对话路由、消息读写、上下文快照。"""

import uuid
from datetime import datetime, timezone

from psycopg2.extras import Json, RealDictCursor


# ── Sessions ──────────────────────────────────────────────────────────


def upsert_session(conn, session_id: str, user_id: str | None = None) -> dict:
    """创建或更新会话（幂等），返回 session 行。"""
    now = datetime.now(timezone.utc)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO ai_agent_sessions (id, user_id, created_at, updated_at)
             VALUES (%s, %s, %s, %s)
             ON CONFLICT (id) DO UPDATE SET
               user_id = COALESCE(EXCLUDED.user_id, ai_agent_sessions.user_id),
               updated_at = EXCLUDED.updated_at
             RETURNING id, user_id, created_at, updated_at""",
            (session_id, user_id, now, now),
        )
        return dict(cur.fetchone())


# ── Conversations ─────────────────────────────────────────────────────


def resolve_conversation(
    conn,
    session_id: str,
    route_context_key: str,
    project_id: int | None = None,
    product_id: int | None = None,
    agent_profile: str = "default",
) -> dict:
    """查找或创建 session + route + project/product 对应的对话，返回对话行。

    产品模式：当 product_id 存在时，按 session + route + product 查找。
    """
    coalesced_pid = project_id if project_id is not None else -1
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if product_id is not None:
            # 产品模式：按 product_id 查找
            cur.execute(
                """SELECT id, session_id, route_context_key, project_id, product_id,
                          agent_profile, thread_id, title, created_at, updated_at
                   FROM ai_agent_conversations
                   WHERE session_id = %s
                     AND route_context_key = %s
                     AND product_id = %s""",
                (session_id, route_context_key, product_id),
            )
        else:
            # 旧模式：按 project_id 查找
            cur.execute(
                """SELECT id, session_id, route_context_key, project_id, product_id,
                          agent_profile, thread_id, title, created_at, updated_at
                   FROM ai_agent_conversations
                   WHERE session_id = %s
                     AND route_context_key = %s
                     AND COALESCE(project_id, -1) = %s
                     AND product_id IS NULL""",
                (session_id, route_context_key, coalesced_pid),
            )
        row = cur.fetchone()
        if row:
            return dict(row)

        # 不存在则创建
        thread_id = f"agent-{session_id[:8]}-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        cur.execute(
            """INSERT INTO ai_agent_conversations
               (session_id, route_context_key, project_id, product_id, agent_profile, thread_id, created_at, updated_at)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
             RETURNING id, session_id, route_context_key, project_id, product_id,
                       agent_profile, thread_id, title, created_at, updated_at""",
            (session_id, route_context_key, project_id, product_id, agent_profile, thread_id, now, now),
        )
        return dict(cur.fetchone())


def get_conversation(conn, conversation_id: int) -> dict | None:
    """按 ID 获取对话。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, session_id, route_context_key, project_id, product_id,
                      agent_profile, thread_id, title, created_at, updated_at
               FROM ai_agent_conversations WHERE id = %s""",
            (conversation_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


# ── Messages ──────────────────────────────────────────────────────────


def list_messages(
    conn,
    conversation_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """分页获取对话消息，按时间正序。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, conversation_id, role, content, tool_calls, tool_call_id,
                      token_in, token_out, latency_ms, model, created_at
               FROM ai_agent_messages
               WHERE conversation_id = %s
               ORDER BY created_at ASC, id ASC
               LIMIT %s OFFSET %s""",
            (conversation_id, limit, offset),
        )
        return [dict(r) for r in cur.fetchall()]


def insert_message(
    conn,
    conversation_id: int,
    role: str,
    content: str = "",
    tool_calls: list | None = None,
    tool_call_id: str | None = None,
    token_in: int | None = None,
    token_out: int | None = None,
    latency_ms: int | None = None,
    model: str | None = None,
) -> dict:
    """插入一条消息，返回消息行。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO ai_agent_messages
               (conversation_id, role, content, tool_calls, tool_call_id,
                token_in, token_out, latency_ms, model)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
             RETURNING id, conversation_id, role, content, tool_calls, tool_call_id,
                       token_in, token_out, latency_ms, model, created_at""",
            (
                conversation_id, role, content,
                Json(tool_calls) if tool_calls else None,
                tool_call_id, token_in, token_out, latency_ms, model,
            ),
        )
        return dict(cur.fetchone())


# ── Context Snapshots ─────────────────────────────────────────────────


def save_context_snapshot(
    conn,
    conversation_id: int,
    summary: str,
    state_json: dict | None = None,
    last_message_id: int | None = None,
) -> dict:
    """保存上下文快照。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO ai_agent_context_snapshots
               (conversation_id, summary, state_json, last_message_id)
             VALUES (%s, %s, %s, %s)
             RETURNING id, conversation_id, summary, state_json, last_message_id, created_at""",
            (conversation_id, summary, Json(state_json) if state_json else None, last_message_id),
        )
        return dict(cur.fetchone())


def get_latest_snapshot(conn, conversation_id: int) -> dict | None:
    """获取最新的上下文快照。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, conversation_id, summary, state_json, last_message_id, created_at
               FROM ai_agent_context_snapshots
               WHERE conversation_id = %s
               ORDER BY created_at DESC
               LIMIT 1""",
            (conversation_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


# ── Sandboxes ─────────────────────────────────────────────────────────


def upsert_sandbox(
    conn,
    session_id: str,
    sandbox_id: str,
    provider: str = "local",
    status: str = "active",
    workspace_path: str | None = None,
    mounted_project_id: int | None = None,
) -> dict:
    """创建或更新会话沙箱。"""
    now = datetime.now(timezone.utc)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO ai_agent_sandboxes
               (session_id, sandbox_id, provider, status, workspace_path, mounted_project_id,
                created_at, updated_at)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
             ON CONFLICT (session_id, sandbox_id) DO UPDATE SET
               status = EXCLUDED.status,
               workspace_path = EXCLUDED.workspace_path,
               mounted_project_id = EXCLUDED.mounted_project_id,
               updated_at = EXCLUDED.updated_at
             RETURNING id, session_id, sandbox_id, provider, status,
                       workspace_path, mounted_project_id, created_at, updated_at""",
            (session_id, sandbox_id, provider, status, workspace_path, mounted_project_id, now, now),
        )
        return dict(cur.fetchone())


def get_active_sandbox(conn, session_id: str) -> dict | None:
    """获取会话的活跃沙箱。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, session_id, sandbox_id, provider, status,
                      workspace_path, mounted_project_id, created_at, updated_at
               FROM ai_agent_sandboxes
               WHERE session_id = %s AND status = 'active'
               ORDER BY created_at DESC LIMIT 1""",
            (session_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
