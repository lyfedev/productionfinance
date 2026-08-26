---
phase: 04-cost-localization-landed-cost-outputs
plan: 03
subsystem: cost-localization
tags: [per-diem, gsa, seasonality, housing, travel, figure-caveat, quarter-invariance]

requires:
  - phase: 04-cost-localization-landed-cost-outputs
    provides: "04-01's Figure.basis provenance axis, CityCostProfile schema, CanonicalBudget/build_canonical_budget, engine.cost_localizer.localize, engine.landed_cost.aggregate; 04-02's dynamic labour+fringe pricing path, the committed New York and Los Angeles cost profiles"
provides:
  - "engine.figure.Figure.caveat (D-61) — a structural per-diem/housing reimbursement-ceiling disclaimer, serialized in figure_to_dict"
  - "engine.per_diem — PerDiemTable schema, load_per_diem, lodging_for_month; PER_DIEM_PATH_BY_ID discovered by glob (never a hard-coded jurisdiction-shaped literal)"
  - "engine.seasonality — _shoot_calendar/shoot_calendar (D-65), month_weighted_per_diem (returns housing + per_diem as two sibling Figures, D-62's discipline extended to travel)"
  - "engine.landed_cost.SeasonalityState and compute_quarter_invariance — a genuine 4-run measurement of which Figure labels move with the quarter, never a hardcoded list (D-66/D-67); additive LandedCost/aggregate() fields"
  - "engine.cost_profile.TravelBlock and CityCostProfile.travel — housing/per_diem/flights priced dynamically from imported headcount only"
  - "Committed GSA per-diem snapshots for New York County (month-banded) and Los Angeles County (flat), re-confirmed against the raw FY2026 bulk file"
  - "engine.cost_localizer.localize's widened spec parameter, threading imported headcount and the shoot calendar into housing/per_diem/flights pricing"
affects: [04-04, 04-05, 04-06, 04-07, "Phase 6 (interface renders the caveat, seasonality_state and quarter_variant_lines)", "Phase 8 (proof panel walks the widened Figure DAG, now including two more sibling-Figure categories)"]

actuals:
  tokens: 68000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "A per-diem/housing/flights snapshot lookup table (PER_DIEM_PATH_BY_ID) is built by GLOBBING committed files and reading each one's own declared id, never a Python dict literal — this is what let engine/per_diem.py embed jurisdiction-shaped ids (us-ny-new-york-county) as DATA without tripping the JUR-05 substring scan a hard-coded literal would have."
    - "A cost category's dynamic-vs-static pricing dispatch (labour: craft mapping present; housing/per_diem/flights: travel block present) is decided per-line inside localize(), and the same 'declared block is present -> dynamic path, absent -> static per-line path' shape now covers three category families identically."
    - "A quarter-invariance claim is a MEASUREMENT, not a declared list: compute_quarter_invariance() diffs real Figure values across N labelled re-runs and is proven non-vacuous by mutating a rate and re-running (tests/test_engine_seasonality.py)."
    - "D-62's 'never fold two distinct costs into one Figure' discipline extends past labour/fringe to travel: month_weighted_per_diem returns housing (lodging) and per_diem (M&IE) as two sibling Figures, never a combined per-diem number."

key-files:
  created:
    - engine/per_diem.py
    - engine/seasonality.py
    - data/per_diem/gsa/us-ny-new-york-county.yaml
    - data/per_diem/gsa/us-ca-los-angeles-county.yaml
    - sources/gsa/2026-08-26-gsa-fy2026-per-diem-master-rates-file.xlsx
    - tests/test_engine_per_diem.py
    - tests/test_engine_seasonality.py
  modified:
    - engine/figure.py
    - engine/figure_serialize.py
    - engine/landed_cost.py
    - engine/cost_profile.py
    - engine/cost_localizer.py
    - data/cost_profiles/us-ny-new-york.yaml
    - data/cost_profiles/us-ca-los-angeles.yaml
    - app/services/spec.py
    - sources/MANIFEST.yaml
    - tests/test_engine_cost_localizer.py
    - .planning/WINDOWS.md

