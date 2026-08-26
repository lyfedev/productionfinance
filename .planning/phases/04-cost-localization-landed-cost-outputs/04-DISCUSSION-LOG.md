# Phase 4: Cost Localization & Landed-Cost Outputs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-26
**Phase:** 04-cost-localization-landed-cost-outputs
**Areas discussed:** City cost profiles, Cost-line honesty, Seasonality, Sensitivity output — all four delegated to Claude in a single response

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| City cost profiles | Which cities get a `CityCostProfile` in this phase, and does a city price its costs with no curated rule file? Determines whether the ranked list and two-city gap are demonstrable now, and whether a non-USD city lands here for COST-08. | ✓ (delegated) |
| Cost-line honesty | Does the cost side get its own vocabulary — sourced / estimated-with-method / acknowledged-gap — beside the existing validated/researched tiers? Can an estimated line roll silently into a ranked total? | ✓ (delegated) |
| Seasonality | Sourced-only (per-diem month bands) vs modelled seasonal multipliers on stages, housing and crew labelled as assumptions. | ✓ (delegated) |
| Sensitivity output | How OUT-03 is computed (perturbation vs analytic), what counts as one input and how far it is nudged, and what keeps it descriptive rather than prescriptive. | ✓ (delegated) |

**User's choice:** *"you decide all, give your most thoughtful answer"*
**Notes:** Full delegation of all four areas in one response — the same posture taken in Phase 1 and Phase 3 ("none. all good."). No area was narrowed, excluded, or annotated. No scope creep was raised and no external document was referenced during the exchange.

---

## Claude's Discretion

All four presented areas, plus five items flagged in the preamble as Claude's call unless raised:

| Area | Decision reached | CONTEXT.md ref |
|------|------------------|----------------|
| City cost profiles | Cost profiles are Phase 4's artifact and rule files stay Phase 5's; floor set NY / LA / London, stretch Atlanta / Newark / Hartford; ranking on net landed cost with a separate `incentive_not_modelled` band; no Phase 5 rule file pulled forward | D-53…D-56 |
| Cost-line honesty | New orthogonal `basis` field (`sourced` / `estimated` / `modelling_assumption`); `Figure.confidence` gains no third value; basis degrades to the weakest input and never defaults on an empty list; acknowledged gaps are a declared exclusion list, not a `$0` line; per-diem caveat is a field on the figure; fringe is its own line; CI walks Route A's tree for any `validated` node | D-58…D-63 |
| Seasonality | Sourced-only, riding on published per-diem month bands; shoot calendar derived (needed for housing nights anyway); quarter-invariant lines named in the response; seasonal stage/crew/equipment variation declared an acknowledged gap | D-64…D-66 |
| Sensitivity output | Perturbation re-running the real pipeline, never an analytic derivative (the model is full of cliffs); per-input step sizes declared in committed YAML and displayed on every row; cliff crossings reported; CI grep for prescriptive vocabulary | D-67…D-70 |
| The D-36 seam (flagged in preamble) | Route A returns dollars; its spend is never `validated`; validation pairs may never route through the budget model; Routes A and B stay visibly distinct; the existing import guard is replaced, not deleted | D-71…D-73 |
| FX (flagged in preamble) | Committed dated snapshot, not a live call; a missing pair is a refusal, never a derived cross-rate | D-74 |
| Currency as a component | Currency is a first-class gap component with its own line and date, not a hidden conversion | D-75 |
| INC-10 exemptions | Cost reductions that never touch the incentive figure — folding them in would corrupt the one number that must stay reproducible against a government disclosure | D-76 |
| OUT-04 chart of accounts | Tag every line at creation; do not build the view. Ship the data, defer the rendering to Phase 11 | D-77 |
| Runtime posture | No network call and no new dependency anywhere in Phase 4; golden cost tests assert exact `Decimal` totals in CI | D-57, D-78 |

**Rejected options recorded deliberately** (so a later agent does not rediscover them as shortcuts):

- Treating an unmodelled incentive as `$0` to make the ranking look complete — **D-56**, rated one-way.
- An analytic/derivative sensitivity estimate — **D-67**; it is not merely less precise, it is wrong at exactly the cliffs (minimum-spend, tier bands, per-project cap) that make the output interesting.
- A modelled seasonal multiplier on stages or labour — **D-64**; an invented number applied to the largest lines would move the product's headline ranking.

**Escalate rather than quietly reverse:** D-56, D-59/D-63, D-64, D-72 — each is load-bearing on the project's honesty claim.

## Open Item Raised During Analysis

- **GSA monthly lodging rates.** D-64's sourced-only seasonality rests on GSA publishing per-month lodging rates for New York County and Los Angeles County. Believed true, not verified this session, and flagged in CONTEXT.md as the phase's single load-bearing unverified data assumption — the researcher must confirm it before planning around it. The stated fallback is seasonality present where a month band exists and explicitly absent where it does not, never backfilled with a multiplier.

## Deferred Ideas

No scope creep was raised by the user. The deferrals recorded in CONTEXT.md came from the phase-boundary analysis rather than from the discussion: CA/NJ/CT rule files and Job 1 (Phase 5); `DataFreshnessGate` and live FX/per-diem/rate-card refresh (Phase 7); the map, slider, ranked list and the printable assumptions panel PRV-04 (Phase 6); the rendered chart-of-accounts view OUT-04 (Phase 11); overtime, turnaround, meal penalties, kit fees, non-union differentials and negotiated hotel rates (acknowledged gaps, not modelled in Accounts); seasonal stage/crew/equipment variation (acknowledged gap until a sourced index exists); reverse mode (Phase 11, and the reason D-68's step table is data rather than inline constants); extending the D-51 mutation table to a cost anchor once golden cost totals exist (Phase 8).
