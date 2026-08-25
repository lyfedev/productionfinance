---
phase: 02-engine-spine-incentive-interpreter
plan: 07
subsystem: engine
tags: [decimal, pydantic, pytest, incentive-engine, provenance]

# Dependency graph
requires:
  - phase: 02-engine-spine-incentive-interpreter
    provides: "engine/credit.py's blended_by_ceiling_split rate branch and engine/qualifying_base.py's excluded-line-items/minimum-spend steps (plans 02-03, 02-05)"
provides:
  - "blended_by_ceiling_split now slices an effective core expenditure that carries forward the minimum-spend cliff, excluded-line-items and per-person-ceiling reductions — closing CR-01"
  - "EXCLUDED_LINE_ITEMS_TOTAL_LABEL, an always-attached (even-when-zero) marker Figure recording the excluded-line-items reduction total"
  - "A regression fixture and five tests exercising the combination no committed fixture previously exercised: a binding minimum-spend cliff, a non-empty excluded_line_items list and a binding per-person ceiling, all on one blended_by_ceiling_split programme"
affects: [02-09, 02-08]

# Actuals (#2632)
actuals:
  tokens: 9500
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Effective-core-expenditure carry-forward: a rate branch that legitimately re-derives one adjustment (the percentage cap) from raw core expenditure must still carry every OTHER already-applied reduction forward onto that same core-expenditure value before re-deriving — never slice the raw input directly once any reduction has occurred elsewhere in the pipeline."
    - "Always-attached, zero-when-absent marker Figure: EXCLUDED_LINE_ITEMS_TOTAL_LABEL mirrors _apply_uplift_stacking's existing _UPLIFT_ADDITIONAL_RATE_LABEL convention — a downstream step that needs to read 'what did an earlier step to do the base' finds a Decimal('0') marker rather than a missing edge, so 'no adjustment declared' and 'the edge is missing' are never confused."

key-files:
  created:
    - tests/fixtures/jurisdictions/synthetic-blend-adjustments.yaml
  modified:
    - engine/credit.py
    - engine/qualifying_base.py
    - tests/test_engine_credit.py

key-decisions:
  - "Implemented the review's first CR-01 fix suggestion (carry every non-percentage-cap reduction onto core expenditure before slicing), not the 'simpler' second suggestion (slice figure.value directly) — the second suggestion is arithmetically the cap-before-split misreading and produces Decimal('7632000') on the UK fixture, not Decimal('7176000')."
  - "The per-person-ceiling reduction is read as qualifying_base_input.value minus figure.value at entry to the rate branch, relying on the proven invariant that _apply_per_person_ceiling is the only step between Figure construction and the rate branch that changes .value — stated as a comment so a future inserted step is forced to reckon with it, rather than adding a second marker Figure for symmetry with the excluded-line-items total."
  - "A zero-or-below running base short-circuits inside the blended_by_ceiling_split branch specifically, not as a global change to compute_gross_credit or to the other two rate branches — scoped exactly to the code path CR-01 broke, per the plan's prohibition against widening past the recorded gap set."

requirements-completed: [INC-02, INC-03, INC-09, PRV-03]

