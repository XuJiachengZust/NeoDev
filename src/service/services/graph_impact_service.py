from copy import deepcopy
from dataclasses import dataclass, field

from service.repositories import doc_change_repository
from service.repositories import document_repository


@dataclass(slots=True)
class GraphImpactError(Exception):
    category: str
    message: str
    details: dict | None = field(default=None)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)
        self.details = deepcopy(self.details) if self.details is not None else None


def doc_change_impact(
    conn,
    change_id: int | None = None,
    doc_change_id: str | None = None,
) -> dict:
    change = _resolve_doc_change(conn, change_id=change_id, doc_change_id=doc_change_id)
    document = document_repository.find_by_id(conn, change["document_id"])
    if not document:
        raise GraphImpactError(
            category="not_found",
            message="document not found",
            details={"document_id": change["document_id"]},
        )

    details = _as_dict(change.get("details_json"))
    front_matter = _as_dict(document.get("front_matter_json"))
    relations = _as_dict(document.get("relations_json"))

    affected_repositories = _dedupe(
        _as_list(details.get("affected_repositories"))
        + _as_list(front_matter.get("repository"))
        + _as_list(front_matter.get("repositories"))
    )
    affected_modules = _dedupe(
        _as_list(details.get("affected_modules"))
        + _as_list(relations.get("modules"))
        + _as_list(front_matter.get("module"))
        + _as_list(front_matter.get("modules"))
    )
    affected_files = _dedupe(
        _as_list(details.get("affected_files"))
        + _as_list(relations.get("files"))
        + _as_list(front_matter.get("files"))
    )
    affected_symbols = _dedupe(
        _as_list(details.get("affected_symbols"))
        + _as_list(relations.get("symbols"))
        + _as_list(front_matter.get("symbols"))
    )
    evidence = _build_evidence(change, document, details, front_matter, relations)

    return {
        "doc_change_id": change["doc_change_id"],
        "document_summary": {
            "id": document["id"],
            "doc_id": document.get("doc_id"),
            "title": document.get("title"),
            "relative_path": document.get("relative_path"),
            "source_commit": change.get("source_commit"),
            "change_summary": change.get("summary"),
            "status": change.get("status"),
        },
        "affected_repositories": affected_repositories,
        "affected_modules": affected_modules,
        "affected_files": affected_files,
        "affected_symbols": affected_symbols,
        "evidence": evidence,
        "confidence": _confidence(
            affected_repositories,
            affected_modules,
            affected_files,
            affected_symbols,
            evidence,
        ),
        "risk_points": _as_list(details.get("risk_points")),
        "suggested_steps": _as_list(details.get("suggested_steps"))
        or _default_suggested_steps(affected_files, affected_symbols),
    }


def _resolve_doc_change(
    conn,
    change_id: int | None = None,
    doc_change_id: str | None = None,
) -> dict:
    if change_id is None and not doc_change_id:
        raise GraphImpactError(
            category="invalid_argument",
            message="provide --change-id or --doc-change-id",
        )
    if change_id is not None and doc_change_id:
        raise GraphImpactError(
            category="invalid_argument",
            message="provide only one doc change locator",
        )
    if change_id is not None:
        change = doc_change_repository.find_by_id(conn, change_id)
    else:
        change = doc_change_repository.find_by_doc_change_id(conn, doc_change_id)
    if not change:
        raise GraphImpactError(category="not_found", message="doc change not found")
    return change


def _build_evidence(
    change: dict,
    document: dict,
    details: dict,
    front_matter: dict,
    relations: dict,
) -> list[dict]:
    evidence = []
    if details:
        evidence.append(
            {
                "source": "doc_change.details",
                "type": "declared_impact",
                "doc_change_id": change["doc_change_id"],
                "summary": change.get("summary"),
            }
        )

    relation_items = _as_list(relations.get("relations")) + _as_list(front_matter.get("relations"))
    for relation in relation_items:
        if isinstance(relation, dict):
            evidence.append(
                {
                    "source": "document.relations",
                    "type": relation.get("type") or relation.get("relation") or "related",
                    "target": relation.get("target") or relation.get("doc_id") or relation.get("id"),
                    "evidence": relation.get("evidence"),
                    "document_id": document["id"],
                }
            )
        else:
            evidence.append(
                {
                    "source": "document.relations",
                    "type": "related",
                    "target": str(relation),
                    "document_id": document["id"],
                }
            )

    front_matter_keys = sorted(
        key
        for key in ("repository", "repositories", "module", "component", "files", "symbols")
        if front_matter.get(key)
    )
    if front_matter_keys:
        evidence.append(
            {
                "source": "document.front_matter",
                "type": "declared_scope",
                "keys": front_matter_keys,
                "document_id": document["id"],
            }
        )
    return evidence


def _confidence(
    repositories: list[str],
    modules: list[str],
    files: list[str],
    symbols: list[str],
    evidence: list[dict],
) -> str:
    if files or symbols:
        return "medium"
    if repositories or modules or evidence:
        return "low"
    return "unknown"


def _default_suggested_steps(files: list[str], symbols: list[str]) -> list[str]:
    steps = ["review document relations before implementation"]
    if files:
        steps.append("inspect affected files")
    if symbols:
        steps.append("inspect affected symbols")
    return steps


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]


def _dedupe(values: list) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if value is None or isinstance(value, dict):
            continue
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
