---
name: neosuperpower
description: Use NeoDev-owned workflow discipline for requirements, planning, TDD/test-first implementation, systematic debugging, code review, verification, document graph maintenance, and Obsidian/NeoDev relation closure; includes migrated Superpowers workflows under NeoSuperpower naming.
---

# NeoSuperpower

NeoSuperpower is the NeoDev plugin-owned workflow layer. It keeps requirements, planning, implementation, debugging, review, verification, document graph maintenance, and version-branch graph work closed through evidence.

Former Superpowers workflows are embedded as NeoSuperpower skills in this repository. Use `neosuperpower-*` skill names for skill discovery and `neosuperpower:*` phase names in plugin metadata, docs, plans, and reports; keep `superpowers` only as a migration/search keyword.

## Required Phases

- Requirements or design: clarify intent, constraints, affected docs/code, product/version/branch scope, and acceptance evidence before implementation.
- Planning: turn approved requirements into small ordered tasks with verification gates and explicit NeoDev document or graph touch points.
- Implementation: prefer small, testable changes; use test-first discipline for behavior changes; keep NeoDev facts and state changes behind the local `neodev` CLI client.
- Failure investigation: find root cause before fixes; gather evidence across CLI, API, database, graph, and file layers when needed.
- Review: check requirement fit, code quality, stale docs, and direct cleanup after implementation.
- Completion: verify with fresh commands before claiming success, committing, pushing, or deploying.

## Integrated Superpowers Discipline

NeoSuperpower owns the local skill names for the former Superpowers process skills:

| Former Superpowers workflow | Embedded NeoSuperpower skill | NeoSuperpower phase |
| --- | --- | --- |
| brainstorming | `neosuperpower-brainstorming` | `neosuperpower:requirements-or-design` |
| writing-plans / executing-plans | `neosuperpower-writing-plans`, `neosuperpower-executing-plans` | `neosuperpower:planning` |
| test-driven-development | `neosuperpower-test-driven-development` | `neosuperpower:test-driven-implementation` |
| systematic-debugging | `neosuperpower-systematic-debugging` | `neosuperpower:failure-investigation` |
| requesting-code-review / receiving-code-review | `neosuperpower-requesting-code-review`, `neosuperpower-receiving-code-review` | `neosuperpower:review` |
| dispatching-parallel-agents / subagent-driven-development | `neosuperpower-dispatching-parallel-agents`, `neosuperpower-subagent-driven-development` | `neosuperpower:delegated-execution` |
| verification-before-completion | `neosuperpower-verification-before-completion` | `neosuperpower:verification-before-completion` |
| finishing-a-development-branch | `neosuperpower-finishing-a-development-branch` | `neosuperpower:branch-completion` |
| using-superpowers | `neosuperpower-using-neosuperpower` | `neosuperpower:skill-routing` |
| using-git-worktrees | `neosuperpower-using-git-worktrees` | `neosuperpower:workspace-isolation` |
| writing-skills | `neosuperpower-writing-skills` | `neosuperpower:skill-maintenance` |
| requirement-refiner | `neosuperpower-requirement-refiner` | `neosuperpower:requirements-or-design` |

When a workflow document, generated plan, report, command, or plugin capability would previously say `superpowers`, write `neosuperpower` instead. Preserve upstream Superpowers terminology only when explaining migration compatibility, third-party attribution, or searching existing references.

## Weak Orchestration And Awareness

`plugins/neodev-rd-knowledge/workflows/core-workflows.json` carries NeoSuperpower awareness fields:

- `neosuperpower.weak_orchestration`: global advisory contract for embedded skills.
- `workflow_awareness_defaults`: field meanings for workflow-level awareness.
- `workflows.*.neosuperpower_awareness`: per-workflow phase hooks, suggested skills, and evidence focus.

Treat these as soft routing signals:

