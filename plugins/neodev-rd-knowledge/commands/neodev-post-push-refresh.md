# /neodev-post-push-refresh

Use this command after a successful push to refresh NeoDev graph context through NeoDev CLI.

Required boundary:

- Run `python neodev.py cli version-check --json` first.
- Refresh with `python neodev.py git post-push-refresh --project-id <project_id> --branch <branch> --commit-sha <commit_sha> --json`.
- Use `python neodev.py graph refresh-nodes --product-code <product_code> --version-name <version_name> --project-id <project_id> --branch <branch> --commit-sha <commit_sha> --json` only for explicit narrower refreshes.
- Do not write PostgreSQL or Neo4j directly.
