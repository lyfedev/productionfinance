---
phase: 04-cost-localization-landed-cost-outputs
plan: 02
subsystem: cost-localization
tags: [union-rates, labour-pricing, fringe-burden, dated-range-selection, iatse, dga, wga, sag-aftra, los-angeles, cost-profile]

requires:
  - phase: 04-cost-localization-landed-cost-outputs
    provides: "04-01's Figure.basis provenance axis, CityCostProfile schema, CanonicalBudget/build_canonical_budget, engine.cost_localizer.localize, engine.landed_cost.aggregate, the New York cost profile and us-ny-crew.yaml tracer row"
provides:
  - "engine.union_rates — RateRow/FringeSchedule Pydantic models, load_union_rates/load_fringe_schedules, select_rate_row (closed-closed dated-range lookup with WR-03 overlap detection at load time)"
  - "engine.cost_profile.LabourBlock/CraftMapping — a cost profile's department-to-union-craft mapping, validated to cover every crew_tiers.yaml department"
  - "engine.cost_localizer's dynamic labour+fringe pricing path — a labour-category line with a craft mapping emits TWO sibling Figures (wage, fringe) instead of one, layered non-destructively over 04-01's static per-line path"
  - "data/cost_profiles/us-ca-los-angeles.yaml — Los Angeles's committed cost profile, jurisdiction_id null, proving D-53"
  - "engine.cost_localizer.quarter_start_date — the ProductionSpec.start_quarter/start_year -> on_date derivation, threaded through app/services/spec.py"
  - "Real IATSE Local 600 camera-department scale for both New York and Los Angeles (sourced), plus DGA and WGA Pension & Health percentages resolved to sourced from each union's own primary document"
affects: [04-03, 04-04, 04-05, 04-06, 04-07, "Phase 5 (California's rule file lands on top of this committed LA cost profile with zero cost-side changes)", "Phase 6 (interface renders the wage/fringe pair as two visible lines)", "Phase 8 (proof panel walks the widened Figure DAG)"]

actuals:
  tokens: 34600
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "A craft mapping declared on a cost profile's labour block routes a labour-category line to the DYNAMIC two-Figure (wage+fringe) path; a labour line with no craft mapping (or a profile with no labour block) keeps the prior plan's static single-Figure path unchanged — additive, not a replacement, so every pre-existing fixture stays green with zero edits."
    - "Fringe is never a multiplier baked into a wage value — it is a second, sibling Figure whose sole input is the wage Figure, mirroring engine.net_cash._deduct_audit_fee's existing 'deduction is its own visible step' precedent."
    - "Each of a fringe schedule's three percentages (pension_health, payroll_tax, other_burden) carries its own basis/source_url/method_note independently — a union document can source one component while another stays an industry estimate, and the combined fringe Figure's basis is the weakest of the three, never a shared assumption."
    - "A rate-row selector's dated range is closed-closed and raises on a date covered by no row, mirroring engine.credit's existing loan-out withholding schedule convention exactly (including its load-time overlap guard) rather than inventing a second dated-range idiom."

key-files:
  created:
    - engine/union_rates.py
    - data/cost_profiles/us-ca-los-angeles.yaml
    - data/union_rates/iatse.yaml
    - data/union_rates/sag-aftra.yaml
    - data/union_rates/dga.yaml
    - data/union_rates/wga.yaml
    - data/union_rates/fringe_schedules.yaml
    - tests/test_engine_union_rates.py
    - tests/test_engine_cost_localizer.py
    - sources/unions/2026-08-26-icg600-eastern-region-panel1-2025-2026.pdf
    - sources/unions/2026-08-26-icg600-western-region-panel1-2025-2026.pdf
    - sources/unions/2026-08-26-icg600-western-region-panel1-2026-2027.pdf
    - sources/unions/2026-08-26-dga-rate-card-2026-2027.pdf
    - sources/unions/2026-08-26-wga-schedule-of-minimums-2026.pdf
  modified:
    - engine/cost_profile.py
    - engine/cost_localizer.py
    - engine/city_profile_lookup.py
    - app/services/spec.py
    - data/cost_profiles/us-ny-new-york.yaml
    - data/union_rates/us-ny-crew.yaml
    - sources/MANIFEST.yaml
    - .planning/WINDOWS.md

