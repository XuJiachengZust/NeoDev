import pytest

from service.services import commit_message_parser


def test_parse_doc_change_id_from_trailer_block():
    doc_commit = "e" * 40
    message = """feat: implement auth flow

Body line.

Reviewed-by: Ada
DocChange-ID: {doc_commit}
""".format(doc_commit=doc_commit)

    result = commit_message_parser.parse_doc_change_id(message)

    assert result == {
        "doc_change_id": doc_commit,
        "matched_by": "trailer",
    }


def test_parse_doc_change_id_rejects_missing_trailer():
    with pytest.raises(commit_message_parser.CommitMessageParseError) as raised:
        commit_message_parser.parse_doc_change_id("feat: no trailer")

    assert raised.value.category == "invalid_argument"
    assert raised.value.message == "DocChange-ID trailer is required"


def test_parse_doc_change_id_rejects_duplicate_trailers():
    message = """fix: duplicate trailers

DocChange-ID: {first}
DocChange-ID: {second}
""".format(first="a" * 40, second="b" * 40)

    with pytest.raises(commit_message_parser.CommitMessageParseError) as raised:
        commit_message_parser.parse_doc_change_id(message)

    assert raised.value.category == "invalid_argument"
    assert raised.value.details["count"] == 2


def test_parse_doc_change_id_rejects_blank_value():
    with pytest.raises(commit_message_parser.CommitMessageParseError) as raised:
        commit_message_parser.parse_doc_change_id("DocChange-ID:   ")

    assert raised.value.category == "invalid_argument"


def test_parse_doc_change_id_rejects_non_commit_hash():
    with pytest.raises(commit_message_parser.CommitMessageParseError) as raised:
        commit_message_parser.parse_doc_change_id("DocChange-ID: DC-AUTH-001")

    assert raised.value.category == "invalid_argument"
    assert raised.value.message == "DocChange-ID must be a 40-character document commit hash"
