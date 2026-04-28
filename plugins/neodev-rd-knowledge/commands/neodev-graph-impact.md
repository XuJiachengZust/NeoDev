# /neodev-graph-impact

通过本地 `neodev` CLI 调用已配置的远程 NeoDev 服务，检查某个 DocChange 的实现影响范围。

必要边界：

- 先执行 `python plugins/neodev-rd-knowledge/check_neodev_environment.py`。
- 先执行 `neodev config show` 和 `neodev cli version-check --json`。
- 使用 `neodev graph impact --doc-change-id <doc_change_id> --json`。
- 只有需要补充文档证据时，才使用 `neodev graph semantic-search --product-code <product_code> --version-name <version_name> --query <query> --json`。
- 只解释远程 NeoDev CLI payload 返回的事实。
