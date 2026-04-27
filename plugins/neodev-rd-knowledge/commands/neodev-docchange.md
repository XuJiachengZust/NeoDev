# /neodev-docchange

Use this command to register or inspect a controlled document change through the local `neodev` CLI client calling the configured remote NeoDev service.

Required boundary:

- Run `python plugins/neodev-rd-knowledge/check_neodev_environment.py` before write flows.
- Run `neodev config show` and `neodev cli version-check --json` before write flows.
- Validate MVP documents first with `python plugins/neodev-rd-knowledge/validate_mvp_docs.py prd prototype tech-design`.
- Register changes only with `neodev doc change register --document-id <document_id> --json`.
- Do not write PostgreSQL or Neo4j directly.
