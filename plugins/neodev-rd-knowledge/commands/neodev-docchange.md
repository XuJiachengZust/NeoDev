# /neodev-docchange

通过本地 `neodev` CLI 调用已配置的远程 NeoDev 服务，登记或查看受控文档变更。

必要边界：

- 写入流程开始前，先执行 `python plugins/neodev-rd-knowledge/check_neodev_environment.py`。
- 写入流程开始前，先执行 `neodev config show` 和 `neodev cli version-check --json`。
- 先使用 `python plugins/neodev-rd-knowledge/validate_mvp_docs.py prd prototype tech-design` 校验 MVP 文档。
- 登记前先执行 `neodev doc binding list --product-code <product_code> --json` 获取 active `doc_binding_id`。
- 如果没有 active 文档绑定，执行 `neodev doc binding create --product-code <product_code> --project-id <doc_project_id> --branch <branch> --json` 创建绑定。
- 登记前先执行 `neodev doc import --doc-binding-id <doc_binding_id> --force --json`，确保目标文档返回可靠的 `last_seen_commit`。
- 只使用 `neodev doc change register --document-id <document_id> --json` 登记变更；未显式传入时，DocChange-ID 和 source_commit 必须使用目标文档的 40 位 Git commit hash。
- 不允许直接写 PostgreSQL 或 Neo4j。
