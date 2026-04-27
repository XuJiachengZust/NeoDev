import pytest

from service.services.doc_validation_service import DocumentValidationError
from service.services.doc_validation_service import validate_front_matter


def _valid_front_matter() -> dict:
    return {
        "doc_id": "DOC-001",
        "title": "Valid Document",
        "aliases": ["Valid Document"],
        "tags": ["neodev/docs"],
        "created": "2026-04-27",
        "updated": "2026-04-27",
        "related": ["[[TECH-001]]"],
        "doc_type": "prd",
        "product_key": "NEODEV",
        "status": "active",
        "relations": {"target": ["TECH-001"]},
    }


def test_validate_front_matter_accepts_obsidian_properties():
    front_matter = _valid_front_matter()

    assert validate_front_matter(front_matter) == front_matter


def test_validate_front_matter_requires_obsidian_properties():
    front_matter = {
        "doc_id": "DOC-001",
        "title": "Missing Obsidian Properties",
        "doc_type": "prd",
        "product_key": "NEODEV",
        "status": "active",
        "relations": {"target": ["TECH-001"]},
    }

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_front_matter(front_matter)

    assert set(exc_info.value.details["missing_fields"]) == {
        "aliases",
        "tags",
        "created",
        "updated",
        "related",
    }


def test_validate_front_matter_rejects_invalid_obsidian_properties():
    front_matter = _valid_front_matter()
    front_matter.update(
        {
            "aliases": "Invalid Alias",
            "tags": ["#bad-tag"],
            "created": "27-04-2026",
            "updated": {"value": "2026-04-27"},
            "related": "[[TECH-001]]",
        }
    )

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_front_matter(front_matter)

    assert exc_info.value.details["field"] == "aliases"
