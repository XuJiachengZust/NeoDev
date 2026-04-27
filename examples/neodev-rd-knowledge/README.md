# NeoDev RD Knowledge Minimal E2E

这个目录提供 T014 的最小联调样例，用于把 T001-T013 串成一条可复现主链路。

## 范围

- 官方插件：`plugins/neodev-rd-knowledge`
- 官方 skill：`plugins/neodev-rd-knowledge/skills/neodev-rd-knowledge/SKILL.md`
- 共享工作流：`plugins/neodev-rd-knowledge/workflows/core-workflows.json`
- 示例文档仓库：`examples/neodev-rd-knowledge/doc-repo`
- 示例项目仓库：`examples/neodev-rd-knowledge/project-repo`

## 执行方式

按 `manifest.json` 的 `demo_steps` 顺序执行。开发者电脑只安装本地 `neodev` CLI 客户端、skill 和插件；本地客户端必须先通过 `neodev config set-server <remote-url>` 配置统一远程 NeoDev 服务，再用 `neodev config show` 和 `neodev cli version-check --json` 校验。除 `config show` 外，所有业务命令都必须使用 `neodev ... --json`，并以前一步 CLI 返回的结构化字段补齐后续参数。

## 边界

- 不要直接写 PostgreSQL。
- 不要直接写 Neo4j。
- 不要用临时脚本替代 `doc change register`、`graph impact`、`git verify-doc-change` 或 `git post-push-refresh`。
- `semantic_status=degraded` 表示语义能力降级，不等同于主流程失败。

## 主链路

1. `config show`
2. `cli version-check`
3. 创建产品与版本。
4. 绑定 `main` 与 `feature/docchange-demo` 两个分支场景。
5. 扫描 `doc-repo`。
6. 登记 `DC-NEODEV-DEMO-001`。
7. 查询影响面。
8. 提交前校验 `DocChange-ID`。
9. 推送后刷新图谱节点。

## Three-Client Plugin Use

- Codex uses `plugins/neodev-rd-knowledge/.codex-plugin/plugin.json` and the bundled `skills/neodev-rd-knowledge/SKILL.md`.
- Claude Code uses `plugins/neodev-rd-knowledge/.claude-plugin/plugin.json`, `commands/`, `agents/`, and `hooks/hooks.json`.
- Cursor uses `.cursor/rules/*.mdc`; distributable copies live under `plugins/neodev-rd-knowledge/cursor/rules/`.

Before `doc scan` or `doc change register`, validate controlled documents:

```bash
python plugins/neodev-rd-knowledge/validate_mvp_docs.py examples/neodev-rd-knowledge/doc-repo
```

Commit messages should contain exactly one `DocChange-ID` trailer and push refreshes should go through `neodev git post-push-refresh ... --json`.
