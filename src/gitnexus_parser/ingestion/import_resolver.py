"""Import resolution: resolve raw import path to file path, add IMPORTS edges. Simplified (no tsconfig/go.mod)."""

from typing import Optional

from gitnexus_parser.graph import generate_id

# Extensions to try when resolving (aligned with import-processor EXTENSIONS subset)
EXTENSIONS = [
    "",
    ".py",
    "/__init__.py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".lua",
    "/init.lua",
]

RESOLVE_CACHE_CAP = 100_000


def _try_resolve_with_extensions(base_path: str, all_files: set[str]) -> Optional[str]:
    base_path = _normalize(base_path)
    # Normalize for comparison (Windows backslash)
    norm_to_orig = {_normalize(p): p for p in all_files}
    for ext in EXTENSIONS:
        candidate = base_path + ext
        if candidate in norm_to_orig:
            return norm_to_orig[candidate]
    return None


def _normalize(path: str) -> str:
    return path.replace("\\", "/")


def resolve_import_path(
    current_file: str,
    import_path: str,
    all_files: set[str],
    resolve_cache: Optional[dict[str, Optional[str]]] = None,
) -> Optional[str]:
    """
    Resolve import path to a file path in the repository.
    Handles relative (./, ../) and package-style paths via suffix matching.
    """
    cache = resolve_cache if resolve_cache is not None else {}
    cache_key = f"{current_file}::{import_path}"
    if cache_key in cache:
        return cache[cache_key]

    all_list = sorted(all_files)
    normalized_list = [_normalize(p) for p in all_list]

    def cache_result(result: Optional[str]) -> Optional[str]:
        if len(cache) >= RESOLVE_CACHE_CAP:
            to_remove = list(cache.keys())[: RESOLVE_CACHE_CAP // 5]
            for k in to_remove:
                del cache[k]
        cache[cache_key] = result
        return result

    # Relative import: . or ../
    current_file = _normalize(current_file)
    if import_path.startswith("."):
        parts = current_file.split("/")[:-1]  # directory of current file
        for part in import_path.split("/"):
            if part == ".":
                continue
            if part == "..":
                if parts:
                    parts.pop()
            else:
                # ".b" or "b" -> use "b" as path segment
                if part.startswith(".") and part != "..":
                    part = part.lstrip(".")
                if part:
                    parts.append(part)
        base = "/".join(parts)
        resolved = _try_resolve_with_extensions(base, all_files)
        if resolved:
            return cache_result(resolved)
        return cache_result(None)

    # Package/absolute: try as path from root, then suffix match
    base = import_path.replace(".", "/")
    resolved = _try_resolve_with_extensions(base, all_files)
    if resolved:
        return cache_result(resolved)
    path_parts = [p for p in base.split("/") if p]
    for i in range(len(path_parts)):
        suffix = "/".join(path_parts[i:])
        for ext in EXTENSIONS:
            cand = suffix + ext
            for j, n in enumerate(normalized_list):
                if n == cand or n.endswith("/" + cand):
                    return cache_result(all_list[j])
            for j, n in enumerate(normalized_list):
                if n.lower().endswith("/" + cand.lower()):
                    return cache_result(all_list[j])
    return cache_result(None)


def process_imports(
    graph,  # KnowledgeGraph
    extracted_imports: list,
    all_file_paths: set[str],
    resolve_cache: Optional[dict[str, Optional[str]]] = None,
) -> None:
    """
    For each ExtractedImport, resolve target file and add IMPORTS edge (File -> File).
    extracted_imports: list of ExtractedImport (filePath, rawImportPath, language).
    """
    cache = resolve_cache if resolve_cache is not None else {}
    for imp in extracted_imports:
        resolved = resolve_import_path(
            imp.filePath,
            imp.rawImportPath,
            all_file_paths,
            resolve_cache=cache,
        )
        if not resolved or resolved == imp.filePath:
            continue
        source_id = generate_id("File", imp.filePath)
        target_id = generate_id("File", resolved)
        if not graph.getNode(source_id) or not graph.getNode(target_id):
            continue
        rel_id = generate_id("IMPORTS", f"{imp.filePath}->{resolved}")
        graph.addRelationship({
            "id": rel_id,
            "sourceId": source_id,
            "targetId": target_id,
            "type": "IMPORTS",
            "confidence": 1.0,
            "reason": "",
        })
