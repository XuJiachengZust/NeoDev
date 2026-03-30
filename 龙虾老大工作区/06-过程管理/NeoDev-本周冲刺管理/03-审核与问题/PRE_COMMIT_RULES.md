# PRE_COMMIT_RULES

目的：在提交前增加最小工程门槛，避免误带无关内容、生成物或大文件。

## 提交前必须检查

### 1. 范围检查
- staged 文件必须与当前任务目标直接相关
- 禁止 `git add .`
- 禁止将多个业务目标塞进一个 commit

### 2. 生成物检查
以下内容默认禁止提交，除非任务明确要求：
- `web/node_modules/`
- `web/dist/`
- `__pycache__/`
- `.cursor/plans/`
- `.claude/`
- `docker/images/*.tar`
- `bash.exe.stackdump`

### 3. 大文件检查
- 任何意外的大文件都必须在提交前人工确认
- 特别警惕镜像包、压缩包、导出产物

### 4. 提交前最小自检
提交前至少确认：
- 当前任务目标是什么
- staged 文件为什么都需要
- 验证命令是否已执行
- 是否满足 Review Gate

### 5. 建议执行顺序
1. 运行 `git status --short`
2. 运行 `git diff --name-only --cached`
3. 对照当前任务目标检查 staged 文件
4. 再提交
