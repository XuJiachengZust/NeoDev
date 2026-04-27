---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-27-NEODEV-PLUGIN-HOOKS-DOC-VALIDATION-SUPERPOWERS-PLATFORMS
title: "NeoDev 插件钩子、MVP 文档校验与 Superpowers 平台留痕"
aliases:
  - "NeoDev 插件钩子、MVP 文档校验与 Superpowers 平台留痕"
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/plan
created: 2026-04-27
updated: 2026-04-27
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-SUPERPOWERS-SPECS-2026-04-24-NEODEV-CLI-AND-METADATA-FOUNDATION-DESIGN
related:
  - "[[2026-04-24-neodev-cli-and-metadata-foundation-design]]"
---
# NeoDev 插件钩子、MVP 文档校验与 Superpowers 平台留痕

## 已实现范围

- 在 `plugins/neodev-rd-knowledge/` 下新增共享插件脚本：
  - `validate_mvp_docs.py`
  - `generate_mvp_doc.py`
  - `check_docchange_trailer.py`
  - `assets/templates/mvp-doc.md`
- 为共享钩子和脚本补充 Codex manifest 引用。
- 新增 Claude Code 插件入口文件：
  - `.claude-plugin/plugin.json`
  - `commands/*.md`
  - `agents/neodev-rd-knowledge.md`
  - `hooks/hooks.json`
- 新增 Cursor 项目规则和可分发插件副本：
  - `.cursor/rules/*.mdc`
  - `plugins/neodev-rd-knowledge/cursor/rules/*.mdc`
- 更新共享 skill 和工作流契约，补充 MVP 文档校验和 Superpowers 工作流要求。
- 将示例文档更新为可执行的 MVP front matter 契约：
  - `product_key`
  - `status`
  - 映射形式的 `relations.target`
- 收紧服务端 front matter 校验器，使 `doc_type` 和 `status` 与共享脚本使用同一组允许值。

## 契约

所有插件入口都只承担编排职责。它们可以校验文件、引导命令顺序、解释结构化结果，但事实读取和状态变更仍必须通过 `python neodev.py ... --json` 执行。

MVP 受控文档 front matter：

```yaml
doc_id: DOC-001
title: 文档标题
doc_type: prd
product_key: PRODUCT
status: draft
relations:
  target:
    - TARGET-DOC-001
```

允许的 `doc_type`：`prd`、`prototype`、`tech-design`。

允许的 `status`：`draft`、`active`、`deprecated`。

## 验证结果

- `pytest tests/test_official_plugin_skill.py tests/test_minimal_e2e_example.py tests/test_plugin_platforms.py tests/test_plugin_doc_validation_scripts.py -q`
  - 结果：`15 passed`
  - 说明：由于当前工作区无法写入 `.pytest_cache`，pytest 输出了缓存告警。
- `PYTHONUTF8=1 python C:\Users\AH\.codex\skills\.system\skill-creator\scripts\quick_validate.py plugins\neodev-rd-knowledge\skills\neodev-rd-knowledge`
  - 结果：`Skill is valid!`
- `python plugins\neodev-rd-knowledge\validate_mvp_docs.py examples\neodev-rd-knowledge\doc-repo`
  - 结果：`{"ok": true, "checked_count": 2, "errors": []}`
- 额外的扫描器专项检查：
  - `pytest tests/test_official_plugin_skill.py tests/test_minimal_e2e_example.py tests/test_plugin_platforms.py tests/test_plugin_doc_validation_scripts.py tests/test_doc_scan_service.py -q`
  - 结果：`15 passed, 4 skipped`
  - 说明：跳过项是已有的元数据库依赖用例。

## 说明

- Claude Code 钩子通过 `hooks/hooks.json` 中的事件分组和命令钩子表示。
- Cursor 支持基于规则文件，不声明具备与 Claude Code 等价的运行时阻断钩子能力。
- 本次工作在当前分支 `neodev-sp` 上执行，未执行 git commit 或 push。
