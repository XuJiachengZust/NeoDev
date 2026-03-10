"""Product version service: orchestration for product-level versions."""

from service.repositories import product_version_repository as repo


def list_versions(conn, product_id: int, status: str | None = None) -> list[dict]:
    return repo.list_by_product(conn, product_id, status=status)


def get_version(conn, version_id: int) -> dict | None:
    return repo.find_by_id(conn, version_id)


def create_version(
    conn,
    product_id: int,
    version_name: str,
    description: str | None = None,
    status: str = "planning",
    release_date: str | None = None,
) -> dict:
    return repo.create(
        conn, product_id, version_name,
        description=description, status=status, release_date=release_date,
    )


def update_version(conn, version_id: int, **kwargs) -> dict | None:
    return repo.update(conn, version_id, **kwargs)


def delete_version(conn, version_id: int) -> bool:
    return repo.delete(conn, version_id)


def list_branches(conn, version_id: int) -> list[dict]:
    return repo.list_branches(conn, version_id)


def set_branch(conn, version_id: int, project_id: int, branch: str) -> dict:
    return repo.set_branch(conn, version_id, project_id, branch)


def remove_branch(conn, version_id: int, project_id: int) -> bool:
    return repo.remove_branch(conn, version_id, project_id)
