"""Product version service: orchestration for product-level versions."""

from service.repositories import product_version_repository as repo
from service.repositories import version_repository
from service.services import version_service


def list_versions(conn, product_id: int, status: str | None = None) -> list[dict]:
    return repo.list_by_product(conn, product_id, status=status)


def get_version(conn, version_id: int) -> dict | None:
    return repo.find_by_id(conn, version_id)


def get_version_by_name(conn, product_id: int, version_name: str) -> dict | None:
    return repo.find_by_product_and_name(conn, product_id, version_name)


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
    row = repo.set_branch(conn, version_id, project_id, branch)
    branch = (branch or "").strip()
    product_version = repo.find_by_id(conn, version_id) or {}
    version_name = product_version.get("version_name")
    if branch:
        project_version = version_repository.find_by_project_and_branch(conn, project_id, branch)
        if project_version is None:
            version_service.create_version(conn, project_id, branch, version_name=version_name)
        elif version_name and not project_version.get("version_name"):
            version_repository.update_version_name(conn, project_version["id"], version_name)
    return row


def remove_branch(conn, version_id: int, project_id: int) -> bool:
    return repo.remove_branch(conn, version_id, project_id)
