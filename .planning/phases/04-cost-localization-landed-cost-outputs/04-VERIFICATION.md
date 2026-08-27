---
phase: 04-cost-localization-landed-cost-outputs
verified: 2026-08-27T13:30:00Z
status: human_needed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: true
re_verification_detail:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "Every cost category the model has not yet priced is a named, declared exclusion — never a silent gap masquerading as full coverage (D-60's structural guarantee) — CR-01 fixed: engine/cost_localizer.py::localize now tracks consumed_labels across the travel, facilities and budget-quantity branches and raises ValueError naming any CostLine.label consumed by none of them, before any LocalizedBudget is returned. This makes the prior not_priced category-granularity blind spot moot for exactly the failure class CR-01 named: a mismatched label can no longer produce a silently-under-totalled but apparently fully-priced LocalizedBudget — it raises instead."
  gaps_remaining: []
  regressions: []
  notes: >
    Independently re-verified (not taken on the fix report's word): checked out
    engine/cost_localizer.py at commit dfa7455~1 (pre-fix), ran
    tests/test_engine_cost_localizer.py::test_localize_raises_on_a_cost_line_label_that_matches_nothing
    in isolation, confirmed it fails with "DID NOT RAISE ValueError"; restored the
    fixed file and confirmed the same test (and the full 31-test module) passes.
    Live-reran build_canonical_budget -> localize -> aggregate for all three
    committed cities across Q1/Q2/Q3: not_priced == () for all nine combinations,
    NY total varies by quarter (734865 / 758427 / 748263), LA and London are
    quarter-invariant (matching their committed no-month-band per-diem snapshots,
    honestly disclosed rather than backfilled) — no regression from the prior
    verification's live spot-check. Full suite re-run independently: 476 passed
    (matches 04-REVIEW-FIX.md's claim). golden-cost and jurisdiction-additivity
    modules re-run in isolation and unchanged. `git diff --stat` from the prior
    VERIFICATION.md's commit (2ff6b38) to HEAD touches exactly 4 fix commits'
    worth of files (engine/budget.py, engine/city_profile_lookup.py,
    engine/cost_localizer.py, engine/sensitivity.py, their tests, and the
    REVIEW-FIX report) — nothing else changed underneath this re-verification.
    WR-01 (crew-tier boundary ambiguity guard) and WR-03 (fractional sensitivity
    step guard) confirmed wired by reading (resolve_departments calls
    _check_tier_boundaries_for_ambiguous_crew_share; SensitivityStep's
    model_validator calls _step_must_be_a_whole_number) and by the passing
    regression tests in tests/test_engine_budget.py / tests/test_engine_sensitivity.py.
    WR-02 (cross-suffix city-profile lookup collision) was fixed by documentation
    only, exactly as 04-REVIEW-FIX.md states — "New York, CA" still resolves to
    Los Angeles's cost profile at runtime, confirmed by reading
    engine/city_profile_lookup.py's unchanged resolution logic. Judged below as
    an accepted, disclosed limitation, not a gap.
human_verification:
  - test: "Judge whether COST-02's 'localized against published union rate cards (IATSE locals, SAG-AFTRA, DGA, WGA, BECTU, ACTRA)' is genuinely met given the actual data coverage."
    expected: "A reviewer decision on whether the committed data honestly satisfies the roadmap's Success Criterion 1, or whether it should be treated as a documented, accepted scope reduction (an override) pending further sourcing."
    why_human: >
      Unresolved carry-forward from the prior verification — this is a
      data-completeness judgment call, not a programmatically-resolvable
      pass/fail, and nothing in the fix pass touched union-rate coverage. The
      mechanism (dated rate-row selection, mandatory sibling fringe Figure,
      raise-on-no-covering-row, raise-on-overlapping-bands, sourced-requires-
      source_url validators) is genuinely correct and well-tested. But the
      ACTUAL coverage is narrow and honestly disclosed in WINDOWS.md entries
      6-10, 19, 21: only IATSE Local 600's camera department (15% of
      crew_share per data/crew_tiers.yaml, re-confirmed by reading the file)
      is `basis: sourced` for New York and Los Angeles; the other 9 of 10
      below-the-line departments price at a flat $450/day "general_crew" row
      that is `basis: estimated` industry commentary, not transcribed from any
      specific union's published card. SAG-AFTRA (data/union_rates/sag-aftra.yaml)
      has ZERO rate rows — re-confirmed by reading the file — because principal
      cast is not priced as a labour line at all (only its imported headcount
      feeds travel/housing cost). DGA and WGA also have zero CONSUMED rows —
      director and writer are above-the-line roles this phase's crew_tiers.yaml
      explicitly excludes from below-the-line pricing; their rate rows exist in
      the data files but are inert. ACTRA (Canada) is absent entirely since no
      Canadian city is in the floor set (D-54: NY/LA/London only), a legitimate
      scope match, not a gap. London's BECTU coverage mirrors New York/LA's
      shape: one dated, sourced grip-branch row stands in for 9 of 10
      departments (WINDOWS entry 19). Fringe and payroll burden ARE correctly,
      unconditionally emitted as a separate sibling Figure for every craft-
      mapped labour line, so the narrower COST-03 promise is fully met
      regardless of this gap. The open question is specifically whether
      "localized...against published union rate cards" can be said to hold
      when roughly 85% of below-the-line labour cost per city is priced from an
      unattributed flat estimate rather than any of the six named unions'
      actual published rate cards.
deferred: []
---

# Phase 4: Cost Localization & Landed-Cost Outputs Verification Report

**Phase Goal:** The same identical production is priced against each city's real local costs, producing a ranked total landed cost and a gap between any two cities decomposed by component.
**Verified:** 2026-08-27T13:30:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap remediation (fix commits `dfa7455`, `2f34b25`, `795cf86`, `6d3fb5a`)

## What Changed Since The Prior Verification

The prior VERIFICATION.md (superseded by this report, git history preserves it at
commit `2ff6b38`) recorded exactly one BLOCKER: `engine/cost_localizer.py` silently
`continue`d past a `CostLine` whose `label` matched no budget quantity, and
`engine/landed_cost.py`'s `not_priced` was computed at category granularity, unable
to detect a per-line drop (04-REVIEW.md's CR-01). Four fix commits have since
landed, three of which (CR-01, WR-01, WR-03) change runtime behavior and one
(WR-02) is documentation-only. All four are independently re-verified below —
not taken on the fix report's or the orchestrator's word.

## Goal Achievement

### Observable Truths (mapped to ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1a | Labour is priced with fringe and payroll burden ALWAYS emitted as a separate Figure, never a comparison against bare card rates (COST-03 core promise) | ✓ VERIFIED | Unchanged since prior verification. `engine/cost_localizer.py::_price_labour_department` unconditionally returns `(wage_figure, fringe_figure)` as siblings; re-confirmed by reading (this function was not touched by the fix pass). |
| 1b | Labour is genuinely localized against published union rate cards across the six named unions, at material coverage | ? UNCERTAIN (see human_verification) | Unchanged since prior verification — carried forward, not resolved by this verifier per the task's explicit instruction. Only IATSE Local 600's camera department (15% crew_share) is `basis: sourced` per city; SAG-AFTRA has zero rate rows; DGA/WGA rows exist but are never consumed; ACTRA is absent (legitimate scope match, D-54). |
| 2 | Housing/meals/flights/stages/equipment/permits/locations/trucking are all priced per city; GSA/State Dept per diem carries a structural reimbursement-ceiling caveat; estimated lines are labelled estimated; sales-tax/hotel-occupancy exemptions appear as separate stackable reductions where they exist | ✓ VERIFIED | Unchanged since prior verification. Live re-run confirms all ten `COST_CATEGORIES` still price to `not_priced == ()` for NY/LA/London after the fix pass. |
| 3a | Total landed cost is reported per candidate city, ranked, on NET landed cost; only cities with a modelled incentive enter the ranked band; unranked cities carry a cost-only total in a visibly separate band, never a fabricated $0 | ✓ VERIFIED | Unchanged since prior verification; `engine/ranker.py` untouched by the fix pass. |
| 3b | The gap between any two cities decomposes component-by-component, currency included, summing exactly to the headline, with zero-delta rows emitted rather than dropped | ✓ VERIFIED | Unchanged. Re-ran `tests/test_golden_cost.py` and `tests/test_engine_gap.py` in isolation post-fix — golden totals byte-identical to the prior verification's figures (`$758,427` NY Q2, gap `$64,906`). |
| 3c (STRETCH) | Chart-of-accounts (ATL/BTL/Post) tag lands on every budget line at creation; rendered view out of scope (D-77) | ✓ VERIFIED | Unchanged. `engine/budget.py`'s account-tag validation logic untouched by the WR-01 fix (which only added the new boundary-ambiguity guard). |
| 4 | Changing start_quarter changes cost through genuine seasonal (per-diem month-band) variation, not only incentive availability; a non-USD city converts at a dated, cited FX rate carried as its own Figure | ✓ VERIFIED | Re-confirmed live post-fix: NY total varies `734865`/`758427`/`748263` across Q1/Q2/Q3 (a different fixed spec than the prior verification's live check, but the same qualitative NY-variant/LA-invariant/London-invariant shape holds); `engine/fx.py` untouched by the fix pass. |
| 5 | Sensitivity output shows which single input most moves the gap, as a delta with its step named, never a prescriptive recommendation; perturbation re-runs the real pipeline, never a derivative | ✓ VERIFIED | Re-confirmed post-fix. WR-03's fix adds a load-time guard (`SensitivityStep._step_must_be_a_whole_number`) that does not change `sensitivity_rows`' full-pipeline-rerun behavior — `_price_pair` is untouched. `tests/test_engine_sensitivity.py`'s D-70 vocabulary-gate tests still pass (33 passed in that module + `test_engine_budget.py` combined, re-run in isolation). |
| 6 | `not_priced` and the per-line cost accounting are a structurally trustworthy declaration of coverage gaps — never a silent partial total masquerading as full coverage | ✓ VERIFIED | **Gap closed.** `engine/cost_localizer.py::localize` now accumulates `consumed_labels` across every consumption path (travel-category branch at line 448, facilities-category branch at line 475, budget-quantity/labour branch at line 481) and raises `ValueError` naming every `CostLine.label` left unconsumed, BEFORE returning any `LocalizedBudget` — see lines 514-525. This makes the category-granularity limitation of `not_priced` moot for exactly the failure class CR-01 named: a label mismatch can no longer produce a silently-under-totalled `LocalizedBudget` that still reports `not_priced == ()`; it raises instead of returning at all. Independently verified non-vacuous: reverted `engine/cost_localizer.py` to its pre-fix state (`git show dfa7455~1`), re-ran `test_localize_raises_on_a_cost_line_label_that_matches_nothing` in isolation, confirmed `Failed: DID NOT RAISE ValueError`; restored the fix and confirmed the same test and the full 31-test module pass. |

**Score:** 6/6 must-haves verified (1 sub-item, 1b, remains routed to human judgment per the task's explicit instruction not to resolve it either way)

### Independent Judgment on the Two Items Flagged for Judgment Call

**CR-01 (the prior BLOCKER) — judged CLOSED, not merely mitigated.** The fix
addresses the raise-on-unmatched-label half directly, and on independent reading
this makes the `not_priced` category-granularity question moot rather than
"technically still a blind spot": the ONLY way a per-line silent drop could
previously reach a caller was via the bare `continue` at the old lines 475-477
producing a `LocalizedBudget` that never included the dropped line. Post-fix,
that same code path now marks the label unconsumed, and the unconsumed check
runs unconditionally before `localize()` returns *anything* — there is no
longer a code path that returns a `LocalizedBudget` with a silently-dropped
label. `not_priced` itself is still literally computed at category granularity
(that line of code did not change), but the failure mode CR-01 described (a
9-of-10-departments-priced-but-1-silently-dropped `LocalizedBudget` reporing
`not_priced == ()`) can no longer occur — the pipeline raises before that
`LocalizedBudget` is ever constructed. Judged: fully closed, not a residual
gap, not an override needed.

**WR-02 (undocumented -> documented cross-suffix collision) — judged an
ACCEPTED, disclosed limitation, not an open defect.** `"New York, CA"` still
resolves to Los Angeles's cost profile at runtime (confirmed by reading the
unchanged `resolve_city_to_profile_stem` logic) — the fix added a "KNOWN
LIMITATION" docstring paragraph, no behavior change. For the phase's committed
three-city allow-list (New York, Los Angeles, London), triggering this requires
a visitor to submit an internally self-contradictory city/suffix pair (e.g. a
city literally named "New York" suffixed with California's state code, or any
nonsense string suffixed `", UK"`). This does not falsify any of the five
ROADMAP success criteria for the pricing of an honestly-identified city, mirrors
an already-accepted convention in `app/services/city_lookup.py` (New York's own
suffix fallback has the identical shape), and the module's own explicit design
principle ("no fuzzy match, explicit allow-list only") means fixing it would
require reintroducing exactly the fuzzy prefix-validation this module exists to
avoid. Judged: a genuine but narrow, now-honestly-disclosed limitation —
WARNING-grade, not BLOCKER-grade, consistent with 04-REVIEW.md's own Warning
(not Critical) classification. Not routed as a gap.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/cost_localizer.py` | Stage [2] localize() | ✓ VERIFIED | Gap closed — `consumed_labels` tracking + raise on unmatched label confirmed by reading and by independent revert/restore test. |
| `engine/landed_cost.py` | Stage [6] aggregate(), COST_CATEGORIES, PERMANENT_EXCLUSIONS | ✓ VERIFIED | Untouched by the fix pass; category-level `not_priced` computation is now moot for the CR-01 failure class since `localize()` raises before returning a partial `LocalizedBudget`. |
| `engine/budget.py` | Canonical budget, department shares, account tags, crew-tier boundary guard | ✓ VERIFIED | `_check_tier_boundaries_for_ambiguous_crew_share` confirmed wired into `resolve_departments`; two new regression tests confirmed passing (differentiated-boundary raises, identical-boundary does not). |
| `engine/sensitivity.py` | Perturb-and-rerun sensitivity engine, fractional-step guard | ✓ VERIFIED | `SensitivityStep._step_must_be_a_whole_number` confirmed wired as a `model_validator`; three new regression tests confirmed passing. |
| `engine/city_profile_lookup.py` | Suffix-based city-to-profile resolution | ✓ VERIFIED (documented limitation) | KNOWN LIMITATION docstring paragraph confirmed present; runtime resolution logic unchanged (by design — documentation-only fix). |
| All other Phase 4 artifacts (`engine/union_rates.py`, `engine/per_diem.py`, `engine/seasonality.py`, `engine/facilities.py`, `engine/exemptions.py`, `engine/fx.py`, `engine/ranker.py`, `engine/gap.py`, data files) | — | ✓ VERIFIED (unchanged) | `git diff --stat` from the prior verification's commit confirms none of these files were touched by the fix pass; prior verification's findings for these carry forward unchanged. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `CostLine.label` | `budget.line_quantities` / travel categories / facilities categories | `engine/cost_localizer.py::localize` | ✓ WIRED (was ✗ UNGUARDED) | Now raises `ValueError` naming every unmatched label before returning — confirmed by reading and by independent revert/restore of the regression test. |
| `data/crew_tiers.yaml` tier boundaries | `resolve_departments` | `_check_tier_boundaries_for_ambiguous_crew_share` | ✓ WIRED | Confirmed called unconditionally on every load; confirmed the real committed table (identical `crew_share` across tiers) does not trigger the guard (full suite green). |
| `data/sensitivity_steps.yaml` step values | `SensitivityStep` model | `_step_must_be_a_whole_number` | ✓ WIRED | Confirmed as a `model_validator(mode="after")`; confirmed the real committed table (`step: "1"` everywhere) does not trigger the guard. |
| All key links carried forward from the prior verification | — | — | ✓ WIRED (unchanged) | None of the underlying modules for these links were touched by the fix pass. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CR-01 regression test is non-vacuous (fails pre-fix, passes post-fix) | Reverted `engine/cost_localizer.py` to `dfa7455~1`, ran the named test, restored the fix, re-ran | Pre-fix: `Failed: DID NOT RAISE ValueError`. Post-fix: passes; full 31-test module passes | ✓ PASS |
| `not_priced` is empty for all three committed cities, all three quarters, post-fix | Live Python re-run of `build_canonical_budget` → `localize` → `aggregate` for NY/LA/London × Q1/Q2/Q3 | `()` for all nine combinations | ✓ PASS |
| Start-quarter genuinely varies New York's cost, not Los Angeles's or London's, post-fix | Live Python re-run across Q1/Q2/Q3 | NY: 734865/758427/748263; LA: 693521 flat; London: 548595 flat (GBP) | ✓ PASS |
| Golden cost / gap totals are unchanged by the fix pass | `uv run pytest tests/test_golden_cost.py tests/test_engine_jurisdiction_additivity.py -q` | 10 passed | ✓ PASS |
| WR-01/WR-03 regression modules pass in isolation | `uv run pytest tests/test_engine_budget.py tests/test_engine_sensitivity.py -q` | 33 passed | ✓ PASS |
| No debt markers introduced by the four fix commits | `git show dfa7455 2f34b25 795cf86 6d3fb5a \| grep -nE "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` | no matches | ✓ PASS |
| Full test suite, re-run independently | `uv run pytest -q` | 476 passed, 0 failed | ✓ PASS |
| Change surface since prior verification is exactly the claimed 4 fix commits | `git diff --stat 2ff6b38 HEAD` | 8 files changed: `engine/budget.py`, `engine/city_profile_lookup.py`, `engine/cost_localizer.py`, `engine/sensitivity.py`, 3 test files, 1 review-fix report — nothing else | ✓ PASS |

### Requirements Coverage

Unchanged from the prior verification — the fix pass touched no requirement
mapping. All 13 requirement IDs (`COST-01` through `COST-08`, `INC-10`, `OUT-01`
through `OUT-04`) declared across the phase's 7 plans are present in
`.planning/REQUIREMENTS.md` and marked `Complete`; no orphaned requirements
(re-confirmed: `grep "Phase 4" .planning/REQUIREMENTS.md` lists exactly the
same 13 IDs the plans declare).

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| COST-01 | 04-01 | One identical budget model localized per city, comparison never bare rates | ✓ SATISFIED | Unchanged. |
| COST-02 | 04-02, 04-05 | Labour against published union rate cards | ? PARTIALLY SATISFIED | Unchanged — see human_verification. |
| COST-03 | 04-02 | Fringe and payroll burden included, not bare card rates | ✓ SATISFIED | Unchanged. |
| COST-04 | 04-03 | GSA/State Dept per diem labelled as reimbursement ceilings, not market rates | ✓ SATISFIED | Unchanged. |
| COST-05 | 04-03 | Flights/housing computed for imported crew and cast specifically | ✓ SATISFIED | Unchanged. |
| COST-06 | 04-04 | Stage/equipment/permit/location/trucking priced, estimated lines labelled | ✓ SATISFIED | Unchanged. |
| COST-07 | 04-03 | Start quarter drives seasonal cost variation, not only incentive availability | ✓ SATISFIED | Re-confirmed live post-fix. |
| COST-08 | 04-05 | Multi-currency costs converted via dated, cited FX rate | ✓ SATISFIED | Unchanged. |
| INC-10 | 04-04 | Sales tax / hotel occupancy exemptions as separate stackable reductions | ✓ SATISFIED | Unchanged. |
| OUT-01 | 04-06 | Total landed cost per candidate city, ranked | ✓ SATISFIED | Unchanged. |
| OUT-02 | 04-06 | Cost gap decomposed by component | ✓ SATISFIED | Re-confirmed unchanged golden totals. |
| OUT-03 | 04-07 | Sensitivity: single input moving the gap most, as a delta, never prescriptive | ✓ SATISFIED | Re-confirmed post-fix. |
| OUT-04 | 04-01 | Chart-of-accounts tagging (stretch: tags only, no view) | ✓ SATISFIED | Unchanged. |

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in any of the four
fix commits' diffs (re-checked directly against the commits, not the working
tree). WINDOWS.md gained no new entries beyond id 25 since the prior
verification (`wc -l` and tail confirm the ledger ends at entry 25, matching
the prior verification's own references) — the fix pass introduced no new
disclosed lint debt either.

### Human Verification Required

### 1. Is COST-02/Success-Criterion-1's union-rate-card coverage sufficient?

**Test:** Review `.planning/WINDOWS.md` entries 6-10, 19, 21 alongside
`data/union_rates/*.yaml` and decide whether the current coverage (1 of 10
below-the-line departments genuinely sourced from a published card, per city;
SAG-AFTRA/DGA/WGA/ACTRA contributing nothing to the priced total) constitutes
"localized... against published union rate cards" as the roadmap success
criterion states, or whether this should be recorded as an accepted, documented
scope reduction (an override) pending further sourcing in a later session.
**Expected:** A decision — either accept as-is (given the honest disclosure and
DataDome-blocked SAG-AFTRA access), or open a follow-up plan to fetch the
remaining per-craft IATSE locals (80, 728, 800, 705, 706, 695, 871, 700) and
Teamsters Local 399.
**Why human:** Data-completeness/scope-sufficiency judgment call, not a
programmatically resolvable pass/fail — unchanged from the prior verification;
the fix pass did not touch union-rate data or logic.

### Gaps Summary

**No gaps remain.** The prior verification's sole BLOCKER (CR-01: silent
per-line label drop) is closed and independently re-verified as genuinely
non-vacuous — reverting the fix reproduces the exact failure the review
described, restoring it eliminates that failure class entirely by raising
before any partial `LocalizedBudget` can be returned. WR-01 and WR-03's
behavior-changing fixes are confirmed wired and covered by passing regression
tests that do not alter any committed data's output. WR-02 was closed by
documentation only (an explicit, deliberate choice matching the review's own
primary recommendation) — the cross-suffix collision it names still exists at
runtime, but is judged an accepted, low-likelihood, now-honestly-disclosed
limitation for the phase's committed three-city allow-list, not a defect
blocking phase completion.

One item — carried forward unchanged, not resolved by this verifier per
explicit instruction — remains routed to human judgment: whether the phase's
narrow (~15% of below-the-line labour cost per city) genuine union-rate-card
coverage satisfies Success Criterion 1's letter. This is the sole reason this
report's status is `human_needed` rather than `passed`: every other truth is
fully VERIFIED, but Step 9 of the verification process routes to
`human_needed` whenever any human-verification item exists, regardless of how
many other truths pass clean.

---

_Verified: 2026-08-27T13:30:00Z_
_Verifier: Claude (gsd-verifier)_
