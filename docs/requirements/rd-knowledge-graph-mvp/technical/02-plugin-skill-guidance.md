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

产品默认与插件 / skill 配合使用，但所有真实执行都通过本地 `neodev` CLI 客户端调用统一远程 NeoDev 服务完成。开发者电脑只安装 CLI 客户端、官方 skill 和官方插件，不在本地部署 NeoDev 服务、数据库或图谱。

MVP 不是只提供接入规范，而是需要同时交付：

- 官方插件
- 官方 skill

边界原则：

- 插件 / skill = 引导层、编排层、解释层
- 本地 CLI 客户端 = 远程服务调用层
- 远程 NeoDev 服务 = 执行层、事实层、状态层

## 2. 职责边界

### 2.1 插件 / Skill 负责

- 引导用户选择正确 CLI
- 拼装和补全参数
- 把多步操作编排成工作流
- 用自然语言解释结果
- 做交互式风险提示
- 在会话开始或关键写操作前检查本地 CLI 是否已配置远程服务，并检查 CLI/远程服务版本兼容性

### 2.2 插件 / Skill 不负责

- 写业务状态
- 持久化图谱事实
- 判定最终校验结果
- 兼容多套 CLI 输出协议

版本协作规则：

- 默认与本地 CLI 客户端和远程 NeoDev 服务强一致
- 发现未配置远程服务时优先调用 `neodev config set-server <url>`
- 发现不一致时优先调用 `neodev cli version-check --json`
- 版本不兼容时不继续高风险写操作

### 2.3 本地 CLI 客户端负责

- 保存和读取远程服务地址
- 把命令、参数和本地项目路径上下文发送给远程 NeoDev 服务
- 返回远程服务的结构化结果

### 2.4 远程 NeoDev 服务负责

- 执行业务动作
- 落盘状态和关系事实
- 刷新图谱、链路和必要索引
- 产出结构化结果

## 3. 推荐交互流程

### 3.1 会话启动前版本检查

1. 插件 / skill 启动会话
2. 调用 `neodev config show` 确认本地 CLI 已配置远程服务
3. 调用 `neodev cli version-check --json`
4. 如果兼容，继续正常工作流
5. 如果不兼容且允许自动更新，触发自动拉齐
6. 如果不兼容且不能自动更新，停止高风险写操作

### 3.2 文档变更到实现方案

1. 引导用户确认产品、版本、文档范围
2. 调用 `doc change register`
3. 调用 `graph impact`
4. 必要时补充：
- `graph semantic-search`
- `graph entity-context`
- `graph get-chain`
5. 基于 CLI 结果生成代码修改建议

### 3.3 仓库接入与自动图谱构建

1. 确认仓库地址和项目名称。
2. 调用 `project create --repo-url` 登记仓库。
3. 远程 NeoDev 服务自动触发图谱构建；插件 / skill 不再显式展示或调用旧分析入口。
4. 如需纳入产品版本范围，调用 `product version bind-branch`。
5. 图谱构建完成后按需调用：
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

1. 推送成功后引导执行 `project refresh-commit-graph`
2. 如需进一步核查：
- `graph get-chain`
3. 当 CLI 返回 `fallback=true` 时，解释为什么回退到 `project refresh-graph`
4. 向用户解释哪些代码节点、关系和分支快照已更新

## 4. 参数补全规则

- 产品相关操作默认补全 `product_key`
- 检索默认补全 `product_version_id`
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
- 对 `project refresh-commit-graph` 结果重点解释本次提交刷新了哪些文件，以及是否回退到分支图刷新

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
| 手工维护图节点 | `graph node add/update/delete/show/list` |
| 手工维护图关系 | `graph edge add/update/delete/show/list` |
| 接入仓库并自动构建图谱 | `project create --repo-url` |
| 查看仓库项目 | `project show` |
| 推送前校验 | `git verify-doc-change` |
| 推送后刷新本次提交对应图谱 | `project refresh-commit-graph` |

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
- 产品版本自动图谱构建触发与状态查看
- 推送前 `DocChange-ID` 校验
- 危险提交提示与确认
- 推送后图谱、链路和 结构化描述刷新

交付约束：

- 插件与 skill 的工作流保持一致
- 插件与 skill 调用同一套 CLI 契约
- 插件与 skill 不得各自发明额外状态机
