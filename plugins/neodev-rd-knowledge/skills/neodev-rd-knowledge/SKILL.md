---
name: neodev-rd-knowledge
description: Use when working in NeoDev RD knowledge workflows that need DocChange registration, graph impact/context, product-version branch analysis, Git pre-push verification, dangerous commit handling, or post-push refresh through the NeoDev CLI.
---

# NeoDev RD Knowledge

Use this skill to guide NeoDev knowledge-graph and Git consistency workflows. This skill is an orchestration layer only: every real action must go through `python neodev.py ... --json`.

## Required Boundary

- Start write or risk-sensitive workflows with `cli version-check`.
- Do not parse human text output; request `--json` and use the structured payload.
- Do not create extra state machines in prompts or scripts.
- 不要直接写 PostgreSQL。
- 不要直接写 Neo4j。
- Do not run ad hoc SQL, graph queries, or persistence scripts as a substitute for a NeoDev CLI command.

## Workflow Source

The canonical command order is in `workflows/core-workflows.json` in this plugin. Use that file for exact step names, command templates, and shared plugin/skill workflow alignment.

## Main Flows

### Document Change To Implementation

1. Run `cli version-check`.
2. Register the controlled change with `doc change register`.
3. Read impact with `graph impact`.
4. Add context with `graph semantic-search`, `graph entity-context`, and `graph get-chain` when needed.
5. Use the CLI facts to plan code edits; do not invent affected files without evidence.

### Branch Analysis

1. Run `cli version-check`.
2. Start analysis with `product version analyze`.
3. Read progress with `product version analyze-status`.
4. Use `product version watch-status` as a single status read; external orchestration controls repeated polling.

### Pre-Push Verification

1. Check that the commit message contains exactly one `DocChange-ID`.
2. Run `git verify-doc-change`.
3. If risk is reported, explain it and require explicit user confirmation before continuing.
4. Use `git dangerous-commit list` to inspect pending risk items.

### Post-Push Refresh

1. After a successful push, run `git post-push-refresh`.
2. If a smaller or explicit scope is needed, use `graph refresh-nodes`.
3. Use `graph get-chain` to inspect follow-up dependency or impact chains.

## Result Interpretation

- Treat `ok=false` as blocking unless the user explicitly chooses a safe alternative.
- Treat `version_mismatch` as a stop condition for high-risk write flows.
- Explain `semantic_status=degraded` as a degraded graph or embedding state, not as a command failure.
- Keep user-facing explanations tied to fields returned by the CLI payload.
