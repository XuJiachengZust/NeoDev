"""内容哈希计算：纯函数，无 I/O，用于 AI 描述缓存的内容寻址。

哈希规则：
- 叶子节点：sha256(chat_model + \0 + embedding_model + \0 + label + \0 + name + \0 + sourceCode)
- 容器节点：sha256(chat_model + \0 + embedding_model + \0 + label + \0 + name + \0 + sorted(child_hashes))
"""

import hashlib
from typing import Any


def compute_leaf_hash(
    chat_model: str, embedding_model: str, label: str, name: str, source_code: str
) -> str:
    """计算叶子节点的内容哈希。无源码时用 name 替代。"""
    content = source_code if source_code else name
    raw = f"{chat_model}\0{embedding_model}\0{label}\0{name}\0{content}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_container_hash(
    chat_model: str, embedding_model: str, label: str, name: str, child_hashes: list[str]
) -> str:
    """计算容器节点的内容哈希（包含全部子节点哈希，排序保证确定性）。"""
    children_part = "\0".join(sorted(child_hashes))
    raw = f"{chat_model}\0{embedding_model}\0{label}\0{name}\0{children_part}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_all_hashes(
    node_by_id: dict[str, dict[str, Any]],
    edges: list[tuple[str, str]],
    chat_model: str,
    embedding_model: str,
) -> dict[str, str]:
    """一次遍历自底向上计算所有节点的内容哈希。

    返回 {node_id: content_hash}。
    含环路检测（computing set 防止无限递归）。
    """
    # 构建 parent → children 映射
    children_map: dict[str, list[str]] = {nid: [] for nid in node_by_id}
    node_ids = set(node_by_id.keys())
    for parent_id, child_id in edges:
        if parent_id in node_ids and child_id in node_ids and child_id != parent_id:
            children_map[parent_id].append(child_id)

    result: dict[str, str] = {}
    computing: set[str] = set()  # 环路检测

    def _compute(nid: str) -> str:
        if nid in result:
            return result[nid]
        if nid in computing:
            # 环路：用叶子方式兜底
            node = node_by_id[nid]
            label = str(node.get("label") or "")
            name = str(node.get("name") or nid)
            h = compute_leaf_hash(chat_model, embedding_model, label, name, name)
            result[nid] = h
            return h

        computing.add(nid)
        node = node_by_id[nid]
        label = str(node.get("label") or "")
        name = str(node.get("name") or nid)
        children = children_map.get(nid, [])

        if not children:
            # 叶子节点
            source = str(node.get("sourceCode") or node.get("source_code") or "").strip()
            h = compute_leaf_hash(chat_model, embedding_model, label, name, source)
        else:
            # 容器节点：递归计算子节点哈希
            child_hashes = [_compute(cid) for cid in children]
            h = compute_container_hash(chat_model, embedding_model, label, name, child_hashes)

        computing.discard(nid)
        result[nid] = h
        return h

    for nid in node_by_id:
        _compute(nid)

    return result
