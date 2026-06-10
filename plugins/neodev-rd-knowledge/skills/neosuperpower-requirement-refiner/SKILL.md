---
name: "neosuperpower-requirement-refiner"
description: "当 NeoDev/DSC 任务需要把粗需求、原型、零散说明、已有 PRD、业务规则或代码事实细化为可追踪、可评估的总分结构 PRD，并生成符合 NeoDev 受控文档格式的 requirements 文档时使用。"
---

# 需求文档细化器

## 1. 适用范围

本技能用于把不完整需求细化为“总 PRD + 按功能拆分的一系列子 PRD”。默认采用主智能体编排多个子智能体的闭环方式执行，不建议由单一智能体独立完成全部事实收集、编写和验收。

适用场景：

- 用户要求细化需求、整理 PRD、补齐业务规则、拆分功能 PRD。
- 输入包含粗需求、原型、截图、已有需求文档、会议纪要、代码事实或接口线索。
- 需要统一业务对象、属性、术语、定义，并形成可研发、可测试、可验收的 PRD。

不适用场景：

- 直接实现代码、设计数据库表、生成 API JSON、部署或回归验证。
- 只分析原型图组件清单，优先使用 `prototype-component-analyzer`。
- API 契约已经明确且用户要求生成网关 API，优先使用 `api-designer`。

## 2. 强制原则

- 先按仓库 `harness/BOOTSTRAP.md` 定位项目、规则和事实源。
- 不允许自由发挥。无法从用户输入、本地文档、代码事实或已确认上下文证明的信息，必须提问或写入待确认问题。
- 先统一总 PRD 的业务对象、属性、术语、定义和跨功能规则，再拆功能子 PRD。
- 功能拆分以用户可感知能力为单位，不按前端、后端、数据库等技术层拆分。
- 子 PRD 不得重新定义总 PRD 已统一的对象、属性、术语和业务规则；发现冲突时回到总 PRD 修订。
- Mermaid 为默认图表格式。只有事实足够支撑时才生成数据流图和时序图；事实不足时必须写明缺口和待确认问题，不得用通用 UI/API/DB 链路补图。
- 不生成未确认的 API、表结构、枚举、权限、状态机或业务规则；只能列候选并标为待确认。
- 所有需求、业务规则、AC、测试场景和待确认问题必须能追溯到事实源编号或问题编号。
- 所有功能性需求点必须用具体业务场景说明，不能只写抽象能力、抽象节点或泛化规则。场景至少包含：触发条件、用户说法或业务背景、推荐操作顺序、数据读写细节、输出示例关注点、失败反馈、下一步动作和验收关注点。
- 当用户要求“闭环”“流程”“命令串联”“业务链路”等内容时，必须写业务场景闭环，而不是只画流程图或列阶段名。闭环场景必须说明每一步为什么发生、使用什么输入、改变什么事实、产出什么证据，以及如何进入下一步或回退修复。
- 主智能体负责任务理解、项目定位、分派、合并、冲突裁决和最终收口；执行器子智能体负责事实收集、总 PRD、子 PRD 和待确认问题等分工产出；评估器子智能体负责独立验收。
- 完成 PRD 后，主智能体必须先按质量清单做合并自检，再交给独立评估器子智能体评估；主智能体自检不得替代独立评估。

## 3. 固定产物结构

默认输出到命中的子项目内：

```text
<target-project>/docs/requirements/<feature-name>/
├── README.md
├── 00-source-index.md
├── 01-master-prd.md
├── features/
│   ├── F001-<feature-a>.md
│   ├── F002-<feature-b>.md
│   └── F003-<feature-c>.md
└── 99-open-questions.md
```

仅当需求明确跨多个子项目且无法归入单一项目时，才允许输出到仓库根级 `docs/requirements/<feature-name>/`，并在 `README.md` 中说明跨项目原因。

所有产物都是 NeoDev 受控文档，必须满足：

- 每个 `.md` 文件必须从 YAML front matter 开始，不能从 `#` 标题开始。
- 必填字段：`doc_id`、`title`、`aliases`、`tags`、`created`、`updated`、`related`、`doc_type`、`product_key`、`status`、`relations.target`。
- `doc_type` 只能是 `prd`、`prototype` 或 `tech-design`。总 PRD、功能子 PRD 和 README 默认用 `prd`；事实源索引和待确认问题默认用 `tech-design`。
- `relations.target` 只能写真实存在的 `doc_id`。需求集内部文档可互相关联，但不得保留模板占位 ID。
- `related` 必须是 Obsidian wikilink，并由 `sync_obsidian_links.py` 根据 `relations.target` 同步生成。
- 正文末尾必须包含 `## 关联文档`，内容同 `related` 对应的 wiki 链接。
- 输出路径不得包含 `superpowers`，跨项目输出也必须仍在一个 docs root 内。

