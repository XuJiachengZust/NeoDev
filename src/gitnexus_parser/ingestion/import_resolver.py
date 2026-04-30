"""Import resolution: resolve raw import path to file path, add IMPORTS edges. Simplified (no tsconfig/go.mod)."""

from dataclasses import dataclass
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


@dataclass(frozen=True)
class ImportResolverIndex:
    exact: dict[str, str]
    exact_lower: dict[str, str]
    suffix: dict[str, str]
    suffix_lower: dict[str, str]


def build_import_resolver_index(all_files: set[str]) -> ImportResolverIndex:
    exact: dict[str, str] = {}
    exact_lower: dict[str, str] = {}
    suffix: dict[str, str] = {}
    suffix_lower: dict[str, str] = {}

    for original in sorted(all_files):
        normalized = _normalize(original)
        exact.setdefault(normalized, original)
        exact_lower.setdefault(normalized.lower(), original)
        parts = [part for part in normalized.split("/") if part]
        for index in range(len(parts)):
            path_suffix = "/".join(parts[index:])
            suffix.setdefault(path_suffix, original)
            suffix_lower.setdefault(path_suffix.lower(), original)

    return ImportResolverIndex(
        exact=exact,
        exact_lower=exact_lower,
        suffix=suffix,
        suffix_lower=suffix_lower,
    )


def _try_resolve_with_extensions(
    base_path: str,
    all_files: set[str],
    resolver_index: Optional[ImportResolverIndex] = None,
) -> Optional[str]:
    base_path = _normalize(base_path)
    index = resolver_index or build_import_resolver_index(all_files)
    for ext in EXTENSIONS:
        candidate = base_path + ext
        if candidate in index.exact:
            return index.exact[candidate]
        lower_candidate = candidate.lower()
        if lower_candidate in index.exact_lower:
            return index.exact_lower[lower_candidate]
    return None


def _normalize(path: str) -> str:
    return path.replace("\\", "/")


def resolve_import_path(
    current_file: str,
    import_path: str,
    all_files: set[str],
    resolve_cache: Optional[dict[str, Optional[str]]] = None,
    resolver_index: Optional[ImportResolverIndex] = None,
) -> Optional[str]:
    """
    Resolve import path to a file path in the repository.
    Handles relative (./, ../) and package-style paths via suffix matching.
    """
    cache = resolve_cache if resolve_cache is not None else {}
    cache_key = f"{current_file}::{import_path}"
    if cache_key in cache:
        return cache[cache_key]

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
        resolved = _try_resolve_with_extensions(base, all_files, resolver_index)
        if resolved:
            return cache_result(resolved)
        return cache_result(None)

    # Package/absolute: try as path from root, then suffix match
    base = import_path.replace(".", "/")
    index = resolver_index or build_import_resolver_index(all_files)
    resolved = _try_resolve_with_extensions(base, all_files, index)
    if resolved:
        return cache_result(resolved)
    path_parts = [p for p in base.split("/") if p]
    for i in range(len(path_parts)):
        suffix = "/".join(path_parts[i:])
        for ext in EXTENSIONS:
            cand = suffix + ext
            resolved = index.suffix.get(cand)
            if resolved:
                return cache_result(resolved)
            resolved = index.suffix_lower.get(cand.lower())
            if resolved:
                return cache_result(resolved)
    return cache_result(None)


def process_imports(
    graph,  # KnowledgeGraph
    extracted_imports: list,
    all_file_paths: set[str],
    resolve_cache: Optional[dict[str, Optional[str]]] = None,
    file_ids_by_path: Optional[dict[str, str]] = None,
) -> None:
    """
    For each ExtractedImport, resolve target file and add IMPORTS edge (File -> File).
    extracted_imports: list of ExtractedImport (filePath, rawImportPath, language).
    """
    cache = resolve_cache if resolve_cache is not None else {}
    file_ids_by_path = file_ids_by_path or {}
    resolver_index = build_import_resolver_index(all_file_paths)
    for imp in extracted_imports:
        resolved = resolve_import_path(
            imp.filePath,
            imp.rawImportPath,
            all_file_paths,
            resolve_cache=cache,
            resolver_index=resolver_index,
        )
        if not resolved or resolved == imp.filePath:
            continue
        source_id = file_ids_by_path.get(imp.filePath) or generate_id("File", imp.filePath)
        target_id = file_ids_by_path.get(resolved) or generate_id("File", resolved)
        if not graph.getNode(source_id) or not graph.getNode(target_id):
            continue
        rel_id = generate_id("IMPORTS", f"{source_id}->{target_id}")
        graph.addRelationship({
            "id": rel_id,
            "sourceId": source_id,
            "targetId": target_id,
            "type": "IMPORTS",
            "confidence": 1.0,
            "reason": "",
        })
