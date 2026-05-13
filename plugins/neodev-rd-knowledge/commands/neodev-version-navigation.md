# /neodev-version-navigation

Discover product/version/project/branch names and use them for code and document graph navigation.

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

Expected fields:

- `product.name`
- `version.version_name`
- `branches[].project_name`
- `branches[].branch_name`
- `query_params[]`
- `resolved_versions[]` for branch lookup

Use the returned names directly:

```bash
neodev graph get-chain \
  --product-code <product_code> \
  --version-name <version_name> \
  --project-name <project_name> \
  --branch-name <branch> \
  --file-path <path> \
  --json

neodev doc graph show \
  --product-name <product_name> \
  --version-name <version_name> \
  --json
```

`product version show` is read-only. It must not refresh code graphs, import documents, or query Neo4j.
