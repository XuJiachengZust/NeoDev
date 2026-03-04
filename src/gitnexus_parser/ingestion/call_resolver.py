"""Call resolution: resolve call targets via symbol table, add CALLS edges."""

from gitnexus_parser.graph import generate_id


def process_calls(
    graph,  # KnowledgeGraph
    extracted_calls: list,  # list of ExtractedCall
    symbol_table,  # SymbolTable
) -> None:
    """
    For each ExtractedCall, resolve calledName to a node id and add CALLS edge.
    sourceId = call.sourceId (enclosing function or File), targetId = resolved node.
    """
    for call in extracted_calls:
        target_id = symbol_table.lookup_exact(call.filePath, call.calledName)
        reason = "same-file"
        if not target_id:
            fuzzy = symbol_table.lookup_fuzzy(call.calledName)
            if fuzzy:
                target_id = fuzzy[0].nodeId
                reason = "fuzzy-global"
            else:
                continue
        if call.sourceId == target_id:
            continue
        rel_id = generate_id("CALLS", f"{call.sourceId}:{call.calledName}->{target_id}")
        graph.addRelationship({
            "id": rel_id,
            "sourceId": call.sourceId,
            "targetId": target_id,
            "type": "CALLS",
            "confidence": 0.9 if reason == "fuzzy-global" else 1.0,
            "reason": reason,
        })
