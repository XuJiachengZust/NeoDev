---
doc_id: NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-TECHNICAL-01-TECHNICAL-DESIGN
title: CLI 命令简化技术设计
aliases:
  - CLI 命令简化技术设计
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/requirements
  - requirements/cli-command-simplification
created: 2026-06-10
updated: 2026-06-10
related:
  - '[[requirements/cli-command-simplification/01-master-prd|CLI 命令简化总 PRD]]'
  - '[[requirements/cli-command-simplification/features/F001-workflow-entrypoints|F001 高层工作流入口 PRD]]'
  - '[[requirements/cli-command-simplification/features/F002-command-visibility-and-compatibility|F002 命令可见性与兼容策略 PRD]]'
  - '[[requirements/cli-command-simplification/features/F003-agent-command-routing|F003 Agent 命令路由收口 PRD]]'
  - '[[requirements/cli-command-simplification/technical/README|CLI 命令简化技术设计索引]]'
doc_type: tech-design
product_key: NEODEV
status: draft
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-MASTER-PRD
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-F001-WORKFLOW-ENTRYPOINTS
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-F002-COMMAND-VISIBILITY-AND-COMPATIBILITY
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-F003-AGENT-COMMAND-ROUTING
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-TECHNICAL-README
---

# CLI 命令简化技术设计

## 1. 设计目标

本设计实现 CLI 命令简化 PRD 中的 F001、F002、F003。目标不是删除底层命令，而是在现有 `argparse` CLI、远程 `/api/cli/execute` 转发和插件 workflow 之上增加一个可维护的命令分层与工作流聚合层。

核心目标：

- 新增 `doctor/context/setup/docs/change/git/status` 这组 primary 工作流入口。
- 保留 `product/project/doc/graph/git` 原子命令、高级图谱命令和历史兼容命令的可调用性。
- 默认 `neodev --help` 只展示 primary 主路径和 `neodev help --all` 提示。
- `neodev help --all` 展示 primary、advanced、internal、hidden 全部命令，并标注替代入口和风险。
- Agent 插件默认收口到 `context/docs/change/submit` 四个意图入口，不默认推荐 internal/hook-only 命令。
- 每个高层命令输出 `scenario_id`、`stage`、`steps`、`summary`、`closure_evidence`、`next_actions`、`failed_step` 或 `retry_hint`，支撑业务闭环。

## 2. 非目标

- 不删除现有原子命令。
- 不改写 `graph type/node/edge` 手工图谱能力的业务语义。
- 不新增数据库表结构。
- 不改变远程服务作为事实读写边界的约束。
- 不把 post-push 原子更新拆回多条 Agent 手工命令。

## 3. 现状依据

| 现状 | 文件 | 设计结论 |
| --- | --- | --- |
| CLI 由 `build_parser()` 构建，所有模块通过 `register_commands()` 注册到 argparse。 | `src/service/cli/executor.py`, `src/service/cli/commands/__init__.py` | 保留注册方式，在注册层补 metadata 与 help 可见性。 |
| 远程执行把 argv 透传到 `/api/cli/execute`，服务端复用 `execute_local()`。 | `src/service/cli/remote_client.py`, `src/service/routers/cli.py` | 高层命令必须作为普通 argv 可远程转发，不引入本地-only 行为。 |
| `product version analyze/analyze-status/watch-status` 已通过 `argparse.SUPPRESS` 和隐藏 choices 从标准 help 降噪。 | `src/service/cli/commands/product.py` | 抽象为通用 visibility 机制，避免各模块复制隐藏逻辑。 |
| `graph type/node/edge` 已注册并有 contract/unit tests。 | `src/service/cli/commands/graph.py`, `tests/test_cli_contract.py`, `tests/test_graph_management_cli_unit.py` | 手工图谱命令归为 advanced，继续可执行，可在全量 help 中发现。 |
| 插件 manifest 和 `core-workflows.json` 已承载 workflow awareness。 | `plugins/neodev-rd-knowledge/.codex-plugin/plugin.json`, `plugins/neodev-rd-knowledge/workflows/core-workflows.json` | 插件层只改推荐入口和命令说明，不改变 CLI 执行边界。 |

## 4. 总体架构

