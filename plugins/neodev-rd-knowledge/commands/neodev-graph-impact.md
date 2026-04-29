# /neodev-graph-impact

用于通过远程 NeoDev 服务查询 DocChange 的影响范围。

执行前先确认远程 CLI 环境：

```bash
python plugins/neodev-rd-knowledge/check_neodev_environment.py
neodev config show
neodev cli version-check --json
```

查询影响范围：

```bash
neodev graph impact --doc-change-id <doc_change_id> --json
```

代码图谱不再提供语义搜索入口；需要代码上下文时使用 `graph entity-context` 或 `graph get-chain`。
