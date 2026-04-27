# /neodev-graph-impact

Use this command to inspect implementation impact for a DocChange through the local `neodev` CLI client calling the configured remote NeoDev service.

Required boundary:

- Run `python plugins/neodev-rd-knowledge/check_neodev_environment.py` first.
- Run `neodev config show` and `neodev cli version-check --json` first.
- Use `neodev graph impact --doc-change-id <doc_change_id> --json`.
- Use `neodev graph semantic-search --product-code <product_code> --version-name <version_name> --query <query> --json` only when more evidence is needed.
- Explain only facts returned by remote NeoDev CLI payloads.