```mermaid
flowchart LR
  User[用户或 Agent] --> CLI[neodev CLI]
  CLI --> Parser[argparse parser]
  Parser --> Metadata[Command Metadata Registry]
  Parser --> Workflows[Workflow Commands]
  Parser --> Atomic[Existing Atomic Commands]
  Metadata --> DefaultHelp[neodev --help]
  Metadata --> AllHelp[neodev help --all]
  Workflows --> StepRunner[Workflow Step Runner]
  StepRunner --> Atomic
  Atomic --> Remote[/api/cli/execute or local services]
  Remote --> Evidence[Structured Evidence]
  Evidence --> Summary[Workflow Summary and next_actions]
  Metadata --> Plugin[Plugin intent docs and defaultPrompt]
```

分层原则：

- `primary` 是用户日常入口，默认 help 展示。
- `advanced` 是排障、维护、原子能力和手工图谱命令，默认 help 不展开，`help --all` 展示。
- `internal` 是 hook 或脚本内部入口，默认 help 不展示，`help --all` 展示并标注风险。
- `hidden` 是历史兼容或不推荐入口，默认 help 不展示，`help --all` 展示迁移说明。

## 5. 模块设计

### 5.1 命令元数据注册表

新增 `src/service/cli/command_metadata.py`。

职责：

- 定义命令可见性枚举。
- 维护命令路径、摘要、可见性、替代入口、风险说明、适用意图。
- 为 help 渲染、contract test、插件文档生成提供单一数据源。

建议结构：

```python
from dataclasses import dataclass, field
from enum import Enum


class CommandVisibility(str, Enum):
    PRIMARY = "primary"
    ADVANCED = "advanced"
    INTERNAL = "internal"
    HIDDEN = "hidden"


@dataclass(frozen=True)
class CommandMetadata:
    path: tuple[str, ...]
    visibility: CommandVisibility
    summary: str
    replacement: str | None = None
    risk: str | None = None
    intents: tuple[str, ...] = field(default_factory=tuple)
    scenarios: tuple[str, ...] = field(default_factory=tuple)
```

初始映射：

| 命令 | visibility | replacement | risk/intents |
| --- | --- | --- | --- |
| `doctor` | primary | 无 | intent=context |
| `context show` | primary | 无 | intent=context, scenarios=S01/S06 |
| `setup repo` | primary | 无 | intent=context, scenario=S01 |
| `docs sync` | primary | 无 | intent=docs, scenario=S02 |
| `change start` | primary | 无 | intent=change, scenario=S03 |
| `change impact` | primary | 无 | intent=change/submit, scenarios=S03/S04 |
| `git check` | primary | 无 | intent=submit, scenario=S04 |
| `status` | primary | 无 | intent=context/submit, scenarios=S05/S06 |
| `product ...` | advanced | 对应 primary 入口或无 | 原子产品/版本管理 |
| `project ...` | advanced | `setup repo` 或 `status` | 仓库接入/图谱维护 |
| `doc ...` | advanced | `docs sync` 或 `change start` | 文档原子能力 |
| `graph impact/get-chain/entity-context` | advanced | `change impact` | 图谱排障/分析 |
| `graph type/node/edge ...` | advanced | 无 | manual graph mutation |
| `git dangerous-commit list/resolve` | advanced | `git check` | commit risk maintenance |
| `git post-push-graph-update` | internal | `status` | hook-only |
| `product version analyze/analyze-status/watch-status` | hidden | `setup repo` 或 `status` | legacy compatibility |

约束：

- 元数据不决定命令是否能执行，只决定展示、提示和测试。
- 已注册命令缺失 metadata 时，contract test 必须失败。
- 未知 visibility 值必须抛出配置错误。

### 5.2 Help 渲染与可见性过滤

新增 `src/service/cli/help_renderer.py` 与 `src/service/cli/help_visibility.py`。

职责：

- `neodev --help`：展示 primary 命令和 `neodev help --all` 提示。
- `neodev help --all`：按 visibility 分组展示所有命令。
- `neodev help --json --all`：输出结构化命令清单，供插件或测试消费。
- 保留各子命令自身 `--help`，例如 `neodev graph edge add --help` 继续可用。

默认 help 示例：

```text
NeoDev primary commands:
  neodev doctor
  neodev context show
  neodev setup repo
  neodev docs sync
  neodev change start
  neodev change impact
  neodev git check
  neodev status

Run `neodev help --all` to show advanced, internal, and hidden commands.
```

