# /neodev-graph-impact

Query the impact of a DocChange through the configured remote NeoDev service.

Check the local CLI boundary first:

```bash
python plugins/neodev-rd-knowledge/check_neodev_environment.py
neodev config show
neodev cli version-check --json
```

Query impact:

```bash
neodev graph impact --doc-change-id <doc_change_id> --json
```

Interpretation:

- `document_summary` identifies the source document and DocChange status.
- `evidence` usually starts from `document.relations`.
- `confidence=low` is expected when the document has no code links yet; report that as an evidence gap, not as command failure.

For code graph context, do not use semantic search. Use the names discovered from `product version show`:

```bash
neodev graph get-chain \
  --product-code <product_code> \
  --version-name <version_name> \
  --project-name <project_name> \
  --branch-name <branch> \
  --file-path <path> \
  --json

neodev graph entity-context \
  --product-code <product_code> \
  --version-name <version_name> \
  --project-name <project_name> \
  --branch-name <branch> \
  --entity-id <node_id> \
  --json
```
