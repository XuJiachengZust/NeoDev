---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-27-NEODEV-PLUGIN-SKILL-ZH-LOCALIZATION
title: NeoDev 官方插件与 Skill 中文化留痕
aliases:
- NeoDev 官方插件与 Skill 中文化留痕
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
- '[[neosuperpower/specs/2026-04-24-neodev-cli-and-metadata-foundation-design|NeoDev
  CLI 与元数据基础设计]]'
---

# NeoDev 官方插件与 Skill 中文化留痕

日期：2026-04-27

## 背景

用户要求官方 skill 和插件内容使用中文，并显式指定 `$skill-creator`。本轮按 skill-creator 原则处理：

- 保留机器字段、命令模板、workflow id、插件 name 等稳定契约。
- 将人类可读内容改为中文。
- 保持 `SKILL.md` 简洁，只放执行者真正需要的流程和边界。

## 修改范围

插件：

- `plugins/neodev-rd-knowledge/.codex-plugin/plugin.json`
- `.agents/plugins/marketplace.json`

工作流：

- `plugins/neodev-rd-knowledge/workflows/core-workflows.json`

Skill：

- `plugins/neodev-rd-knowledge/skills/neodev-rd-knowledge/SKILL.md`

测试：

- `tests/test_official_plugin_skill.py`

## 中文化口径

已改为中文：

- 插件描述
- 插件展示名
- 插件 short/long description
- 插件能力标签
- 默认提示词
- 插件市场展示名和分类
- workflow `contract`
- workflow `goal`
- skill frontmatter `description`
- skill 标题、边界、流程和结果解释

保留英文或机器字符串：

- `neodev-rd-knowledge`
- JSON key
- workflow id / step id
- CLI 命令
- `DocChange-ID`、`semantic_status`、`version_mismatch` 等契约字段

## TDD 记录

红灯：

```powershell
pytest tests/test_official_plugin_skill.py -q
```

结果：失败，插件展示名、workflow contract、skill description/body 仍为英文。

修复：

- 将插件和 skill 人类可读内容改为中文。
- 增加测试约束：关键展示字段必须包含中文，旧英文标题不得残留。
- 修复 workflow JSON 中文化时漏掉的逗号。

验证：

```powershell
pytest tests/test_official_plugin_skill.py tests/test_cli_contract.py::test_root_entrypoint_returns_version_check_json tests/test_minimal_e2e_example.py -q
```

结果：`6 passed, 1 warning`。

Skill 校验：

```powershell
$env:PYTHONUTF8='1'; python C:\Users\AH\.codex\skills\.system\skill-creator\scripts\quick_validate.py plugins\neodev-rd-knowledge\skills\neodev-rd-knowledge
```

结果：`Skill is valid!`。

说明：`PYTHONUTF8=1` 是为了避免 Windows 默认 GBK 读取 UTF-8 中文 skill 时误报解码失败。

## 关联文档
- [[neosuperpower/specs/2026-04-24-neodev-cli-and-metadata-foundation-design|NeoDev CLI 与元数据基础设计]]
