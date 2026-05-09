---
name: neodev-rd-knowledge
description: Use the local NeoDev CLI client against the configured remote NeoDev service to manage product versions, branch code graphs, version-scoped document bindings/imports, DocChange records, graph impact, and NeoSuperpower workflows.
---

# NeoDev RD Knowledge

Use the local `neodev` CLI client as the only normal boundary for NeoDev facts and state changes. The API service, PostgreSQL, Neo4j, graph refresh, document import, and DocChange state live in the remote NeoDev environment.

Direct PostgreSQL or Neo4j access is allowed only for debugging mismatches between CLI/API and storage. Do not use direct database writes as a workflow shortcut.

Shared workflow contracts live in `plugins/neodev-rd-knowledge/workflows/core-workflows.json`; plugin docs, commands, and skills should stay aligned with that file.

NeoSuperpower is the plugin-owned workflow layer. Former Superpowers planning, test-first implementation, systematic debugging, code-review, delegation, verification, and branch-completion workflows are embedded as `neosuperpower-*` skills and represented with `neosuperpower:*` phase names in this plugin. Treat `superpowers` as a migration/search keyword and third-party attribution term only.

Workflow weak orchestration lives in `core-workflows.json` as `neosuperpower.weak_orchestration` plus per-workflow `neosuperpower_awareness`. These fields make agents aware of relevant phases, suggested embedded skills, and evidence focus without changing the explicit CLI `steps`. Use them as soft routing and verification hints; do not treat them as extra mandatory CLI commands.

## Session Checks

Before write workflows, high-risk reads, commit/push checks, or verification:

```bash
neodev config show
neodev cli version-check --json
```

If the client is not installed or not configured:

```bash
scripts/install-neodev-client.cmd -Server <remote_api_url>
neodev config set-server <remote_api_url>
```

When testing from this repository without installing the shim, use:

```bash
python neodev.py --server <remote_api_url> <command> --json
```

## Version-Branch Navigation

`product version show` is the low-noise discovery entry point. It returns product, version, project, branch, and `query_params`; it must not trigger graph refresh, document import, or Neo4j reads.

Version lookup:

```bash
neodev product version show \
  --product-code <product_code> \
  --version-name <version_name> \
  --json
```

Branch reverse lookup:

```bash
neodev product version show \
  --project-name <project_name> \
  --branch-name <branch> \
  --json
```

Use the returned names directly for graph and document queries:

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

Prefer `--project-name` / `--branch-name` in user-facing workflows. Use IDs only when a command has no name-based alternative or while debugging.

## Repository And Code Graph Flow

1. Create or reuse a product and version:

```bash
neodev product create --name <product_name> --product-code <product_code> --json
neodev product version create --product-code <product_code> --version-name <version_name> --json
```

2. Register the code repository:

```bash
neodev project create --name <project_name> --repo-url <repo_url> --json
# or, for a server-local checkout:
neodev project create --name <project_name> --repo-path <repo_path> --json
```

3. Bind version to project branch:

```bash
neodev product version bind-branch \
  --product-code <product_code> \
  --version-name <version_name> \
  --project-name <project_name> \
  --branch <branch> \
  --json
```

4. Refresh or verify the branch code graph:

```bash
neodev project refresh-graph --project-name <project_name> --branch <branch> --json
```

A ready graph should return `graph_id`, `head_commit`, `node_count`, and `edge_count`. Nodes and edges written to Neo4j should include version scope fields such as `product_version_id`, `product_name`, `version_name`, `project_name`, and `branch_name`.

## Version-Scoped Document Flow

Document bindings are scoped to a product version. `doc_bindings.product_version_id` and imported `documents.product_version_id` must point at the target version.

Create or discover a binding:

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

Use `--force` only when intentionally rebuilding existing chunks/embeddings:

```bash
neodev doc import --doc-binding-id <doc_binding_id> --force --json
```

Verify the document graph by version:

```bash
neodev doc graph show --product-name <product_name> --version-name <version_name> --json
```

Expected evidence is `status=ready` and a positive `document_count`. Scanner errors for Markdown files without valid front matter are data-quality findings, not necessarily import failure, as long as valid controlled documents were registered/imported.

## DocChange And Impact

DocChange IDs are 40-character Git commit hashes for the imported source document. Business labels are not valid `DocChange-ID` values.

```bash
neodev doc change register \
  --document-id <document_id> \
  --doc-change-id <40_char_document_commit_hash> \
  --source-commit <40_char_document_commit_hash> \
  --summary "<summary>" \
  --json

neodev graph impact --doc-change-id <doc_change_id> --json
```

Low-confidence impact results are acceptable when the only evidence is document relations and no code links exist. Report that as a data/evidence limitation rather than a CLI failure.

## Controlled Documents

Controlled Markdown documents must live under one docs root. Open that root as the Obsidian vault when graph visibility matters.

Standard top-level directories:

- `prd/`
- `prototype/`
- `tech-design/`
- `neosuperpower/`
- product-domain directories such as `<domain>/`

NeoSuperpower documents live under:

- `neosuperpower/plans/`
- `neosuperpower/specs/`
- `neosuperpower/skills/<skill_name>/`
- `neosuperpower/reports/`
- `neosuperpower/templates/`

Do not create `docs/superpowers/` or generate controlled docs outside the docs root.

When migrating older Superpowers references, move new controlled workflow output to `docs/neosuperpower/` paths and update tags, aliases, and relation text to use `neosuperpower`. Do not preserve parallel `superpowers` and `neosuperpower` document trees.

Before import or DocChange registration, validate:

```bash
python plugins/neodev-rd-knowledge/sync_obsidian_links.py <docs_path>
python plugins/neodev-rd-knowledge/validate_mvp_docs.py <docs_path>
python plugins/neodev-rd-knowledge/validate_obsidian_docs.py <docs_path>
```

## Completion Evidence

For a full NeoDev self-test through the local CLI client, capture at least:

- product/version/project identifiers
- branch binding from `product version show`
- code graph `node_count` and `edge_count`
- `graph get-chain` or `graph entity-context` returning nodes with version fields
- `doc binding list` showing `product_version_id`
- `doc scan` / `doc import` counts
- `doc graph show` returning `status=ready`
- optional `doc change register` and `graph impact` output