key-decisions:
  - "The GSA bulk file was downloaded and parsed directly (stdlib zipfile + xml.etree, no new dependency, no AWS Textract) rather than relying on 04-RESEARCH.md's WebFetch-summarized figures — the raw file (row ID 266 New York, row ID 22 Los Angeles) reproduced every CITED figure byte-for-byte, raising both snapshots from CITED to basis: sourced with zero discrepancy to record."
  - "PER_DIEM_PATH_BY_ID is built by globbing data/per_diem/**/*.yaml and reading each file's own per_diem_id, not a Python dict literal — this was a deliberate design change from the plan's literal phrasing, made specifically to avoid the same JUR-05 substring-scan collision plan 04-02 hit and fixed by editing the test file; globbing avoids the collision structurally with zero test-file edits."
  - "month_weighted_per_diem returns TWO sibling Figures (housing, per_diem) rather than the plan prose's single combined Figure — required by Task 3's explicit 'split into two sibling Figures' instruction and by COST_CATEGORIES treating housing and per_diem as separate categories; reconciled here rather than left as a prose contradiction."
  - "localize() gained a keyword-only spec: ProductionSpec | None = None parameter, required only when a profile declares a housing/per_diem/flights cost line alongside a travel: block — mirroring the existing on_date/labour relationship exactly, so every pre-04-03 synthetic fixture with no travel block is unaffected."
  - "flight_round_trip_rate is basis: estimated ($450, a disclosed national-average figure) for both cities — no per-route or per-city published airfare table was located this session (04-RESEARCH.md Assumption A5); recorded to WINDOWS.md rather than presented as sourced."

requirements-completed: [COST-04, COST-05, COST-07]

coverage:
  - id: D1
    description: "Both floor US cities have a committed, dated, hash-archived GSA per-diem snapshot re-confirmed against the raw bulk file — New York genuinely month-banded, Los Angeles genuinely flat for FY2026, with zero discrepancy from 04-RESEARCH.md's CITED figures"
    requirement: COST-04
    verification:
      - kind: unit
        ref: "tests/test_engine_per_diem.py#test_ny_lodging_by_month_matches_raw_gsa_bulk_file_reconfirmation"
        status: pass
      - kind: unit
        ref: "tests/test_engine_per_diem.py#test_la_lodging_flat_rate_matches_raw_gsa_bulk_file_reconfirmation"
        status: pass
      - kind: unit
        ref: "tests/test_source_truth.py (manifest hash reconciliation over the archived xlsx)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Figure.caveat lands as a structural field (D-61), serialized in figure_to_dict, and every per-diem/housing Figure in a real Route A response carries a non-null caveat naming the reimbursement ceiling"
    requirement: COST-04
    verification:
      - kind: unit
        ref: "tests/test_engine_seasonality.py#test_new_york_per_diem_carries_the_ceiling_caveat_and_basis"
        status: pass
      - kind: integration
        ref: "tests/test_engine_cost_localizer.py#test_every_per_diem_and_housing_figure_has_a_non_null_caveat"
        status: pass
    human_judgment: false
  - id: D3
    description: "Housing, per diem and flights price against imported crew and imported principal cast headcount only; locally-hired crew and local cast generate zero of each, by name in the derivation"
    requirement: COST-05
    verification:
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_zero_imported_headcount_produces_computed_zero_never_not_priced"
        status: pass
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_ten_imported_crew_produces_exactly_ten_times_the_one_person_figure"
        status: pass
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_increasing_locally_hired_crew_alone_leaves_travel_costs_unchanged"
        status: pass
    human_judgment: false
  - id: D4
    description: "The start quarter changes New York's per-diem total through published month bands and leaves Los Angeles's unchanged; the absence of a month band is stated explicitly, never backfilled with a multiplier"
    requirement: COST-07
    verification:
      - kind: unit
        ref: "tests/test_engine_seasonality.py#test_changing_start_quarter_changes_new_york_but_not_los_angeles"
        status: pass
      - kind: integration
        ref: "manual reproduction: Route A priced at Q1 vs Q3 2026 for the fixed test spec — New York cost_total 664261 -> 677659, Los Angeles cost_total 626698 -> 626698 unchanged (see Next Phase Readiness)"
        status: pass
    human_judgment: false
  - id: D5
    description: "quarter_invariant_lines/quarter_variant_lines are a genuine measurement over four real re-runs, never a hardcoded list — proven non-vacuous by mutating a rate and re-running"
    requirement: COST-07
    verification:
      - kind: unit
        ref: "tests/test_engine_seasonality.py#test_compute_quarter_invariance_is_a_real_measurement_not_a_literal_list"
        status: pass
      - kind: unit
        ref: "tests/test_engine_seasonality.py#test_compute_quarter_invariance_against_real_committed_per_diem_tables"
        status: pass
    human_judgment: false
  - id: D6
    description: "Both committed profiles' not_priced now names only the five facilities categories (stages, equipment, permits, locations, trucking); no engine/ source file carries a bare jurisdiction-id literal"
    verification:
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_both_committed_profiles_not_priced_names_only_five_facilities_categories"
        status: pass
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_no_jurisdiction_id_literal_in_cost_localizer_per_diem_or_seasonality"
        status: pass
      - kind: unit
        ref: "tests/test_engine_jurisdiction_additivity.py (repo-wide JUR-05 gate, unmodified, still green)"
        status: pass
    human_judgment: false

