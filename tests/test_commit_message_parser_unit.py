import pytest

from service.services import commit_message_parser


def test_parse_doc_change_id_from_trailer_block():
    message = """feat: implement auth flow

Body line.

Reviewed-by: Ada
DocChange-ID: DC-AUTH-001
"""

    result = commit_message_parser.parse_doc_change_id(message)

    assert result == {
        "doc_change_id": "DC-AUTH-001",
        "matched_by": "trailer",
    }


def test_parse_doc_change_id_rejects_missing_trailer():
    with pytest.raises(commit_message_parser.CommitMessageParseError) as raised:
        commit_message_parser.parse_doc_change_id("feat: no trailer")

    assert raised.value.category == "invalid_argument"
    assert raised.value.message == "DocChange-ID trailer is required"


def test_parse_doc_change_id_rejects_duplicate_trailers():
    message = """fix: duplicate trailers

DocChange-ID: DC-1
DocChange-ID: DC-2
"""

    with pytest.raises(commit_message_parser.CommitMessageParseError) as raised:
        commit_message_parser.parse_doc_change_id(message)

    assert raised.value.category == "invalid_argument"
    assert raised.value.details["count"] == 2


def test_parse_doc_change_id_rejects_blank_value():
    with pytest.raises(commit_message_parser.CommitMessageParseError) as raised:
        commit_message_parser.parse_doc_change_id("DocChange-ID:   ")

    assert raised.value.category == "invalid_argument"
