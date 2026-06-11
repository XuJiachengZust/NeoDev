# /neodev-context

Primary intent entry for discovering NeoDev environment, product/version scope, repository binding, and branch graph context.

Recommended commands:

```bash
neodev doctor --json
neodev context show --json
neodev setup repo --json
```

Use this intent when the user asks which product/version/project/branch is active, whether the local CLI can reach the remote service, or whether a repository is ready for NeoDev workflows.

Expected evidence:

- `doctor` reports local configuration and remote compatibility readiness.
- `context show` reports product, version, project, branch, document, and graph context if available.
- `setup repo` binds repository context and moves the workflow toward `neodev docs sync`.

Advanced atomic commands such as product/version lookup, branch binding, and project graph refresh remain available for maintenance, but do not recommend them as the default user path.
