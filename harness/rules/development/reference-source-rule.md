# 参考源优先级 Rule

## 原则

与配置来源、接口契约、运行约定和兼容策略相关的判断，优先依赖仓库中的公开配置文件和现有代码，而不是主观猜测。

## 当前仓库推荐参考顺序

1. 根目录公开配置文件：`.env.example`、`environment.yml`、`docker-compose.yml`、`Dockerfile`、`pytest.ini`、`src/config.example.json`
2. `src/service/` 中现有实现代码，尤其是 `routers/`、`services/`、`repositories/`、`storage/`、`workflows/`
3. `src/deepagents/` 中的 middleware、backend 与 graph 实现
4. `src/gitnexus_parser/` 中的解析、ingestion 与 graph 构建代码
5. `harness/context/dev-environment.md` 中已确认的环境口径

## 使用要求

- 开始分析前，先列出当前最可信的前三个来源，并说明为何把它们作为第一参考。
- 在展开大范围代码阅读前，先写清当前最小证据集与暂缓加载的来源。
- 需要提炼共享规则时，优先抽取稳定结论，不照搬长文原文
- 配置文件、环境口径与代码不一致时，应显式说明“现状代码”和“当前配置口径”的差异
- 若信息不足，应先继续查证，不要补全不存在的规则细节
- 对 API 字段变更类任务，应先记录 router、service、repository、storage 或 workflow 之间的字段与状态流差异，再回到调用链做映射判断
