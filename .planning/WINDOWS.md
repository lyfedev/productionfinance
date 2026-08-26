---
schema_version: 1
open_count: 5
waived_count: 0
fixed_count: 0
total_count: 5
last_updated: 2026-08-26T19:10:01.392Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | deviation | .env.example |  | Still not created in repo (carried from 01-01); Task 2 created /opt/prodfin/.env directly on host with the documented required content instead | open |  | 2026-08-25T07:02:39.792Z |  |
| 2 | 02 | lint-warning | engine/pipeline.py |  | Pre-existing ruff violations (RUF022 __all__ sort, FURB157 verbose Decimal, ISC004 implicit concat) predate 02-08; repo-wide baseline was already 294 ruff errors before this plan (confirmed via git stash comparison) — out of scope per executor scope-boundary rule, not introduced by 02-08's changes | open |  | 2026-08-25T18:41:03.532Z |  |
| 3 | 02 | unmet-truth | tests/test_engine_against_validation_pairs.py |  | jurisdictions/us-ct.yaml's real transfer_discount.typical_rate_low/typical_rate_high are both null (CGS 12-217jj(e)(1) states no market discount rate); engine.net_cash.transferable correctly refuses to convert at an unsourced rate, so price_jurisdiction raises ValueError for every active Connecticut pair — Christmas Always reproduces exactly through the direct base-then-credit path but NOT through price_jurisdiction as plan 02-09 originally required. Documented in test_christmas_always_reproduces_exactly_through_price_jurisdiction; resolves automatically if us-ct.yaml is ever sourced with a real discount rate. | open |  | 2026-08-25T19:00:12.777Z |  |
| 4 | 02 | lint-warning | engine/credit.py,tests/test_engine_credit.py,tests/test_engine_against_validation_pairs.py |  | Plan 02-09 adds 4 new FURB157 (verbose Decimal("N") constructor) findings — same established RD-01 quoted-Decimal convention already present 293 times pre-existing across engine/tests (confirmed via git stash: 296 baseline -> 297 after this plan's changes across engine/+tests/). No new rule categories introduced. Out of scope per executor scope-boundary rule; repo-wide ruff cleanup remains open, tracked separately (see entry 2). | open |  | 2026-08-25T19:00:20.858Z |  |
| 5 | 04 | lint-warning | engine/cost_localizer.py,engine/landed_cost.py,engine/budget.py |  | Plan 04-01 adds 6 new FURB157 (verbose Decimal("N") constructor, RD-01 quoted-Decimal convention) and 2 new ISC004 (implicit string concat in a derivation tuple, same pre-existing pattern as engine/qualifying_base.py and engine/pipeline.py) findings — repo-wide ruff baseline measured 300 before this plan (git worktree at 0f475c1), 315 after (net +15, remainder from other new test files in the same established categories). No new rule categories introduced. Out of scope per executor scope-boundary rule; repo-wide ruff cleanup remains open, tracked in entry 2. | open |  | 2026-08-26T19:10:01.392Z |  |

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
  },
  {
    "id": 3,
    "kind": "unmet-truth",
    "phase": "02",
    "file": "tests/test_engine_against_validation_pairs.py",
    "line": null,
    "description": "jurisdictions/us-ct.yaml's real transfer_discount.typical_rate_low/typical_rate_high are both null (CGS 12-217jj(e)(1) states no market discount rate); engine.net_cash.transferable correctly refuses to convert at an unsourced rate, so price_jurisdiction raises ValueError for every active Connecticut pair — Christmas Always reproduces exactly through the direct base-then-credit path but NOT through price_jurisdiction as plan 02-09 originally required. Documented in test_christmas_always_reproduces_exactly_through_price_jurisdiction; resolves automatically if us-ct.yaml is ever sourced with a real discount rate.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-25T19:00:12.777Z",
    "resolved_at": null
  },
  {
    "id": 4,
    "kind": "lint-warning",
    "phase": "02",
    "file": "engine/credit.py,tests/test_engine_credit.py,tests/test_engine_against_validation_pairs.py",
    "line": null,
    "description": "Plan 02-09 adds 4 new FURB157 (verbose Decimal(\"N\") constructor) findings — same established RD-01 quoted-Decimal convention already present 293 times pre-existing across engine/tests (confirmed via git stash: 296 baseline -> 297 after this plan's changes across engine/+tests/). No new rule categories introduced. Out of scope per executor scope-boundary rule; repo-wide ruff cleanup remains open, tracked separately (see entry 2).",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-25T19:00:20.858Z",
    "resolved_at": null
  },
  {
    "id": 5,
    "kind": "lint-warning",
    "phase": "04",
    "file": "engine/cost_localizer.py,engine/landed_cost.py,engine/budget.py",
    "line": null,
    "description": "Plan 04-01 adds 6 new FURB157 (verbose Decimal(\"N\") constructor, RD-01 quoted-Decimal convention) and 2 new ISC004 (implicit string concat in a derivation tuple, same pre-existing pattern as engine/qualifying_base.py and engine/pipeline.py) findings — repo-wide ruff baseline measured 300 before this plan (git worktree at 0f475c1), 315 after (net +15, remainder from other new test files in the same established categories). No new rule categories introduced. Out of scope per executor scope-boundary rule; repo-wide ruff cleanup remains open, tracked in entry 2.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T19:10:01.392Z",
    "resolved_at": null
  }
]
````
