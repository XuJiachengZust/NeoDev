import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "plugins" / "neodev-rd-knowledge" / "validate_obsidian_docs.py"


def _make_tmp_dir() -> Path:
    path = ROOT / ".test-tmp" / f"obsidian-doc-validation-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    return path


def _run_validator(*paths: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *(str(path) for path in paths)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _write_doc(path: Path, front_matter: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{front_matter}\n---\n\n# Body\n", encoding="utf-8")


def test_validate_obsidian_docs_accepts_neodev_obsidian_properties():
    tmp_path = _make_tmp_dir()
    try:
        _assert_validate_obsidian_docs_accepts_neodev_obsidian_properties(tmp_path)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def _assert_validate_obsidian_docs_accepts_neodev_obsidian_properties(tmp_path: Path):
    _write_doc(
        tmp_path / "docs" / "valid.md",
        """
doc_id: NEODEV-DOC-VALID
title: "有效文档"
aliases:
  - "有效文档"
tags:
  - neodev/docs
created: 2026-04-27
updated: 2026-04-27
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-RELATED
related:
  - "[[related]]"
""".strip(),
    )
    _write_doc(
        tmp_path / "docs" / "related.md",
        """
doc_id: NEODEV-DOC-RELATED
title: "关联文档"
aliases:
  - "关联文档"
tags:
  - neodev/docs
created: 2026-04-27
updated: 2026-04-27
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-VALID
related:
  - "[[valid]]"
""".strip(),
    )

    result = _run_validator(tmp_path / "docs")

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload == {"ok": True, "checked_count": 2, "errors": []}


def test_validate_obsidian_docs_rejects_preamble_and_bad_properties():
    tmp_path = _make_tmp_dir()
    try:
        _assert_validate_obsidian_docs_rejects_preamble_and_bad_properties(tmp_path)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def _assert_validate_obsidian_docs_rejects_preamble_and_bad_properties(tmp_path: Path):
    bad = tmp_path / "docs" / "bad.md"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text(
        """
note before yaml
---
doc_id: NEODEV-DOC-BAD
title: Bad
aliases: Bad
tags:
  - "#neodev/docs"
created: 27-04-2026
updated:
  value: 2026-04-27
doc_type: note
product_key: NEODEV
status: planned
relations:
  related:
    - NEODEV-DOC-MISSING
related: "[[missing]]"
---
""".lstrip(),
        encoding="utf-8",
    )

    result = _run_validator(tmp_path / "docs")

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["ok"] is False
    assert payload["checked_count"] == 1
    assert payload["errors"][0]["field"] == "front_matter"


def test_validate_obsidian_docs_checks_wiki_links():
    tmp_path = _make_tmp_dir()
    try:
        _assert_validate_obsidian_docs_checks_wiki_links(tmp_path)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def _assert_validate_obsidian_docs_checks_wiki_links(tmp_path: Path):
    _write_doc(
        tmp_path / "docs" / "valid.md",
        """
doc_id: NEODEV-DOC-VALID
title: "有效文档"
aliases:
  - "有效文档"
tags:
  - neodev/docs
created: 2026-04-27
updated: 2026-04-27
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-MISSING
related:
  - "[[missing-note]]"
""".strip(),
    )

    result = _run_validator(tmp_path / "docs")

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert {error["field"] for error in payload["errors"]} == {
        "relations.target",
        "related",
    }