duration: 95min
completed: 2026-08-26
status: complete
---

# Phase 4 Plan 03: Seasonality, GSA Per Diem, and Imported-Headcount Travel Costs Summary

**GSA's FY2026 bulk per-diem file confirms New York's month-banded and Los Angeles's flat lodging rates byte-for-byte against 04-RESEARCH.md's CITED figures; housing, per diem and flights now price against imported crew and cast only, each carrying a structural reimbursement-ceiling caveat, and New York's start quarter genuinely moves the number through the housing line alone — New York's fixed-test-spec landed cost moves from $447,532 (04-02) to $515,867.**

## Performance

- **Duration:** 95 min
- **Started:** 2026-08-26T23:00:00Z (approximate — GSA fetch/parse predates the first commit)
- **Completed:** 2026-08-27T00:35:00Z
- **Tasks:** 3
- **Files modified:** 18 (7 created, 11 modified)

## Accomplishments

- **Re-confirmed against the raw GSA bulk file, not a WebFetch summarization.** Downloaded `FY2026_PerDiemMasterRatesFile.xlsx` directly from `gsa.gov/system/files` and parsed it with stdlib `zipfile`/`xml.etree` (no new dependency, no AWS Textract or any AWS AI endpoint). Row ID 266 (New York City, five seasonal bands: Oct-Dec $342, Jan-Feb $179, Mar-Jun $281, Jul-Aug $237, Sep $342; M&IE $92 flat) and row ID 22 (Los Angeles, flat $191 lodging, $86 M&IE, no SEASON BEGIN/END populated) reproduce 04-RESEARCH.md's CITED figures byte-for-byte — **zero discrepancy to record**, and both snapshots are raised from CITED to `basis: sourced`.
- **`Figure.caveat` (D-61)** lands as a structural, non-empty-validated field on `engine/figure.py`, serialized in `figure_to_dict` next to `basis` — every per-diem and housing Figure in a real Route A response carries it, verified by direct JSON-boundary reproduction, not just at the dataclass level.
- **`engine/per_diem.py`** — `PerDiemTable` (exactly one of `lodging_by_month`/`lodging_flat_rate`, sourced/method_note discipline matching `RateRow`/`FringeComponent`), `load_per_diem`, `lodging_for_month` (raises on a month absent from a band map, never a nearest-neighbour guess). `PER_DIEM_PATH_BY_ID` is built by **globbing** every committed per-diem YAML and reading its own declared id — a deliberate design choice (see Decisions) that avoided the exact JUR-05 substring-scan collision plan 04-02 hit, with zero test-file edits.
- **`engine/seasonality.py`** — `_shoot_calendar`/`shoot_calendar` (D-65: total shoot days spread across calendar months at a disclosed `SHOOT_DAYS_PER_WEEK = 5` modelling assumption) and `month_weighted_per_diem`, which returns housing (lodging) and per diem (M&IE) as **two sibling Figures** — D-62's "never fold two distinct costs into one number" discipline extended from labour/fringe to travel.
- **`engine/landed_cost.py`** gains `SeasonalityState` and `compute_quarter_invariance` — a genuine measurement comparing N labelled re-runs' Figure values, proven non-vacuous by a test that mutates a rate and re-runs to see membership move. Against the real committed tables (Q1/Q2/Q3 2026, the FY2026 snapshot's coverage window), New York's **only** quarter-variant line is `Housing — imported crew and cast` (M&IE is flat, so per diem itself is quarter-invariant); Los Angeles has **zero** variant lines.
- **`engine/cost_profile.py`** gains `TravelBlock`/`CityCostProfile.travel`; **`engine/cost_localizer.py`**'s `localize()` gains a keyword-only `spec` parameter and prices housing, per diem and flights dynamically from `crew_imported_count + principal_cast_imported_count` only — locally-hired crew and local cast generate exactly `Decimal("0")` with an explicit "this is a computed zero" derivation line, never an entry in `not_priced`. Both committed profiles' `not_priced` now names only the five facilities categories (stages, equipment, permits, locations, trucking).
- **68 new tests** across `tests/test_engine_per_diem.py`, `tests/test_engine_seasonality.py`, and 9 additions to `tests/test_engine_cost_localizer.py`: schema validation (neither/both lodging shapes), month-absent-from-band raises, linearity (10x headcount = 10x cost), the genuine zero case, the quarter-invariance measurement against real data, and a re-assertion that `engine/cost_localizer.py`/`engine/per_diem.py`/`engine/seasonality.py` carry no bare jurisdiction-id literal.

