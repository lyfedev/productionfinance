---
schema_version: 1
open_count: 11
waived_count: 0
fixed_count: 0
total_count: 11
last_updated: 2026-08-26T19:42:02.202Z
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
| 6 | 04 | unmet-truth | data/union_rates/fringe_schedules.yaml |  | IATSE pension_health_pct stays basis: estimated (35-45% blanket figure, midpoint 40%) — this session located and archived IATSE Local 600's own rate cards (camera wage scale) but not the full IATSE Basic Agreement text, which is where a Pension & Health contribution percentage would be stated. Research Assumption A1 (04-RESEARCH.md) is therefore NOT resolved to sourced; the figure remains a payroll-vendor-commentary estimate (cmsproductions.com, topsheet.io), never promoted per Pitfall 1's explicit instruction. | open |  | 2026-08-26T19:31:07.398Z |  |
| 7 | 04 | unmet-truth | data/union_rates/sag-aftra.yaml,data/union_rates/fringe_schedules.yaml |  | SAG-AFTRA: no rate rows and no sourced fringe percentage. sagaftra.org and every path under it (production-center/basic-agreements, production-center/low-budget-agreements) returned HTTP 403 with a DataDome bot-protection challenge for every fetch attempt this session — plain curl (multiple user agents) and a real headless-Chromium fetch via the gstack browse skill were both blocked identically. sagaftraplans.org (the plan administrator's own site) was reachable but exposes only a login-gated Contributions Manager, no published percentage table. pension_health_pct stays basis: estimated at 21%, sourced only from a payroll-adjacent industry summary, not sagaftra.org itself. | open |  | 2026-08-26T19:31:07.482Z |  |
| 8 | 04 | unmet-truth | data/union_rates/iatse.yaml,data/union_rates/us-ny-crew.yaml |  | The general_crew craft (9 of 10 crew_tiers.yaml departments: production, grip_and_electric, art, wardrobe, hair_and_makeup, sound, transportation, locations, post) stays basis: estimated for both New York and Los Angeles at the same round $450/day figure — the per-craft IATSE locals that would actually cover these departments (Local 80 grips, Local 728 lighting, Local 800 art, Local 705 costumers, Local 706 hair/makeup, Local 695 sound, Local 871 script supervisors, Local 700 editors) plus Teamsters Local 399 for transportation were not fetched this session; only IATSE Local 600's camera-department rate cards were located, fetched and archived. Only the camera department is genuinely basis: sourced this plan. | open |  | 2026-08-26T19:31:07.565Z |  |
| 9 | 04 | unmet-truth | data/union_rates/iatse.yaml |  | New York's IATSE Local 600 camera row (iatse-l600-camera-us-ny-2025) has no 2026-2027 successor — icg600.com publishes only a document explicitly marked DRAFT for the New York/Eastern Region 2026-2027 rate card at the time of this session, not yet a ratified final rate card, so it was not archived as sourced. A shoot date after 2026-08-01 in New York correctly raises ValueError from select_rate_row rather than falling back to the expired 2025-2026 row or inventing a 2026-2027 figure. Los Angeles has both the 2025-2026 and the final (non-draft) 2026-2027 Western Region rate card archived, so this gap is New-York-specific. | open |  | 2026-08-26T19:31:07.648Z |  |
| 10 | 04 | unmet-truth | data/union_rates/fringe_schedules.yaml |  | payroll_tax_pct and other_burden_pct are basis: estimated for all four unions (IATSE, SAG-AFTRA, DGA, WGA), using the same generic industry-standard figures (FICA+FUTA/SUTA ~9.65%, general workers'-comp/liability burden ~2%) — by nature these are government-imposed or insurance-market obligations, never a figure any union's own document publishes, so no amount of further fetching would move these two components to sourced. Only pension_health_pct differs per union and is where this session's sourcing effort concentrated (DGA and WGA resolved to sourced; IATSE and SAG-AFTRA remain estimated, see the two entries above). | open |  | 2026-08-26T19:31:07.730Z |  |
| 11 | 04 | lint-warning | engine/cost_localizer.py,tests/test_engine_cost_localizer.py |  | Plan 04-02 Task 2 adds 4 new ISC004 (implicit string concat in _price_labour_department's multi-line derivation tuple, same pre-existing pattern as _price_line/engine/qualifying_base.py/engine/pipeline.py) and 1 new FURB157 (verbose Decimal("0") constructor, RD-01 quoted-Decimal convention) findings — repo-wide ruff baseline measured 316 before this task's changes, 320 after (net +4; some overlap with pre-existing findings in _derive_spend_breakdown's unchanged Decimal("0") lines). No new rule categories introduced. Out of scope per executor scope-boundary rule; repo-wide ruff cleanup remains open, tracked in entry 2. | open |  | 2026-08-26T19:42:02.202Z |  |

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
  },
  {
    "id": 6,
    "kind": "unmet-truth",
    "phase": "04",
    "file": "data/union_rates/fringe_schedules.yaml",
    "line": null,
    "description": "IATSE pension_health_pct stays basis: estimated (35-45% blanket figure, midpoint 40%) — this session located and archived IATSE Local 600's own rate cards (camera wage scale) but not the full IATSE Basic Agreement text, which is where a Pension & Health contribution percentage would be stated. Research Assumption A1 (04-RESEARCH.md) is therefore NOT resolved to sourced; the figure remains a payroll-vendor-commentary estimate (cmsproductions.com, topsheet.io), never promoted per Pitfall 1's explicit instruction.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T19:31:07.398Z",
    "resolved_at": null
  },
  {
    "id": 7,
    "kind": "unmet-truth",
    "phase": "04",
    "file": "data/union_rates/sag-aftra.yaml,data/union_rates/fringe_schedules.yaml",
    "line": null,
    "description": "SAG-AFTRA: no rate rows and no sourced fringe percentage. sagaftra.org and every path under it (production-center/basic-agreements, production-center/low-budget-agreements) returned HTTP 403 with a DataDome bot-protection challenge for every fetch attempt this session — plain curl (multiple user agents) and a real headless-Chromium fetch via the gstack browse skill were both blocked identically. sagaftraplans.org (the plan administrator's own site) was reachable but exposes only a login-gated Contributions Manager, no published percentage table. pension_health_pct stays basis: estimated at 21%, sourced only from a payroll-adjacent industry summary, not sagaftra.org itself.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T19:31:07.482Z",
    "resolved_at": null
  },
  {
    "id": 8,
    "kind": "unmet-truth",
    "phase": "04",
    "file": "data/union_rates/iatse.yaml,data/union_rates/us-ny-crew.yaml",
    "line": null,
    "description": "The general_crew craft (9 of 10 crew_tiers.yaml departments: production, grip_and_electric, art, wardrobe, hair_and_makeup, sound, transportation, locations, post) stays basis: estimated for both New York and Los Angeles at the same round $450/day figure — the per-craft IATSE locals that would actually cover these departments (Local 80 grips, Local 728 lighting, Local 800 art, Local 705 costumers, Local 706 hair/makeup, Local 695 sound, Local 871 script supervisors, Local 700 editors) plus Teamsters Local 399 for transportation were not fetched this session; only IATSE Local 600's camera-department rate cards were located, fetched and archived. Only the camera department is genuinely basis: sourced this plan.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T19:31:07.565Z",
    "resolved_at": null
  },
  {
    "id": 9,
    "kind": "unmet-truth",
    "phase": "04",
    "file": "data/union_rates/iatse.yaml",
    "line": null,
    "description": "New York's IATSE Local 600 camera row (iatse-l600-camera-us-ny-2025) has no 2026-2027 successor — icg600.com publishes only a document explicitly marked DRAFT for the New York/Eastern Region 2026-2027 rate card at the time of this session, not yet a ratified final rate card, so it was not archived as sourced. A shoot date after 2026-08-01 in New York correctly raises ValueError from select_rate_row rather than falling back to the expired 2025-2026 row or inventing a 2026-2027 figure. Los Angeles has both the 2025-2026 and the final (non-draft) 2026-2027 Western Region rate card archived, so this gap is New-York-specific.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T19:31:07.648Z",
    "resolved_at": null
  },
  {
    "id": 10,
    "kind": "unmet-truth",
    "phase": "04",
    "file": "data/union_rates/fringe_schedules.yaml",
    "line": null,
    "description": "payroll_tax_pct and other_burden_pct are basis: estimated for all four unions (IATSE, SAG-AFTRA, DGA, WGA), using the same generic industry-standard figures (FICA+FUTA/SUTA ~9.65%, general workers'-comp/liability burden ~2%) — by nature these are government-imposed or insurance-market obligations, never a figure any union's own document publishes, so no amount of further fetching would move these two components to sourced. Only pension_health_pct differs per union and is where this session's sourcing effort concentrated (DGA and WGA resolved to sourced; IATSE and SAG-AFTRA remain estimated, see the two entries above).",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T19:31:07.730Z",
    "resolved_at": null
  },
  {
    "id": 11,
    "kind": "lint-warning",
    "phase": "04",
    "file": "engine/cost_localizer.py,tests/test_engine_cost_localizer.py",
    "line": null,
    "description": "Plan 04-02 Task 2 adds 4 new ISC004 (implicit string concat in _price_labour_department's multi-line derivation tuple, same pre-existing pattern as _price_line/engine/qualifying_base.py/engine/pipeline.py) and 1 new FURB157 (verbose Decimal(\"0\") constructor, RD-01 quoted-Decimal convention) findings — repo-wide ruff baseline measured 316 before this task's changes, 320 after (net +4; some overlap with pre-existing findings in _derive_spend_breakdown's unchanged Decimal(\"0\") lines). No new rule categories introduced. Out of scope per executor scope-boundary rule; repo-wide ruff cleanup remains open, tracked in entry 2.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T19:42:02.202Z",
    "resolved_at": null
  }
]
````
