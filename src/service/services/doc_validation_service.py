"""Validation helpers for controlled product documents."""

from dataclasses import dataclass


REQUIRED_FRONT_MATTER_FIELDS = {
    "doc_id",
    "title",
    "doc_type",
    "product_key",
    "status",
    "relations",
}


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

    missing = sorted(
        field for field in REQUIRED_FRONT_MATTER_FIELDS if not front_matter.get(field)
    )
    if missing:
        raise DocumentValidationError(
            f"missing required front matter fields: {', '.join(missing)}",
            {"missing_fields": missing},
        )

    relations = front_matter.get("relations")
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

    return front_matter