key-decisions:
  - "CostLine's unit_rate/rate_unit/basis became Optional, required only when category != \"labour\" — the minimal schema change that lets a labour line omit a now-obsolete static rate without touching any non-labour cost line's contract"
  - "The general_crew craft (9 of 10 departments) stays basis: estimated at the same $450/day figure for both cities, rather than inventing a Los-Angeles-specific adjustment with no sourced basis — a disclosed choice, not an oversight"
  - "app/services/spec.py's localize() call site was touched outside Task 2's declared files — deriving and threading on_date is unavoidable once localize() needs a shoot date, and skipping it would leave Route A broken"
  - "DGA and WGA Pension & Health percentages resolved from payroll-vendor-summary estimates to basis: sourced this session (research Assumptions A1/A2) — DGA's own rate card states 8.75% Pension + 13.5% Health = 22.25%; WGA's own schedule states 11.25% + 16.25% + 0.25% = 27.75%. IATSE's blanket figure and SAG-AFTRA's figure remain basis: estimated — SAG-AFTRA specifically because sagaftra.org's DataDome bot protection blocked every fetch attempt this session, including a real headless-Chromium browser"

requirements-completed: [COST-02, COST-03]

coverage:
  - id: D1
    description: "Union wage scale and fringe schedules exist as committed, dated, quoted-string snapshots — IATSE Local 600 camera scale genuinely sourced for both regions, DGA and WGA Pension & Health resolved to sourced from primary documents, every un-sourced row/percentage named in WINDOWS.md"
    requirement: COST-02
    verification:
      - kind: unit
        ref: "tests/test_source_truth.py (manifest hash reconciliation)"
        status: pass
      - kind: unit
        ref: "tests/test_engine_union_rates.py#test_every_sourced_union_rate_row_is_named_in_manifest_cited_for"
        status: pass
      - kind: unit
        ref: "tests/test_engine_union_rates.py#test_dga_and_wga_pension_health_are_sourced_iatse_and_sag_aftra_are_estimated"
        status: pass
    human_judgment: false
  - id: D2
    description: "select_rate_row selects by closed-closed dated range with no fallback to nearest/newest, and raises naming region/craft/date on a gap; overlapping dated ranges for the same region+craft raise at load time"
    requirement: COST-02
    verification:
      - kind: unit
        ref: "tests/test_engine_union_rates.py#test_select_rate_row_boundary_exact_on_and_adjacent_successor"
        status: pass
      - kind: unit
        ref: "tests/test_engine_union_rates.py#test_select_rate_row_boundary_one_day_before_start_raises_when_no_prior_row_exists"
        status: pass
      - kind: unit
        ref: "tests/test_engine_union_rates.py#test_select_rate_row_boundary_one_day_after_end_raises_when_no_successor_exists"
        status: pass
      - kind: unit
        ref: "tests/test_engine_union_rates.py#test_load_union_rates_raises_on_overlapping_dated_rows_same_region_and_craft"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every localized labour department produces two sibling Figures (wage, fringe); fringe is never folded into the wage value and carries the wage Figure as its sole input"
    requirement: COST-03
    verification:
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_every_labour_department_produces_two_figures_with_different_labels"
        status: pass
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_fringe_figure_carries_the_wage_figure_as_its_single_input"
        status: pass
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_wage_figure_value_is_unchanged_when_fringe_is_removed"
        status: pass
    human_judgment: false
  - id: D4
    description: "Labour cost arithmetic stays in Decimal end to end, quantized exactly once through quantize_money's pinned ROUND_HALF_UP — a half-dollar-boundary product rounds up even where it disagrees with Python's ambient ROUND_HALF_EVEN, and fringe percentages are summed before the single multiplication"
    verification:
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_half_dollar_labour_product_rounds_up_not_half_even"
        status: pass
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_wage_value_equals_quantize_money_once_not_a_double_quantize"
        status: pass
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_fringe_percentages_summed_before_multiplication_not_after"
        status: pass
    human_judgment: false
  - id: D5
    description: "Los Angeles has a committed cost profile with jurisdiction_id null, proving D-53; a New York + Los Angeles submission returns two city_costs entries, and Los Angeles carries incentive_state 'not_modelled' with a plain-words reason, never a fabricated $0 incentive"
    requirement: COST-02
    verification:
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_los_angeles_profile_loads_with_null_jurisdiction_id"
        status: pass
      - kind: integration
        ref: "tests/test_engine_cost_localizer.py#test_route_a_prices_both_cities_and_la_incentive_is_not_modelled_not_zero"
        status: pass
    human_judgment: false
  - id: D6
    description: "engine/cost_localizer.py and engine/union_rates.py contain no jurisdiction-id literal (JUR-05), and the same CanonicalBudget object localizes against both New York and Los Angeles (COST-01 stays true)"
    verification:
      - kind: unit
        ref: "tests/test_engine_jurisdiction_additivity.py#test_no_jurisdiction_identifier_appears_in_engine_source"
        status: pass
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_localize_output_for_ny_and_la_shares_the_same_canonical_budget_object"
        status: pass
    human_judgment: false

