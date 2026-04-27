"""Validation helpers for controlled product documents."""

import re
from dataclasses import dataclass
from datetime import date


REQUIRED_FRONT_MATTER_FIELDS = {
    "aliases",
    "created",
    "doc_id",
    "title",
    "doc_type",
    "product_key",
    "related",
    "status",
    "tags",
    "updated",
    "relations",
}

VALID_DOC_TYPES = {"prd", "prototype", "tech-design"}
VALID_STATUSES = {"draft", "active", "deprecated"}
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class DocumentValidationError(Exception):
    message: str
    details: dict


def validate_front_matter(front_matter: object) -> dict:
    if not isinstance(front_matter, dict):
        raise DocumentValidationError(
            "front matter must be a mapping",
            {"field": "front_matter"},
        )

    validated = dict(front_matter)
    missing = sorted(
        field for field in REQUIRED_FRONT_MATTER_FIELDS if not validated.get(field)
    )
    if missing:
        raise DocumentValidationError(
            f"missing required front matter fields: {', '.join(missing)}",
            {"missing_fields": missing},
        )

    _validate_string_list(validated.get("aliases"), "aliases")
    _validate_string_list(validated.get("tags"), "tags", reject_hash_prefix=True)
    _validate_string_list(validated.get("related"), "related")
    validated["created"] = _validate_date(validated.get("created"), "created")
    validated["updated"] = _validate_date(validated.get("updated"), "updated")

    doc_type = validated.get("doc_type")
    if doc_type not in VALID_DOC_TYPES:
        raise DocumentValidationError(
            "doc_type must be one of: prd, prototype, tech-design",
            {"field": "doc_type", "allowed": sorted(VALID_DOC_TYPES)},
        )

    status = validated.get("status")
    if status not in VALID_STATUSES:
        raise DocumentValidationError(
            "status must be one of: draft, active, deprecated",
            {"field": "status", "allowed": sorted(VALID_STATUSES)},
        )

    relations = validated.get("relations")
    if not isinstance(relations, dict):
        raise DocumentValidationError(
            "relations must be a mapping",
            {"field": "relations"},
        )

    target = relations.get("target")
    if not isinstance(target, list) or not target:
        raise DocumentValidationError(
            "relations.target must be a non-empty list",
            {"field": "relations.target"},
        )
    if any(not isinstance(item, str) or not item.strip() for item in target):
        raise DocumentValidationError(
            "relations.target must contain non-empty strings",
            {"field": "relations.target"},
        )

    return validated


def _validate_string_list(
    value: object,
    field: str,
    *,
    reject_hash_prefix: bool = False,
) -> None:
    if not isinstance(value, list) or not value:
        raise DocumentValidationError(
            f"{field} must be a non-empty list",
            {"field": field},
        )
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise DocumentValidationError(
            f"{field} must contain non-empty strings",
            {"field": field},
        )
    if reject_hash_prefix and any(item.strip().startswith("#") for item in value):
        raise DocumentValidationError(
            f"{field} entries must omit the leading #",
            {"field": field},
        )


def _validate_date(value: object, field: str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and DATE_PATTERN.fullmatch(value):
        return value
    raise DocumentValidationError(
        f"{field} must use YYYY-MM-DD",
        {"field": field},
    )