全量 help JSON 示例：

```json
{
  "commands": [
    {
      "command": "neodev graph edge add",
      "visibility": "advanced",
      "summary": "手动创建图边，用于维护/排障/手工关联节点",
      "replacement": null,
      "risk": "manual graph mutation",
      "intents": []
    }
  ]
}
```

实现注意：

- 当前 `execute_local()` 已捕获 argparse help 并包装成 `build_success_payload("help", {"text": help_text})`。`neodev help --all` 应走普通 handler，返回 `command="help all"` 或 `command="help"`。
- 不建议依赖 argparse 内部 `_choices_actions` 作为唯一事实源。可以继续用它隐藏默认 choices，但真实命令清单以 `command_metadata.py` 为准。
- `product.py` 现有 `_hide_subparser_choices()` 可迁移到通用 helper，保留兼容行为。

### 5.3 工作流命令层

新增 `src/service/cli/commands/workflow.py`，或按顶层命令拆为 `doctor.py`、`context.py`、`setup.py`、`docs.py`、`change.py`、`status.py`。建议先采用单文件 `workflow.py`，避免过早拆散编排逻辑。

职责：

- 注册 primary 命令：
  - `doctor`
  - `context show`
  - `setup repo`
  - `docs sync`
  - `change start`
  - `change impact`
  - `git check`
  - `status`
- 复用现有命令 handler 或 service，不复制核心业务逻辑。
- 输出统一 workflow payload。

统一输出：

```json
{
  "scenario_id": "S02",
  "stage": "docs",
  "steps": [
    {
      "id": "validate_docs",
      "command": "python plugins/neodev-rd-knowledge/validate_mvp_docs.py docs",
      "status": "success",
      "summary": "7 controlled docs valid"
    }
  ],
  "summary": {
    "doc_graph_status": "updated",
    "imported_docs": 12,
    "failed_docs": []
  },
  "closure_evidence": [
    {"type": "doc_graph", "status": "updated"}
  ],
  "next_actions": [
    {"intent": "change", "command": "neodev change start"}
  ]
}
```

失败输出：

```json
{
  "scenario_id": "S02",
  "stage": "docs",
  "failed_step": "validate_docs",
  "summary": {
    "failed_docs": ["docs/requirements/example.md"]
  },
  "retry_hint": "Fix front matter and rerun `neodev docs sync`.",
  "next_actions": [
    {"intent": "docs", "command": "neodev docs sync"}
  ]
}
```

### 5.4 工作流步骤执行器

新增 `src/service/cli/workflow_runner.py`。

职责：

- 顺序执行只读或写入步骤。
- 记录每个步骤的 `id/command/status/summary/error`。
- 任一依赖步骤失败时停止后续非补偿步骤。
- 将底层错误转换为 workflow 级 `failed_step` 和 `retry_hint`。

建议接口：

```python
@dataclass
class WorkflowStep:
    id: str
    command: tuple[str, ...]
    required: bool = True
    writes_state: bool = False


@dataclass
class WorkflowResult:
    scenario_id: str
    stage: str
    steps: list[dict]
    summary: dict
    closure_evidence: list[dict]
    next_actions: list[dict]
    failed_step: str | None = None
    retry_hint: str | None = None
```

执行边界：

- 对本地脚本类校验步骤，可调用 Python 函数或受控脚本入口。
- 对已有 CLI 原子能力，优先直接复用 handler/service；如果为了兼容远程行为需要 argv 形式，必须避免递归调用自身 workflow 命令。
- 写入远程状态仍由现有 service/CLI handler 完成，runner 不直接写数据库。

### 5.5 Primary 命令到原子能力映射