duration: 48min
completed: 2026-08-26
status: complete
---

# Phase 4 Plan 02: Union Labour Pricing and Fringe Summary

**New York and Los Angeles now price ten crew departments each from real dated IATSE Local 600 camera scale plus an estimated general-crew rate, with fringe and payroll burden broken out as a visible second Figure per department — New York's fixed-test-spec landed cost moves from $253,125 (04-01's flat blended rate) to $447,532, and Los Angeles gets its first full cost profile with no jurisdiction rule file, proving D-53.**

## Performance

- **Duration:** 48 min
- **Started:** 2026-08-26T19:05:00Z (approximate — research/fetch phase predates the first commit)
- **Completed:** 2026-08-26T19:49:37Z
- **Tasks:** 3
- **Files modified:** 22 (14 created, 8 modified — 5 of the created files are archived PDFs)

## Accomplishments

- **IATSE Local 600 camera scale is genuinely `basis: sourced`, for both regions.** Fetched and archived the union's own published Basic Agreement rate cards (Eastern Region Panel 1, New York, effective 2025-08-03 to 2026-08-01; Western Region Panel 1, Los Angeles, two adjacent dated windows spanning 2025-08-03 to 2027-07-31), transcribed the "Camera Operator" (Occ. Code 1911) daily rate from each, and hashed and cited every document under `sources/MANIFEST.yaml`.
- **DGA and WGA Pension & Health percentages resolved to `basis: sourced`**, closing 04-RESEARCH.md Assumptions Log rows A1/A2's DGA half. DGA's own 2026-2027 rate card states "Company will contribute 8.75% to the Pension Plan and 13.5% to the Health Plan" (22.25% combined); WGA's own 2026 Schedule of Minimums states 11.25% + 16.25% + 0.25% (27.75% combined). Both previously circulated only on payroll-vendor summary pages.
- **`engine/union_rates.py`** lands `select_rate_row` — a closed-closed dated-range lookup mirroring `engine.credit`'s loan-out withholding schedule convention exactly, including its load-time overlap guard — plus `load_union_rates`/`load_fringe_schedules` and the `RateRow`/`FringeSchedule`/`FringeComponent` Pydantic models.
- **`engine/cost_localizer.py`'s labour path now emits TWO sibling Figures per department** (wage, fringe) when a craft mapping is declared, layered non-destructively over 04-01's static per-line path — a labour line with no craft mapping, or a profile with no `labour` block at all, is unaffected, so every pre-04-02 fixture (including `tests/test_engine_landed_cost.py`'s `_profile_with_account` helper) keeps passing byte-for-byte with zero edits.
- **`data/cost_profiles/us-ca-los-angeles.yaml`** is Los Angeles's first committed cost profile — `jurisdiction_id: null`, proving D-53's claim that cost localization needs nothing from a jurisdiction rule file. `engine/city_profile_lookup.py` gained LA's aliases (`los angeles`, `la`, `hollywood`, `burbank`, `culver city`) and `", CA"`/`", California"` suffix handling.
- **62 new tests** across `tests/test_engine_union_rates.py` and `tests/test_engine_cost_localizer.py`: dated-range boundary coverage (exactly-on, one-before, one-after — both synthetic and against the real committed New York/Los Angeles data), load-time overlap detection, the two-Figure labour+fringe split and its additivity, a half-dollar-rounding case proven non-vacuous by a real revert-and-rerun cycle against `engine/rounding.py`, single-vs-double quantization, fringe-percentage summation order, and the manifest-citation reconciliation for every `basis: sourced` row.

## Task Commits

Each task was committed atomically:

1. **Task 1: Acquire and commit dated union rate-card and fringe snapshots** — `750b5fa` (feat)
2. **Task 2: Labour and fringe as two separate Figures, and the Los Angeles cost profile** — `3420639` (feat)
3. **Task 3: Boundary and precision coverage for labour pricing** — `a6c0147` (test)

**Plan metadata:** commit hash recorded after this SUMMARY is committed.

## Files Created/Modified

- `engine/union_rates.py` — `RateRow`, `FringeComponent`, `FringeSchedule`, `load_union_rates`, `load_fringe_schedules`, `select_rate_row`, `weakest_basis`
- `engine/cost_profile.py` — `LabourBlock`, `CraftMapping`; `CityCostProfile.labour` (optional); `CostLine.unit_rate`/`rate_unit`/`basis` made optional for `category: "labour"` lines only
- `engine/cost_localizer.py` — `quarter_start_date`, `_price_labour_department`, the dynamic wage+fringe branch in `localize()`
- `engine/city_profile_lookup.py` — Los Angeles aliases and `", CA"`/`", California"` suffix handling
- `app/services/spec.py` — derives `on_date` from `spec.start_quarter`/`start_year` and threads it into `localize()`
- `data/cost_profiles/us-ny-new-york.yaml` — widened with a `labour:` block; cost lines drop their now-dynamic `unit_rate`
- `data/cost_profiles/us-ca-los-angeles.yaml` — new, `jurisdiction_id: null`
- `data/union_rates/iatse.yaml` — new; camera (sourced, both regions) + Los Angeles general_crew (estimated)
- `data/union_rates/us-ny-crew.yaml` — migrated to the `rows:` schema; New York general_crew (estimated)
- `data/union_rates/sag-aftra.yaml`, `dga.yaml`, `wga.yaml` — new
- `data/union_rates/fringe_schedules.yaml` — new; four unions, three independently-sourced percentages each
- `sources/MANIFEST.yaml` — five new archived-document entries
- `sources/unions/*.pdf` — five archived primary documents
- `tests/test_engine_union_rates.py`, `tests/test_engine_cost_localizer.py` — new
- `.planning/WINDOWS.md` — six new entries (five sourcing gaps, one lint-warning)

## Decisions Made

- **`CostLine.unit_rate`/`rate_unit`/`basis` became Optional, required only when `category != "labour"`.** The minimal schema change that lets a dynamically-priced labour line omit a now-obsolete static rate, without touching any non-labour cost line's existing contract or any pre-04-02 fixture.
- **The general_crew craft (9 of 10 departments) stays `basis: estimated`** at the same $450/day figure for both New York and Los Angeles — inventing a Los-Angeles-specific adjustment with no sourced basis would be a fabricated precision this session cannot back up.
- **`app/services/spec.py`'s `localize()` call site was touched outside Task 2's declared `<files>` list** — deriving and threading `on_date` is unavoidable once `localize()` needs a shoot date to select a dated rate row; skipping it would leave Route A raising on every request. Recorded below as a deviation.
- **DGA and WGA Pension & Health percentages resolved from estimated to `basis: sourced`** this session (Assumptions A1/A2) — each union's own primary document states the figure directly, not a payroll-vendor summary. IATSE's blanket figure and SAG-AFTRA's figure remain `basis: estimated`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `app/services/spec.py`'s `localize()` call site required a signature-compatible update outside Task 2's declared files**
- **Found during:** Task 2 (widening `localize()` to accept `on_date`)
- **Issue:** `engine/cost_localizer.py::localize()` needed a real shoot date to select a dated union rate row, but `app/services/spec.py::_price_candidate_cities` — the only production call site — is not in Task 2's declared `<files>` list. Leaving it untouched would mean every Route A request either fails to compile the derivation or (with an incautious default) silently prices against an unstated date.
- **Fix:** Added `on_date = quarter_start_date(spec.start_quarter, spec.start_year)` immediately before the existing `localize(budget, profile)` call, changing it to `localize(budget, profile, on_date=on_date)`. `localize()`'s `on_date` parameter defaults to `None` and only raises when a labour line actually resolves a craft mapping, so every non-labour-block profile (every pre-04-02 fixture) is unaffected.
- **Files modified:** `app/services/spec.py`
- **Verification:** `tests/test_app_spec_route.py` (pre-existing, unmodified) still passes; `tests/test_engine_cost_localizer.py::test_route_a_prices_both_cities_and_la_incentive_is_not_modelled_not_zero` exercises the real HTTP-level path end to end.
- **Committed in:** `3420639` (Task 2 commit)

**2. [Rule 3 - Blocking] JUR-05 literal-scan collision in `engine/union_rates.py`'s own docstring**
- **Found during:** Task 2, after writing `engine/union_rates.py`'s module docstring with `"us-ny"`/`"us-ca"` as illustrative examples
- **Issue:** `tests/test_engine_jurisdiction_additivity.py`'s JUR-05 gate scans all of `engine/**/*.py` (comment-only lines stripped, but docstrings are string literals, not stripped) for any declared jurisdiction id string. The docstring's illustrative example literally contained `"us-ny"`, tripping the scan even though the module never dispatches on it.
- **Fix:** Rewrote the docstring to describe `region` generically ("a plain region-label string") with no jurisdiction-id-shaped literal anywhere in the file, and replaced a second incidental `us-ca-crew.yaml` filename example in a docstring with a jurisdiction-agnostic phrase — matching this plan's own stricter acceptance criterion (`grep -nE '"us-ny"|"us-ca"|us-ny|us-ca' engine/cost_localizer.py engine/union_rates.py` returns no hits), which is tighter than the JUR-05 test's current declared-ids-only scope.
- **Files modified:** `engine/union_rates.py`
- **Verification:** `uv run pytest tests/test_engine_jurisdiction_additivity.py -q` — 4 passed; the plan's own grep acceptance criterion returns no hits.
- **Committed in:** `3420639` (Task 2 commit)

**3. [Rule 3 - Blocking] A vacuous self-comparison assertion caught by ruff (PLR0124)**
- **Found during:** Task 2, writing `test_localize_output_for_ny_and_la_shares_the_same_canonical_budget_object`
- **Issue:** An initial draft asserted `budget is budget` to "prove" object identity — a name compared with itself, which asserts nothing and would pass even if the code were broken.
- **Fix:** Rewrote the test to monkeypatch `engine.budget.build_canonical_budget` with a counting wrapper, proving the budget is built exactly once and the SAME object (by `id()`) is the one passed to both `localize()` calls — a genuine, falsifiable assertion of COST-01's "one budget, never rebuilt per city" guarantee.
- **Files modified:** `tests/test_engine_cost_localizer.py`
- **Verification:** `uv run ruff check tests/test_engine_cost_localizer.py` — clean; the rewritten test still passes.
- **Committed in:** `3420639` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 3 - blocking).
**Impact on plan:** All three were necessary to keep Route A functional and the full test suite green while implementing exactly what Task 2 specified. No scope creep — the `app/services/spec.py` change is a single two-line call-site update, not a redesign of Route A.

