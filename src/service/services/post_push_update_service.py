"""Atomic post-push document/code graph update orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from service.cli.errors import CliError
from service.repositories import project_repository
from service.services import branch_graph_neo4j_service
from service.services import doc_change_service
from service.services import doc_import_service
from service.services import git_consistency_service
from service.services import project_service


@dataclass(slots=True)
class PostPushUpdateError(Exception):
    category: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


def apply_post_push_update(conn, payload: dict[str, Any]) -> dict[str, Any]:
    """Apply all post-push side effects as one service-owned transaction."""
    try:
        result = _apply(conn, payload)
        return result
    except PostPushUpdateError:
        _rollback(conn)
        raise
    except git_consistency_service.GitConsistencyError as exc:
        _rollback(conn)
        raise PostPushUpdateError(
            category=exc.category,
            message=exc.message,
            details=_details_with_rollback(exc.details, "rolled_back"),
        ) from exc
    except CliError as exc:
        _rollback(conn)
        raise PostPushUpdateError(
            category=exc.category,
            message=exc.message,
            details=_details_with_rollback(exc.details, "rolled_back"),
        ) from exc
    except project_service.ProjectServiceError as exc:
        _rollback(conn)
        raise PostPushUpdateError(
            category=exc.category,
            message=exc.message,
            details=_details_with_rollback(exc.details, "rolled_back"),
        ) from exc
    except Exception as exc:
        _rollback(conn)
        raise PostPushUpdateError(
            category="internal_error",
            message=str(exc) or "post-push graph update failed",
            details=_exception_rollback_details(exc),
        ) from exc


def _apply(conn, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PostPushUpdateError(
            category="invalid_argument",
            message="payload must be a JSON object",
            details={"rollback_status": "not_needed"},
        )
    branch = _required_text(payload.get("branch"), "branch")
    project = _resolve_project(conn, payload.get("project") or {})
    commit_results = [
        item
        for item in payload.get("commit_results") or []
        if isinstance(item, dict) and item.get("scope") in {"document", "code"}
    ]
    if not commit_results:
        raise PostPushUpdateError(
            category="invalid_argument",
            message="commit_results must include document or code commits",
            details={"rollback_status": "not_needed"},
        )

    doc_import_results: list[dict[str, Any]] = []
    docchange_register_results: list[dict[str, Any]] = []
    docchange_link_results: list[dict[str, Any]] = []

    document_commits = [item for item in commit_results if item.get("scope") == "document"]
    if document_commits:
        doc_binding_id = _required_int(project.get("doc_binding_id"), "doc_binding_id")
        import_result = doc_import_service.import_binding(conn, doc_binding_id, force=False)
        doc_import_results.append(import_result)
        docs_by_path = _index_documents_by_path(import_result.get("documents") or [])
        for item in document_commits:
            commit_sha = _required_text(item.get("commit_sha"), "commit_sha")
            for path in item.get("documents") or []:
                document = docs_by_path.get(_normalize_path(path))
                if not document:
                    raise PostPushUpdateError(
                        category="not_found",
                        message="document id unavailable after import",
                        details={
                            "commit_sha": commit_sha,
                            "relative_path": path,
                            "rollback_status": "rolled_back",
                        },
                    )
                registered = doc_change_service.register_doc_change(
                    conn,
                    document_id=int(document["id"]),
                    doc_change_id=commit_sha,
                    source_commit=commit_sha,
                    summary=f"Document change from {commit_sha[:12]}",
                    created_by="neodev-post-push-hook",
                )
                doc_change = registered.get("doc_change") or {}
                docchange_register_results.append(
                    {
                        **registered,
                        "commit_sha": commit_sha,
                        "relative_path": path,
                        "doc_change_id": doc_change.get("doc_change_id") or commit_sha,
                    }
                )

    for item in commit_results:
        if item.get("scope") != "code":
            continue
        commit_sha = _required_text(item.get("commit_sha"), "commit_sha")
        verified = git_consistency_service.verify_doc_change(
            conn,
            project_id=int(project["project_id"]),
            branch=branch,
            commit_sha=commit_sha,
            commit_message=_required_text(item.get("commit_message"), "commit_message"),
        )
        docchange_link_results.append({**verified, "commit_sha": commit_sha})

    graph_refresh_result = project_service.refresh_graph(
        conn,
        project_id=int(project["project_id"]),
        branch=branch,
        commit=False,
        commit_failure_state=False,
        restore_neo4j_on_error=True,
    )
    if not graph_refresh_result.get("head_commit"):
        rollback_status, restore_details = _restore_neo4j_if_needed(graph_refresh_result)
        raise PostPushUpdateError(
            category="invalid_result",
            message="post-push graph refresh result missing head_commit",
            details={
                "graph_refresh_result": _public_graph_refresh_result(graph_refresh_result),
                "rollback_status": rollback_status,
                **restore_details,
            },
        )
    _commit_or_raise(conn, graph_refresh_result)
    public_graph_refresh_result = _public_graph_refresh_result(graph_refresh_result)

    return {
        "status": "completed",
        "operation_id": str(payload.get("run_id") or ""),
        "atomic": True,
        "transaction_status": "committed",
        "project": {
            "project_id": project["project_id"],
            "project_name": project.get("project_name"),
            "branch": branch,
        },
        "commit_range": payload.get("commit_range") or [],
        "doc_import_results": doc_import_results,
        "docchange_register_results": docchange_register_results,
        "docchange_link_results": docchange_link_results,
        "graph_refresh_result": public_graph_refresh_result,
        "rollback_status": "not_needed",
    }


def _resolve_project(conn, project_payload: dict[str, Any]) -> dict[str, Any]:
    project_id = _optional_int(project_payload.get("project_id"))
    project_name = _optional_text(project_payload.get("project_name") or project_payload.get("name"))
    if project_id is not None:
        row = project_repository.find_by_id(conn, project_id)
        if not row:
            raise PostPushUpdateError(
                category="not_found",
                message="project not found",
                details={"project_id": project_id, "rollback_status": "not_needed"},
            )
    elif project_name:
        matches = project_repository.find_by_name(conn, project_name)
        if not matches:
            raise PostPushUpdateError(
                category="not_found",
                message="project not found",
                details={"project_name": project_name, "rollback_status": "not_needed"},
            )
        row = max(matches, key=lambda item: item["id"])
        project_id = int(row["id"])
    else:
        raise PostPushUpdateError(
            category="invalid_argument",
            message="project_id or project_name is required",
            details={"rollback_status": "not_needed"},
        )

    return {
        "project_id": int(project_id),
        "project_name": row.get("name") or project_name,
        "doc_binding_id": _optional_int(project_payload.get("doc_binding_id")),
    }


def _index_documents_by_path(documents: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for document in documents:
        relative_path = _normalize_path(document.get("relative_path"))
        if not relative_path or not document.get("id"):
            continue
        for candidate in _document_path_candidates(relative_path):
            indexed[candidate] = document
    return indexed


def _document_path_candidates(relative_path: str) -> set[str]:
    candidates = {relative_path}
    if relative_path.startswith("docs/"):
        candidates.add(relative_path.removeprefix("docs/"))
    else:
        candidates.add(f"docs/{relative_path}")
    return {candidate for candidate in candidates if candidate}


def _normalize_path(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/")


def _required_text(value: Any, field_name: str) -> str:
    text = _optional_text(value)
    if not text:
        raise PostPushUpdateError(
            category="invalid_argument",
            message=f"{field_name} is required",
            details={"field": field_name, "rollback_status": "rolled_back"},
        )
    return text


def _optional_text(value: Any) -> str:
    return str(value or "").strip()


def _required_int(value: Any, field_name: str) -> int:
    integer = _optional_int(value)
    if integer is None:
        raise PostPushUpdateError(
            category="invalid_argument",
            message=f"{field_name} is required",
            details={"field": field_name, "rollback_status": "rolled_back"},
        )
    return integer


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _rollback(conn) -> None:
    rollback = getattr(conn, "rollback", None)
    if callable(rollback):
        rollback()


def _exception_rollback_details(exc: Exception) -> dict[str, Any]:
    details = {"rollback_status": str(getattr(exc, "rollback_status", "rolled_back"))}
    restore_error = getattr(exc, "restore_error", None)
    if restore_error is not None:
        details["neo4j_restore_error"] = str(restore_error)
    commit_error = getattr(exc, "commit_error", None)
    if commit_error is not None:
        details["failure_state_commit_error"] = str(commit_error)
    return details


def _details_with_rollback(details: dict[str, Any] | None, default_status: str) -> dict[str, Any]:
    merged = dict(details or {})
    merged.setdefault("rollback_status", default_status)
    return merged


def _commit_or_raise(conn, graph_refresh_result: dict[str, Any]) -> None:
    try:
        conn.commit()
    except Exception as exc:
        graph_action = graph_refresh_result.get("graph_action")
        if graph_action == "skipped_unchanged":
            rollback_status = "rolled_back"
            restore_details: dict[str, Any] = {}
        else:
            rollback_status, restore_details = _restore_neo4j_if_needed(graph_refresh_result)
        raise PostPushUpdateError(
            category="internal_error",
            message="post-push transaction commit failed",
            details={
                "rollback_status": rollback_status,
                "graph_refresh_result": _public_graph_refresh_result(graph_refresh_result),
                **restore_details,
            },
        ) from exc


def _restore_neo4j_if_needed(graph_refresh_result: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if graph_refresh_result.get("graph_action") == "skipped_unchanged":
        return "rolled_back", {}
    restore_context = graph_refresh_result.get("_neo4j_restore")
    if not restore_context:
        return "rollback_failed", {}
    try:
        restore_result = branch_graph_neo4j_service.restore_branch_graph_snapshot(**restore_context)
    except Exception as exc:
        return "rollback_failed", {"neo4j_restore_error": str(exc)}
    return "rolled_back", {"neo4j_restore_result": restore_result}


def _public_graph_refresh_result(graph_refresh_result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in graph_refresh_result.items() if key != "_neo4j_restore"}
