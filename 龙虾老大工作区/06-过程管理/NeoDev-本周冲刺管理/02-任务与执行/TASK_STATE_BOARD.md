# TASK_STATE_BOARD

说明：这是当前任务状态主板。以后所有任务都必须先定义目标与边界，再进入状态机。

| Task ID | 任务名称 | 目标 | 边界 | 当前状态 | 上次更新时间 | 当前证据 | 下一步动作 | 超时阈值 | 是否需老大审核 |
|---|---|---|---|---|---|---|---|---|---|
| W1-02 | 项目级 requirements 路由挂载 | 让项目级 requirements API 正式接入主 API 聚合器 | 仅限 `src/service/routers/api.py` 与必要验证；不扩展到无关源码 | review_pending | 2026-03-26 16:36 | `api.py` diff 已确认；已跑 `pytest tests/test_api_requirements.py -q`，结果 8 skipped | stage 目标文件并按最小单元提交 | 30m | 否 |
| W1-SM-01 | 最小强状态机落地 | 建立任务状态板、执行心跳、汇报约束、状态跃迁规则 | 仅限过程管理目录文档；不修改 NeoDev 业务源码 | executing | 2026-03-26 15:33 | 正在创建状态机文档 | 写完后进入 artifact_ready | 30m | 否 |