| Primary 命令 | 复用能力 | 读写边界 | 成功后下一步 |
| --- | --- | --- | --- |
| `doctor` | `config show`, `cli version-check` | 只读本地配置和远程兼容状态 | `context show` 或 `setup repo` |
| `context show` | `product version show`, `project show`, `doc binding list`, `doc graph show` | 只读上下文、binding、图谱状态 | `setup repo`, `docs sync`, `status` |
| `setup repo` | `product create/version create`, `project create/init-status`, `product version bind-branch`, `project refresh-graph` | 写产品/版本/项目/分支绑定和图谱初始化事实 | `docs sync` |
| `docs sync` | 文档校验脚本、`doc binding list/create`, `doc scan`, `doc import`, `doc graph show` | 写 doc imports、doc chunks、doc graph | `change start` 或 done |
| `change start` | `doc change register`, `graph impact` | 写 DocChange 和实现上下文 | `change impact` |
| `change impact` | `graph impact`, `graph get-chain`, `graph entity-context` | 读图谱和影响范围，必要时写风险状态候选 | `git check` |
| `git check` | `check_git_commit_scope.py`, `git verify-doc-change`, `git dangerous-commit list` | 读 Git diff 和远程风险事实，可写检查/风险状态 | commit/push 或修复 |
| `status` | `context show`, `doc graph show`, post-push run record, branch/doc/code graph 状态 | 只读状态和 hook 结果 | done 或回到 docs/change/submit |

### 5.6 高级命令保留

高级命令保留规则：

- 所有 `advanced/internal/hidden` 命令继续注册到 argparse。
- 直接执行时仍走原 handler。
- 子命令 `--help` 继续可用。
- 远程转发继续可用。
- contract tests 必须覆盖关键高级命令注册。
- 默认 help 不展开这些命令。
- `help --all` 展示这些命令和说明。

手动关联图节点归类：

| 能力 | 命令 | visibility | 说明 |
| --- | --- | --- | --- |
| 查看类型 | `graph type node list`, `graph type edge list` | advanced | 手工图谱维护前的类型检查。 |
| 创建节点 | `graph node add` | advanced | 受控创建手工节点。 |
| 更新节点 | `graph node update` | advanced | 修改手工节点属性或状态。 |
| 创建边 | `graph edge add` | advanced | 手动关联两个图节点。 |
| 更新边 | `graph edge update` | advanced | 调整关系类型、属性或状态。 |
| 删除节点/边 | `graph node delete`, `graph edge delete` | advanced | 归档手工图事实。 |

`graph edge add` 示例：

```bash
neodev graph edge add \
  --project-id <owner_project_id> \
  --branch <branch> \
  --edge-id <edge_id> \
  --from-node-id <from_node_id> \
  --to-node-id <to_node_id> \
  --type RELATES_TO \
  --json
```

### 5.7 插件意图路由

更新范围：

- `plugins/neodev-rd-knowledge/.codex-plugin/plugin.json`
- `plugins/neodev-rd-knowledge/workflows/core-workflows.json`
- `plugins/neodev-rd-knowledge/commands/`
- 相关 skill 文档中默认命令推荐段落。

四个默认意图：

| 意图 | 默认推荐 | fallback |
| --- | --- | --- |
| `context` | `neodev doctor`, `neodev context show`, `neodev setup repo` | 现有 version_branch_navigation / repository_auto_graph workflow |
| `docs` | `neodev docs sync` | version_scoped_document_import |
| `change` | `neodev change start`, `neodev change impact` | doc_change_to_implementation |
| `submit` | `neodev git check`, `neodev status` | commit_scope_routing / pre_push_verification / post-push result interpretation |

Agent 汇报要求：

- 汇报当前 `scenario_id` 和 `stage`。
- 汇报 `closure_evidence`。
- 汇报 `next_intent` 或 done。
- 遇到 internal 命令时说明原因，不把它作为普通推荐入口。
- push 后只解释 post-push 原子结果，不手动拆分执行 `doc import`、`doc change register`、`project refresh-graph`。

## 6. 数据与接口契约

### 6.1 命令元数据 JSON

`neodev help --json --all` 输出：

```json
{
  "visibility_levels": ["primary", "advanced", "internal", "hidden"],
  "commands": [
    {
      "command": "neodev docs sync",
      "path": ["docs", "sync"],
      "visibility": "primary",
      "summary": "同步当前版本文档并更新文档图谱",
      "replacement": null,
      "risk": null,
      "intents": ["docs"],
      "scenarios": ["S02"]
    }
  ]
}
```

### 6.2 Workflow payload

