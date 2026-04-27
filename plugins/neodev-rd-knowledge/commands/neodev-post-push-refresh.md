# /neodev-post-push-refresh

Use this command after a successful push to refresh NeoDev graph context through the local `neodev` CLI client calling the configured remote NeoDev service.

Required boundary:

- Run `python plugins/neodev-rd-knowledge/check_neodev_environment.py` first.
- Run `neodev config show` and `neodev cli version-check --json` first.
- Refresh with `neodev git post-push-refresh --project-id <project_id> --branch <branch> --commit-sha <commit_sha> --json`.
- Use `neodev graph refresh-nodes --product-code <product_code> --version-name <version_name> --project-id <project_id> --branch <branch> --commit-sha <commit_sha> --json` only for explicit narrower refreshes.
- Do not write PostgreSQL or Neo4j directly.
