---
phase: 04-cost-localization-landed-cost-outputs
reviewed: 2026-08-26T00:00:00Z
depth: standard
files_reviewed: 66
files_reviewed_list:
  - engine/figure.py
  - engine/figure_serialize.py
  - engine/pipeline.py
  - engine/cost_profile.py
  - engine/city_profile_lookup.py
  - engine/budget.py
  - engine/cost_localizer.py
  - engine/landed_cost.py
  - engine/union_rates.py
  - engine/per_diem.py
  - engine/seasonality.py
  - engine/facilities.py
  - engine/exemptions.py
  - engine/fx.py
  - engine/ranker.py
  - engine/gap.py
  - engine/sensitivity.py
  - app/services/spec.py
  - app/routers/spec.py
  - app/templates/spec_result.html
  - data/cost_profiles/us-ny-new-york.yaml
  - data/cost_profiles/us-ca-los-angeles.yaml
  - data/cost_profiles/gb-london.yaml
  - data/crew_tiers.yaml
  - data/sensitivity_steps.yaml
  - data/fx/gbp-usd.yaml
  - data/union_rates/us-ny-crew.yaml
  - data/union_rates/iatse.yaml
  - data/union_rates/sag-aftra.yaml
  - data/union_rates/dga.yaml
  - data/union_rates/wga.yaml
  - data/union_rates/bectu.yaml
  - data/union_rates/fringe_schedules.yaml
  - data/per_diem/gsa/us-ny-new-york-county.yaml
  - data/per_diem/gsa/us-ca-los-angeles-county.yaml
  - data/per_diem/state-dept/gb-london.yaml
  - data/facilities/us-ny-new-york.yaml
  - data/facilities/us-ca-los-angeles.yaml
  - data/facilities/gb-london.yaml
  - data/tax_exemptions/us-ny-new-york.yaml
  - data/tax_exemptions/us-ca-los-angeles.yaml
  - data/tax_exemptions/gb-london.yaml
  - sources/MANIFEST.yaml
  - tests/test_engine_figure_basis.py
  - tests/test_engine_cost_profile.py
  - tests/test_engine_budget.py
  - tests/test_engine_cost_localizer.py
  - tests/test_engine_landed_cost.py
  - tests/test_engine_union_rates.py
  - tests/test_engine_per_diem.py
  - tests/test_engine_seasonality.py
  - tests/test_engine_facilities.py
  - tests/test_engine_exemptions.py
  - tests/test_engine_fx.py
  - tests/test_engine_ranker.py
  - tests/test_engine_gap.py
  - tests/test_engine_sensitivity.py
  - tests/test_golden_cost.py
  - tests/test_route_a_basis_walk.py
  - tests/test_app_spec_route.py
  - tests/test_engine_against_validation_pairs.py
  - tests/test_engine_jurisdiction_additivity.py
  - tests/fixtures/cost_profiles/synthetic-minimal.yaml
  - tests/fixtures/cost_profiles/synthetic-ranked.yaml
  - tests/fixtures/cost_profiles/synthetic-unranked.yaml
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-08-26T00:00:00Z
**Depth:** standard
**Files Reviewed:** 66
**Status:** issues_found

## Summary

This phase adds the cost-localization engine (canonical budget, dynamic
labour/fringe pricing, travel, facilities, exemptions, FX, ranking, gap
decomposition, sensitivity) and its Route A wiring. The engineering
discipline is unusually strong for a hackathon build: monetary arithmetic
is `Decimal` end to end (no bare `.quantize()`, no float contamination,
verified by grep and by dedicated rounding-order tests); `yaml.safe_load`
is used everywhere; the previously-caught GBP-vs-USD raw-sort bug in
`engine/ranker.py` has a permanent regression test
(`test_unranked_band_compares_a_gbp_city_and_a_usd_city_in_the_same_currency`);
`engine/cost_localizer.py` is independently scanned for jurisdiction-id
literals; `combined_basis`'s weakest-wins/empty-sequence-raises contract is
directly tested; and a hand-derived, independently-computed golden-cost
fixture (`tests/test_golden_cost.py`) exactly reproduces the pipeline's
output for all three committed cities and their gap, which is strong,
non-vacuous evidence the core money math is correct.

Against that strength, one genuine correctness gap survives: cost lines
whose `label` doesn't resolve to a budget quantity are silently dropped
(a bare `continue`), and `not_priced` is tracked at the *category* level,
not the per-line level — so a labour cost profile with 9 correctly-matched
department lines and 1 mistyped label reports `not_priced == ()` (looks
fully priced) while silently omitting a whole department's wage+fringe
cost from the total. This is the exact "silent-failure path" class this
project otherwise structurally refuses everywhere else (`engine/fx.py`,
`engine/union_rates.py`, `engine/per_diem.py`, `engine/facilities.py`,
`engine/exemptions.py` all raise loudly on an unmatched lookup). A few
smaller robustness gaps (tier-boundary ambiguity, suffix-based city
lookup collisions, a silent-truncating `int(Decimal(...))`) round out the
warnings.

