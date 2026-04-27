# /neodev-doc-scan

Use this command to scan controlled PRD, prototype, and technical design documents through the local `neodev` CLI client calling the configured remote NeoDev service.

Required boundary:

- Run `python plugins/neodev-rd-knowledge/check_neodev_environment.py` before remote CLI workflows.
- Run `python plugins/neodev-rd-knowledge/validate_mvp_docs.py prd prototype tech-design` before scan.
- Stop if validation returns `ok=false`.
- Confirm the local client is configured with `neodev config show`.
- Scan only with `neodev doc scan --doc-binding-id <doc_binding_id> --json`.
- Do not bypass the remote NeoDev service with direct database or graph writes.
