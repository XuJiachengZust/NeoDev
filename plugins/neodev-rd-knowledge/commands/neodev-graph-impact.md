# /neodev-graph-impact

Use this command to inspect implementation impact for a DocChange through NeoDev CLI.

Required boundary:

- Run `python neodev.py cli version-check --json` first.
- Use `python neodev.py graph impact --doc-change-id <doc_change_id> --json`.
- Use `python neodev.py graph semantic-search --product-code <product_code> --version-name <version_name> --query <query> --json` only when more evidence is needed.
- Explain only facts returned by NeoDev CLI payloads.
