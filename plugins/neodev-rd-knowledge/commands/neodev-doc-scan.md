# /neodev-doc-scan

Use the local `neodev` CLI client to scan/import controlled documents through the configured remote NeoDev service.

Required checks:

```bash
python plugins/neodev-rd-knowledge/check_neodev_environment.py
neodev config show
neodev cli version-check --json
python plugins/neodev-rd-knowledge/validate_mvp_docs.py <docs_path>
python plugins/neodev-rd-knowledge/validate_obsidian_docs.py <docs_path>
```

Resolve or create a version-scoped binding:

```bash
neodev doc binding list --product-code <product_code> --json
neodev doc binding create \
  --product-code <product_code> \
  --version-name <version_name> \
  --project-name <project_name> \
  --repo-path <repo_path> \
  --branch <branch> \
  --json
```

Scan and import:

```bash
neodev doc scan --doc-binding-id <doc_binding_id> --json
neodev doc import --doc-binding-id <doc_binding_id> --json
```

Use `--force` only when intentionally rebuilding existing document chunks/embeddings.

Verify:

```bash
neodev doc graph show --product-name <product_name> --version-name <version_name> --json
```

Expected evidence:

- `doc binding list` shows `product_version_id`.
- `doc scan` registers controlled documents and reports invalid front matter as scan errors.
- `doc import` returns positive `imported_count` or `updated_count`.
- `doc graph show` returns `status=ready` and `document_count > 0`.

Do not write PostgreSQL or Neo4j directly in the normal workflow.
