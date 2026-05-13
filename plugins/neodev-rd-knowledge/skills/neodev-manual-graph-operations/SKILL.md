---
name: neodev-manual-graph-operations
description: Use when manually inspecting, creating, updating, deleting, or validating NeoDev graph types, graph nodes, graph edges, or branch graph evidence through the local neodev CLI.
---

# NeoDev Manual Graph Operations

Use the local `neodev` CLI as the normal boundary. Direct PostgreSQL or Neo4j access is diagnostic only, and direct writes are not a manual graph workflow.

## Start

Always confirm the target service and client contract first:

```bash
neodev config show
neodev cli version-check --json
```

Resolve the project/version/branch context before writing graph facts:

```bash
neodev product version show --product-code <product_code> --version-name <version_name> --json
neodev product version show --project-name <project_name> --branch-name <branch> --json
neodev project show --project-id <project_id> --json
```

Prefer names for product/version branch navigation. Use IDs for manual graph management commands that require `--project-id`.

## Type Vocabulary

`graph type` commands return the allowed type vocabulary for manual graph validation. They are not an observed Neo4j branch graph inventory.

The returned rows merge built-in graph/document types with project-owned manual types. `id: null` means a built-in type that is valid for the project but is not stored as a manual PostgreSQL type row.

```bash
neodev graph type node list --project-id <project_id> --json
neodev graph type edge list --project-id <project_id> --json
```

Common built-in node types include `Project`, `BranchGraph`, `DocumentGraph`, `Document`, `Folder`, `File`, `Class`, `Method`, `Function`, and `Process`.

Common built-in edge types include `CALLS`, `CONTAINS`, `DEFINES`, `IMPORTS`, `HAS_BRANCH_GRAPH`, `HAS_DOCUMENT`, `LINKS_TO_CODE`, and `RELATES_TO`.

## Manual Types

Create manual types only when the built-in vocabulary does not express the intended project-specific fact.

```bash
neodev graph type node add --project-id <project_id> --key <TYPE_KEY> --name "<name>" --json
neodev graph type edge add --project-id <project_id> --key <TYPE_KEY> --name "<name>" --allowed-from-type <NODE_TYPE> --allowed-to-type <NODE_TYPE> --cross-project-allowed --json
```

Endpoint constraints refer to node type keys in the owner project. If `--allowed-from-type` or `--allowed-to-type` is omitted, that side is unrestricted.

## Manual Nodes And Edges

Manual node and edge commands manage controlled manual graph rows. When `--branch` is supplied, the service also records a manual operation for the current branch snapshot path; these commands are still not branch graph dumps.

```bash
neodev graph node add --project-id <project_id> --branch <branch> --node-id <node_id> --type <TYPE_KEY> --name "<name>" --prop key=value --json
neodev graph node list --project-id <project_id> --type <TYPE_KEY> --json
neodev graph node show --project-id <project_id> --node-id <node_id> --json
neodev graph node update --project-id <project_id> --branch <branch> --node-id <node_id> --name "<name>" --prop key=value --json
neodev graph node delete --project-id <project_id> --branch <branch> --node-id <node_id> --json
```

```bash
neodev graph edge add --project-id <owner_project_id> --branch <branch> --edge-id <edge_id> --from-node-id <from_node_id> --to-node-id <to_node_id> --type <TYPE_KEY> --json
neodev graph edge list --project-id <project_id> --node-id <node_id> --type <TYPE_KEY> --json
neodev graph edge show --project-id <project_id> --edge-id <edge_id> --json
neodev graph edge update --project-id <project_id> --branch <branch> --edge-id <edge_id> --type <TYPE_KEY> --prop key=value --json
neodev graph edge delete --project-id <project_id> --branch <branch> --edge-id <edge_id> --json
```

For cross-project edges, add `--from-project-id` and/or `--to-project-id` when endpoint node IDs are not globally unambiguous. The edge owner project must match either endpoint project, and the relation type must allow cross-project edges.

## Branch Graph Evidence

Use branch graph query commands when the question is about code/document evidence already indexed in Neo4j:

```bash
neodev graph get-chain --product-code <product_code> --version-name <version_name> --project-name <project_name> --branch-name <branch> --symbol <symbol> --json
neodev graph entity-context --product-code <product_code> --version-name <version_name> --project-name <project_name> --branch-name <branch> --entity-id <entity_id> --json
```

If the user asks for "all actual node labels or relation types currently observed in Neo4j" and the CLI has no inventory command for that, say the CLI does not expose that inventory yet. Do not substitute `graph type ... list` as observed graph evidence.

## Verification

After manual changes, verify with the matching `type list`, `node show/list`, or `edge show/list` command. If the change is meant to affect branch evidence, also run `graph get-chain` or `graph entity-context` against the product/version/project/branch context and report the returned IDs/counts.
