# NeoDev CLI And Metadata Foundation Design

## 1. Scope

This design covers only the first implementation slice of the RD knowledge graph MVP:

- `T001` CLI shell and unified result contract
- `T002` lightweight metadata model and migration

Explicitly out of scope for this slice:

- product/version business workflows in `T003`
- document scan and DocChange lifecycle commands in `T004` and `T005`
- branch analysis orchestration, graph refresh, semantic search, git verification, plugin, and skill delivery

The goal of this slice is to establish a stable command execution shell and a persistent metadata foundation that later tasks can build on without reworking the base contract.

## 2. Design Decisions

### 2.1 CLI form

The CLI will use Python standard library `argparse` instead of adding a new framework.

Reasons:

- the repository does not currently use Typer or Click
- `argparse` avoids new dependency and environment churn
- this slice needs contract stability more than CLI ergonomics

Two entry styles will be supported and will share the same implementation:

- internal module entry: `python -m service.cli.main ...`
- repo root launcher: `python neodev.py ...`

The repo root launcher exists so future plugin and skill code can call a stable top-level command without knowing Python module layout.

### 2.2 Result contract

Every CLI command in this slice will support `--json` and return a unified top-level structure:

- `ok`
- `command`
- `timestamp`
- `data`
- `errors`

Human-readable output may exist for local use, but JSON is the canonical protocol for automation.

Error categories implemented in this slice:

- `invalid_argument`
- `not_found`
- `conflict`
- `not_ready`
- `internal_error`
- `version_mismatch`

Each error category will map to a stable process exit code through a shared CLI error adapter.

### 2.3 Initial command surface

This slice will not pretend later business features already exist. Command groups will be introduced in a controlled way:

- `cli version-check` will be implemented for real
- the shared CLI framework will be ready for `product`, `doc`, `graph`, and `git` groups
- only command groups needed to prove routing and contract behavior will be registered now

If a future-facing command is registered early, it must fail explicitly with structured `not_ready` output instead of partial behavior.

## 3. File Layout

New CLI code will be added under `src/service/cli/`:

- `main.py`: parser bootstrap and top-level dispatch
- `output.py`: success/error JSON payload builders and human-readable rendering helpers
- `errors.py`: typed CLI errors, category mapping, exit-code mapping
- `commands/__init__.py`: command registration entry
- `commands/cli.py`: `cli version-check`
- `commands/product.py`: reserved command-group registration if needed for parser shape

New repo-root launcher:

- `neodev.py`

The launcher will only delegate into `service.cli.main` and will not contain business logic.

## 4. Metadata Boundary

Existing tables and repositories already present in the codebase will be treated as baseline instead of being redesigned in this slice:

- `products`
- `product_versions`
- `product_version_branches`
- `ai_preprocess_status`

New metadata introduced in this slice:

- `doc_bindings`
- `documents`
- `doc_changes`
- `code_change_links`
- `dangerous_commit_records`

These tables are the minimum needed to support later document governance, DocChange lifecycle, commit linkage, and dangerous-commit tracking without forcing those facts into graph storage.

`BranchAnalysisTask` will not get a new table yet. The existing `ai_preprocess_status` table remains the temporary system of record for branch-analysis runtime state, and later tasks will access it through an adapter instead of binding directly to raw table semantics everywhere.

## 5. Metadata Model

### 5.1 `doc_bindings`

Purpose:
associate a product with its controlled documentation repository and scanning root.

Minimum fields:

- `id`
- `product_id`
- `repo_path`
- `repo_url`
- `default_branch`
- `is_active`
- `created_at`
- `updated_at`

Constraints:

- one active doc binding per product in MVP
- foreign key to `products`

### 5.2 `documents`

Purpose:
persist scanned document metadata independent from graph enrichment.

Minimum fields:

- `id`
- `doc_binding_id`
- `doc_id`
- `doc_type`
- `relative_path`
- `title`
- `front_matter_json`
- `relations_json`
- `status`
- `last_seen_commit`
- `last_scanned_at`
- `created_at`
- `updated_at`

Constraints:

- unique `doc_id`
- unique `(doc_binding_id, relative_path)`

### 5.3 `doc_changes`

Purpose:
represent implementation-facing change records generated from controlled documentation changes.

Minimum fields:

