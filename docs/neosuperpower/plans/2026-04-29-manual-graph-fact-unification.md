---
doc_id: NEODEV-DOC-NEOSUPERPOWER-PLANS-2026-04-29-MANUAL-GRAPH-FACT-UNIFICATION
title: Manual Graph Fact Unification Implementation Plan
aliases:
- Manual Graph Fact Unification Implementation Plan
tags:
- neodev/docs
- neodev/tech-design
- neosuperpower/plans
created: 2026-04-29
updated: 2026-04-29
related:
- '[[neosuperpower/specs/2026-04-29-manual-graph-fact-unification-design|Manual Graph
  Fact Unification Design]]'
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
  - NEODEV-DOC-NEOSUPERPOWER-SPECS-2026-04-29-MANUAL-GRAPH-FACT-UNIFICATION-DESIGN
---

# Manual Graph Fact Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make manual graph edits write into the same branch-scoped fact graph as scanner output, and make branch refresh clear old branch graph data before rebuilding.

**Architecture:** Keep `graph_*` tables as management records, but have manual node and edge mutations update `code_facts`, `branch_snapshot_facts`, operation logs, and Neo4j. Branch refresh uses an explicit cleanup service before creating the new snapshot so old manual and scan facts stop being visible for that branch.

**Tech Stack:** Python, psycopg2, pytest, PostgreSQL migrations, Neo4j Cypher.

---

### Task 1: Branch Refresh Cleanup

**Files:**
- Modify: `src/service/repositories/branch_snapshot_repository.py`
- Modify: `src/service/services/branch_snapshot_service.py`
- Modify: `src/service/services/sync_service.py`
- Test: `tests/test_code_fact_snapshot_service.py`

- [ ] **Step 1: Write failing tests**

Add a test proving `branch_snapshot_service.clear_branch_graph()` delegates cleanup with `project_id` and branch, and a test proving `sync_service.refresh_graph_for_branch()` calls cleanup before creating a replacement snapshot even when the snapshot hash matches.

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_code_fact_snapshot_service.py -q --basetemp=.codex-pytest-tmp-manual-graph`

- [ ] **Step 3: Implement cleanup**

Add repository functions to delete branch snapshots for `project_id + branch_name`, delete orphan active manual facts when safe, and expose `clear_branch_graph()` in the service. Change refresh to always rebuild after cleanup, removing the no-change shortcut for branch refresh.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_code_fact_snapshot_service.py -q --basetemp=.codex-pytest-tmp-manual-graph`

### Task 2: Manual Fact Projection

**Files:**
- Modify: `docker/migrations/021_code_fact_snapshot_rebuild.sql`
- Create: `docker/migrations/023_manual_graph_fact_unification.sql`
- Modify: `docker/Dockerfile.postgres`
- Modify: `src/service/repositories/graph_management_repository.py`
- Modify: `src/service/services/graph_management_service.py`
- Test: `tests/test_graph_manual_management_migration.py`
- Test: `tests/test_graph_manual_fact_projection.py`

- [ ] **Step 1: Write failing tests**

Add tests for operation log schema and service behavior: manual node add writes `graph_nodes`, upserts one fact, adds it to current snapshot, and logs the operation; manual node archive removes it from snapshot visibility and logs archive.

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_graph_manual_management_migration.py tests/test_graph_manual_fact_projection.py -q --basetemp=.codex-pytest-tmp-manual-graph`

- [ ] **Step 3: Implement projection**

Add `graph_operation_logs`, fact id helpers, snapshot membership helpers, and branch-aware service methods. Use existing `code_facts.node_type` values by mapping manual nodes to `Function` unless a supported fact type is explicitly provided in properties.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_graph_manual_management_migration.py tests/test_graph_manual_fact_projection.py -q --basetemp=.codex-pytest-tmp-manual-graph`

### Task 3: CLI Branch Context and Transactions

**Files:**
- Modify: `src/service/cli/commands/graph.py`
- Test: `tests/test_graph_management_cli_unit.py`

- [ ] **Step 1: Write failing tests**

Add tests proving `graph node add` passes `branch` to the service and `_with_db` commits write commands. Add parallel tests for edge add.

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_graph_management_cli_unit.py -q --basetemp=.codex-pytest-tmp-manual-graph`

- [ ] **Step 3: Implement CLI changes**

Add `--branch` to node and edge mutations, pass branch into service calls, and commit on successful DB callback with rollback on service errors.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_graph_management_cli_unit.py -q --basetemp=.codex-pytest-tmp-manual-graph`

### Task 4: Neo4j Manual Sync

**Files:**
- Create: `src/service/services/manual_graph_sync_service.py`
- Modify: `src/service/services/graph_management_service.py`
- Test: `tests/test_manual_graph_sync_service.py`

- [ ] **Step 1: Write failing tests**

Add tests for node upsert Cypher, edge upsert Cypher, node archive Cypher, and relation type normalization.

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_manual_graph_sync_service.py -q --basetemp=.codex-pytest-tmp-manual-graph`

- [ ] **Step 3: Implement sync service**

Load project Neo4j config, upsert manual nodes as `:GraphNode:CodeFact`, archive by setting status, and upsert relationships using validated relationship type names.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_manual_graph_sync_service.py -q --basetemp=.codex-pytest-tmp-manual-graph`

### Task 5: Regression Sweep

**Files:**
- Test only

- [ ] **Step 1: Run focused suite**

Run: `pytest tests/test_code_fact_snapshot_service.py tests/test_graph_manual_management_migration.py tests/test_graph_manual_fact_projection.py tests/test_graph_management_cli_unit.py tests/test_manual_graph_sync_service.py tests/test_graph_query_service_unit.py -q --basetemp=.codex-pytest-tmp-manual-graph`

- [ ] **Step 2: Fix failures**

Fix only failures caused by this change set.

- [ ] **Step 3: Final status**

Report changed files, verification command, and remaining risks.

## 关联文档
- [[neosuperpower/specs/2026-04-29-manual-graph-fact-unification-design|Manual Graph Fact Unification Design]]