推荐 doc_id 规则：

| 文件 | doc_id 格式 |
| --- | --- |
| `README.md` | `NEODEV-DOC-REQUIREMENTS-<FEATURE-NAME>-README` |
| `00-source-index.md` | `NEODEV-DOC-REQUIREMENTS-<FEATURE-NAME>-SOURCE-INDEX` |
| `01-master-prd.md` | `NEODEV-DOC-REQUIREMENTS-<FEATURE-NAME>-MASTER-PRD` |
| `features/F001-<feature-a>.md` | `NEODEV-DOC-REQUIREMENTS-<FEATURE-NAME>-F001-<FEATURE-A>` |
| `99-open-questions.md` | `NEODEV-DOC-REQUIREMENTS-<FEATURE-NAME>-OPEN-QUESTIONS` |

生成或修改产物后必须运行：

```bash
python plugins/neodev-rd-knowledge/sync_obsidian_links.py docs
python plugins/neodev-rd-knowledge/validate_mvp_docs.py docs
python plugins/neodev-rd-knowledge/validate_obsidian_docs.py docs
```

校验失败时不得声称 PRD 完成；先修复 front matter、relations 或 Obsidian 链接。

使用模板：

- 产物索引：`assets/templates/README.md`
- 总 PRD：`assets/templates/master-prd.md`
- 功能子 PRD：`assets/templates/feature-prd.md`
- 事实源索引：`assets/templates/source-index.md`
- 待确认问题：`assets/templates/open-questions.md`
- 主从编排流程：`references/orchestrator-workflow.md`
- 执行器分派模板：`references/executor-subagent-templates.md`
- 质量清单：`references/quality-checklist.md`
- 评估器分派模板：`references/evaluator-subagent-template.md`

## 4. 工作流程

1. 主智能体读取 `harness/BOOTSTRAP.md`，按渐进加载规则定位项目、事实源和约束。
2. 主智能体读取 `references/orchestrator-workflow.md`，制定本次 DAG：事实收集 -> 总 PRD -> 子 PRD/问题清单 -> 合并自检 -> 独立评估 -> 修复循环。
3. 主智能体锁定输出目录：优先使用 `<target-project>/docs/requirements/<feature-name>/`，跨项目才使用根级 `docs/requirements/<feature-name>/`。
4. 主智能体按 `references/executor-subagent-templates.md` 分派执行器子智能体；每个分派都必须明确角色、上下文范围、允许修改边界、禁止事项、预期产出和验证标准。
5. 事实收集执行器收集输入材料，产出 `00-source-index.md`：用户输入、本地需求文档、原型、代码、接口、数据库、测试材料。
6. 总 PRD 执行器基于事实源编写 `01-master-prd.md`：统一业务口径、功能地图、跨功能业务规则、跨功能典型场景、可被事实支撑的总数据流图、主时序图和总体验收。
7. 子 PRD 执行器按功能拆分 `features/Fxxx-*.md`。每个子 PRD 必须引用总 PRD 中的对象、属性、术语和业务规则，并补齐该功能的典型场景细节。
8. 问题清单执行器维护 `99-open-questions.md`，区分阻塞问题和非阻塞问题，并把问题编号回填到相关 PRD 章节。
9. 主智能体合并执行器结果，处理总分口径冲突，写入 `README.md`，汇总产物清单、范围、事实源、阻塞问题和评估状态。
10. 主智能体按 `references/quality-checklist.md` 做合并自检，重点检查事实源/问题、需求、功能、业务规则、场景细节、AC、测试场景是否闭环。
11. 主智能体按 `references/evaluator-subagent-template.md` 创建独立评估器子智能体评估产物；评估器不得与任何执行器复用同一角色。
12. 若评估结论为“不通过”或“有风险待修复”，主智能体按问题边界重新分派修复执行器，再次评估，直到通过、用户中止或确认升级处理。
13. 若后续进入实现阶段，再由总控路由到 `api-designer`、`db-table-designer`、`javaweb-backend-api-dev` 等技能。

## 5. 编号规则

| 类型 | 编号格式 | 示例 |
| --- | --- | --- |
| 业务对象 | `BO-xxx` | `BO-001 标签` |
| 业务属性 | `BO-xxx-Axx` | `BO-001-A01 标签名称` |
| 总需求 | `R-xxx` | `R-001 标签统一管理` |
| 功能 | `Fxxx` | `F001 新建标签` |
| 业务规则 | `BR-Fxxx-xx` 或 `BR-G-xx` | `BR-F001-01` |
| 验收项 | `AC-Fxxx-xx` | `AC-F001-01` |
| 测试场景 | `TC-Fxxx-xx` | `TC-F001-01` |
| 待确认问题 | `Q-xxx` | `Q-001` |

