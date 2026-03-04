"""File extension to language mapping, aligned with supported-languages.ts and ingestion/utils.ts."""

from typing import Optional

# Supported languages (same as SupportedLanguages enum)
SUPPORTED_LANGUAGES = frozenset({
    "javascript", "typescript", "python", "java", "c", "cpp", "csharp", "go", "rust", "php", "lua",
})


def get_language_from_filename(path: str) -> Optional[str]:
    """Map file path/name to language. Returns None for unsupported extensions."""
    path_lower = path.lower().replace("\\", "/")
    # TypeScript (including TSX)
    if path_lower.endswith(".tsx") or path_lower.endswith(".ts"):
        return "typescript"
    if path_lower.endswith(".jsx") or path_lower.endswith(".js"):
        return "javascript"
    if path_lower.endswith(".py"):
        return "python"
    if path_lower.endswith(".java"):
        return "java"
    if path_lower.endswith(".c") or path_lower.endswith(".h"):
        return "c"
    if any(path_lower.endswith(ext) for ext in (".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".hh")):
        return "cpp"
    if path_lower.endswith(".cs"):
        return "csharp"
    if path_lower.endswith(".go"):
        return "go"
    if path_lower.endswith(".rs"):
        return "rust"
    if any(path_lower.endswith(ext) for ext in (".php", ".phtml", ".php3", ".php4", ".php5", ".php8")):
        return "php"
    if path_lower.endswith(".lua"):
        return "lua"
    return None
