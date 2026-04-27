# /neodev-doc-scan

Use this command to scan controlled PRD, prototype, and technical design documents through NeoDev CLI.

Required boundary:

- Run `python plugins/neodev-rd-knowledge/validate_mvp_docs.py prd prototype tech-design` before scan.
- Stop if validation returns `ok=false`.
- Scan only with `python neodev.py doc scan --doc-binding-id <doc_binding_id> --json`.
- Do not bypass NeoDev CLI with direct database or graph writes.
