"""聚合采样与聚合 prompt 构建：按节点类型取前 N 个下级，并在提示词中注明采样。"""


def sample_children(
    children: list[dict],
    sample_size: int,
    max_desc_chars: int | None = None,
) -> list[dict]:
    """
    对下级列表按 name 升序排序，取前 sample_size 条；可选对单条描述按 max_desc_chars 截断。
    children 每项需含 name、desc（或 id 作 fallback 排序键）。
    """
    if not children:
        return []
    key = "name" if any(c.get("name") is not None for c in children) else "id"
    sorted_children = sorted(children, key=lambda c: (c.get(key) or ""))
    sampled = sorted_children[:sample_size]
    if max_desc_chars is not None and max_desc_chars > 0:
        result = []
        for s in sampled:
            d = dict(s)
            desc = (d.get("desc") or "") if isinstance(d.get("desc"), str) else str(d.get("desc", ""))
            if len(desc) > max_desc_chars:
                d["desc"] = desc[:max_desc_chars].rstrip() + "…"
            result.append(d)
        return result
    return [dict(s) for s in sampled]


def build_aggregate_prompt(
    scope: str,
    name: str,
    items: list[dict],
    total: int,
) -> str:
    """
    构建聚合用 prompt：含「下级采样」说明及 name/desc 列表。
    items 为已采样的 [{"name": ..., "desc": ...}]，total 为原始下级总数。
    """
    n = len(items)
    sampling_phrase = (
        f"以下为下级节点的**采样**（共 {total} 个，此处仅展示前 {n} 个作为代表），"
        "请基于该采样推断本节点的整体职责与作用。"
    )
    block_lines = [f"{scope}「{name}」的下级采样：", "", sampling_phrase, ""]
    for it in items:
        block_lines.append(f"- {it.get('name', '')}: {it.get('desc', '')}")
    return "\n".join(block_lines)
