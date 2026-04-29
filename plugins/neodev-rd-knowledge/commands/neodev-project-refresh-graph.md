# /neodev-project-refresh-graph

用于在远程 NeoDev 服务上重建某个项目分支的代码图谱。

执行前先确认远程 CLI 环境：

```bash
python plugins/neodev-rd-knowledge/check_neodev_environment.py
neodev config show
neodev cli version-check --json
```

刷新分支图谱：

```bash
neodev project refresh-graph --project-id <project_id> --branch <branch> --json
```

该命令不再需要 `--version-id`、`--commit-sha`，也不再执行提交级增量同步。