所有 primary 工作流命令的 `data` 至少包含：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `scenario_id` | string | 是 | `S01` 至 `S06` 或 `ad-hoc`。 |
| `stage` | string | 是 | `context/setup/docs/change/impact/submit/status`。 |
| `steps` | list | 是 | 每个步骤的执行摘要。 |
| `summary` | object | 是 | 面向用户的聚合事实。 |
| `closure_evidence` | list | 是 | 来自服务端、原子命令或 hook 结果的证据。 |
| `next_actions` | list | 是 | 下一命令、下一意图或 done。 |
| `failed_step` | string/null | 否 | 失败时必填。 |
| `retry_hint` | string/null | 否 | 失败时建议提供。 |

### 6.3 错误处理

错误仍使用现有 payload 顶层：

- `ok=false`
- `command`
- `timestamp`
- `data=null`
- `errors[]`

workflow 失败但可结构化解释时，优先在 `errors[0].details` 中放入：

```json
{
  "scenario_id": "S02",
  "stage": "docs",
  "failed_step": "validate_docs",
  "retry_hint": "Fix front matter and rerun `neodev docs sync`.",
  "next_actions": [{"command": "neodev docs sync"}]
}
```

## 7. 关键场景设计

### 7.1 新仓库首次接入

用户说“把这个仓库接入 NeoDev”。

执行：

```text
neodev doctor
neodev context show
neodev setup repo
neodev status
```

技术细节：

- `doctor` 检查本地 server 配置和 `cli version-check`。
- `context show` 读取产品、版本、项目、分支、doc binding、graph status。
- `setup repo` 复用 product/project/version/bind-branch/refresh-graph 能力。
- `status` 输出产品、版本、项目、分支和图谱状态，`next_actions=[docs sync]`。

验收关注点：

- 缺少 server 时不执行写操作。
- 缺少 product/version/project 时明确列出 required fields。
- 接入后能从 `status` 看见闭环证据。

### 7.2 文档同步

用户说“PRD 改了，同步当前版本文档”。

执行：

```text
neodev context show
neodev docs sync
neodev status
```

技术细节：

- `docs sync` 先运行受控文档校验。
- 缺少 doc binding 时创建或提示 `setup repo/context`。
- 复用 `doc scan/import/doc graph show`。
- 成功输出 `imported_docs/failed_docs/doc_graph_status`。

验收关注点：

- YAML/front matter 错误必须列出文件和字段。
- 成功后 `status` 显示文档图谱更新。

### 7.3 从需求启动开发

用户说“按这个需求开始实现”。

执行：

```text
neodev docs sync
neodev change start
neodev change impact
```

技术细节：

- `change start` 选择或注册 DocChange。
- `change impact` 复用 `graph impact/get-chain/entity-context`。
- 输出 DocChange-ID、关联文档、影响节点、风险点。

验收关注点：

- 无法定位文档时不能猜测，必须提示补充文档路径或先同步文档。
- 必须输出可用于后续提交的 DocChange-ID。

### 7.4 提交前检查

用户说“提交前检查一下”。

执行：

```text
neodev change impact
neodev git check
```

技术细节：

- `git check` 复用 `check_git_commit_scope.py`、`git verify-doc-change` 和 `git dangerous-commit list`。
- 输出 commit scope、required trailer、risk summary。

验收关注点：

- mixed scope 必须阻断并提示拆分。
- code-only commit 必须有一个有效 DocChange-ID。
- dangerous commit 未处理时不得建议继续提交。

### 7.5 push 后状态回看

用户说“push 后现在闭环了吗”。

执行：

```text
neodev status
```

技术细节：

- 读取 post-push hook 结果、DocChange、doc graph、code graph、dangerous commit 和当前 branch 状态。
- 不手动替代 hook 刷新图谱。
- 输出 `hook_status`、`open_gaps`、`next_actions`。

验收关注点：

- hook failed 时解释原始错误和缺口。
- 无缺口时输出 done。
- 有缺口时指向 docs/change/submit 的最小修复入口。

### 7.6 手动关联图节点

维护者明确要求“手动关联图节点”。

执行：

```text
neodev graph type edge list --project-id <project_id> --json
neodev graph node show --project-id <project_id> --node-id <from_node_id> --json
neodev graph node show --project-id <project_id> --node-id <to_node_id> --json
neodev graph edge add --project-id <project_id> --branch <branch> --edge-id <edge_id> --from-node-id <from_node_id> --to-node-id <to_node_id> --type <TYPE_KEY> --json
neodev graph edge show --project-id <project_id> --edge-id <edge_id> --json
```

