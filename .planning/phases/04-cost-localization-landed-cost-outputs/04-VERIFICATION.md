---
phase: 04-cost-localization-landed-cost-outputs
verified: 2026-08-27T12:00:00Z
status: gaps_found
score: 5/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Every cost category the model has not yet priced is a named, declared exclusion — never a silent gap masquerading as full coverage (D-60's structural guarantee)"
    status: failed
    reason: >
      04-REVIEW.md's Critical finding CR-01 is real and unmitigated: engine/cost_localizer.py:475-477
      resolves a labour/static cost line's priced quantity by `budget.line_quantities.get(cost_line.label)`
      and does a bare `continue` when the lookup misses, with no test covering the miss path
      (`grep` for "mismatch|no matching|unmatched|skipped" in tests/test_engine_cost_localizer.py
      returns nothing). `not_priced` (engine/landed_cost.py:287-289) is computed from
      `categories_priced`, a set of CATEGORY names, not a per-line accounting — so a labour cost
      profile with 9 correctly-matched department lines and 1 mismatched label would report
      `not_priced == ()` ("every category priced") while silently dropping that department's wage
      AND fringe cost from the total. Verified independently: no cross-validation exists between
      `CostLine.label` (declared in data/cost_profiles/*.yaml) and `crew_tiers.yaml` department
      labels — `CityCostProfile._labour_covers_every_department_when_declared` only checks that a
      craft mapping exists per department NAME, never that a CostLine with the matching LABEL is
      actually present in `cost_lines`. Currently produces CORRECT totals for all three committed
      cities (independently hand-derived and confirmed via tests/test_golden_cost.py, and via a
      live `not_priced == ()` re-check for NY/LA/London performed during this verification), so no
      Roadmap success criterion is falsified TODAY — but the structural guarantee this project's own
      design philosophy repeatedly claims ("provenance is structural, not aspirational", D-58 through
      D-63) does not actually hold for a future data-authoring typo in a committed YAML file, which
      is exactly the "government-paid, provably matching" trust class this project exists to earn.
      This is an unresolved Critical finding in the phase's own committed code review with no
      override recorded in this VERIFICATION.md's frontmatter.
    artifacts:
      - path: "engine/cost_localizer.py"
        issue: "Lines 475-477 (and the facilities/travel fallthrough shape at 506-508): a CostLine whose label matches no budget quantity is silently `continue`d rather than raising or being tracked per-line."
      - path: "engine/landed_cost.py"
        issue: "Lines 287-289: `not_priced` is derived from `categories_priced` (a category-level set), which cannot detect a per-line silent drop within an otherwise-priced category."
    missing:
      - "Track per-line consumption (a `consumed_labels: set[str]`) alongside category-level tracking in `engine.cost_localizer.localize`, and raise `ValueError` naming any declared `CostLine.label` that matched neither a budget quantity, a travel category, nor a facilities category — per 04-REVIEW.md CR-01's own suggested fix."
      - "A regression test in tests/test_engine_cost_localizer.py that constructs a cost profile with one intentionally-mismatched label and asserts the pipeline raises rather than silently under-totals."
human_verification:
  - test: "Judge whether COST-02's 'localized against published union rate cards (IATSE locals, SAG-AFTRA, DGA, WGA, BECTU, ACTRA)' is genuinely met given the actual data coverage."
    expected: "A reviewer decision on whether the committed data honestly satisfies the roadmap's Success Criterion 1, or whether it should be treated as a documented, accepted scope reduction (an override) pending further sourcing."
    why_human: >
      This is a data-completeness judgment call, not a programmatically-resolvable pass/fail. The
      mechanism (dated rate-row selection, mandatory sibling fringe Figure, raise-on-no-covering-row,
      raise-on-overlapping-bands, sourced-requires-source_url validators) is genuinely correct and
      well-tested. But the ACTUAL coverage is narrow and honestly disclosed in WINDOWS.md entries
      6-10, 19, 21: only IATSE Local 600's camera department (15% of crew_share per
      data/crew_tiers.yaml, confirmed by reading the file) is `basis: sourced` for New York and Los
      Angeles; the other 9 of 10 below-the-line departments price at a flat $450/day "general_crew"
      row that is `basis: estimated` industry commentary, not transcribed from any specific union's
      published card. SAG-AFTRA (data/union_rates/sag-aftra.yaml) has ZERO rate rows — confirmed by
      reading the file — because principal cast is not priced as a labour line at all (only its
      imported headcount feeds travel/housing cost). DGA and WGA also have zero CONSUMED rows —
      director and writer are above-the-line roles this phase's crew_tiers.yaml explicitly excludes
      from below-the-line pricing; their rate rows exist in the data files but are inert (their
      region never matches a committed profile's `labour.region`). ACTRA (Canada) is absent entirely
      since no Canadian city is in the floor set (D-54: NY/LA/London only), which is a legitimate
      scope match, not a gap. London's BECTU coverage mirrors New York/LA's shape: one dated,
      sourced grip-branch row stands in for 9 of 10 departments (WINDOWS entry 19). Fringe and
      payroll burden ARE correctly, unconditionally emitted as a separate sibling Figure for every
      craft-mapped labour line (never folded into the wage line — confirmed in
      engine/cost_localizer.py's `_price_labour_department`), so the narrower COST-03 promise
      ('never compared against bare published rates') is fully and structurally met regardless of
      this gap. The open question is specifically whether 'localized...against published union rate
      cards' can be said to hold when roughly 85% of below-the-line labour cost per city is priced
      from an unattributed flat estimate rather than any of the six named unions' actual published
      rate cards.
deferred: []
---

# Phase 4: Cost Localization & Landed-Cost Outputs Verification Report

**Phase Goal:** The same identical production is priced against each city's real local costs, producing a ranked total landed cost and a gap between any two cities decomposed by component.
**Verified:** 2026-08-27T12:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (mapped to ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1a | Labour is priced with fringe and payroll burden ALWAYS emitted as a separate Figure, never a comparison against bare card rates (COST-03 core promise) | ✓ VERIFIED | `engine/cost_localizer.py::_price_labour_department` unconditionally returns `(wage_figure, fringe_figure)` as siblings for every craft-mapped line; `engine/union_rates.py`'s `RateRow`/`FringeComponent` validators reject `basis: sourced` without a `source_url` and reject any non-sourced basis without a `method_note`. |
| 1b | Labour is genuinely localized against published union rate cards across the six named unions, at material coverage | ? UNCERTAIN (see human_verification) | Only IATSE Local 600's camera department (15% crew_share) is `basis: sourced` per city; the other 9 of 10 departments price at a flat `basis: estimated` day rate not tied to any specific union document. SAG-AFTRA has zero rate rows (`rows: []`, confirmed by reading `data/union_rates/sag-aftra.yaml`); DGA/WGA rows exist but are never consumed (above-the-line roles this phase does not price); ACTRA is absent (no Canadian floor city, a legitimate scope match). Every gap is honestly disclosed in `.planning/WINDOWS.md` entries 6-10, 19, 21 — never silently promoted to `sourced`. |
| 2 | Housing/meals/flights/stages/equipment/permits/locations/trucking are all priced per city; GSA/State Dept per diem carries a structural reimbursement-ceiling caveat; estimated lines are labelled estimated; sales-tax/hotel-occupancy exemptions appear as separate stackable reductions where they exist | ✓ VERIFIED | All ten `COST_CATEGORIES` price to `not_priced == ()` for NY/LA/London (re-confirmed live during this verification). `Figure.caveat` is a structural, non-empty-or-None field (`engine/figure.py:104,117-120`) that survives `figure_to_dict` (`engine/figure_serialize.py:41`) and is asserted non-null on every per-diem/housing Figure by `tests/test_engine_cost_localizer.py::test_every_per_diem_and_housing_figure_has_a_non_null_caveat`. `engine/facilities.py`'s `FacilitiesEntry._never_sourced` validator rejects `basis: "sourced"` at load time — schema-enforced, not convention. `engine/exemptions.py::exemption_reductions` emits NY's sales-tax exemption and LA's hotel-occupancy exemption as their own stackable, sourced-or-disclosed Figures, structurally excluded from the incentive DAG (confirmed by reading the module: an exemption's only route into the total is via `LocalizedBudget.lines`, never `price_jurisdiction`). London declares zero exemptions, honestly disclosed as "not verified this session" (WINDOWS entry 20), not fabricated. Note: individual per-line captions (caveat text, per-line basis) are not rendered in `app/templates/spec_result.html` today — they are, however, fully present in the `/api/v1/spec` JSON response via `figure_to_dict`, and Phase 4's own SUMMARY documents this as deferred to Phase 6's UI ("interface renders city_costs/basis"), consistent with the phased plan. |
| 3a | Total landed cost is reported per candidate city, ranked, on NET landed cost; only cities with a modelled incentive enter the ranked band; unranked cities carry a cost-only total in a visibly separate band, never a fabricated $0 | ✓ VERIFIED | `engine/ranker.py::rank` places New York (rule file exists, incentive prices) in `net_ranked` and Los Angeles/London (no rule file) in `incentive_not_modelled` with `cost_only_total` and a plain-words `reason` — confirmed by reading the module and by `tests/test_engine_ranker.py`/`tests/test_app_spec_route.py`. Bands are concatenated, never interleaved (`ranked_sorted + unranked_sorted`). |
| 3b | The gap between any two cities decomposes component-by-component, currency included, summing exactly to the headline, with zero-delta rows emitted rather than dropped | ✓ VERIFIED | `tests/test_golden_cost.py::test_new_york_vs_los_angeles_golden_gap` hand-derives all five non-zero components (Camera labour, Camera fringe, Equipment, Housing, Per diem) plus 20 zero-delta rows and asserts the sum equals the independently-derived headline `$64,906` exactly. `tests/test_engine_gap.py` additionally proves this for every ordered pair among the three committed cities and proves a London pair carries a `Currency` component while NY-vs-LA does not. |
| 3c (STRETCH) | Chart-of-accounts (ATL/BTL/Post) tag lands on every budget line at creation; the rendered view is out of scope this phase (D-77) | ✓ VERIFIED | `data/crew_tiers.yaml` departments and `engine.cost_profile.CostLine` both carry a mandatory `account: AccountTag` field, validated against a closed set in `engine/budget.py`. No rendered chart-of-accounts view exists — matches D-77's explicit "ship the data, defer the view" decision, not a gap. |
| 4 | Changing start_quarter changes cost through genuine seasonal (per-diem month-band) variation, not only incentive availability; a non-USD city converts at a dated, cited FX rate carried as its own Figure | ✓ VERIFIED | Live re-run during this verification: New York housing moves $41,349 (Q1) → $64,911 (Q2) → $54,747 (Q3) while Los Angeles stays flat at $44,121 across all three quarters (LA's committed GSA snapshot has no month band, honestly disclosed rather than backfilled). `engine/fx.py::rate_figure` returns the FX rate as its own `Figure` with its own `as_of_date`/`source_url`, distinct from any converted cost figure; `load_fx_snapshot` refuses (never inverts or cross-derives) a missing or reverse-direction pair — proven by `tests/test_engine_fx.py`. `tests/test_golden_cost.py`'s London tests independently hand-derive both the GBP total and its USD conversion and confirm the pipeline matches exactly. |
| 5 | Sensitivity output shows which single input most moves the gap, as a delta with its step named, never a prescriptive recommendation; perturbation re-runs the real pipeline, never a derivative | ✓ VERIFIED | `engine/sensitivity.py::sensitivity_rows` calls `_price_pair` (a full re-run of `build_canonical_budget` → `localize` → `rank` → `decompose_gap`) once per declared step — no derivative, gradient, or `numpy` import anywhere (`grep` confirms). The D-70 vocabulary gate (`recommend`, `should`, `consider`, `best`, `optimal`, `you could`, …) is tested over BOTH the engine's emitted strings (`tests/test_engine_sensitivity.py`) and the rendered HTML body (`tests/test_app_spec_route.py`), each test's own docstring recording that it was proven to fail on an inserted word and reverted — a genuine, non-vacuous CI gate, independently re-run and confirmed passing during this verification. |
| 6 | `not_priced` and the per-line cost accounting are a structurally trustworthy declaration of coverage gaps — never a silent partial total masquerading as full coverage | ✗ FAILED | See `gaps` above (CR-01). |

**Score:** 5/6 must-haves verified (1 failed as a structural gap; 1 sub-item routed to human judgment, not counted against or for the score)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/cost_profile.py` | CityCostProfile schema, load_cost_profile | ✓ VERIFIED | Present, substantive, wired; account tag + basis validators confirmed by reading. |
| `engine/budget.py` | Canonical budget, department shares, account tags | ✓ VERIFIED | `build_canonical_budget` confirmed producing byte-identical quantities regardless of candidate city; account tags present. |
| `engine/cost_localizer.py` | Stage [2] localize() | ⚠️ VERIFIED WITH GAP | Present, substantive, wired, and produces correct output for all committed data — but contains CR-01 (silent-drop on label mismatch). |
| `engine/landed_cost.py` | Stage [6] aggregate(), COST_CATEGORIES, PERMANENT_EXCLUSIONS | ⚠️ VERIFIED WITH GAP | `not_priced` computation is category-level only (feeds CR-01). |
| `engine/union_rates.py` | Dated rate row selection, fringe schedules | ✓ VERIFIED | Closed-closed date ranges, overlap detection, raise-on-no-covering-row all confirmed by reading and by `tests/test_engine_union_rates.py`. |
| `engine/per_diem.py` | GSA/State Dept month-weighted per diem, structural caveat | ✓ VERIFIED | `ceiling_caveat` non-empty validator confirmed; `month_weighted_per_diem` confirmed live producing quarter-variant NY / quarter-invariant LA output. |
| `engine/seasonality.py` | Shoot calendar, per-diem month weighting | ✓ VERIFIED | Confirmed via live re-run (Q1/Q2/Q3 NY housing values). |
| `engine/facilities.py` | Never-sourced facilities pricing | ✓ VERIFIED | `_never_sourced` validator confirmed rejecting `basis: sourced` at load time. |
| `engine/exemptions.py` | Stackable cost-reduction exemptions | ✓ VERIFIED | Structurally excluded from the incentive DAG; confirmed by reading `exemption_reductions` and its wiring in `cost_localizer.localize`. |
| `engine/fx.py` | Dated FX conversion, D-74 refusal semantics | ✓ VERIFIED | Refuse-rather-than-derive and refuse-rather-than-invert both confirmed by reading; rate figure and identity-conversion paths both tested. |
| `engine/ranker.py` | Two-band ranked list | ✓ VERIFIED | Confirmed by reading; bands concatenated not interleaved. |
| `engine/gap.py` | Component-by-component gap decomposition | ✓ VERIFIED | Exact-equality sum confirmed via golden test and cross-pair test. |
| `engine/sensitivity.py` | Perturb-and-rerun sensitivity engine | ✓ VERIFIED | Full pipeline re-run per row confirmed; no analytic shortcut. |
| `data/union_rates/*.yaml`, `data/per_diem/**/*.yaml`, `data/facilities/*.yaml`, `data/tax_exemptions/*.yaml`, `data/fx/*.yaml` | Committed dated snapshots | ✓ VERIFIED (with honest coverage gaps) | All present, `yaml.safe_load` only, RD-01 quoted-numeric convention confirmed; coverage gaps disclosed in WINDOWS.md, not hidden. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `data/union_rates/*.yaml` | `engine/union_rates.py::select_rate_row` | dated rate row lookup | ✓ WIRED | Confirmed selection logic and raise-on-gap behavior. |
| `data/union_rates/fringe_schedules.yaml` | sibling fringe Figure | `_price_labour_department` | ✓ WIRED | Confirmed never folded into wage line. |
| `Figure.caveat` | `figure_to_dict` | JSON boundary | ✓ WIRED | Confirmed field survives serialization; confirmed non-null on per-diem/housing lines by test. |
| `data/facilities/*.yaml` | `not_priced` emptying | `engine/facilities.py` → `cost_localizer.localize` | ✓ WIRED | Confirmed live: `not_priced == ()` for NY/LA/London. |
| `data/tax_exemptions/*.yaml` | cost-line reduction, never the incentive DAG | `engine/exemptions.py` | ✓ WIRED | Confirmed structurally disjoint from `price_jurisdiction`'s return tree. |
| `data/fx/gbp-usd.yaml` | cited FX Figure in the gap decomposition | `engine/fx.py::rate_figure` → `engine/gap.py` | ✓ WIRED | Confirmed via `tests/test_engine_gap.py::test_london_pairs_carry_a_currency_component_ny_vs_la_does_not`. |
| `engine/landed_cost.py::LandedCost` | ranked list rendered to the visitor | `ranker.py` → `app/services/spec.py` → `app/routers/spec.py` / `app/templates/spec_result.html` | ✓ WIRED | Confirmed both HTML template and `/api/v1/spec` JSON path render `net_ranked_cities`/`incentive_not_modelled_cities`, `gap`, `sensitivity`. |
| `data/sensitivity_steps.yaml` | perturbation loop, full re-run | `engine/sensitivity.py::sensitivity_rows` | ✓ WIRED | Confirmed by reading; every row triggers `_price_pair`, a full chain re-run. |
| `CostLine.label` | `budget.line_quantities` | `engine/cost_localizer.py::localize` | ✗ UNGUARDED | No raise, no per-line tracking on a miss (CR-01) — see gaps. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `not_priced` is empty for all three committed cities | live Python re-run of `build_canonical_budget` → `localize` → `aggregate` for NY/LA/London | `()` for all three | ✓ PASS |
| Start-quarter genuinely varies New York's per-diem-driven housing cost, not Los Angeles's | live Python re-run across Q1/Q2/Q3 | NY: 41,349 / 64,911 / 54,747; LA: 44,121 flat | ✓ PASS |
| D-70 prescriptive-vocabulary gate fires on engine strings and rendered HTML | `uv run pytest -k "prescriptive or vocabulary"` (both test modules) | 1 passed in each module | ✓ PASS |
| Golden cost / gap totals are hand-derived and non-vacuous (mutation-proof) | `uv run pytest tests/test_golden_cost.py -q` | 6 passed, including a live rate-perturbation test confirming the total moves from $758,427 to $758,597 | ✓ PASS |
| D-63 basis walk (no `validated` confidence reachable from a Route A total) | `uv run pytest tests/test_route_a_basis_walk.py -q` | passed; module docstring documents a prior red-then-reverted mutation proving non-vacuity | ✓ PASS |
| D-72 guard (validation pairs never route through the budget model) | `grep`-based source-scan test in `tests/test_engine_against_validation_pairs.py` | passed | ✓ PASS |
| Full test suite | `uv run pytest -q` | 470 passed, 0 failed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| COST-01 | 04-01 | One identical budget model localized per city, comparison never bare rates | ✓ SATISFIED | `build_canonical_budget` is spec-driven only; fringe never folded into wage. |
| COST-02 | 04-02, 04-05 | Labour against published union rate cards | ? PARTIALLY SATISFIED | See Truth 1b / human_verification above. |
| COST-03 | 04-02 | Fringe and payroll burden included, not bare card rates | ✓ SATISFIED | Always emitted as a sibling Figure. |
| COST-04 | 04-03 | GSA/State Dept per diem labelled as reimbursement ceilings, not market rates | ✓ SATISFIED | Structural `caveat` field, non-null, tested. |
| COST-05 | 04-03 | Flights/housing computed for imported crew and cast specifically | ✓ SATISFIED | `_price_travel_categories` keys strictly off imported headcount. |
| COST-06 | 04-04 | Stage/equipment/permit/location/trucking priced, estimated lines labelled | ✓ SATISFIED | Schema rejects `basis: sourced` for facilities at load time. |
| COST-07 | 04-03 | Start quarter drives seasonal cost variation, not only incentive availability | ✓ SATISFIED | Live-confirmed NY quarter variance / LA invariance. |
| COST-08 | 04-05 | Multi-currency costs converted via dated, cited FX rate | ✓ SATISFIED | `rate_figure` + refuse-rather-than-derive/invert, tested. |
| INC-10 | 04-04 | Sales tax / hotel occupancy exemptions as separate stackable reductions | ✓ SATISFIED | Structurally excluded from incentive DAG; confirmed by reading. |
| OUT-01 | 04-06 | Total landed cost per candidate city, ranked | ✓ SATISFIED | Two-band ranker, never interleaved. |
| OUT-02 | 04-06 | Cost gap decomposed by component | ✓ SATISFIED | Golden gap test, exact-sum assertion. |
| OUT-03 | 04-07 | Sensitivity: single input moving the gap most, as a delta, never prescriptive | ✓ SATISFIED | Perturb-and-rerun engine + tested vocabulary gate. |
| OUT-04 | 04-01 | Chart-of-accounts tagging (stretch: tags only, no view) | ✓ SATISFIED | Tags present on every budget/cost line at creation; view explicitly deferred per D-77. |

No orphaned requirements: all 13 IDs mapped to this phase in `.planning/REQUIREMENTS.md` appear in at least one plan's `requirements:` frontmatter field (`04-01` through `04-07`), and no plan declares a requirement ID absent from REQUIREMENTS.md.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX` debt markers found in phase-modified files. No `TODO`/`HACK`/`PLACEHOLDER` found. No `.quantize()` call sites outside `engine/rounding.py` (grep-confirmed, matching every plan SUMMARY's own self-check). All 21 lint-warning entries in `.planning/WINDOWS.md` (ids 2, 5, 11, 14, 17, 23, 24, 25, etc.) are pre-existing `ruff` categories (FURB157 verbose-Decimal, ISC004 implicit-concat, RUF022 `__all__` sort) with no CI lint job gating the build (`.github/workflows/ci.yml` has no `ruff`/lint job) — non-blocking by the project's own established convention, not a phase-4-introduced regression.

The one code-quality finding that IS blocking-grade is `engine/cost_localizer.py`'s CR-01 silent-drop path — see Gaps Summary.

### Human Verification Required

### 1. Is COST-02/Success-Criterion-1's union-rate-card coverage sufficient?

**Test:** Review `.planning/WINDOWS.md` entries 6-10, 19, 21 alongside `data/union_rates/*.yaml` and decide whether the current coverage (1 of 10 below-the-line departments genuinely sourced from a published card, per city; SAG-AFTRA/DGA/WGA/ACTRA contributing nothing to the priced total) constitutes "localized... against published union rate cards" as the roadmap success criterion states, or whether this should be recorded as an accepted, documented scope reduction (an override) pending further sourcing in a later session.
**Expected:** A decision — either accept as-is (given the honest disclosure and DataDome-blocked SAG-AFTRA access), or open a follow-up plan to fetch the remaining per-craft IATSE locals (80, 728, 800, 705, 706, 695, 871, 700) and Teamsters Local 399.
**Why human:** Data-completeness/scope-sufficiency judgment call, not a programmatically resolvable pass/fail — the underlying mechanism is fully correct and well-tested regardless of which way this is decided.

### Gaps Summary

One genuine structural gap survives, matching the phase's own committed code review (04-REVIEW.md CR-01), unresolved and untested: `engine/cost_localizer.py::localize` silently drops a `CostLine` whose `label` matches no budget quantity (a bare `continue`), and `engine/landed_cost.py::aggregate`'s `not_priced` list is derived from category-level tracking that cannot detect this class of failure. This does not currently produce an incorrect number for any of the three committed cities — confirmed independently via `tests/test_golden_cost.py`'s hand-derived totals and via a live `not_priced == ()` re-check performed during this verification — but it is a real, load-bearing gap in the "provenance is structural, not aspirational" guarantee this phase (and the project's Core Value statement) repeatedly claims: a future one-character label typo in a committed YAML file would silently understate the headline total with zero test or CI signal. The fix is well-scoped (per-line consumption tracking plus a raise on any unmatched label, as the review's own suggested patch describes) and does not require re-deriving any already-correct committed data.

Separately, a judgment call is flagged for human review (not counted as a gap, since it is not programmatically resolvable): whether the phase's union-rate-card coverage — genuinely correct and well-tested where it exists, but narrow (roughly 15% of below-the-line labour cost per city is actually sourced from a named union's published card; SAG-AFTRA/DGA/WGA/ACTRA contribute nothing to the priced total) — satisfies Success Criterion 1's letter. This gap is honestly and thoroughly disclosed in `.planning/WINDOWS.md` (entries 6-10, 19, 21) rather than hidden, and the fringe/burden-inclusion promise (COST-03) that criterion 1 also names is fully and unconditionally met.

Every other Roadmap success criterion (2, 3, 4, 5) is independently confirmed true in the codebase via direct reading, live re-execution, and the phase's own hand-derived (non-vacuous, mutation-tested) golden fixtures.

---

_Verified: 2026-08-27T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
