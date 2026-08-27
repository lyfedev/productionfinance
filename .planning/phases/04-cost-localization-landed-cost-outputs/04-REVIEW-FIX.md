---
phase: 04-cost-localization-landed-cost-outputs
fixed_at: 2026-08-27T06:25:53Z
review_path: .planning/phases/04-cost-localization-landed-cost-outputs/04-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-08-27T06:25:53Z
**Source review:** .planning/phases/04-cost-localization-landed-cost-outputs/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope (critical + warning): 4
- Fixed: 4
- Skipped: 0
- IN-01 (info) is out of scope for this run's `fix_scope: critical_warning` and was not attempted.

**Test suite:** 470 passed at HEAD before this run -> **476 passed** after (`uv run pytest -q`), all green. The net +6 is entirely new regression tests added by this fix pass (1 for CR-01, 2 for WR-01, 3 for WR-03); WR-02 was a documentation-only fix with no new test. `tests/test_golden_cost.py`'s hand-derived landed-cost totals for all three committed cities and their pairwise gap are **unchanged** — confirmed by an explicit re-run of that file (and `tests/test_engine_jurisdiction_additivity.py`) both before and after each fix, in addition to the full-suite run.

## Fixed Issues

### CR-01: Cost lines with a mismatched label are silently dropped from the total, and `not_priced` cannot detect it

**Files modified:** `engine/cost_localizer.py`, `tests/test_engine_cost_localizer.py`
**Commit:** `dfa7455`
**Applied fix:** Added a `consumed_labels: set[str]` accumulator to `localize()`, populated at every point a `CostLine.label` is actually consumed (the travel-category branch, the facilities-category branch, and the budget-quantity branch — covering both the dynamic labour path and the static per-line path described at the review's cited `506-508` fallthrough). After the main loop, computes `unmatched = {cost_line.label for cost_line in profile.cost_lines if cost_line.label not in consumed_labels}` and raises `ValueError` naming every unmatched label, the city id, and why (a label matching no budget quantity, travel category, or facilities category is a data authoring error, never a silent partial total) — following the review's own suggested fix shape almost verbatim. Verified no existing test or fixture relies on the old silent-skip/"widening" behavior (checked `tests/test_engine_cost_localizer.py`, `tests/test_engine_ranker.py`, `tests/test_engine_gap.py`, `tests/test_engine_landed_cost.py`, and the three synthetic cost-profile fixtures) before applying. Added `test_localize_raises_on_a_cost_line_label_that_matches_nothing`, a genuine regression test (confirmed to fail with `DID NOT RAISE ValueError` when the fix is reverted, via `git stash`) using a synthetic profile with a capitalization-slip label (`"Camera Labour Days"` vs. the real `"Camera labour days"`).

### WR-01: Crew-tier bracket boundaries overlap with no ambiguity guard

**Files modified:** `engine/budget.py`, `tests/test_engine_budget.py`
**Commit:** `2f34b25`
**Applied fix:** Chose the review's second offered option (an overlap-detection guard mirroring `engine.union_rates._check_rate_rows_for_overlaps`) over declaring the brackets half-open, since half-open bounds would require special-casing the last tier's inclusive upper edge and risked touching real pricing behavior for no benefit — the guard approach preserves today's exact tie-break behavior while catching a *future* differentiation. Added `_check_tier_boundaries_for_ambiguous_crew_share`, called from `resolve_departments` on every load: for each pair of adjacent tiers in `_TIER_ORDER` (via `itertools.pairwise`, to avoid a new `RUF007` lint finding from a raw `zip(seq, seq[1:])`) that share a boundary headcount, it compares every department's `crew_share` on both sides and raises `ValueError` naming the department, both tiers, and the shared boundary if they differ. Confirmed the real committed `data/crew_tiers.yaml` (all `crew_share` values identical across tiers) does not trigger the guard — full suite green with zero behavior change. Added two regression tests using `monkeypatch` on `_load_crew_tiers_table` with a synthetic two-tier table: one proving a differentiated boundary share raises, one proving an identical boundary share does not (the real file's current shape).

### WR-02: Suffix-based cost-profile lookup resolves on the trailing suffix alone

**Files modified:** `engine/city_profile_lookup.py`
**Commit:** `795cf86`
**Applied fix:** This is a documentation-only fix, matching the review's own primary recommendation verbatim ("No code change strictly required given the documented design tradeoff; consider at minimum a code comment... explicitly naming the cross-suffix collision as an accepted limitation"). Added a "KNOWN LIMITATION" paragraph to the module docstring explicitly naming the cross-suffix collision (e.g. `"New York, CA"` resolving to Los Angeles, `", UK"` resolving to London regardless of prefix), explaining why it is an accepted tradeoff (mirrors `app/services/city_lookup.py`'s existing New-York-only precedent; low real-world likelihood; the module's whole discipline is "no fuzzy match, explicit allow-list only," and validating the prefix against the suffix would reintroduce exactly the fuzzy matching this module exists to avoid) so it is not "rediscovered as a bug" later, per the review's stated goal. No runtime behavior changed — the allow-list design and the `test_engine_jurisdiction_additivity.py` JUR-05 exclusion are untouched.

### WR-03: `sensitivity.py` step application silently truncates a non-integer step

**Files modified:** `engine/sensitivity.py`, `tests/test_engine_sensitivity.py`
**Commit:** `6d3fb5a`
**Applied fix:** Chose the review's `model_validator`-at-load-time option (mirroring `engine.cost_profile.CostLine`'s own `@model_validator(mode="after")` pattern) over changing `_step_delta` to raise inline, since validating at the `SensitivityStep` model boundary catches the defect the moment a bad row is loaded rather than only when it's actually applied. Added `_step_must_be_a_whole_number` to `SensitivityStep`: parses `step` with `Decimal()` (raising a clear `ValueError` on a malformed value) and raises if `step_value % 1 != 0`, naming the offending row's id and step value, and explaining exactly why (the existing `_step_delta`'s `int(Decimal(...))` would otherwise silently truncate). Confirmed every currently-committed row in `data/sensitivity_steps.yaml` uses `step: "1"` and does not trigger the guard. Added three regression tests: direct `SensitivityStep` construction with a fractional step raising, a whole-number step not raising, and the same guard firing through the real `load_sensitivity_steps()` path (confirmed the first two fail with `DID NOT RAISE ValidationError` when the fix is reverted, via `git stash`).

## Skipped Issues

None — all four in-scope findings were fixed.

---

_Fixed: 2026-08-27T06:25:53Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