- `id`
- `doc_change_id`
- `document_id`
- `status`
- `source_commit`
- `summary`
- `details_json`
- `created_by`
- `implemented_at`
- `created_at`
- `updated_at`

Constraints:

- unique `doc_change_id`
- status limited to MVP states:
  - `pending_implementation`
  - `in_implementation`
  - `implemented`

### 5.4 `code_change_links`

Purpose:
persist the fact that a code commit references a DocChange.

Minimum fields:

- `id`
- `doc_change_id`
- `project_id`
- `branch`
- `commit_sha`
- `commit_message`
- `created_at`

Constraints:

- foreign key to `doc_changes`
- index on `(project_id, branch, commit_sha)`

### 5.5 `dangerous_commit_records`

Purpose:
track risky commits that were explicitly allowed to proceed and need follow-up resolution.

Minimum fields:

- `id`
- `project_id`
- `branch`
- `commit_sha`
- `risk_level`
- `reason`
- `status`
- `resolved_by`
- `resolved_at`
- `extra_json`
- `created_at`
- `updated_at`

Constraints:

- index on `(project_id, status, created_at)`
- status supports at least `open` and `resolved`

## 6. Implementation Approach

### 6.1 CLI architecture

The CLI will use a thin command layer over repository and service code:

- parser layer parses arguments only
- command handlers call service/repository functions
- output layer formats results
- error layer translates exceptions into category + exit code

This avoids coupling CLI payload shape to FastAPI response shape and keeps later HTTP and CLI evolution independent.

### 6.2 Migration strategy

Migration will follow the existing `docker/migrations/*.sql` pattern with a new incremental SQL file.

The migration must be idempotent and additive:

- create missing tables
- add needed indexes and constraints
- avoid destructive alteration of existing tables in this slice

This keeps startup migration behavior safe under the current `service.migrate.run_migrations()` model.

### 6.3 Repository strategy

For new metadata tables, repository modules will be added under `src/service/repositories/`.

Repository rules for this slice:

- direct SQL is acceptable and consistent with the existing codebase
- return plain `dict` rows to match current repository style
- keep write operations narrow and explicit
- do not prematurely add orchestration logic into repositories

No new service layer will be created unless the command flow needs orchestration beyond a single repository call. This keeps the first slice small and avoids speculative abstractions.

## 7. Testing Strategy

### 7.1 CLI tests

Tests for `T001` will verify:

- `python neodev.py ... --json` returns the required top-level fields
- `python -m service.cli.main ... --json` returns equivalent behavior
- `cli version-check --json` succeeds with stable shape
- invalid arguments map to structured error payloads and stable non-zero exit codes
- not-yet-implemented command surfaces return explicit `not_ready` if exposed

### 7.2 Metadata tests

Tests for `T002` will verify:

- migration creates the new tables successfully
- repository create/get/list/update operations behave correctly
- unique constraints hold for `doc_change_id`, `doc_id`, and document path scope
- dangerous commit resolution writes `resolved_by` and `resolved_at`
- audit timestamps are present

### 7.3 Acceptance evidence

Before claiming completion, the following evidence must exist:

- automated tests for CLI contract and metadata repositories pass
- at least one real command run succeeds, specifically:
  - `python neodev.py cli version-check --json`

## 8. Risks And Guardrails

Risk:
the CLI may drift into a second application surface with duplicated business logic.

Guardrail:
keep the CLI thin and push reusable behavior down into repositories or focused services only when needed.

Risk:
metadata models may overreach and lock in later workflow semantics too early.

Guardrail:
this slice adds only persistence structures and stable identifiers; later workflow rules remain in later tasks.

Risk:
future tasks may depend directly on `ai_preprocess_status` table shape.

Guardrail:
later branch-analysis work must read runtime task state through an adapter, preserving freedom to introduce a dedicated task model later.

## 9. Done Criteria For This Slice

This slice is complete when:

- `neodev.py` works as a stable repo-root CLI entry
- `src/service/cli/` provides shared parsing, output, and error infrastructure
- `cli version-check` is implemented and returns the agreed contract
- the new metadata tables exist through migration
- repository access exists for the new metadata objects
- automated tests cover the CLI contract and metadata persistence
- at least one real CLI invocation is executed as final verification
