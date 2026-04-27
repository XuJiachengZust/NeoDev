---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-02-PLUGIN-SKILL-GUIDANCE
title: "插件 / Skill 引导规范"
aliases:
  - "插件 / Skill 引导规范"
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/requirements
created: 2026-04-27
updated: 2026-04-27
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-01-MASTER-PRD
related:
  - "[[01-master-prd]]"
---
# 插件 / Skill 引导规范

## 1. 目标

产品默认与插件 / skill 配合使用，但所有真实执行都下沉到 CLI。

MVP 不是只提供接入规范，而是需要同时交付：

- 官方插件
- 官方 skill

边界原则：

- 插件 / skill = 引导层、编排层、解释层
- CLI = 执行层、事实层、状态层

## 2. 职责边界

### 2.1 插件 / Skill 负责

- 引导用户选择正确 CLI
- 拼装和补全参数
- 把多步操作编排成工作流
- 用自然语言解释结果
- 做交互式风险提示
- 在会话开始或关键写操作前检查 CLI 版本兼容性

### 2.2 插件 / Skill 不负责

- 写业务状态
- 持久化图谱事实
- 判定最终校验结果
- 兼容多套 CLI 输出协议

版本协作规则：

- 默认与 CLI 强一致
- 发现不一致时优先调用 `cli version-check`
- 版本不兼容时不继续高风险写操作

### 2.3 CLI 负责

- 执行业务动作
- 落盘状态和关系事实
- 刷新图谱、链路、AI 描述
- 产出结构化结果

## 3. 推荐交互流程

### 3.1 会话启动前版本检查

1. 插件 / skill 启动会话
2. 调用 `cli version-check`
3. 如果兼容，继续正常工作流
4. 如果不兼容且允许自动更新，触发自动拉齐
5. 如果不兼容且不能自动更新，停止高风险写操作

### 3.2 文档变更到实现方案

1. 引导用户确认产品、版本、文档范围
2. 调用 `doc change register`
3. 调用 `graph impact`
4. 必要时补充：
- `graph semantic-search`
- `graph entity-context`
- `graph get-chain`
5. 基于 CLI 结果生成代码修改建议

### 3.3 分支分析

1. 确认 `product / version / project / branch`
2. 调用 `product version analyze`
3. 轮询：
- `product version analyze-status`
- `product version watch-status`
4. 分析完成后按需调用：
- `graph semantic-search`
- `graph get-chain`

### 3.4 推送前校验

1. 检查 commit message 中是否包含 `DocChange-ID`
2. 调用 `git verify-doc-change`
3. 如果是危险提交：
- 解释风险
- 询问是否继续
4. 如果用户确认继续，再调用对应 CLI 写入风险记录

### 3.5 推送后刷新

1. 推送成功后引导执行 `git post-push-refresh`
2. 如需进一步核查：
- `graph refresh-nodes`
- `graph get-chain`
3. 向用户解释哪些节点、链路和 AI 描述已更新

## 4. 参数补全规则

- 产品相关操作默认补全 `product_key`
- 检索和分析默认补全 `product_version_id`
- 图谱操作默认补全 `project_id` 和 `branch`
- 刷新和链路命令优先推荐最小范围参数

## 5. 风险提示规则

- 高风险写操作前先做版本检查
- 发现 `version_mismatch` 时先停止写操作
- 发现危险提交时必须提示风险和后果
- 不把 CLI 校验失败解释成“可以忽略的提示”

## 6. 结果解释规则

- 把 CLI 返回结果转成可理解的结论
- 解释影响范围、风险点、建议步骤
- 对 `graph get-chain` 结果重点解释链路意义，而不是原样倾倒数据
- 对 `graph refresh-nodes` 结果重点解释哪些节点被刷新、哪些 embedding 被复用

## 7. 推荐命令映射

| 场景 | 推荐 CLI |
| --- | --- |
| 检查版本并自动拉齐 | `cli version-check` |
| 登记文档变更 | `doc change register` |
| 看文档变更详情 | `doc change show` |
| 看影响范围 | `graph impact` |
| 做产品版本语义检索 | `graph semantic-search` |
| 看实体上下文 | `graph entity-context` |
| 看调用链 / 依赖链 / 影响链 | `graph get-chain` |
| 手动刷新节点 | `graph refresh-nodes` |
| 触发分支分析 | `product version analyze` |
| 看分析状态 | `product version analyze-status` |
| 推送前校验 | `git verify-doc-change` |
| 推送后刷新图谱与 AI 描述 | `git post-push-refresh` |

## 8. 禁止事项

- 插件 / skill 直接写业务表或图谱状态
- 插件 / skill 自行决定 `DocChange` 状态流转
- 插件 / skill 绕过 CLI 直接修改校验结果
- 插件 / skill 自行兼容多套 CLI 结果结构

## 9. 最小集成要求

- 能调用 `cli version-check`
- 能调用核心读命令和核心写命令
- 能处理中断、失败和危险提交提示
- 能解释语义检索、链路获取、节点刷新、推送校验结果

## 10. MVP 交付要求

MVP 中插件 / skill 不再是“可选参考实现”，而是正式交付件。

必须交付：

- 一份官方插件实现
- 一份官方 skill 实现

两者都需要覆盖完整主流程：

- 会话启动与版本检查
- 文档变更登记与影响分析
- 产品版本分支分析触发与状态查看
- 推送前 `DocChange-ID` 校验
- 危险提交提示与确认
- 推送后图谱、链路和 AI 描述刷新

交付约束：

- 插件与 skill 的工作流保持一致
- 插件与 skill 调用同一套 CLI 契约
- 插件与 skill 不得各自发明额外状态机
