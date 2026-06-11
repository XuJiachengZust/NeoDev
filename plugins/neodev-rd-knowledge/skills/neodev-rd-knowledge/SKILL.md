---
name: neodev-rd-knowledge
description: Use the local NeoDev CLI client against the configured remote NeoDev service to manage product versions, branch code graphs, version-scoped document bindings/imports, DocChange records, graph impact, and NeoSuperpower workflows.
---

# NeoDev RD Knowledge

Use the local `neodev` CLI client as the only normal boundary for NeoDev facts and state changes. The API service, PostgreSQL, Neo4j, graph refresh, document import, and DocChange state live in the remote NeoDev environment.

Direct PostgreSQL or Neo4j access is allowed only for debugging mismatches between CLI/API and storage. Do not use direct database writes as a workflow shortcut.

Shared workflow contracts live in `plugins/neodev-rd-knowledge/workflows/core-workflows.json`; plugin docs, commands, and skills should stay aligned with that file.

NeoSuperpower is the plugin-owned workflow layer. Former Superpowers planning, test-first implementation, systematic debugging, code-review, delegation, verification, and branch-completion workflows are embedded as `neosuperpower-*` skills and represented with `neosuperpower:*` phase names in this plugin. Treat `superpowers` as a migration/search keyword and third-party attribution term only.

`browser-acceptance-testing` is also embedded in this plugin for strict page acceptance workflows. Use it when a task requires browser-driven user-perspective validation with a test plan, user-confirmed detailed cases, screenshots, network evidence, diagnostics, and a final report.

Workflow weak orchestration lives in `core-workflows.json` as `neosuperpower.weak_orchestration` plus per-workflow `neosuperpower_awareness`. These fields make agents aware of relevant phases, suggested embedded skills, and evidence focus without changing the explicit CLI `steps`. Use them as soft routing and verification hints; do not treat them as extra mandatory CLI commands.

## Primary Intent Entries

Default user-facing routing is four intents:

- context: `neodev doctor`, `neodev context show`, `neodev setup repo`
- docs: `neodev docs sync`
- change: `neodev change start`, `neodev change impact`
- submit: `neodev git check`, `neodev status`

Use atomic commands as advanced troubleshooting references, compatibility paths, or hook/script internals. Do not recommend internal hook-only commands as normal user entry points. When a primary command lacks enough context, report the missing input and the next primary intent instead of hand-stitching multiple atomics.

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

## Agent Post-Push Automation

When an Agent `Bash(git push *)` tool call succeeds, the plugin PostToolUse hook runs:

```bash
post_push_graph_update.py --json
```

The script, not the hook command, discovers local context from Git, `.neodev/project.json`, `NEODEV_PROJECT_ID`, `NEODEV_PROJECT_NAME`, `NEODEV_DOC_BINDING_ID`, and the configured local `neodev` CLI. The hook must not pass remote-only business parameters such as project, branch, or commit range.

After local commit-scope validation, the script performs one server-side atomic write call:

```bash
neodev git post-push-graph-update --payload-file <local_payload_file> --json
```

The atomic CLI owns document import, DocChange registration, code DocChange linking, branch graph refresh, PostgreSQL commit/rollback, and Neo4j branch graph replacement. Do not replace this with separate `doc import`, `doc change register`, code-link, or `project refresh-graph` calls in the post-push path.

Expected result JSON contains `hook_status`, `classification_summary`, `doc_import_results`, `docchange_register_results`, `docchange_link_results`, `graph_refresh_result`, `run_record`, `rollback_status`, `errors`, and:

```json
{"skill":"neodev-rd-knowledge","action":"interpret_post_push_result"}
```

Interpret `interpret_post_push_result` as follows:

- `hook_status=success`: summarize document imports, DocChange registrations, code links, and graph refresh evidence.
- `hook_status=skipped`: report that no new commits required post-push work.
- `hook_status=failed`: report the blocking local validation error and the retry command.
- `hook_status=not_ready`: report the missing local precondition; do not run remote write commands manually unless the missing context is resolved.
- `rollback_status=rolled_back`: report that the server-side atomic command rolled back the failed update.
- `rollback_status=rollback_failed`: stop and ask for manual recovery; do not invent database or Neo4j state.
- Missing required result fields mean `invalid_result`: report the raw JSON and do not infer success.
- A `skill_hint` that does not point to `{"skill":"neodev-rd-knowledge","action":"interpret_post_push_result"}` is a `skill_hint mismatch`: do not apply this post-push interpretation contract.

Run persistence is local and stable: history is appended and latest status is overwritten under `.neodev/post_push_graph_update/` using `append_history+overwrite_latest`.

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