- Use `phase_hooks` to notice which NeoSuperpower discipline applies to the current task.
- Use `suggested_skills` only when the task, risk, or evidence actually matches the skill trigger.
- Use `evidence_focus` as a reporting and verification checklist.
- Do not insert awareness hooks into `steps`; keep CLI execution order governed by each workflow's explicit steps.
- If `non_blocking` is `true`, read-only discovery and low-risk context gathering may proceed without stopping for a formal plan.
- If `non_blocking` is `false`, collect the listed evidence before making completion, commit, push, or state-change claims.

## NeoDev CLI Boundary

Use the local CLI client for normal workflow operations:

```bash
neodev config show
neodev cli version-check --json
```

If the `neodev` shim is not installed while working in this repository, use:

```bash
python neodev.py --server <remote_api_url> <command> --json
```

Do not treat direct PostgreSQL or Neo4j access as the canonical workflow. Use direct DB/graph inspection only to debug or verify a suspected CLI/API/storage mismatch.

## Version Scope

Current NeoDev workflows are version scoped:

- Code graph queries should use product/version/project/branch names discovered from `product version show`.
- Document bindings must include a product version.
- Imported documents must carry `product_version_id`.
- Document graph reads use `--product-name` and `--version-name`.

Recommended discovery sequence:

```bash
neodev product version show --product-code <product_code> --version-name <version_name> --json
neodev product version show --project-name <project_name> --branch-name <branch> --json
```

Then query code graph context with the returned names:

```bash
neodev graph get-chain \
  --product-code <product_code> \
  --version-name <version_name> \
  --project-name <project_name> \
  --branch-name <branch> \
  --file-path <path> \
  --json
```

## Document Graph Closure

For controlled docs, NeoDev and Obsidian must both close:

- All generated controlled docs live under one `<docs_root>`.
- Open `<docs_root>` as the Obsidian vault when graph visibility matters; do not use nested vault roots as the source of truth.
- Use these standard top-level directories: `prd/`, `prototype/`, `tech-design/`, `neosuperpower/`, or a product-domain directory such as `<domain>/`.
- NeoSuperpower-generated workflow docs live under `neosuperpower/plans/`, `neosuperpower/specs/`, `neosuperpower/skills/<skill_name>/`, `neosuperpower/reports/`, or `neosuperpower/templates/`.
- Do not create `docs/superpowers/` or generate controlled docs outside `<docs_root>`.
- Every generated document starts with YAML front matter.
- Required fields are `doc_id`, `title`, `aliases`, `tags`, `created`, `updated`, `related`, `doc_type`, `product_key`, `status`, and `relations.target`.
- `doc_type` is one of `prd`, `prototype`, or `tech-design`; `status` is one of `draft`, `active`, or `deprecated`.
- `relations.target` contains only real document `doc_id` values.
- `related` contains Obsidian wikilinks to the target files.
- The body includes a generated `## 关联文档` section with the same target wikilinks.
- Tags use `neosuperpower` for workflow-owned material, for example `neosuperpower/generated` or `<product_key>/neosuperpower`.

Generate a new controlled document with the plugin generator when possible:

```bash
python plugins/neodev-rd-knowledge/generate_mvp_doc.py \
  --output <docs_path>/<relative_file>.md \
  --doc-id <real_doc_id> \
  --title "<title>" \
  --doc-type tech-design \
  --product-key <product_key> \
  --target <existing_target_doc_id>
```

Then run:

```bash
python plugins/neodev-rd-knowledge/sync_obsidian_links.py <docs_path>
python plugins/neodev-rd-knowledge/validate_mvp_docs.py <docs_path>
python plugins/neodev-rd-knowledge/validate_obsidian_docs.py <docs_path>
```

Import through a version-scoped binding:

```bash
neodev doc binding create \
  --product-code <product_code> \
  --version-name <version_name> \
  --project-name <project_name> \
  --repo-path <repo_path> \
  --branch <branch> \
  --json

neodev doc import --doc-binding-id <doc_binding_id> --json
neodev doc graph show --product-name <product_name> --version-name <version_name> --json
```

## Naming

Use `neosuperpower` in plugin metadata, docs, tags, and Obsidian paths. Phase labels such as `neosuperpower:implementation` and `neosuperpower:verification-before-completion` are handled by this skill.
