"""Product service: orchestration for product CRUD and project binding."""

from service.repositories import product_repository as repo


def list_products(conn, status: str | None = None) -> list[dict]:
    return repo.list_all(conn, status=status)


def get_product(conn, product_id: int) -> dict | None:
    return repo.find_by_id(conn, product_id)


def create_product(
    conn,
    name: str,
    code: str | None = None,
    description: str | None = None,
    owner: str | None = None,
) -> dict:
    return repo.create(conn, name, code=code, description=description, owner=owner)


def update_product(conn, product_id: int, **kwargs) -> dict | None:
    return repo.update(conn, product_id, **kwargs)


def delete_product(conn, product_id: int) -> bool:
    return repo.delete(conn, product_id)


def list_projects(conn, product_id: int) -> list[dict]:
    return repo.list_projects(conn, product_id)


def create_project_in_product(
    conn,
    product_id: int,
    name: str,
    repo_path: str,
    repo_username: str | None = None,
    repo_password: str | None = None,
    repo_url: str | None = None,
) -> dict:
    return repo.create_project(
        conn, product_id, name, repo_path,
        repo_username=repo_username, repo_password=repo_password,
        repo_url=repo_url,
    )


def bind_project(conn, product_id: int, project_id: int) -> bool:
    return repo.bind_project(conn, product_id, project_id)


def unbind_project(conn, product_id: int, project_id: int) -> bool:
    return repo.unbind_project(conn, product_id, project_id)
