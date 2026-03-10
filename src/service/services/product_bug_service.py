"""Product bug service: orchestration for bug management."""

from service.repositories import product_bug_repository as repo


def list_bugs(
    conn,
    product_id: int,
    status: str | None = None,
    severity: str | None = None,
    version_id: int | None = None,
) -> list[dict]:
    return repo.list_by_product(
        conn, product_id,
        status=status, severity=severity, version_id=version_id,
    )


def get_bug(conn, bug_id: int) -> dict | None:
    return repo.find_by_id(conn, bug_id)


def create_bug(
    conn,
    product_id: int,
    title: str,
    description: str | None = None,
    external_id: str | None = None,
    severity: str = "minor",
    status: str = "open",
    priority: str = "medium",
    assignee: str | None = None,
    reporter: str | None = None,
    version_id: int | None = None,
    fix_version_id: int | None = None,
    requirement_id: int | None = None,
) -> dict:
    return repo.create(
        conn, product_id, title,
        description=description, external_id=external_id,
        severity=severity, status=status, priority=priority,
        assignee=assignee, reporter=reporter,
        version_id=version_id, fix_version_id=fix_version_id,
        requirement_id=requirement_id,
    )


def update_bug(conn, bug_id: int, **kwargs) -> dict | None:
    return repo.update(conn, bug_id, **kwargs)


def delete_bug(conn, bug_id: int) -> bool:
    return repo.delete(conn, bug_id)


def bind_commits(conn, bug_id: int, commit_ids: list[int]) -> int:
    return repo.bind_commits(conn, bug_id, commit_ids)


def unbind_commits(conn, bug_id: int, commit_ids: list[int]) -> int:
    return repo.unbind_commits(conn, bug_id, commit_ids)


def list_commits(conn, bug_id: int) -> list[dict]:
    return repo.list_commits(conn, bug_id)
