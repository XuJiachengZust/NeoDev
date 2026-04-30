from psycopg2.extras import Json, RealDictCursor


def get_node_type(conn, project_id: int, type_key: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, project_id, type_key, name, description, status
            FROM graph_node_types
            WHERE project_id = %s AND type_key = %s AND status = 'active'
            """,
            (project_id, type_key),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_node_types(conn, project_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, project_id, type_key, name, description, status
            FROM graph_node_types
            WHERE project_id = %s
            ORDER BY type_key
            """,
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def get_relation_type(conn, project_id: int, type_key: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, project_id, type_key, name, description,
                   allowed_from_types, allowed_to_types,
                   cross_project_allowed, status
            FROM graph_relation_types
            WHERE project_id = %s AND type_key = %s AND status = 'active'
            """,
            (project_id, type_key),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_relation_types(conn, project_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, project_id, type_key, name, description,
                   allowed_from_types, allowed_to_types,
                   cross_project_allowed, status
            FROM graph_relation_types
            WHERE project_id = %s
            ORDER BY type_key
            """,
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def upsert_node_type(
    conn,
    *,
    project_id: int,
    type_key: str,
    name: str,
    description: str | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO graph_node_types (project_id, type_key, name, description, status)
            VALUES (%s, %s, %s, %s, 'active')
            ON CONFLICT (project_id, type_key)
            DO UPDATE SET name = EXCLUDED.name,
                          description = EXCLUDED.description,
                          status = 'active',
                          updated_at = now()
            RETURNING id, project_id, type_key, name, description, status
            """,
            (project_id, type_key, name, description),
        )
        return dict(cur.fetchone())


def archive_node_type(conn, *, project_id: int, type_key: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE graph_node_types
            SET status = 'archived', updated_at = now()
            WHERE project_id = %s AND type_key = %s
            RETURNING id, project_id, type_key, name, description, status
            """,
            (project_id, type_key),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def upsert_relation_type(
    conn,
    *,
    project_id: int,
    type_key: str,
    name: str,
    description: str | None = None,
    allowed_from_types: list[str] | None = None,
    allowed_to_types: list[str] | None = None,
    cross_project_allowed: bool = True,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO graph_relation_types (
                project_id, type_key, name, description,
                allowed_from_types, allowed_to_types, cross_project_allowed, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
            ON CONFLICT (project_id, type_key)
            DO UPDATE SET name = EXCLUDED.name,
                          description = EXCLUDED.description,
                          allowed_from_types = EXCLUDED.allowed_from_types,
                          allowed_to_types = EXCLUDED.allowed_to_types,
                          cross_project_allowed = EXCLUDED.cross_project_allowed,
                          status = 'active',
                          updated_at = now()
            RETURNING id, project_id, type_key, name, description,
                      allowed_from_types, allowed_to_types,
                      cross_project_allowed, status
            """,
            (
                project_id,
                type_key,
                name,
                description,
                Json(allowed_from_types or []),
                Json(allowed_to_types or []),
                cross_project_allowed,
            ),
        )
        return dict(cur.fetchone())


def archive_relation_type(conn, *, project_id: int, type_key: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE graph_relation_types
            SET status = 'archived', updated_at = now()
            WHERE project_id = %s AND type_key = %s
            RETURNING id, project_id, type_key, name, description,
                      allowed_from_types, allowed_to_types,
                      cross_project_allowed, status
            """,
            (project_id, type_key),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_node(conn, project_id: int, node_id: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, project_id, node_id, type_key, name, properties,
                   source, file_path, content_hash, status
            FROM graph_nodes
            WHERE project_id = %s AND node_id = %s
            """,
            (project_id, node_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_nodes(conn, project_id: int, type_key: str | None = None) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if type_key:
            cur.execute(
                """
                SELECT id, project_id, node_id, type_key, name, properties,
                       source, file_path, content_hash, status
                FROM graph_nodes
                WHERE project_id = %s AND type_key = %s
                ORDER BY node_id
                """,
                (project_id, type_key),
            )
        else:
            cur.execute(
                """
                SELECT id, project_id, node_id, type_key, name, properties,
                       source, file_path, content_hash, status
                FROM graph_nodes
                WHERE project_id = %s
                ORDER BY node_id
                """,
                (project_id,),
            )
        return [dict(row) for row in cur.fetchall()]


def get_node_by_any_project(conn, node_id: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, project_id, node_id, type_key, name, properties,
                   source, file_path, content_hash, status
            FROM graph_nodes
            WHERE node_id = %s
            ORDER BY project_id
            LIMIT 1
            """,
            (node_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def archive_node(conn, *, project_id: int, node_id: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE graph_nodes
            SET status = 'archived', updated_at = now()
            WHERE project_id = %s AND node_id = %s
            RETURNING id, project_id, node_id, type_key, name, properties,
                      source, file_path, content_hash, status
            """,
            (project_id, node_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def upsert_node(
    conn,
    *,
    project_id: int,
    node_id: str,
    type_key: str,
    name: str,
    properties: dict | None = None,
    source: str = "manual",
    status: str = "active",
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO graph_nodes (
                project_id, node_id, type_key, name, properties, source, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (project_id, node_id)
            DO UPDATE SET type_key = EXCLUDED.type_key,
                          name = EXCLUDED.name,
                          properties = EXCLUDED.properties,
                          status = EXCLUDED.status,
                          updated_at = now()
            RETURNING id, project_id, node_id, type_key, name, properties,
                      source, file_path, content_hash, status
            """,
            (project_id, node_id, type_key, name, Json(properties or {}), source, status),
        )
        return dict(cur.fetchone())


def update_node(conn, *, project_id: int, node_id: str, updates: dict) -> dict | None:
    existing = get_node(conn, project_id, node_id)
    if not existing:
        return None
    allowed = {"type_key", "name", "properties", "status"}
    assignments = []
    args = []
    for key, value in updates.items():
        if key not in allowed:
            continue
        assignments.append(f"{key} = %s")
        args.append(Json(value) if key == "properties" else value)
    if not assignments:
        return existing
    args.extend([project_id, node_id])
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            UPDATE graph_nodes
            SET {", ".join(assignments)}, updated_at = now()
            WHERE project_id = %s AND node_id = %s
            RETURNING id, project_id, node_id, type_key, name, properties,
                      source, file_path, content_hash, status
            """,
            args,
        )
        row = cur.fetchone()
        return dict(row) if row else None


def upsert_edge(
    conn,
    *,
    project_id: int,
    edge_id: str,
    from_node_id: str,
    to_node_id: str,
    from_project_id: int,
    to_project_id: int,
    type_key: str,
    properties: dict | None = None,
    status: str = "active",
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO graph_edges (
                project_id, edge_id, from_node_id, to_node_id,
                from_project_id, to_project_id, type_key, properties, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (project_id, edge_id)
            DO UPDATE SET from_node_id = EXCLUDED.from_node_id,
                          to_node_id = EXCLUDED.to_node_id,
                          from_project_id = EXCLUDED.from_project_id,
                          to_project_id = EXCLUDED.to_project_id,
                          type_key = EXCLUDED.type_key,
                          properties = EXCLUDED.properties,
                          status = EXCLUDED.status,
                          updated_at = now()
            RETURNING id, project_id, edge_id, from_node_id, to_node_id,
                      from_project_id, to_project_id, type_key, properties, status
            """,
            (
                project_id,
                edge_id,
                from_node_id,
                to_node_id,
                from_project_id,
                to_project_id,
                type_key,
                Json(properties or {}),
                status,
            ),
        )
        return dict(cur.fetchone())


def get_edge(conn, project_id: int, edge_id: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, project_id, edge_id, from_node_id, to_node_id,
                   from_project_id, to_project_id, type_key, properties, status
            FROM graph_edges
            WHERE project_id = %s AND edge_id = %s
            """,
            (project_id, edge_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_edges(conn, project_id: int, node_id: str | None = None, type_key: str | None = None) -> list[dict]:
    filters = ["project_id = %s"]
    args: list = [project_id]
    if node_id:
        filters.append("(from_node_id = %s OR to_node_id = %s)")
        args.extend([node_id, node_id])
    if type_key:
        filters.append("type_key = %s")
        args.append(type_key)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT id, project_id, edge_id, from_node_id, to_node_id,
                   from_project_id, to_project_id, type_key, properties, status
            FROM graph_edges
            WHERE {" AND ".join(filters)}
            ORDER BY edge_id
            """,
            args,
        )
        return [dict(row) for row in cur.fetchall()]


def update_edge(conn, *, project_id: int, edge_id: str, updates: dict) -> dict | None:
    existing = get_edge(conn, project_id, edge_id)
    if not existing:
        return None
    allowed = {"type_key", "properties", "status"}
    assignments = []
    args = []
    for key, value in updates.items():
        if key not in allowed:
            continue
        assignments.append(f"{key} = %s")
        args.append(Json(value) if key == "properties" else value)
    if not assignments:
        return existing
    args.extend([project_id, edge_id])
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            UPDATE graph_edges
            SET {", ".join(assignments)}, updated_at = now()
            WHERE project_id = %s AND edge_id = %s
            RETURNING id, project_id, edge_id, from_node_id, to_node_id,
                      from_project_id, to_project_id, type_key, properties, status
            """,
            args,
        )
        row = cur.fetchone()
        return dict(row) if row else None


def archive_edge(conn, *, project_id: int, edge_id: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE graph_edges
            SET status = 'archived', updated_at = now()
            WHERE project_id = %s AND edge_id = %s
            RETURNING id, project_id, edge_id, from_node_id, to_node_id,
                      from_project_id, to_project_id, type_key, properties, status
            """,
            (project_id, edge_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create_operation_log(
    conn,
    *,
    project_id: int,
    branch_name: str | None,
    snapshot_id: int | None,
    object_kind: str,
    object_id: str,
    operation: str,
    before_json: dict | None = None,
    after_json: dict | None = None,
    actor: str | None = None,
    source: str = "manual",
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO graph_operation_logs (
                project_id, branch_name, graph_id, object_kind, object_id,
                operation, before_json, after_json, actor, source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, project_id, branch_name, graph_id, object_kind,
                      object_id, operation, before_json, after_json, actor,
                      source, created_at
            """,
            (
                project_id,
                branch_name,
                snapshot_id,
                object_kind,
                object_id,
                operation,
                Json(before_json or {}),
                Json(after_json or {}),
                actor,
                source,
            ),
        )
        return dict(cur.fetchone())