技术细节：

- 该流程属于 advanced，不出现在默认 help。
- Agent 不默认推荐，除非用户显式要求手工图谱维护。
- 变更后通过 `edge show/list` 验证；如需分支证据，再运行 `graph get-chain` 或 `graph entity-context`。

验收关注点：

- 类型不存在时提示先创建或选择合法 edge type。
- 端点节点不存在时不得创建关系。
- 跨项目关系必须符合 relation type 的 `cross_project_allowed`。

## 8. 文件改造范围

| 文件 | 动作 | 责任 |
| --- | --- | --- |
| `src/service/cli/command_metadata.py` | 新增 | 命令元数据、visibility、替代入口和风险说明。 |
| `src/service/cli/help_renderer.py` | 新增 | 默认 help 与 `help --all` 的文本/JSON 渲染。 |
| `src/service/cli/help_visibility.py` | 新增 | argparse choices 降噪 helper。 |
| `src/service/cli/workflow_runner.py` | 新增 | 工作流步骤执行、失败聚合、next_actions 生成。 |
| `src/service/cli/commands/workflow.py` | 新增 | 注册 primary 工作流命令。 |
| `src/service/cli/commands/help.py` | 新增 | 注册 `neodev help --all`。 |
| `src/service/cli/commands/__init__.py` | 修改 | 注册 help 和 workflow 命令。 |
| `src/service/cli/executor.py` | 修改 | 接入默认 help 渲染和 metadata 检查。 |
| `src/service/cli/commands/product.py` | 修改 | 迁移隐藏 choices 到通用 helper。 |
| `plugins/neodev-rd-knowledge/.codex-plugin/plugin.json` | 修改 | defaultPrompt 收口到四意图和 primary 命令。 |
| `plugins/neodev-rd-knowledge/workflows/core-workflows.json` | 修改 | 增加 primary 命令感知，保留 fallback workflow。 |
| `plugins/neodev-rd-knowledge/commands/` | 修改 | 命令说明从原子主题收口到 context/docs/change/submit，旧文档标记 advanced。 |
| `plugins/neodev-rd-knowledge/skills/neodev-rd-knowledge/SKILL.md` | 修改 | 更新默认推荐路径和 internal/hook-only 规则。 |

## 9. 测试设计

### 9.1 Contract tests

新增或调整 `tests/test_cli_contract.py`：

- `test_primary_commands_are_registered`
- `test_default_help_only_shows_primary_commands`
- `test_help_all_shows_advanced_internal_hidden_commands`
- `test_advanced_graph_management_commands_remain_registered`
- `test_internal_post_push_command_remains_callable_but_hidden_from_default_help`
- `test_every_registered_command_has_metadata`
- `test_missing_visibility_metadata_fails_contract`

关键断言：

```python
assert "graph edge add" not in default_help.stdout
assert "git post-push-graph-update" not in default_help.stdout
assert "neodev help --all" in default_help.stdout
assert "graph edge add" in help_all.stdout
assert "visibility=advanced" in help_all.stdout
```

### 9.2 Workflow unit tests

新增 `tests/test_cli_workflow_commands.py`：

- `doctor` 成功时输出 server 和 version-check 摘要。
- `docs sync` 某步骤失败时输出 `failed_step` 和 `retry_hint`。
- `git check` mixed scope 时输出 blocking risk。
- `status` hook success 时输出 `next_actions=[done]`。
- 每个 primary 命令输出 `scenario_id/stage/closure_evidence/next_actions`。

### 9.3 Remote execution tests

调整 `tests/test_cli_remote_execution.py`：

- 远程 argv `["docs", "sync", "--json"]` 可转发。
- 远程 argv `["help", "--all", "--json"]` 返回命令元数据。
- 远程 argv `["graph", "edge", "add", ...]` 不因 visibility 被拒绝。

### 9.4 Plugin tests

调整 `tests/test_official_plugin_skill.py` 和 `tests/test_plugin_platforms.py`：

- defaultPrompt 包含 context/docs/change/submit 或 primary 命令。
- defaultPrompt 不默认推荐 `git post-push-graph-update`。
- 手工图谱 skill/commands 仍能发现 `graph node/edge/type`。
- post-push 解释规则仍要求只解释原子结果，不手动刷新图谱。