coverage:
  - id: D1
    description: "A committed fixture and regression suite reproduce CR-01 by execution — failing RED against the unfixed engine with the exact wrong values (Decimal('7176000') where Decimal('6496000') and Decimal('0') were expected)"
    requirement: PRV-03
    verification:
      - kind: unit
        ref: "tests/test_engine_credit.py#test_blend_honours_excluded_items_and_per_person_ceiling"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py#test_blend_minimum_spend_cliff_zeroes_the_credit_and_the_derivation_agrees"
        status: pass
    human_judgment: false
  - id: D2
    description: "blended_by_ceiling_split reports a credit that reflects the minimum-spend cliff, excluded line items and per-person ceiling — each adjustment moves the number independently and honouring only one fails"
    requirement: INC-02
    verification:
      - kind: unit
        ref: "tests/test_engine_credit.py#test_blend_each_adjustment_moves_the_number_independently"
        status: pass
    human_judgment: false
  - id: D3
    description: "The percentage-cap per-slice re-derivation (SCOPE-FREEZE.md dimension 3's carve-out) and the enhanced/standard threshold boundary behavior are unchanged"
    requirement: INC-03
    verification:
      - kind: unit
        ref: "tests/test_engine_credit.py#test_blend_enhanced_threshold_boundary"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py#test_blend_two_rates_by_ceiling_reproduces_uk_example_and_not_the_cap_before_split_misreading"
        status: pass
    human_judgment: false
  - id: D4
    description: "A binding minimum-spend cliff reaches the credit (Decimal('0')) rather than being silently discarded, evaluated against the post-exclusion qualifying base, with a boundary sweep at the threshold and one dollar below"
    requirement: INC-09
    verification:
      - kind: unit
        ref: "tests/test_engine_credit.py#test_blend_minimum_spend_cliff_zeroes_the_credit_and_the_derivation_agrees"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every already-reproducing figure still reproduces byte-identically: Anora, Christmas Always, the UK worked example (gross and net), and zz-fixture-throwaway's jurisdiction total"
    verification:
      - kind: unit
        ref: "tests/test_engine_against_validation_pairs.py#test_anora_reproduces_exactly"
        status: pass
      - kind: unit
        ref: "tests/test_engine_against_validation_pairs.py#test_christmas_always_reproduces_exactly"
        status: pass
      - kind: unit
        ref: "tests/test_engine_net_cash.py#test_taxable_mechanism_uk_worked_example"
        status: pass
      - kind: unit
        ref: "tests/test_engine_jurisdiction_additivity.py (full module)"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py#test_blend_uk_worked_example_unchanged"
        status: pass
    human_judgment: false

duration: 51min
completed: 2026-08-25
status: complete
---

# Phase 2 Plan 07: CR-01 Gap Closure Summary

**Fixed `blended_by_ceiling_split` to slice an effective core expenditure carrying forward the minimum-spend cliff, excluded-line-items and per-person-ceiling reductions, closing the one defect blocking three of Phase 2's five roadmap success criteria.**

## Performance

- **Duration:** 51 min
- **Started:** 2026-08-25T18:39:00Z (approx., prior plan's completion timestamp)
- **Completed:** 2026-08-25T18:30:19Z (Task 2 commit)
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- Reproduced CR-01 by execution: a new fixture (`synthetic-blend-adjustments.yaml`) combines `blended_by_ceiling_split` with a binding minimum-spend cliff, a non-empty `excluded_line_items` list, and a binding per-person ceiling — the exact combination no committed fixture previously exercised — and five new tests, three of which failed RED against the unfixed engine with the documented wrong value `Decimal('7176000')`.
- Fixed the branch: `engine/credit.py`'s `blended_by_ceiling_split` rate step now computes an *effective core expenditure* — raw core expenditure minus the excluded-line-items total and the per-person-ceiling reduction, both floored at zero — and slices that, never the raw core-expenditure Figure directly. The percentage-cap per-slice re-derivation (SCOPE-FREEZE.md dimension 3's carve-out) is preserved unchanged.
- Added a zero-or-below short circuit: a binding minimum-spend cliff (or a per-person-ceiling reduction driving the base negative) now returns `Decimal('0')` before any slice is rated, instead of silently falling through to the raw-core-expenditure calculation.
- Added `EXCLUDED_LINE_ITEMS_TOTAL_LABEL`, an always-attached marker Figure (`Decimal('0')` when no items are excluded, never omitted) recording exactly what `_apply_excluded_line_items` subtracted, so the rate branch can read it back without recomputing and risking drift.
- Every previously-reproducing figure still reproduces byte-identically: Anora (`Decimal('991190')`), Christmas Always (`Decimal('1159502')`), the UK worked example (gross `Decimal('7176000')`, net `Decimal('5382000')`), and `zz-fixture-throwaway.yaml`'s jurisdiction total (`Decimal('12475000')`).

## Task Commits

Each task was committed atomically, RED then GREEN:

1. **Task 1: Red — a fixture and a regression suite that reproduce CR-01 end to end** - `6ce2d9d` (test)
2. **Task 2: Green — slice the actually-adjusted base, preserving only the percentage-cap carve-out** - `f14ad18` (fix)

**Plan metadata:** committed separately after this SUMMARY.

## Files Created/Modified

