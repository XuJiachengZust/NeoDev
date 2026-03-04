"""Heritage resolution: EXTENDS / IMPLEMENTS from extracted heritage list."""

from gitnexus_parser.graph import generate_id


def process_heritage_from_extracted(
    graph,  # KnowledgeGraph
    extracted_heritage: list,  # list of ExtractedHeritage
    symbol_table,  # SymbolTable
) -> None:
    """Add EXTENDS and IMPLEMENTS edges from pre-extracted heritage (no AST)."""
    for h in extracted_heritage:
        if h.kind == "extends":
            child_id = (
                symbol_table.lookup_exact(h.filePath, h.className)
                or (symbol_table.lookup_fuzzy(h.className)[0].nodeId if symbol_table.lookup_fuzzy(h.className) else None)
                or generate_id("Class", f"{h.filePath}:{h.className}")
            )
            fuzzy_parent = symbol_table.lookup_fuzzy(h.parentName)
            parent_id = (fuzzy_parent[0].nodeId if fuzzy_parent else None) or generate_id("Class", h.parentName)
            if child_id != parent_id:
                rel_id = generate_id("EXTENDS", f"{child_id}->{parent_id}")
                graph.addRelationship({
                    "id": rel_id,
                    "sourceId": child_id,
                    "targetId": parent_id,
                    "type": "EXTENDS",
                    "confidence": 1.0,
                    "reason": "",
                })
        elif h.kind == "implements":
            class_id = (
                symbol_table.lookup_exact(h.filePath, h.className)
                or (symbol_table.lookup_fuzzy(h.className)[0].nodeId if symbol_table.lookup_fuzzy(h.className) else None)
                or generate_id("Class", f"{h.filePath}:{h.className}")
            )
            fuzzy_iface = symbol_table.lookup_fuzzy(h.parentName)
            interface_id = (fuzzy_iface[0].nodeId if fuzzy_iface else None) or generate_id("Interface", h.parentName)
            if class_id and interface_id:
                rel_id = generate_id("IMPLEMENTS", f"{class_id}->{interface_id}")
                graph.addRelationship({
                    "id": rel_id,
                    "sourceId": class_id,
                    "targetId": interface_id,
                    "type": "IMPLEMENTS",
                    "confidence": 1.0,
                    "reason": "",
                })
        elif h.kind == "trait-impl":
            struct_id = (
                symbol_table.lookup_exact(h.filePath, h.className)
                or (symbol_table.lookup_fuzzy(h.className)[0].nodeId if symbol_table.lookup_fuzzy(h.className) else None)
                or generate_id("Struct", f"{h.filePath}:{h.className}")
            )
            fuzzy_trait = symbol_table.lookup_fuzzy(h.parentName)
            trait_id = (fuzzy_trait[0].nodeId if fuzzy_trait else None) or generate_id("Trait", h.parentName)
            if struct_id and trait_id:
                rel_id = generate_id("IMPLEMENTS", f"{struct_id}->{trait_id}")
                graph.addRelationship({
                    "id": rel_id,
                    "sourceId": struct_id,
                    "targetId": trait_id,
                    "type": "IMPLEMENTS",
                    "confidence": 1.0,
                    "reason": "trait-impl",
                })