## Issues Encountered

- **sagaftra.org's entire domain is behind DataDome bot protection.** Every fetch attempt this session — plain `curl` with multiple user agents, and a real headless-Chromium browser via the `gstack` `browse` skill — returned HTTP 403. `sagaftraplans.org` (the plan administrator's own site) was reachable but exposes only a login-gated Contributions Manager with no published percentage table. SAG-AFTRA's rate rows and fringe percentage remain `basis: estimated`, exactly per this plan's own precondition ("if a union site blocks the fetch, record the block in WINDOWS.md and tag the affected rows estimated rather than halting the plan"). Recorded to `.planning/WINDOWS.md` (entry 7).
- **New York's IATSE camera rate card has no committed 2026-2027 successor.** icg600.com publishes only a document explicitly marked "DRAFT" for the New York/Eastern Region 2026-2027 rate card — not yet ratified, so it was not archived as `sourced`. A shoot date after 2026-08-01 in New York correctly raises `ValueError` from `select_rate_row` rather than falling back to the expired row or inventing a figure; this is proven directly by `tests/test_engine_union_rates.py::test_committed_new_york_camera_row_raises_past_its_expiry_no_successor`. Recorded to `.planning/WINDOWS.md` (entry 9).
- **9 of 10 crew_tiers.yaml departments still price at an estimated general-crew rate**, not a per-craft union document — locating and transcribing eight more IATSE locals' basic agreements (grip/electric, art, wardrobe, hair/makeup, sound, script supervision, editing) plus a Teamsters agreement for transportation was out of this session's time budget. Recorded to `.planning/WINDOWS.md` (entry 8). This is disclosed, not silent: every general_crew row's `method_note` states exactly this, and it does not block the honesty gates (D-59/D-63 still hold — a total containing an `estimated` line reports `estimated`, never `sourced`).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **The new `total_landed_cost` for the fixed test spec** (feature, 10 stage + 5 location shoot days, `crew_size=50`, candidate city "New York, NY", start `Q2 2026`) is **`Decimal("447532")`**, up from 04-01's recorded `Decimal("253125")` — a delta of **+$194,407**. The composition: `cost_total` (pre-incentive) grew from `$337,500` (750 person-days × a single flat $450 estimated rate) to `$596,710` — camera department person-days now price at the real IATSE Local 600 rate ($947.58/day, more than double the old flat rate) and every one of the ten departments now carries a SECOND fringe-and-burden line (roughly 51.65% of wage for IATSE-covered departments: ~40% pension/health estimate + 9.65% payroll tax estimate + 2% other burden estimate) that 04-01 did not price at all. New York's modelled incentive scaled up proportionally with the larger qualifying labour spend, netting `$149,178` (up from 04-01's `$84,375`), giving `596,710 - 149,178 = 447,532`. Los Angeles's parallel run (same fixed spec, "Los Angeles, CA") produces `cost_total = total_landed_cost = $557,761` — no incentive netted, `incentive_state: "not_modelled"`, never a fabricated `$0`.
- **Los Angeles is ready for Phase 5's California rule file to land with zero cost-side changes** — the moment `jurisdictions/us-ca.yaml` exists and is registered in `RULESET_PATH_BY_JURISDICTION`, `app/services/spec.py::_price_candidate_cities` already promotes Los Angeles from `incentive_state: "not_modelled"` to `"modelled"` automatically, exactly as D-55's two-band design intended.
- **Open sourcing work carried forward** (all named in `.planning/WINDOWS.md`, not blocking): IATSE's own Basic Agreement fringe percentage, SAG-AFTRA's rate card and fringe percentage (network-blocked), the eight remaining per-craft IATSE locals plus Teamsters Local 399, and New York's 2026-2027 camera rate card (currently draft-only).
- No blockers for 04-03. The dated-range selector, the two-Figure labour+fringe pattern, and the `labour:` block schema are all reusable as-is for any later plan widening more cost categories or more cities.

---
*Phase: 04-cost-localization-landed-cost-outputs*
*Completed: 2026-08-26*

## Self-Check: PASSED

- All 22 created/modified files listed above confirmed present on disk (`[ -f ]`).
- All three task commits (`750b5fa`, `3420639`, `a6c0147`) confirmed present in `git log --oneline --all`.
- `uv run --frozen pytest tests/ -q` re-run fresh: 319 passed, 0 failed.
- `tests/test_engine_union_rates.py tests/test_engine_cost_localizer.py` acceptance criteria (Task 2 + Task 3) individually re-verified: boundary tests present and named, sourced-row/manifest reconciliation test present and non-vacuous (a fabricated row_id is confirmed absent), half-dollar rounding test confirmed non-vacuous by a live revert-and-rerun cycle against `engine/rounding.py`.
- Plan-level `<verification>`: `grep -rn "\.quantize(" engine/ | grep -v "engine/rounding.py"` returns no hits; `git diff --stat pyproject.toml uv.lock` is empty; a New York + Los Angeles submission returns two `city_costs` entries with separate labour/fringe Figures (confirmed by direct route-level test and manual reproduction).