- `tests/fixtures/jurisdictions/synthetic-blend-adjustments.yaml` - New synthetic fixture declaring three `blended_by_ceiling_split` programmes (`blend-adjustments-both`, `blend-adjustments-ceiling-only`, `blend-adjustments-cliff`) with a hand-worked derivation of every expected value in the header comment
- `tests/test_engine_credit.py` - Five new tests: `test_blend_honours_excluded_items_and_per_person_ceiling`, `test_blend_each_adjustment_moves_the_number_independently`, `test_blend_minimum_spend_cliff_zeroes_the_credit_and_the_derivation_agrees` (also covers the INC-09 threshold boundary edge), `test_blend_enhanced_threshold_boundary`, `test_blend_uk_worked_example_unchanged`
- `engine/qualifying_base.py` - `EXCLUDED_LINE_ITEMS_TOTAL_LABEL` constant (exported in `__all__`); `_apply_excluded_line_items` now returns `(Figure, Decimal)` so the recorded total can never drift from what was actually subtracted; `compute_qualifying_base` attaches the marker Figure unconditionally
- `engine/credit.py` - New `_find_excluded_line_items_total` helper mirroring `_find_uplift_additional_rate`; the `blended_by_ceiling_split` branch of `_apply_rate` rewritten to compute and slice an effective core expenditure, with a zero-or-below short circuit and an unconditional new derivation line naming the raw core expenditure, the total reduction, and the effective core expenditure

## Decisions Made

See `key-decisions` in frontmatter. In short: implemented the review's carry-forward fix (not the simpler-looking cap-before-split misreading); relied on the proven "only `_apply_per_person_ceiling` changes `.value` between construction and the rate step" invariant rather than adding a second marker Figure; scoped the zero-or-below short circuit to `blended_by_ceiling_split` only, per the plan's explicit prohibition against widening past the recorded gap set.

## Deviations from Plan

None — plan executed exactly as written. (One implementation slip was caught and fixed before any commit: the zero-or-below short circuit's first draft omitted `value=Decimal("0")` from its `with_step` call, which would have left the credit at whatever negative value the per-person ceiling had already produced. Caught immediately by re-running `test_blend_minimum_spend_cliff_zeroes_the_credit_and_the_derivation_agrees` before committing Task 2 — normal TDD iteration within the task, not a deviation from what the plan specified, so not logged as a Rule N item.)

## Issues Encountered

`uv run ruff check engine/ tests/` reports 294 findings post-change versus 285 pre-existing on the unmodified baseline (verified via `git stash`). All 9 new findings are `FURB157` (`Decimal("0")` → `Decimal(0)`) and `ISC004` (multi-line f-string tuple without a trailing comma) — the same two style-only rule classes already present 285 times throughout the pre-existing codebase, using the identical established convention (quoted-string `Decimal` literals, per RD-01) as the code immediately surrounding my changes. No `[tool.ruff.lint]` select/ignore configuration exists in `pyproject.toml`, and no `.github` workflow runs `ruff check` as a gate. Per the deviation rules' scope boundary ("do not auto-fix pre-existing issues unrelated to current task"), these were left as-is rather than reformatted repo-wide. `ruff check` was already failing before this plan started and remains a known, unrelated backlog item.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CR-01 is closed. All three previously-failed roadmap truths (SC1, SC2, SC3) are back under test for the third of three modelled rate structures.
- `jurisdictions/SCOPE-FREEZE.md` is unmodified — verified via `git diff --name-only`.
- Ready for `/gsd-verify-work` to re-run Phase 2 verification against this fix, and for plan 02-08 (WR-01/WR-02/WR-04) and 02-09 (validation-pairs re-coupling, loan-out withholding overlap guard) to proceed as scoped in the plan's coverage audit.
- Pre-existing repo-wide `ruff check` backlog (285 findings, unrelated to this plan) remains open — not this plan's scope to close.

## Self-Check: PASSED

- `tests/fixtures/jurisdictions/synthetic-blend-adjustments.yaml` — FOUND on disk
- `git log --oneline --all --grep="02-07"` → 2 commits found (`6ce2d9d`, `f14ad18`)
- All task `<acceptance_criteria>` re-verified passing (see Task Commits and Files sections above)
- Plan-level `<verification>` re-run: `uv run pytest tests/ -q` → 147 passed (142 baseline + 5 new); Anora/Christmas Always/UK/zz-fixture-throwaway all exact; `bash .github/scripts/vendor-scan.sh` exits 0; `jurisdictions/SCOPE-FREEZE.md` untouched

---
*Phase: 02-engine-spine-incentive-interpreter*
*Completed: 2026-08-25*
