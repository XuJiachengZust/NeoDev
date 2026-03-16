"""需求文档 Service：协调文件存储与元数据，提供文档读写、版本、diff、生成上下文等。"""

from service.repositories import product_repository as product_repo
from service.repositories import product_requirement_repository as requirement_repo
from service.repositories import requirement_doc_repository as doc_repo
from service.storage import RequirementDocStorage


def get_doc(conn, storage: RequirementDocStorage, product_id: int, requirement_id: int) -> dict | None:
    """
    读取当前文档内容及元数据。
    若文件或元数据不存在则返回 None。
    """
    meta = doc_repo.find_meta(conn, requirement_id)
    if not meta:
        return None
    content = storage.read(product_id, requirement_id)
    if content is None:
        return None
    out = dict(meta)
    out["content"] = content
    return out


def save_doc(
    conn,
    storage: RequirementDocStorage,
    product_id: int,
    requirement_id: int,
    content: str,
    generated_by: str | None = None,
) -> dict:
    """
    保存文档：归档旧版本到文件系统，写入新内容，更新元数据。
    generated_by 可选：'manual' | 'agent' | 'workflow'。
    返回更新后的元数据（含 version）。
    """
    meta = doc_repo.find_meta(conn, requirement_id)
    version = 1 if not meta else (meta["version"] + 1)
    rel_path = f"{product_id}/{requirement_id}/doc.md"
    storage.write(product_id, requirement_id, content, version)
    return doc_repo.upsert_meta(
        conn, requirement_id, version, generated_by=generated_by, file_path=rel_path
    )


def list_versions(
    conn,
    storage: RequirementDocStorage,
    product_id: int,
    requirement_id: int,
) -> list[dict]:
    """
    列出版本号（含当前版本）。从文件系统得到已归档版本，从元数据得到当前版本号，合并去重排序。
    返回 [{"version": 1}, {"version": 2}, ...]。
    """
    archived = storage.list_versions(product_id, requirement_id)
    meta = doc_repo.find_meta(conn, requirement_id)
    current = meta["version"] if meta else None
    all_versions = sorted(set(archived) | ({current} if current is not None else set()))
    return [{"version": v} for v in all_versions]


def get_version_content(
    conn,
    storage: RequirementDocStorage,
    product_id: int,
    requirement_id: int,
    version: int,
) -> str | None:
    """获取指定版本内容。当前版本从 doc.md 读，历史版本从 versions/vN.md 读。"""
    meta = doc_repo.find_meta(conn, requirement_id)
    current_version = meta["version"] if meta else None
    if current_version is not None and version == current_version:
        return storage.read(product_id, requirement_id)
    return storage.read_version(product_id, requirement_id, version)


def get_diff_contents(
    conn,
    storage: RequirementDocStorage,
    product_id: int,
    requirement_id: int,
    v1: int,
    v2: int,
) -> dict:
    """返回两个版本的原始内容，供前端做 diff。键为 "v1"、"v2"，值可能为 None（版本不存在）。"""
    c1 = get_version_content(conn, storage, product_id, requirement_id, v1)
    c2 = get_version_content(conn, storage, product_id, requirement_id, v2)
    return {"v1": c1, "v2": c2}


def can_generate_children(conn, requirement_id: int) -> bool:
    """当前需求是否已有文档（有文档才允许生成子级文档）。"""
    meta = doc_repo.find_meta(conn, requirement_id)
    return meta is not None


def get_generation_context(
    conn,
    storage: RequirementDocStorage,
    product_id: int,
    requirement_id: int,
) -> dict:
    """
    获取工作流/Agent 生成所需的上下文：产品信息、当前需求、父文档内容、兄弟需求列表。
    """
    product = product_repo.find_by_id(conn, product_id)
    current = requirement_repo.find_by_id(conn, requirement_id)
    if not product or not current:
        return {}
    parent_id = current.get("parent_id")
    parent_doc_content: str | None = None
    if parent_id is not None:
        parent_doc_content = storage.read(product_id, parent_id)

    siblings = requirement_repo.list_by_product(
        conn, product_id, parent_id=parent_id
    )
    sibling_requirements = [s for s in siblings if s["id"] != requirement_id]

    return {
        "product": product,
        "current_requirement": current,
        "parent_doc_content": parent_doc_content,
        "sibling_requirements": sibling_requirements,
    }


def get_children_without_doc(conn, requirement_id: int) -> list[dict]:
    """返回该需求下尚未关联文档的子需求列表（用于批量生成子级）。"""
    req = requirement_repo.find_by_id(conn, requirement_id)
    if not req:
        return []
    product_id = req["product_id"]
    children = requirement_repo.list_by_product(
        conn, product_id, parent_id=requirement_id
    )
    if not children:
        return []
    child_ids = [c["id"] for c in children]
    has_map = doc_repo.batch_has_doc(conn, child_ids)
    return [c for c in children if not has_map.get(c["id"], False)]
