"""Repository-level fact identity helpers."""

from gitnexus_parser.graph import generate_id


def build_file_fact_key(*, repo_id: int, file_path: str, file_content_hash: str) -> str:
    return f"repo:{repo_id}:file:{file_path}:hash:{file_content_hash}"


def build_file_fact_id(*, repo_id: int, file_path: str, file_content_hash: str) -> str:
    return generate_id("File", build_file_fact_key(
        repo_id=repo_id,
        file_path=file_path,
        file_content_hash=file_content_hash,
    ))


def build_symbol_fact_key(
    *,
    repo_id: int,
    label: str,
    file_path: str,
    name: str,
    start_line: int | None,
    end_line: int | None,
    file_content_hash: str,
) -> str:
    return (
        f"repo:{repo_id}:symbol:{label}:{file_path}:{name}:"
        f"{start_line or 0}:{end_line or 0}:hash:{file_content_hash}"
    )


def build_symbol_fact_id(
    *,
    repo_id: int,
    label: str,
    file_path: str,
    name: str,
    start_line: int | None,
    end_line: int | None,
    file_content_hash: str,
) -> str:
    return generate_id(label, build_symbol_fact_key(
        repo_id=repo_id,
        label=label,
        file_path=file_path,
        name=name,
        start_line=start_line,
        end_line=end_line,
        file_content_hash=file_content_hash,
    ))