## 6. 必填内容

总 PRD 必须包含：

- 背景与目标、范围与非目标、用户角色。
- 业务对象清单、业务对象属性字典、术语与定义统一。
- 对象关系与生命周期。
- 功能地图、功能拆分清单、跨功能业务规则。
- 跨功能典型业务场景：每个场景必须包含触发条件、操作顺序、数据读写、输出示例、下一步和验收关注点。
- 跨功能数据流图、跨功能主时序图。
- 非功能需求、权限、安全、兼容性约束。
- 总体验收标准、待确认问题索引。

每个功能子 PRD 必须包含：

- 功能编号、名称、优先级、状态。
- 引用的业务对象、属性、术语和跨功能业务规则。
- 功能目标、用户故事或使用场景、前置条件。
- 典型场景与细节表：每个功能至少包含一个 P0 正向场景；复杂功能必须覆盖关键异常和回退场景。场景表必须包含触发条件/用户说法、推荐操作顺序、数据读写细节、输出示例关注点、失败反馈、下一步动作和验收关注点。
- 页面入口与导航路径。
- 交互说明：入口、触发动作、页面反馈、状态变化、失败反馈、退出路径。
- 业务规则：创建、编辑、删除、状态流转、权限、数据一致性、异常处理。
- 字段、状态、枚举、校验规则。
- 功能内数据流图、功能内时序图。
- 接口与数据口径、异常与边界场景。
- Given/When/Then 验收标准、测试场景建议、关联需求与依赖、待确认问题。

## 7. 提问策略

读取 `references/question-policy.md`。以下信息缺失时不得猜测：

- 标准业务对象名称、别名归属、属性含义、枚举值、状态含义。
- 功能范围、非目标、权限边界、数据可见性、删除/恢复/撤销规则。
- 接口路径、请求响应、数据库结构、跨系统同步、定时任务、异步处理。
- 验收标准、异常处理、兼容策略、迁移策略。

## 8. 软件工程约束

读取 `references/software-engineering-rules.md`，并确保 PRD 满足：

- 单一事实源：总 PRD 是业务对象、属性、术语和跨功能规则的唯一来源。
- 可追踪：每条需求、业务规则、AC 和测试场景都必须关联事实源编号或待确认问题编号。
- 可测试：每个功能至少有 P0 正向场景、关键异常场景和回归关注点；场景必须足够具体，测试人员能据此写出操作步骤和预期结果。
- 可实现：子 PRD 必须明确输入、输出、状态变化、数据读写边界和失败反馈。
- 可验收：不得用“形成闭环”“支持流程”“完成同步”等抽象说法替代场景细节；必须说明具体输入、动作、数据变化、输出证据和下一步。
- 可审查：所有 AI 推断必须标注为候选，不能写成已确认结论。

## 9. 主从子智能体闭环

默认采用以下角色：

- 主智能体：理解任务、读取 `harness`、确定输出路径、拆分 DAG、创建子智能体、合并产物、裁决冲突、触发评估和收口。
- 事实收集执行器：只负责事实源索引和事实分类，不编写业务结论。
- 总 PRD 执行器：只负责总 PRD 的对象、属性、术语、范围、跨功能规则和总体验收。
- 子 PRD 执行器：只负责一个或一组功能子 PRD，不重新定义总 PRD 口径。
- 问题清单执行器：只负责阻塞/非阻塞问题整理和问题编号回填。
- 评估器子智能体：只读检查产物质量，给出“通过 / 不通过 / 有风险待修复”结论。

分派模板读取 `references/executor-subagent-templates.md`。编排流程读取 `references/orchestrator-workflow.md`。

## 10. 评估器子智能体

每次执行闭环完成后，必须使用独立评估器子智能体，要求：

- 角色：评估器子智能体。
- 推荐创建参数：`agent_type=explorer`、`reasoning_effort=medium` 或更高、`fork_context=false`，按任务复杂度显式指定 `model`。
- 边界：只读检查 `SKILL.md`、模板、引用规则、本次生成的 PRD 产物，以及命中子项目或仓库中的相关代码事实；禁止修改文件、禁止执行会写入状态的操作。
- 产出：按“通过 / 不通过 / 有风险待修复”给出结论，并列出文件路径、问题、影响和修复建议。
- 模板：使用 `references/evaluator-subagent-template.md`，分派时必须补齐上下文范围、验证标准和禁止事项。
- 禁止：评估器不得与执行器复用同一子智能体，不得由产出该 PRD 的执行器自评通过。

## 11. 输出要求

执行本技能时，最终回复必须说明：

- 产物路径。
- 总 PRD 和功能子 PRD 清单。
- 仍待确认的问题数量和阻塞级别。
- 已使用的主要事实源。
- 若存在后续开发意图，推荐下一步技能链。