## Task Commits

Each task was committed atomically:

1. **Task 1: Commit GSA per-diem snapshots for New York County and Los Angeles County, re-confirmed against the raw bulk file** — `f00fecb` (feat)
2. **Task 2: The shoot calendar, month-weighted per diem, and the quarter-invariant statement** — `9a83eaa` (feat)
3. **Task 3: Housing, per diem and flights for imported crew and cast only** — `c0d004d` (feat)

**Plan metadata:** commit hash recorded after this SUMMARY is committed.

## Files Created/Modified

- `engine/per_diem.py` — new; `PerDiemTable`, `load_per_diem`, `lodging_for_month`, `PER_DIEM_PATH_BY_ID` (glob-discovered)
- `engine/seasonality.py` — new; `SHOOT_DAYS_PER_WEEK`, `MonthNights`, `_shoot_calendar`/`shoot_calendar`, `month_weighted_per_diem`
- `engine/figure.py` — `Figure.caveat` (D-61)
- `engine/figure_serialize.py` — `"caveat"` key added to `figure_to_dict`
- `engine/landed_cost.py` — `SeasonalityState`, `compute_quarter_invariance`, additive `LandedCost`/`aggregate()` fields
- `engine/cost_profile.py` — `TravelBlock`, `CityCostProfile.travel`, widened dynamic-pricing category exemption
- `engine/cost_localizer.py` — `_price_travel_categories`, `localize()`'s widened `spec` parameter
- `data/per_diem/gsa/us-ny-new-york-county.yaml`, `us-ca-los-angeles-county.yaml` — new, `basis: sourced`
- `data/cost_profiles/us-ny-new-york.yaml`, `us-ca-los-angeles.yaml` — `travel:` block + 3 cost lines each
- `sources/gsa/2026-08-26-gsa-fy2026-per-diem-master-rates-file.xlsx` — new, archived raw bulk file
- `sources/MANIFEST.yaml` — one new entry
- `app/services/spec.py` — `localize()` call site threaded with `spec=spec`
- `tests/test_engine_per_diem.py`, `tests/test_engine_seasonality.py` — new
- `tests/test_engine_cost_localizer.py` — 8 existing `localize()` call sites threaded with `spec=`, 7 new Task 3 tests
- `.planning/WINDOWS.md` — three new entries

## Decisions Made

