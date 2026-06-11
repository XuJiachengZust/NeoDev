# /neodev-submit

Primary intent entry for pre-submit checks and post-submit closure status.

Recommended commands:

```bash
neodev git check --json
neodev status --json
```

Use this intent when the user asks whether a change is ready to commit, whether staged changes match document scope, whether a DocChange trailer is required, or whether the pushed branch is closed.

Expected evidence:

- `git check` classifies staged changes as document-only, code-only, mixed, or empty.
- `git check` identifies required trailers, dangerous commit records, and retry guidance.
- `status` summarizes document graph, code graph, DocChange, and hook result evidence.
- `status` returns `open_gaps=[]` when the business workflow is closed.

Do not manually replace the server-side post-push hook transaction with separate document import, DocChange register, or graph refresh calls. Interpret the hook result and route gaps back to `neodev docs sync`, `neodev change impact`, or `neodev git check`.
