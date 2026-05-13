# /neodev-project-refresh-graph

Refresh or verify a project branch code graph on the remote NeoDev service.

Check the local CLI boundary first:

```bash
python plugins/neodev-rd-knowledge/check_neodev_environment.py
neodev config show
neodev cli version-check --json
```

Refresh by project name when possible:

```bash
neodev project refresh-graph --project-name <project_name> --branch <branch> --json
```

ID form is allowed when the project name is unavailable:

```bash
neodev project refresh-graph --project-id <project_id> --branch <branch> --json
```

After refresh, verify:

- `graph_id`
- `head_commit`
- `node_count > 0`
- `edge_count >= 0`
- `graph_errors` is empty

If `graph_action=skipped_unchanged`, the current remote Neo4j graph already matches the branch head and version scope.

Then query with names:

```bash
neodev product version show --project-name <project_name> --branch-name <branch> --json
neodev graph get-chain --product-code <product_code> --version-name <version_name> --project-name <project_name> --branch-name <branch> --file-path <path> --json
```

This command does not require `--version-id` or `--commit-sha`.
