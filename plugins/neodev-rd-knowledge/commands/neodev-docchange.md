# /neodev-docchange

Register or inspect controlled document changes through the local `neodev` CLI client against the configured remote NeoDev service.

Required checks:

```bash
python plugins/neodev-rd-knowledge/check_neodev_environment.py
neodev config show
neodev cli version-check --json
python plugins/neodev-rd-knowledge/validate_mvp_docs.py <docs_path>
python plugins/neodev-rd-knowledge/validate_obsidian_docs.py <docs_path>
```

Before registering a DocChange, import the version-scoped document binding:

```bash
neodev doc binding list --product-code <product_code> --json
neodev doc import --doc-binding-id <doc_binding_id> --json
```

The selected document must have `id`, `product_version_id`, and `last_seen_commit`.

Register:

```bash
neodev doc change register \
  --document-id <document_id> \
  --doc-change-id <40_char_document_commit_hash> \
  --source-commit <40_char_document_commit_hash> \
  --summary "<summary>" \
  --created-by <user> \
  --json
```

The `DocChange-ID` must be a 40-character Git commit hash. Business labels such as `CLI-E2E-...` are intentionally rejected.

Inspect:

```bash
neodev doc change show --doc-change-id <doc_change_id> --json
neodev graph impact --doc-change-id <doc_change_id> --json
```

Do not write DocChange records directly in PostgreSQL.