## 10. 迁移与兼容策略

### 10.1 旧命令兼容

- 旧命令不删除。
- 原有参数保持兼容。
- 原有 contract tests 继续运行。
- 对 hidden/internal 命令可以增加 warning，但不能改变 exit code 或 payload 顶层结构。

### 10.2 Help 迁移

- 第一阶段：新增 metadata 和 `help --all`，默认 help 降噪。
- 第二阶段：插件文档和 prompt 收口到四意图。
- 第三阶段：新增 workflow 命令并保持 fallback 到原 core workflows。
- 第四阶段：根据使用情况决定是否为 hidden 命令增加 deprecated 提示；本设计不删除命令。

### 10.3 Agent 迁移

- Agent 默认使用 primary 或 workflow。
- 高层命令未实现时，允许 fallback 到 `core-workflows.json` 现有原子步骤，但必须报告 fallback 原因。
- internal 命令只在 hook 结果解释或用户明确排障时出现。

## 11. 安全与风险控制

| 风险 | 控制 |
| --- | --- |
| 高层命令吞掉底层错误 | `steps[]` 记录原子命令和失败摘要，失败时返回 `failed_step`。 |
| 默认 help 隐藏导致脚本不可用 | visibility 不影响 parser 注册和 handler 调用。 |
| Agent 误用 hook-only 命令 | internal 命令不进入 defaultPrompt，`help --all` 标注 hook-only。 |
| 手工图谱命令被普通用户误用 | `graph type/node/edge` 归为 advanced，默认 help 不展示。 |
| metadata 与 parser 注册不一致 | contract test 枚举 parser 和 metadata，缺失即失败。 |
| 工作流复制业务逻辑 | workflow runner 只编排现有 handler/service，不直接写数据库。 |
| 输出泄露敏感信息 | summary 和 retry_hint 对 token、连接串、payload 内容做脱敏。 |

## 12. 需求覆盖矩阵

| 需求/规则 | 技术设计覆盖 |
| --- | --- |
| F001 高层工作流入口 | 5.3、5.4、5.5、7.1 至 7.5、9.2 |
| F002 命令可见性与兼容策略 | 5.1、5.2、5.6、9.1、10.1、10.2 |
| F003 Agent 命令路由收口 | 5.7、9.4、10.3 |
| BR-G-01 保留原子命令 | 5.6、10.1 |
| BR-G-02 默认推荐工作流命令 | 5.2、5.7、9.4 |
| BR-G-03 hook-only 不作为普通入口 | 5.1、5.2、5.7、11 |
| BR-G-04 聚合结果和下一步 | 5.3、6.2、7 |
| BR-G-05 失败步骤和重试提示 | 5.4、6.3、9.2 |
| BR-G-06 单命令操作与数据闭环 | 6.2、7 |
| BR-G-07 命令间业务闭环 | 5.5、7.1 至 7.5 |
| BR-G-08 具体场景细节 | 7.1 至 7.6 |

## 13. 开放问题

当前技术设计无阻塞开放问题。以下为实现阶段可细化但不阻塞设计的工程选择：

| 编号 | 问题 | 建议默认值 |
| --- | --- | --- |
| TD-Q-001 | 工作流命令是集中在 `workflow.py` 还是按命令拆文件？ | 先集中在 `workflow.py`，超过 500 行或职责分裂明显时再拆。 |
| TD-Q-002 | workflow runner 是直接调用 handler 还是通过 argv 递归执行？ | 优先直接调用 handler/service，避免递归 CLI 和重复解析。 |
| TD-Q-003 | `help --all` 是否展示完整参数？ | 第一阶段展示命令、摘要、visibility、replacement、risk；完整参数仍由子命令 `--help` 提供。 |

## 14. 关联文档

- [[requirements/cli-command-simplification/01-master-prd|CLI 命令简化总 PRD]]
- [[requirements/cli-command-simplification/features/F001-workflow-entrypoints|F001 高层工作流入口 PRD]]
- [[requirements/cli-command-simplification/features/F002-command-visibility-and-compatibility|F002 命令可见性与兼容策略 PRD]]
- [[requirements/cli-command-simplification/features/F003-agent-command-routing|F003 Agent 命令路由收口 PRD]]
- [[requirements/cli-command-simplification/technical/README|CLI 命令简化技术设计索引]]