## Critical Issues

### CR-01: Cost lines with a mismatched label are silently dropped from the total, and `not_priced` cannot detect it

**File:** `engine/cost_localizer.py:475-477` (see also the static-path fallthrough at `engine/cost_localizer.py:506-508`)

**Issue:** `localize()` resolves a cost line's priced quantity by looking
it up in the canonical budget by label:

```python
quantity = budget.line_quantities.get(cost_line.label)
if quantity is None:
    continue
```

This is documented as intentional ("a profile is free to widen with
lines a given budget shape does not (yet) supply quantities for"), and
it is a reasonable mechanism for forward-compatibility. The problem is
what happens when the mismatch is *not* deliberate widening but a data
mistake — e.g. a committed `data/cost_profiles/*.yaml` labour line whose
`label` doesn't byte-for-byte match `data/crew_tiers.yaml`'s department
`label` (a capitalization slip, an extra space, a rename on one side but
not the other). In that case:

1. The line is silently excluded from `LocalizedBudget.lines` — its wage
   *and* fringe cost (fringe is never separately reachable; it's derived
   from the wage line inside the same branch) vanish from `cost_total`
   with no exception, no warning, no derivation line stating an
   exclusion occurred.
2. `not_priced` (`engine/landed_cost.py::aggregate`) is computed from
   `categories_priced`, a `set[str]` of *category names*, not a per-line
   accounting. Since the other nine labour departments still price
   successfully, `"labour"` is still added to `categories_priced`, so
   `not_priced` reports `()` — "every category priced" — even though one
   entire department's cost is missing from the number.

This directly contradicts the project's own stated design elsewhere:
`engine/fx.py` "refuses rather than derives," `engine/union_rates.py`
raises loudly on a date/region/craft with no covering row,
`engine/per_diem.py`/`engine/facilities.py`/`engine/exemptions.py` all
raise `ValueError` naming the id when a lookup fails. This is the one
lookup in the cost-pricing chain that fails silently instead — and it is
also the one place in the codebase where a plain string-equality typo in
a committed YAML file (not a visitor input) can silently understate the
headline "total landed cost" number this whole product exists to make
provably correct. `tests/test_golden_cost.py`'s hand-derived fixture
currently proves the *existing* committed data is correct, but it cannot
catch a *future* edit that reintroduces this class of mismatch, because
nothing structural forces every declared cost line to actually be
consumed.

**Fix:** Track per-line consumption, not just per-category consumption,
and raise (or at minimum surface a per-line disclosure, never a bare
`continue`) when a declared `CostLine` matches neither a budget quantity,
a travel category, nor a facilities category:

```python
lines: list[Figure] = []
categories_priced: set[str] = set()
consumed_labels: set[str] = set()
...
for cost_line in profile.cost_lines:
    ... existing travel/facilities branches, each doing
    consumed_labels.add(cost_line.label) ...

    quantity = budget.line_quantities.get(cost_line.label)
    if quantity is None:
        continue
    consumed_labels.add(cost_line.label)
    ...

unmatched = {
    cost_line.label
    for cost_line in profile.cost_lines
    if cost_line.label not in consumed_labels
}
if unmatched:
    raise ValueError(
        f"localize(): {profile.city_id!r} declares cost line label(s) "
        f"{sorted(unmatched)!r} that match no budget quantity, travel "
        "category, or facilities category — a label mismatch is a data "
        "authoring error, never a silent partial total"
    )
```

(A profile genuinely *widening* ahead of the budget shape, per the
existing docstring's stated use case, would need an explicit opt-in list
rather than an unconditional silent skip.)

## Warnings

### WR-01: Crew-tier bracket boundaries overlap with no ambiguity guard, unlike every other dated/ranged lookup in this phase

**File:** `engine/budget.py:139-162` (`_infer_department_tier`), `data/crew_tiers.yaml:35-50`

**Issue:** `data/crew_tiers.yaml`'s tier brackets are inclusive-inclusive
and touch at every boundary: `micro: [15, 30]`, `small: [30, 60]`,
`mid: [60, 120]`, `large: [120, 200]`, `tentpole: [200, 400]`. A headcount
of exactly 30, 60, 120 or 200 satisfies *two* brackets simultaneously.
`_infer_department_tier` resolves this silently by iterating
`_TIER_ORDER` (narrowest first) and returning the first match, so the
boundary value always resolves to the *lower* tier — a deterministic but
undocumented tie-break. Contrast this with `engine/union_rates.py`'s
`_check_rate_rows_for_overlaps` (WR-03), which treats an analogous
overlapping-range situation as a load-time authoring error to be raised,
never silently resolved by iteration order.

Currently harmless in practice: every department's `crew_share` value in
`data/crew_tiers.yaml` is identical across all five tiers, so which tier
a boundary headcount resolves to has zero effect on the computed output
today (confirmed by reading the full department table). But nothing
prevents a future data change that differentiates `crew_share` by tier
from silently reintroducing a real, unflagged discontinuity at exactly
30/60/120/200 crew.

**Fix:** Either declare the brackets half-open in the data (e.g.
`headcount_high` documented as exclusive) and adjust the comparison to
`low <= headcount < high`, or add an overlap-detection check mirroring
`_check_rate_rows_for_overlaps` that fails loudly if adjacent brackets
share a boundary value with differing `crew_share`s once/if tiers are
ever differentiated.

### WR-02: Suffix-based cost-profile lookup resolves on the trailing suffix alone, independent of the city name

**File:** `engine/city_profile_lookup.py:79-95`

**Issue:** `resolve_city_to_profile_stem` falls back to matching a
trailing `", NY"/", New York"`, `", CA"/", California"`, or
`", UK"/", United Kingdom"/", England"` suffix when the full normalized
string isn't in the alias table. The match is purely suffix-based: any
string ending in one of these suffixes resolves to that suffix's
committed stem, regardless of what precedes it. This means a submission
naming (for example) `"New York, CA"` resolves to Los Angeles's cost
profile, and any nonsense city name suffixed `", UK"` resolves to
London's — silently pricing the wrong city with no error surfaced
anywhere in the response. This mirrors an already-accepted convention in
`app/services/city_lookup.py`, but Phase 4 widens the suffix set from one
family to three, which increases the collision surface (a `", CA"` or
`", UK"` mismatch was not previously possible here).

Low real-world likelihood (a visitor would have to type an internally
contradictory city/state pair), and consistent with this module's
explicit "no fuzzy match, explicit allow-list only" design, so this is
not a blocking defect — but it is worth naming as a known false-positive
class, since the product's core promise is per-city correctness.

**Fix:** No code change strictly required given the documented design
tradeoff; consider at minimum a code comment (or a `SCOPE-FREEZE.md`
entry) explicitly naming the cross-suffix collision as an accepted
limitation, so it isn't rediscovered as a "bug" later.

### WR-03: `sensitivity.py` step application silently truncates a non-integer step

**File:** `engine/sensitivity.py:213-214`

**Issue:** `_step_delta` computes `int(Decimal(step.step))`. Every
currently-declared row in `data/sensitivity_steps.yaml` uses `step: "1"`,
so this is a no-op today. But the module's own docstring promises "a new
row is a table addition ... zero code changes" for any plain-integer
`spec_field` — and a future contributor adding, say, `step: "0.5"` for
some future fractional-unit field would have that value silently
truncated to `0` (a zero-effect step reported as a real perturbation)
rather than raising, with no test or schema guard catching it.

**Fix:** Validate that `Decimal(step.step)` has no fractional part at
`SensitivityStep` load time (a `model_validator`, matching this file's
own `StrictModel` pattern used throughout the rest of this phase), or
change `_step_delta` to raise when `Decimal(step.step) % 1 != 0` instead
of silently truncating.

## Info

### IN-01: `SpendBreakdown.core_expenditure` includes every priced cost line, including travel/flights, with no jurisdiction-specific exclusions

**File:** `engine/cost_localizer.py:347-374` (`_derive_spend_breakdown`)

**Issue:** The docstring is explicit that "no exclusions are declared at
the cost-localization layer," and `core_expenditure` is set equal to
`total_spend` unconditionally. This means Route A's modelled qualified
spend (fed into `engine.pipeline.price_jurisdiction` via
`localized.spend_breakdown.total_spend`) includes imported-crew
housing/per-diem/flights cost — categories many real incentive programmes
either exclude entirely or cap separately — with no jurisdiction-aware
carve-out. This is already disclosed structurally (the spend is tagged
`spend_confidence="researched"`, never `"validated"`, and the UI carries
`SPEND_ORIGIN_STATEMENT` next to the number), so this is not a hidden
defect — it's a known modelling simplification, in scope for a future
phase's jurisdiction-specific qualifying-base carve-outs rather than a
Phase 4 correctness bug. Noted here only so a future contributor wiring
a jurisdiction-specific exclusion list knows exactly where the current
flat pass-through lives.

---

_Reviewed: 2026-08-26T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
