# /neodev-project-refresh-graph

用于在分支提交变更后，通过本地 `neodev` CLI 调用远程 NeoDev 服务，优先刷新本次提交涉及的代码节点和关系。提交过大或无法可靠定位时，服务会回退到指定项目分支图刷新。

边界要求：

- 先运行 `python plugins/neodev-rd-knowledge/check_neodev_environment.py`。
- 先运行 `neodev config show` 和 `neodev cli version-check --json`。
- 推送后默认使用 `neodev project refresh-commit-graph --project-id <project_id> --version-id <version_id> --branch <branch> --commit-sha <commit_sha> --json`。
- 只有提交内容过多或服务返回需要兜底时，才使用 `neodev project refresh-graph --project-id <project_id> --version-id <version_id> --branch <branch> --json`。
- 手工增删改节点使用 `neodev graph node ... --json`。
- 手工增删改关系使用 `neodev graph edge ... --json`。
- 不直接写 PostgreSQL 或 Neo4j。
