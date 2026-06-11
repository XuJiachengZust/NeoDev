# /neodev-change

Primary intent entry for starting a document-backed implementation change and collecting impact context.

Recommended commands:

```bash
neodev change start --json
neodev change impact --json
```

Use this intent when the user asks to start implementation from requirements, register or prepare a DocChange, inspect affected code/document graph evidence, or decide what needs to be changed before coding.

Expected evidence:

- `change start` identifies the document change source and linked controlled documents.
- `change impact` summarizes impacted graph nodes, relevant code context, risk points, and missing evidence.
- Output includes `steps`, `closure_evidence`, and `next_actions` so the workflow can move to `neodev git check`.

Before editing code, verify the change has document coverage. If no approved requirement or technical design covers the planned files, stop and ask the user whether to update documents first or explicitly proceed without coverage.

Advanced graph impact and entity context commands remain available for deep investigation, but this command is the default implementation planning path.
