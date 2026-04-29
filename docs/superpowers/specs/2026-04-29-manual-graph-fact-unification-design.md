# Manual Graph Fact Unification Design

## Context

NeoDev now has two graph write paths:

- Scanner ingestion writes `code_facts`, `branch_snapshot_facts`, and Neo4j `GraphNode` / `CodeFact` nodes.
- Manual graph commands write `graph_node_types`, `graph_relation_types`, `graph_nodes`, and `graph_edges`.

The manual command family must no longer behave like a separate graph. A node or edge created by `neodev graph node/edge/type ...` must become part of the same branch-visible fact graph used by scanner output. Query commands should not need to know whether a node came from scanning or manual entry.

## Decision

Manual graph writes directly modify the current latest completed snapshot for the target project branch.

Manual nodes and edges are treated as normal graph facts after the write:

- Manual nodes are represented in `code_facts`.
- Manual node membership is added to `branch_snapshot_facts` for the selected latest completed snapshot.
- Manual nodes are upserted into Neo4j with the same common labels used by scanned code facts.
- Manual edges are represented in the same queryable graph as scanned edges.
- Source differences are recorded only as metadata and operation logs.

When the branch is scanned again, the scanner creates a new latest snapshot from scanner output. It does not carry forward earlier manual additions. Therefore manual nodes or edges that are not produced by the new scan naturally disappear from latest-branch queries. Historical PG rows and operation logs may remain for audit.

## CLI Scope

Manual graph commands need branch context when they affect facts:

- `graph node add/update/delete`
- `graph edge add/update/delete`

Supported locators should follow existing project and product-version patterns:

- `--project-id` or `--project-name`
- `--branch`
- optionally `--product-version-id` / `--product-code` + `--version-name` where existing command patterns already support product version lookup

The service resolves the target to:

```text
project_id + branch_name -> latest completed branch_snapshot
```

If no completed snapshot exists for the target branch, the command fails with a clear `invalid_scope` style error.

Type management commands remain project-scoped metadata operations:

- `graph type node add/list/archive`
- `graph type edge add/list/archive`

They do not modify snapshots by themselves.

## Data Model

### Existing Manual Tables

The existing `graph_*` tables remain management and audit-friendly source records:

- `graph_node_types`
- `graph_relation_types`
- `graph_nodes`
- `graph_edges`

These tables continue to store labels, type keys, display names, arbitrary properties, and status.

### Fact Tables

Manual node writes also upsert `code_facts`.

Recommended manual node fact values:

```text
fact_id        = stable manual fact id derived from graph node id
symbol_key     = stable manual symbol key derived from project/type/name or node id
node_type      = supported fact node type used by existing fact queries
file_path      = null or synthetic manual path
qualified_name = manual qualified name
name           = display name
metadata_json  = source, manual_node_id, type_key, properties, operation_id
status         = active or archived
```

Because `code_facts.node_type` currently has a restricted enum-like check constraint, implementation must either map manual graph node types to supported fact node types or widen the schema deliberately. The first implementation should keep schema risk low by mapping manual nodes to an existing supported fact type and preserving the original graph type in `metadata_json.type_key`.

`branch_snapshot_facts` is updated in place for the latest completed snapshot. Add/update adds the fact id. Delete/archive removes or archives it according to existing status semantics; latest snapshot visibility must no longer include deleted manual facts.

### Operation Logs

Add an operation log for manual graph writes:

```text
graph_operation_logs
- id
- project_id
- branch_name
- snapshot_id
- object_kind
- object_id
- operation
- before_json
- after_json
- actor
- source
- created_at
```

The log is the durable distinction between manual and scanned changes. Query behavior must not depend on the log.

## Neo4j Behavior

Manual nodes are upserted as normal queryable graph nodes:

```text
(:GraphNode:CodeFact { project_id, fact_id, id, name, ... })
```

Manual-specific details are properties, not query labels required by core traversal:

```text
source = "manual"
manual_node_id = ...
type_key = ...
```

Manual edges are synchronized to Neo4j relationships between `:GraphNode` endpoints. Relationship type keys must be validated or normalized before being used as Cypher relationship types. Original type keys stay on relationship properties.

Traversal queries must continue to derive branch visibility from PG snapshot membership. After branch rescan, latest snapshot membership changes, so old manual facts stop participating in latest branch traversals.

## Error Handling

Manual fact writes should be transactional:

1. Validate project, branch, snapshot, node type, and relation type.
2. Write or update the `graph_*` management row.
3. Upsert or archive fact table rows.
4. Write operation log.
5. Commit PG transaction.
6. Sync Neo4j.

If PG work fails, no Neo4j sync runs.

If Neo4j sync fails after PG commit, return a failure that includes the committed operation id and enough context to retry sync. The PG operation log remains the source of truth for recovery.

## Testing

Add targeted tests for:

- `graph node add` creates or updates `graph_nodes`, `code_facts`, `branch_snapshot_facts`, and operation logs.
- `graph node delete/archive` removes latest snapshot visibility.
- Branch rescan creates a new snapshot without carrying manual snapshot membership.
- `graph entity-context` and `graph get-chain` can see manual nodes only when their fact ids are present in the latest snapshot.
- Manual type keys are preserved in metadata even when mapped to an existing `code_facts.node_type`.
- PG transaction rollback prevents partial manual fact writes.

## Out Of Scope

- A permanent manual overlay that survives rescans.
- Separate query behavior for manual graph nodes.
- A UI workflow for manual graph editing.
- Full historical diff visualization for manual operations.

## Self Review

The design has no placeholder sections. The branch overwrite behavior is explicit: manual writes modify the current latest completed snapshot, while rescans create a new latest snapshot from scanner output and do not carry manual additions forward. Manual and scanned nodes are query-equivalent; only metadata and operation logs preserve source.
