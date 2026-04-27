# NeoDev Plugin Hooks, MVP Doc Validation, and Superpowers Platform Trace

## Scope Implemented

- Added shared plugin scripts under `plugins/neodev-rd-knowledge/`:
  - `validate_mvp_docs.py`
  - `generate_mvp_doc.py`
  - `check_docchange_trailer.py`
  - `assets/templates/mvp-doc.md`
- Added Codex manifest references for shared hooks and scripts.
- Added Claude Code plugin entry files:
  - `.claude-plugin/plugin.json`
  - `commands/*.md`
  - `agents/neodev-rd-knowledge.md`
  - `hooks/hooks.json`
- Added Cursor project rules and distributable plugin copies:
  - `.cursor/rules/*.mdc`
  - `plugins/neodev-rd-knowledge/cursor/rules/*.mdc`
- Updated the shared skill and workflow contract with MVP document validation and Superpowers workflow expectations.
- Updated the example documents to the executable MVP front matter contract:
  - `product_key`
  - `status`
  - mapping-style `relations.target`
- Tightened the service-side front matter validator so `doc_type` and `status` use the same allowed values as the shared script.

## Contract

All plugin entries remain orchestration-only. They may validate files, guide command order, and explain structured results, but fact reads and state changes still go through `python neodev.py ... --json`.

MVP controlled document front matter:

```yaml
doc_id: DOC-001
title: Document Title
doc_type: prd
product_key: PRODUCT
status: draft
relations:
  target:
    - TARGET-DOC-001
```

Allowed `doc_type`: `prd`, `prototype`, `tech-design`.

Allowed `status`: `draft`, `active`, `deprecated`.

## Validation Results

- `pytest tests/test_official_plugin_skill.py tests/test_minimal_e2e_example.py tests/test_plugin_platforms.py tests/test_plugin_doc_validation_scripts.py -q`
  - Result: `15 passed`
  - Note: pytest emitted a cache warning because `.pytest_cache` is not writable in this workspace.
- `PYTHONUTF8=1 python C:\Users\AH\.codex\skills\.system\skill-creator\scripts\quick_validate.py plugins\neodev-rd-knowledge\skills\neodev-rd-knowledge`
  - Result: `Skill is valid!`
- `python plugins\neodev-rd-knowledge\validate_mvp_docs.py examples\neodev-rd-knowledge\doc-repo`
  - Result: `{"ok": true, "checked_count": 2, "errors": []}`
- Additional scanner-focused check:
  - `pytest tests/test_official_plugin_skill.py tests/test_minimal_e2e_example.py tests/test_plugin_platforms.py tests/test_plugin_doc_validation_scripts.py tests/test_doc_scan_service.py -q`
  - Result: `15 passed, 4 skipped`
  - Note: skipped tests are existing metadata DB-dependent cases.

## Notes

- Claude Code hooks are represented in `hooks/hooks.json` using event groups and command hooks.
- Cursor support is rule-based. It does not claim Claude Code-equivalent runtime blocking hooks.
- This work ran in the current branch `neodev-sp`; no git commit or push was performed.
