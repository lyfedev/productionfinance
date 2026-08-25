---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 0
total_count: 2
last_updated: 2026-08-25T18:41:03.532Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | deviation | .env.example |  | Still not created in repo (carried from 01-01); Task 2 created /opt/prodfin/.env directly on host with the documented required content instead | open |  | 2026-08-25T07:02:39.792Z |  |
| 2 | 02 | lint-warning | engine/pipeline.py |  | Pre-existing ruff violations (RUF022 __all__ sort, FURB157 verbose Decimal, ISC004 implicit concat) predate 02-08; repo-wide baseline was already 294 ruff errors before this plan (confirmed via git stash comparison) — out of scope per executor scope-boundary rule, not introduced by 02-08's changes | open |  | 2026-08-25T18:41:03.532Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "01",
    "file": ".env.example",
    "line": null,
    "description": "Still not created in repo (carried from 01-01); Task 2 created /opt/prodfin/.env directly on host with the documented required content instead",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-25T07:02:39.792Z",
    "resolved_at": null
  },
  {
    "id": 2,
    "kind": "lint-warning",
    "phase": "02",
    "file": "engine/pipeline.py",
    "line": null,
    "description": "Pre-existing ruff violations (RUF022 __all__ sort, FURB157 verbose Decimal, ISC004 implicit concat) predate 02-08; repo-wide baseline was already 294 ruff errors before this plan (confirmed via git stash comparison) — out of scope per executor scope-boundary rule, not introduced by 02-08's changes",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-25T18:41:03.532Z",
    "resolved_at": null
  }
]
````
