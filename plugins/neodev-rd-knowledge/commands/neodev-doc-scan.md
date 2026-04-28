# /neodev-doc-scan

通过本地 `neodev` CLI 调用已配置的远程 NeoDev 服务，扫描受控 PRD、原型和技术设计文档。

必要边界：

- 远程 CLI 工作流开始前，先执行 `python plugins/neodev-rd-knowledge/check_neodev_environment.py`。
- 扫描前执行 `python plugins/neodev-rd-knowledge/validate_mvp_docs.py prd prototype tech-design`。
- 如果校验返回 `ok=false`，停止后续流程。
- 使用 `neodev config show` 确认本地客户端配置。
- 只使用 `neodev doc scan --doc-binding-id <doc_binding_id> --json` 扫描。
- 不允许绕过远程 NeoDev 服务直接写 PostgreSQL 或图数据库。
