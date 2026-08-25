---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-08-25T07:02:39.792Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | deviation | .env.example |  | Still not created in repo (carried from 01-01); Task 2 created /opt/prodfin/.env directly on host with the documented required content instead | open |  | 2026-08-25T07:02:39.792Z |  |

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
  }
]
````
