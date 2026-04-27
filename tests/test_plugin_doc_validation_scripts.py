import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = ROOT / "plugins" / "neodev-rd-knowledge"
VALIDATOR = PLUGIN_ROOT / "validate_mvp_docs.py"
GENERATOR = PLUGIN_ROOT / "generate_mvp_doc.py"
TRAILER_CHECKER = PLUGIN_ROOT / "check_docchange_trailer.py"


def _make_tmp_dir() -> Path:
    path = ROOT / ".test-tmp" / f"plugin-doc-validation-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    return path


def _write_doc(path: Path, front_matter: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{front_matter}\n---\n\nBody\n", encoding="utf-8")


def _run_script(script: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd or ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _json_stdout(result: subprocess.CompletedProcess) -> dict:
    return json.loads(result.stdout)


def test_validate_mvp_docs_accepts_valid_controlled_documents():
    tmp_path = _make_tmp_dir()
    try:
        _assert_validate_mvp_docs_accepts_valid_controlled_documents(tmp_path)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def _assert_validate_mvp_docs_accepts_valid_controlled_documents(tmp_path: Path):
    _write_doc(
        tmp_path / "prd" / "valid.md",
        """
doc_id: DOC-001
title: Valid Document
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
    - TECH-001
""".strip(),
    )

    result = _run_script(VALIDATOR, str(tmp_path))

    payload = _json_stdout(result)
    assert result.returncode == 0
    assert payload == {"ok": True, "checked_count": 1, "errors": []}


def test_validate_mvp_docs_rejects_missing_required_fields():
    tmp_path = _make_tmp_dir()
    try:
        _assert_validate_mvp_docs_rejects_missing_required_fields(tmp_path)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def _assert_validate_mvp_docs_rejects_missing_required_fields(tmp_path: Path):
    _write_doc(
        tmp_path / "prototype" / "missing.md",
        """
doc_id: DOC-002
title: Missing Product
doc_type: prototype
status: draft
relations:
  target:
    - PRD-001
""".strip(),
    )

    result = _run_script(VALIDATOR, str(tmp_path))

    payload = _json_stdout(result)
    assert result.returncode == 1
    assert payload["ok"] is False
    assert payload["checked_count"] == 1
    assert payload["errors"][0]["field"] == "product_key"


def test_validate_mvp_docs_rejects_invalid_doc_type_and_status():
    tmp_path = _make_tmp_dir()
    try:
        _assert_validate_mvp_docs_rejects_invalid_doc_type_and_status(tmp_path)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def _assert_validate_mvp_docs_rejects_invalid_doc_type_and_status(tmp_path: Path):
    _write_doc(
        tmp_path / "tech-design" / "invalid.md",
        """
doc_id: DOC-003
title: Invalid Types
doc_type: note
product_key: NEODEV
status: planned
relations:
  target:
    - PRD-001
""".strip(),
    )

    result = _run_script(VALIDATOR, str(tmp_path))

    payload = _json_stdout(result)
    assert result.returncode == 1
    assert {error["field"] for error in payload["errors"]} == {"doc_type", "status"}


def test_validate_mvp_docs_rejects_invalid_relations_target():
    tmp_path = _make_tmp_dir()
    try:
        _assert_validate_mvp_docs_rejects_invalid_relations_target(tmp_path)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def _assert_validate_mvp_docs_rejects_invalid_relations_target(tmp_path: Path):
    cases = {
        "missing.md": "relations:\n  related:\n    - PRD-001",
        "empty.md": "relations:\n  target: []",
        "wrong-type.md": "relations:\n  target: PRD-001",
    }
    for name, relations in cases.items():
        _write_doc(
            tmp_path / "prd" / name,
            f"""
doc_id: {name}
title: Invalid Relations
doc_type: prd
product_key: NEODEV
status: active
{relations}
""".strip(),
        )

    result = _run_script(VALIDATOR, str(tmp_path))

    payload = _json_stdout(result)
    assert result.returncode == 1
    assert payload["checked_count"] == 3
    assert len(payload["errors"]) == 3
    assert {error["field"] for error in payload["errors"]} == {"relations.target"}


def test_generate_mvp_doc_writes_and_validates_output():
    tmp_path = _make_tmp_dir()
    try:
        _assert_generate_mvp_doc_writes_and_validates_output(tmp_path)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def _assert_generate_mvp_doc_writes_and_validates_output(tmp_path: Path):
    output = tmp_path / "prd" / "generated.md"

    result = _run_script(
        GENERATOR,
        "--doc-id",
        "DOC-GEN-001",
        "--title",
        "Generated PRD",
        "--doc-type",
        "prd",
        "--product-key",
        "NEODEV",
        "--target",
        "TECH-001",
        "--output",
        str(output),
    )

    payload = _json_stdout(result)
    assert result.returncode == 0
    assert payload["ok"] is True
    assert payload["checked_count"] == 1
    assert "doc_id: DOC-GEN-001" in output.read_text(encoding="utf-8")


def test_check_docchange_trailer_accepts_single_valid_trailer():
    result = _run_script(
        TRAILER_CHECKER,
        "--message",
        "feat: implement\n\nDocChange-ID: DC-NEODEV-001",
    )

    payload = _json_stdout(result)
    assert result.returncode == 0
    assert payload["ok"] is True
    assert payload["doc_change_id"] == "DC-NEODEV-001"


def test_check_docchange_trailer_rejects_missing_duplicate_and_malformed():
    messages = [
        "feat: missing",
        "fix: dup\n\nDocChange-ID: DC-ONE\nDocChange-ID: DC-TWO",
        "fix: malformed\n\nDocChange-ID: NOT-A-DC",
    ]

    for message in messages:
        result = _run_script(TRAILER_CHECKER, "--message", message)
        payload = _json_stdout(result)
        assert result.returncode == 1
        assert payload["ok"] is False
        assert payload["checked_count"] == 1
        assert payload["errors"]
