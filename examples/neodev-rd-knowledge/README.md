# NeoDev RD Knowledge Minimal E2E

这个示例用于演示产品、文档、项目分支和图谱刷新之间的最小闭环。

## 目录

- `plugins/neodev-rd-knowledge`
- `plugins/neodev-rd-knowledge/skills/neodev-rd-knowledge/SKILL.md`
- `plugins/neodev-rd-knowledge/workflows/core-workflows.json`
- `examples/neodev-rd-knowledge/doc-repo`
- `examples/neodev-rd-knowledge/project-repo`

## 前置

先配置远程服务：

```bash
neodev config set-server <remote-url>
neodev config show
neodev cli version-check --json
```

## 示例步骤

`manifest.json` 的 `demo_steps` 给出了可复现命令链：

1. 创建产品和版本。
2. 绑定产品版本到项目分支。
3. 扫描文档并登记 DocChange。
4. 查询影响范围。
5. 验证提交消息。
6. 使用 `neodev project refresh-graph --project-id <project_id> --branch <branch> --json` 重建分支图谱。

代码图谱不再使用提交级增量刷新，也不再使用代码语义搜索。

## Three-Client Plugin Use

- Codex 使用 `plugins/neodev-rd-knowledge/.codex-plugin/plugin.json` 和 bundled skill。
- Claude Code 使用 `.claude-plugin`、`commands/`、`agents/`、`hooks/hooks.json`。
- Cursor 使用 `.cursor/rules/*.mdc`，分发副本在 `plugins/neodev-rd-knowledge/cursor/rules/`。

执行 `doc scan` 或 `doc change register` 前可校验受控文档：

```bash
python plugins/neodev-rd-knowledge/validate_mvp_docs.py examples/neodev-rd-knowledge/doc-repo
```
