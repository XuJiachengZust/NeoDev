# /neodev-doc-scan

通过本地 `neodev` CLI 调用已配置的远程 NeoDev 服务，导入受控 PRD、原型和技术设计文档，并可靠写入文档 Git commit。

必要边界：

- 远程 CLI 工作流开始前，先执行 `python plugins/neodev-rd-knowledge/check_neodev_environment.py`。
- 导入前执行 `python plugins/neodev-rd-knowledge/validate_mvp_docs.py <docs_path>` 和 `python plugins/neodev-rd-knowledge/validate_obsidian_docs.py <docs_path>`。
- 如果校验返回 `ok=false`，停止后续流程。
- 使用 `neodev config show` 确认本地客户端配置。
- 先执行 `neodev doc binding list --product-code <product_code> --json` 获取 active `doc_binding_id`。
- 如果没有 active 文档绑定，执行 `neodev doc binding create --product-code <product_code> --project-id <doc_project_id> --branch <branch> --json` 创建绑定。
- 只使用 `neodev doc import --doc-binding-id <doc_binding_id> --force --json` 导入；返回文档摘要中的 `last_seen_commit` 是后续 DocChange-ID 的事实来源。
- 导入成功后，图谱中应由服务投影 `Project -[:HAS_DOCUMENT]-> Document`，不要手工写关系。
- 不允许绕过远程 NeoDev 服务直接写 PostgreSQL 或图数据库。