- **The GSA bulk file was fetched and parsed directly this session**, upgrading both per-diem snapshots from CITED (WebFetch-summarized) to genuinely `basis: sourced`, with zero discrepancy against 04-RESEARCH.md's figures — see Coverage D1 and "Next Phase Readiness" below.
- **`PER_DIEM_PATH_BY_ID` is glob-discovered, not a Python dict literal.** A literal id string like `"us-ny-new-york-county"` embedded directly in `engine/per_diem.py`'s source would have tripped `tests/test_engine_jurisdiction_additivity.py`'s JUR-05 substring scan the same way an early draft of `engine/union_rates.py` did in plan 04-02 (which required editing that test file's exclusion list). Building the mapping by globbing committed YAML files and reading each one's own declared `per_diem_id` avoids the collision structurally, with zero test-file edits — a stronger design than the plan's literal phrasing implied.
- **`month_weighted_per_diem` returns two sibling Figures (housing, per_diem), not one combined Figure.** Task 2's prose describes a single combined Figure; Task 3 explicitly requires "split into two sibling Figures where the table separates lodging from M&IE" — since `housing` and `per_diem` are separate entries in `COST_CATEGORIES`, the two-Figure design is the one that is actually correct and is what got implemented, resolving the prose tension in favour of D-62's established discipline.
- **`localize()`'s new `spec` parameter is keyword-only with a `None` default**, exactly mirroring the existing `on_date`/labour relationship — required only when a profile declares a housing/per_diem/flights line alongside a `travel:` block. Every pre-04-03 synthetic fixture with no `travel` block is unaffected.
- **`flight_round_trip_rate` is `basis: estimated` ($450, a disclosed national-average commentary figure) for both cities** — no per-route or per-city published airfare table was located this session (04-RESEARCH.md Assumption A5). Recorded to `.planning/WINDOWS.md` rather than presented as sourced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `app/services/spec.py`'s `localize()` call site required a signature-compatible update outside this plan's declared files**
- **Found during:** Task 3 (widening `localize()` to accept `spec`)
- **Issue:** Both committed profiles now declare housing/per_diem/flights cost lines alongside a `travel:` block, so `localize()` raises `ValueError` when `spec` is omitted — but `app/services/spec.py::_price_candidate_cities`, the only production call site, is not in Task 3's declared `<files>` list. Leaving it untouched would break every Route A request touching New York or Los Angeles.
- **Fix:** Changed the single call site from `localize(budget, profile, on_date=on_date)` to `localize(budget, profile, on_date=on_date, spec=spec)` — a one-argument addition, `spec` already in scope at that call site. Mirrors plan 04-02's identical precedent (the `on_date` threading fix) exactly.
- **Files modified:** `app/services/spec.py`
- **Verification:** `tests/test_app_spec_route.py` (pre-existing, unmodified) still passes; `tests/test_engine_cost_localizer.py::test_route_a_prices_both_cities_and_la_incentive_is_not_modelled_not_zero` exercises the real HTTP-level path end to end.
- **Committed in:** `c0d004d` (Task 3 commit)

**2. [Rule 3 - Blocking] Eight pre-existing `test_engine_cost_localizer.py` call sites needed the same `spec=` threading**
- **Found during:** Task 3, immediately after widening `localize()`'s signature
- **Issue:** Every pre-existing test calling `localize(budget, _ny_profile(), on_date=on_date)` or the Los Angeles equivalent broke, since both committed profiles now require `spec` for their new travel-category lines.
- **Fix:** Added `spec=spec` to all eight affected call sites (already-in-scope `spec` variables in every case); updated one assertion (`test_every_labour_department_produces_two_figures_with_different_labels`) to account for the three new travel Figures now present in `localized.lines` (23 lines total, not 20) and to select wage labels by their `" labour days"` suffix rather than "not Fringe-prefixed" (which now also matched the travel labels).
- **Files modified:** `tests/test_engine_cost_localizer.py`
- **Verification:** `uv run --frozen pytest tests/ -q` — 362 passed, 0 failed.
- **Committed in:** `c0d004d` (Task 3 commit)

**3. [Rule 1 - Bug] A test file's own docstring collided with the JUR-05 substring scan**
- **Found during:** Task 2, drafting `engine/per_diem.py`'s module docstring
- **Issue:** An early draft's docstring used the literal example `"us-ny-new-york-county"` to explain why a Python dict literal would be dangerous — the illustrative example itself tripped `test_no_jurisdiction_identifier_appears_in_engine_source`, since the docstring is not comment-only and the substring `"us-ny"` is inside it.
- **Fix:** Rewrote the docstring to describe the collision generically ("a committed per-diem id embeds a jurisdiction-shaped prefix... writing that id as a Python literal directly in this module's source would trip the JUR-05 substring scan") with no jurisdiction-id-shaped literal anywhere in the file.
- **Files modified:** `engine/per_diem.py`
- **Verification:** `uv run pytest tests/test_engine_jurisdiction_additivity.py -q` — 4 passed.
- **Committed in:** `9a83eaa` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 bug).
**Impact on plan:** All three were necessary to keep the full test suite green while implementing exactly what the plan specified. No scope creep — the `app/services/spec.py` change is a single keyword-argument addition, not a redesign of Route A.

## Issues Encountered

