---
name: neosuperpower
description: Use NeoDev-owned workflow discipline for requirements, implementation, debugging, verification, document graph maintenance, and Obsidian/NeoDev relation closure.
---

# NeoSuperpower

NeoSuperpower is the NeoDev plugin-owned workflow layer. Use it in NeoDev documents, workflow metadata, generated plans, and Obsidian paths.

## Required Phases

- Requirements or design: clarify intent, constraints, affected docs/code, and acceptance evidence before writing implementation.
- Implementation: prefer small, testable changes; keep NeoDev state changes behind `neodev` CLI.
- Failure investigation: find root cause before fixes; gather evidence across CLI, API, database, graph, and file layers when needed.
- Completion: verify with fresh commands before claiming success.

## Document Graph Closure

For controlled docs, NeoDev and Obsidian must both close:

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
  --docs-root <docs_path> \
  --output <docs_path>/<relative_file>.md \
  --doc-id <real_doc_id> \
  --title "<title>" \
  --doc-type tech-design \
  --product-key <product_key> \
  --target <existing_target_doc_id>
```

Then run `sync_obsidian_links.py`, followed by both validators, before scan/import.

```bash
python plugins/neodev-rd-knowledge/sync_obsidian_links.py <docs_path>
python plugins/neodev-rd-knowledge/validate_mvp_docs.py <docs_path>
python plugins/neodev-rd-knowledge/validate_obsidian_docs.py <docs_path>
```

## Naming

Use `neosuperpower` in plugin metadata, docs, tags, and Obsidian paths. Phase labels such as `neosuperpower:implementation` and `neosuperpower:verification-before-completion` are handled by this skill.
