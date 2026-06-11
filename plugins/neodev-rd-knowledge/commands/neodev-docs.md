# /neodev-docs

Primary intent entry for validating, scanning, and importing controlled documents for the current NeoDev product version.

Recommended command:

```bash
neodev docs sync --json
```

Run local document validators before syncing:

```bash
python plugins/neodev-rd-knowledge/validate_mvp_docs.py <docs_path>
python plugins/neodev-rd-knowledge/validate_obsidian_docs.py <docs_path>
```

Use this intent when the user asks to sync requirements, import controlled docs, refresh document graph evidence, or prepare documents for a DocChange.

Expected evidence:

- Controlled documents validate successfully.
- Version-scoped document binding exists or is created by the workflow.
- Scan/import results identify imported, updated, skipped, or failed documents.
- Next action points to `neodev change start` when a document change should drive implementation.

Advanced atomic document binding, scan, import, and graph commands remain available for troubleshooting, but this command is the default user-facing path.
