"""Project service: orchestration only (Phase 3)."""

from service.repositories import project_repository as repo


def list_projects(conn) -> list[dict]:
    return repo.list_all(conn)


def get_project(conn, project_id: int) -> dict | None:
    return repo.find_by_id(conn, project_id)


def create_project(
    conn,
    name: str,
    repo_path: str,
    watch_enabled: bool = False,
    neo4j_database: str | None = None,
    neo4j_identifier: str | None = None,
    repo_username: str | None = None,
    repo_password: str | None = None,
) -> dict:
    return repo.create(
        conn, name, repo_path, watch_enabled, neo4j_database, neo4j_identifier,
        repo_username=repo_username, repo_password=repo_password,
    )


def update_project(conn, project_id: int, **kwargs) -> dict | None:
    return repo.update(conn, project_id, **kwargs)


def delete_project(conn, project_id: int) -> bool:
    return repo.delete(conn, project_id)