- **The committed FY2026 GSA snapshot has an October-2025-through-September-2026 coverage window** (a genuine federal fiscal year), not a calendar year. A start_quarter of Q4 combined with start_year 2026 derives an October 2026 calendar month, past the snapshot's coverage — `lodging_for_month` correctly raises `ValueError` rather than fabricating a rate (D-64 upheld). This means the quarter-invariance measurement in this plan covers Q1-Q3 2026 for New York; a FY2027 snapshot would be needed to extend it to Q4. Recorded to `.planning/WINDOWS.md` (entry 12) — not routed around.
- **`flight_round_trip_rate` ($450) has no per-route or per-city sourced airfare table** — a disclosed national-average estimate, identical for both cities. Recorded to `.planning/WINDOWS.md` (entry 13).
- **Repo-wide ruff baseline grew from 320 to 343** (net +23) from this plan's new files — the same pre-existing FURB157/ISC004 patterns already tracked across the repo, not a new category. Out of scope per the executor scope-boundary rule; recorded to `.planning/WINDOWS.md` (entry 14, alongside the existing entry 2 tracking the repo-wide cleanup).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **The new `total_landed_cost` for the fixed test spec** (feature, 10 stage + 5 location shoot days, `crew_size=50`, 10 imported crew + 1 imported principal cast, candidate city "New York, NY", start `Q2 2026`) is **`Decimal("515867")`**, up from 04-02's recorded `Decimal("447532")` — a delta of **+$68,335**. Composition: `cost_total` (pre-incentive) grew from `$596,710` (04-02) to `$687,823` (+$91,113 — exactly `housing $64,911 + per_diem $21,252 + flights $4,950`, all priced from the 11 imported people this spec declares). The New York incentive scaled up proportionally with the larger qualifying spend, netting `$171,956` (up from 04-02's `$149,178`), giving `687,823 - 171,956 = 515,867`.
- **Los Angeles's parallel run** (same fixed spec, "Los Angeles, CA") produces `cost_total = total_landed_cost = $626,698` — no incentive netted, `incentive_state: "not_modelled"`.
- **The measured `quarter_invariant_lines`/quarter-variant proof** (Q1/Q2/Q3 2026, the FY2026 snapshot's coverage window): New York's **only** quarter-variant line across the whole priced tree is `Housing — imported crew and cast` (the lodging component moves with the month band; `Per diem (M&IE)` does not, since GSA's M&IE figure is flat at $92 all year); every labour, fringe and flights line is quarter-invariant for New York. Los Angeles has **zero** quarter-variant lines — every single Figure, including `Housing`, is identical across all three quarters, since the FY2026 rate never varies. Direct route-level reproduction: New York's `cost_total` moves `$664,261` (Q1) -> `$677,659` (Q3); Los Angeles's stays at `$626,698` for both.
- **Ready for Phase 6's interface** to render `Figure.caveat`, `LandedCost.seasonality_state` and `quarter_variant_lines`/`quarter_invariant_lines` directly — the engine machinery exists and is proven; wiring it into the live HTTP JSON contract (`CityCost`/`app/routers/spec.py`) is deliberately deferred, matching 04-CONTEXT.md's explicit "No interface treatment... Phase 6" boundary. Route A's JSON response today already carries `caveat` on every Figure via the existing recursive `figure_to_dict` walk (verified directly); it does not yet carry `seasonality_state` or the quarter-invariance lists as top-level `CityCost` fields.
- **Open sourcing work carried forward** (all named in `.planning/WINDOWS.md`, not blocking): `flight_round_trip_rate`'s national-average estimate, the FY2026-only per-diem coverage window (Q4 2026 raises for New York until a FY2027 snapshot lands), and the pre-existing general_crew/SAG-AFTRA/payroll-burden sourcing gaps carried from 04-02.
- No blockers for 04-04. `TravelBlock`, `_price_travel_categories`, and the two-sibling-Figure per-diem pattern are all reusable as-is for any later plan widening more travel-priced cities or categories.

---
*Phase: 04-cost-localization-landed-cost-outputs*
*Completed: 2026-08-26*

## Self-Check: PASSED

- All 18 created/modified files listed above confirmed present on disk (`[ -f ]`).
- All three task commits (`f00fecb`, `9a83eaa`, `c0d004d`) confirmed present in `git log --oneline --all`.
- `uv run --frozen pytest tests/ -q` re-run fresh: 362 passed, 0 failed.
- Plan-level `<verification>`: `grep -rn "\.quantize(" engine/ | grep -v "engine/rounding.py"` returns no hits; `git diff --stat pyproject.toml uv.lock` is empty; both city profiles' `not_priced` confirmed to name only the five facilities categories; a direct Route A reproduction confirms Q1 vs Q3 pricing differs for New York and is identical for Los Angeles; every per-diem/housing Figure in a real Route A JSON response confirmed to carry a non-null `caveat`.
- Task-level acceptance criteria re-verified individually: `grep -c 'lodging_by_month' data/per_diem/gsa/us-ca-los-angeles-county.yaml` returns 0; `grep -nE '"us-ny"|"us-ca"' engine/cost_localizer.py engine/per_diem.py engine/seasonality.py` returns no hits; the repo-wide JUR-05 gate (`tests/test_engine_jurisdiction_additivity.py`) passes unmodified.
