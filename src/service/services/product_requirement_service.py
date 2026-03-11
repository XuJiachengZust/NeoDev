"""Product requirement service: orchestration for three-level requirements."""

from service.repositories import product_requirement_repository as repo


def list_requirements(
    conn,
    product_id: int,
    level: str | None = None,
    parent_id: int | None = None,
    status: str | None = None,
    version_id: int | None = None,
) -> list[dict]:
    return repo.list_by_product(
        conn, product_id,
        level=level, parent_id=parent_id, status=status, version_id=version_id,
    )


def list_tree(conn, product_id: int, version_id: int | None = None) -> list[dict]:
    return repo.list_tree(conn, product_id, version_id=version_id)


def list_tree_with_counts(conn, product_id: int, version_id: int | None = None) -> list[dict]:
    return repo.list_tree_with_commit_counts(conn, product_id, version_id=version_id)


def get_requirement(conn, requirement_id: int) -> dict | None:
    return repo.find_by_id(conn, requirement_id)


def create_requirement(
    conn,
    product_id: int,
    title: str,
    level: str = "story",
    parent_id: int | None = None,
    description: str | None = None,
    external_id: str | None = None,
    status: str = "open",
    priority: str = "medium",
    assignee: str | None = None,
    version_id: int | None = None,
    sort_order: int = 0,
) -> dict:
    return repo.create(
        conn, product_id, title,
        level=level, parent_id=parent_id, description=description,
        external_id=external_id, status=status, priority=priority,
        assignee=assignee, version_id=version_id, sort_order=sort_order,
    )


def update_requirement(conn, requirement_id: int, **kwargs) -> dict | None:
    return repo.update(conn, requirement_id, **kwargs)


def delete_requirement(conn, requirement_id: int) -> bool:
    return repo.delete(conn, requirement_id)


def bind_commits(conn, requirement_id: int, commit_ids: list[int]) -> int:
    return repo.bind_commits(conn, requirement_id, commit_ids)


def unbind_commits(conn, requirement_id: int, commit_ids: list[int]) -> int:
    return repo.unbind_commits(conn, requirement_id, commit_ids)


def list_commits(conn, requirement_id: int) -> list[dict]:
    return repo.list_commits(conn, requirement_id)
