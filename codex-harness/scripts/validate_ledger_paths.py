from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable


HARNESS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = HARNESS_DIR.parent
LEDGER_PATH = HARNESS_DIR / "ledger" / "LEDGER.json"


def resolve_ledger_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def iter_checks(entries: list[dict]) -> Iterable[tuple[str, str, str]]:
    for index, entry in enumerate(entries):
        entry_id = entry.get("id") or f"entry[{index}]"
        for artifact_path in entry.get("artifacts") or []:
            if isinstance(artifact_path, str):
                yield entry_id, "artifact", artifact_path
            else:
                raise TypeError(f"Entry '{entry_id}' has a non-string artifact path: {artifact_path!r}")

        review_path = entry.get("review")
        if review_path is None:
            continue
        if not isinstance(review_path, str):
            raise TypeError(f"Entry '{entry_id}' has a non-string review path: {review_path!r}")
        yield entry_id, "review", review_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate artifact/review paths referenced by ledger/LEDGER.json.")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable JSON output.")
    return parser.parse_args(argv)


def emit_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if args.as_json:
            emit_json({"ok": False, "error": f"Ledger not found: {LEDGER_PATH}", "checked": 0, "entry_count": 0, "missing": []})
        else:
            print(f"[ERROR] Ledger not found: {LEDGER_PATH}")
        return 2
    except json.JSONDecodeError as exc:
        if args.as_json:
            emit_json({"ok": False, "error": f"Invalid JSON in ledger: {exc}", "checked": 0, "entry_count": 0, "missing": []})
        else:
            print(f"[ERROR] Invalid JSON in ledger: {exc}")
        return 2

    entries = ledger.get("entries")
    if not isinstance(entries, list):
        if args.as_json:
            emit_json({"ok": False, "error": "ledger.entries must be a list", "checked": 0, "entry_count": 0, "missing": []})
        else:
            print("[ERROR] ledger.entries must be a list")
        return 2

    checked = 0
    missing: list[tuple[str, str, str]] = []

    for entry_id, path_kind, raw_path in iter_checks(entries):
        checked += 1
        resolved = resolve_ledger_path(raw_path)
        if not resolved.exists():
            missing.append((entry_id, path_kind, raw_path))

    if args.as_json:
        emit_json(
            {
                "ok": not missing,
                "checked": checked,
                "entry_count": len(entries),
                "missing": [
                    {"entry_id": entry_id, "path_kind": path_kind, "path": raw_path}
                    for entry_id, path_kind, raw_path in missing
                ],
            }
        )
        return 0 if not missing else 1

    print(f"Checked {checked} ledger path reference(s) from {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}.")

    if not missing:
        print("OK: all artifact/review paths exist.")
        return 0

    print(f"MISSING: {len(missing)} path reference(s) not found:")
    for entry_id, path_kind, raw_path in missing:
        print(f"- {entry_id} | {path_kind} | {raw_path}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
