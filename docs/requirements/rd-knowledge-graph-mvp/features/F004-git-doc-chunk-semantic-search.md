---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-F004-GIT-DOC-CHUNK-SEMANTIC-SEARCH
title: "F004 Git Document Import, Chunk Embeddings, And Chunk Search"
aliases:
  - "Git Document Import, Chunk Embeddings, And Chunk Search"
tags:
  - neodev/docs
  - neodev/prd
  - neodev/requirements
created: 2026-04-28
updated: 2026-04-28
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-01-MASTER-PRD
related:
  - "[[01-master-prd]]"
---

# F004 Git Document Import, Chunk Embeddings, And Chunk Search

## 1. Scope Override

This document supersedes earlier MVP wording where conflicts exist.

- Documents are imported only from the product's Git-managed document repository.
- Direct document upload is not an MVP ingestion path.
- Controlled document directories are `prd/`, `prototype/`, `tech-design/`, and `docs/`.
- Neo4j stores document-level graph facts only.
- PostgreSQL with pgvector stores document chunks and chunk embeddings.
- Public semantic search returns document chunks, not code graph nodes.

## 2. Document Import

The import command synchronizes the configured document repository before scanning.

Required CLI:

```bash
neodev.py doc import --doc-binding-id <id> --json
```

Expected behavior:

- If `doc_bindings.repo_path` already exists, update it from Git.
- If `repo_path` is missing and `repo_url` exists, clone the repository into `repo_path`.
- Check out `doc_bindings.default_branch`.
- Scan only Markdown files under controlled directories.
- Validate existing YAML front matter rules.
- Persist document metadata, body text, and content hash.
- Mark documents missing from the current Git checkout as deleted or inactive.

## 3. Document Graph

Neo4j remains the document graph fact store.

- Each controlled document maps to one `Document` node.
- Document node identity is based on product, binding, and `doc_id`.
- Document relationships are derived from front matter, especially `relations.target`.
- Chunks do not become graph nodes in MVP.

## 4. Chunking

Chunking runs after document metadata and graph facts are updated.

The chunking strategy is:

1. Structural chunking first.
2. If a structural chunk is too long, split it with semantic-similarity chunking.
3. Preserve original document order.
4. Store chunk text, heading path, index, token estimate, content hash, and embedding status.

Structural chunking must respect:

- Markdown headings
- paragraphs
- lists
- tables
- fenced code blocks

Default thresholds:

- target chunk size: 800 tokens
- maximum structural chunk size before semantic split: 1200 tokens
- overlap: 120 tokens

## 5. Vectorization

Each chunk gets one embedding.

Embedding text includes:

- document title
- `doc_id`
- `doc_type`
- tags
- aliases
- related documents
- relation targets
- heading path
- chunk text

If a chunk content hash is unchanged, the existing embedding is reused unless force refresh is requested.

## 6. Semantic Search

`graph semantic-search` remains the public CLI command name, but its public result is chunk-level document search.

Required result fields:

- `product_version_id`
- `document_id`
- `doc_id`
- `title`
- `doc_type`
- `relative_path`
- `chunk_id`
- `chunk_index`
- `heading_path`
- `snippet`
- `score`
- `semantic_status`

The command must not return code graph node fields such as `entity_id`, `entity_type`, or code `file_path`.

## 7. Acceptance Criteria

- `docs/` Markdown files are included in document import.
- Markdown outside controlled directories is ignored.
- Git repository import is the only document ingestion path.
- Neo4j contains document-level nodes and relationships.
- PG contains document chunks and chunk embeddings.
- Unchanged chunks do not regenerate embeddings.
- `graph semantic-search` returns chunk results scoped to the product version.
