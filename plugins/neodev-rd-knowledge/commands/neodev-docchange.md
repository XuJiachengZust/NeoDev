# /neodev-docchange

Use this command to register or inspect a controlled document change through NeoDev CLI.

Required boundary:

- Run `python neodev.py cli version-check --json` before write flows.
- Validate MVP documents first with `python plugins/neodev-rd-knowledge/validate_mvp_docs.py prd prototype tech-design`.
- Register changes only with `python neodev.py doc change register --document-id <document_id> --json`.
- Do not write PostgreSQL or Neo4j directly.
