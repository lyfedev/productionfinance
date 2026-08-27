---
phase: 04-cost-localization-landed-cost-outputs
plan: 04
subsystem: cost-localization
tags: [facilities, exemptions, cost-06, inc-10, basis, low-bound-pricing, stackable-reductions]

requires:
  - phase: 04-cost-localization-landed-cost-outputs
    provides: "04-01's Figure.basis provenance axis and CityCostProfile schema; 04-02's dynamic labour+fringe pricing; 04-03's Figure.caveat, travel-category dispatch shape, and the not_priced measurement this plan finally empties"
provides:
  - "engine.facilities.FacilitiesTable/FacilitiesEntry/load_facilities/facilities_lines (COST-06) — the five never-sourced cost categories (stages, equipment, permits, locations, trucking), schema-rejected from ever claiming basis: sourced, priced at the LOW BOUND of a disclosed range uniformly across both committed cities"
  - "engine.exemptions.ExemptionsTable/ExemptionEntry/load_exemptions/exemption_reductions (INC-10, D-76) — stackable sales-tax/hotel-occupancy cost reductions matched to a cost line by category, appended to LocalizedBudget.lines, structurally unreachable from price_jurisdiction's incentive DAG"
  - "engine.cost_profile.CityCostProfile.facilities_id/.exemptions_id — the two new profile-level selectors, None-able exactly like labour/travel"
  - "engine.cost_localizer.localize's widened dispatch: a facilities-category cost line prices dynamically from the shoot calendar's day counts when facilities_id is declared; an exemptions_id, when declared, appends every matched reduction Figure after every other line is priced"
  - "Committed data/facilities/{us-ny-new-york,us-ca-los-angeles}.yaml and data/tax_exemptions/{us-ny-new-york,us-ca-los-angeles}.yaml"
  - "Both committed cost profiles now price all ten COST_CATEGORIES — not_priced is empty for New York and Los Angeles, and both cities' total_landed_cost reports basis: modelling_assumption"
affects: [04-05, 04-06, 04-07, "Phase 6 (interface renders the emptied not_priced list and the exemption reduction lines)", "Phase 8 (proof panel re-walks the now-larger Figure DAG, including facilities and exemption nodes)"]

actuals:
  tokens: 21053
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "A committed reference table's id-to-path lookup is built by GLOBBING the data directory and reading each file's own declared id, never a Python dict literal — engine.facilities.FACILITIES_PATH_BY_ID and engine.exemptions.EXEMPTIONS_PATH_BY_ID both follow engine.per_diem.PER_DIEM_PATH_BY_ID's exact convention, avoiding the JUR-05 substring-scan collision a literal dict of city_id-shaped strings would trip."
    - "A category priced from a disclosed [low, high] range with no standardized public rate card applies the LOW BOUND uniformly, never the midpoint — the disclosed upper bound is stated in every Figure's derivation instead of being silently dropped (04-RESEARCH.md row A5)."
    - "A stackable cost reduction is matched to its target cost line by CostCategory string equality (Figure.label == CostLine.label), never a positional index — and is appended to LocalizedBudget.lines as a first-class Figure with the matched target as its single `inputs` entry, so it enters the same summation every other cost line uses without ever being passed to price_jurisdiction."
    - "engine/cost_profile.py's _DYNAMICALLY_PRICED_CATEGORIES tuple is the single switch a category flips to move from the static per-line unit_rate path to a profile-block-driven dynamic path (labour -> travel -> facilities, three plans running) — each addition is a pure widening, never a rewrite of the dispatch shape itself."

key-files:
  created:
    - engine/facilities.py
    - engine/exemptions.py
    - data/facilities/us-ny-new-york.yaml
    - data/facilities/us-ca-los-angeles.yaml
    - data/tax_exemptions/us-ny-new-york.yaml
    - data/tax_exemptions/us-ca-los-angeles.yaml
    - tests/test_engine_facilities.py
    - tests/test_engine_exemptions.py
  modified:
    - engine/cost_profile.py
    - engine/cost_localizer.py
    - data/cost_profiles/us-ny-new-york.yaml
    - data/cost_profiles/us-ca-los-angeles.yaml
    - tests/test_engine_cost_localizer.py
    - tests/test_app_spec_route.py
    - .planning/WINDOWS.md

key-decisions:
  - "Low-bound pricing treatment chosen uniformly over the midpoint for all five facilities categories in both cities — see 'Pricing Treatment' section below for the full stated rationale."
  - "All ten facilities entries and both exemption entries are basis: estimated or modelling_assumption, never sourced — this executor session had no live document-fetch tool (no WebFetch/WebSearch) available, so even the categories most likely to carry a genuine anchor (a city permit-fee schedule, NY's sales-tax exemption, LA's TOT exemption) could not be independently fetched and archived. Recorded honestly to .planning/WINDOWS.md rather than fabricating a source_url or anchor_note."
  - "engine.facilities.FACILITIES_PATH_BY_ID and engine.exemptions.EXEMPTIONS_PATH_BY_ID are glob-discovered, not Python dict literals — following 04-03's engine.per_diem precedent exactly, this avoids the JUR-05 substring-scan collision a literal id-to-path dict would trip on committed ids like the ones this project's own filename convention produces."
  - "engine/cost_profile.py's _DYNAMICALLY_PRICED_CATEGORIES was widened to include all five facilities categories (Rule 3 — blocking issue): the committed cost-profile facilities lines omit unit_rate/rate_unit/basis by design (priced dynamically), and the pre-existing validator required those three fields for any category not already on the dynamic list."
  - "Task 2's combined_basis assertion (both cities' total_landed_cost.basis == 'modelling_assumption') and the not_priced-measurement-not-claim test both landed in tests/test_engine_cost_localizer.py rather than tests/test_engine_landed_cost.py — the committed real profiles these assertions need (not a synthetic single-line fixture) already live in test_engine_cost_localizer.py's helper functions (_ny_profile/_la_profile), so no code changes were needed in engine/landed_cost.py or its test file for this plan."
  - "Commits are grouped as Task 1 alone (facilities schema, self-contained) plus Task 2+3 combined (facilities wiring and INC-10 exemptions), rather than three separate commits — engine/cost_localizer.py's facilities-dispatch and exemption-dispatch code was written in the same file in immediate succession, and splitting it into two commits would have left the Task-2-only commit importing engine.exemptions before that module existed, breaking per-commit buildability. Both actual commits pass the full test suite independently."

requirements-completed: [COST-06, INC-10]

coverage:
  - id: D1
    description: "Stage, equipment, permit, location and trucking costs are all priced for both committed cities, and every one of them is labelled estimated or modelling_assumption — never sourced (COST-06)"
    requirement: COST-06
    verification:
      - kind: unit
        ref: "tests/test_engine_facilities.py#test_loading_a_facilities_entry_with_basis_sourced_raises_naming_cost06"
        status: pass
      - kind: unit
        ref: "tests/test_engine_facilities.py#test_both_committed_facilities_tables_load_with_all_five_categories"
        status: pass
      - kind: integration
        ref: "tests/test_engine_cost_localizer.py#test_both_committed_profiles_not_priced_is_now_empty"
        status: pass
    human_judgment: false
  - id: D2
    description: "A facilities figure derived from a disclosed range states the low bound, the high bound, that the low-bound treatment was taken, and names the driving shoot-day count — never a hidden point estimate"
    requirement: COST-06
    verification:
      - kind: unit
        ref: "tests/test_engine_facilities.py#test_low_bound_treatment_and_derivation_states_both_bounds"
        status: pass
      - kind: unit
        ref: "tests/test_engine_facilities.py#test_stages_is_driven_by_stage_shoot_days_only"
        status: pass
      - kind: unit
        ref: "tests/test_engine_facilities.py#test_locations_and_permits_are_driven_by_location_shoot_days_only"
        status: pass
      - kind: unit
        ref: "tests/test_engine_facilities.py#test_equipment_and_trucking_are_driven_by_total_shoot_days_only"
        status: pass
    human_judgment: false
  - id: D3
    description: "not_priced is empty for both New York and Los Angeles after this plan, is a genuine measurement (not a hardcoded claim), and permanent_exclusions still names all six D-60 items"
    requirement: COST-06
    verification:
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_both_committed_profiles_not_priced_is_now_empty"
        status: pass
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_removing_a_facilities_category_reintroduces_it_to_not_priced"
        status: pass
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_both_committed_profiles_total_landed_cost_basis_is_modelling_assumption"
        status: pass
    human_judgment: false
  - id: D4
    description: "Sales-tax and hotel-occupancy exemptions appear as their own named, stackable, cost-reduction Figures attached to the cost line they reduce — New York against Equipment, Los Angeles against Housing (INC-10, D-76)"
    requirement: INC-10
    verification:
      - kind: unit
        ref: "tests/test_engine_exemptions.py#test_reduction_value_is_negative_rate_times_target_pre_reduction_value"
        status: pass
      - kind: unit
        ref: "tests/test_engine_exemptions.py#test_two_exemptions_same_category_both_appear_as_separate_figures"
        status: pass
      - kind: integration
        ref: "tests/test_engine_exemptions.py#test_both_committed_exemptions_tables_load"
        status: pass
    human_judgment: false
  - id: D5
    description: "An exemption Figure is never reachable from the incentive Figure DAG price_jurisdiction returns, and the gross credit is never greater with exemptions present than without (D-76's structural guarantee)"
    requirement: INC-10
    verification:
      - kind: integration
        ref: "tests/test_engine_exemptions.py#test_exemption_figure_ids_are_disjoint_from_the_incentive_dag"
        status: pass
      - kind: integration
        ref: "tests/test_engine_exemptions.py#test_gross_credit_is_never_greater_with_exemptions_than_without"
        status: pass
      - kind: integration
        ref: "tests/test_engine_exemptions.py#test_cost_total_delta_equals_the_summed_reduction_amount_exactly"
        status: pass
      - kind: unit
        ref: "tests/test_engine_exemptions.py#test_exemption_matching_absent_category_raises_naming_exemption_id"
        status: pass
    human_judgment: false
  - id: D6
    description: "No jurisdiction id string appears in engine/facilities.py, engine/exemptions.py or engine/cost_localizer.py's dispatch code (JUR-05/D-53), and no new .quantize() call site or new runtime dependency was introduced"
    verification:
      - kind: unit
        ref: "tests/test_engine_jurisdiction_additivity.py::test_no_jurisdiction_identifier_appears_in_engine_source (repo-wide gate, unmodified, green)"
        status: pass
      - kind: unit
        ref: "tests/test_engine_facilities.py#test_no_jurisdiction_id_literal_in_facilities_module"
        status: pass
      - kind: unit
        ref: "tests/test_engine_exemptions.py#test_no_jurisdiction_id_literal_in_exemptions_module"
        status: pass
      - kind: other
        ref: "grep -rn '\\.quantize(' engine/ | grep -v engine/rounding.py -- returns no hits; git diff --stat pyproject.toml uv.lock -- empty"
        status: pass
    human_judgment: false

duration: 24min
completed: 2026-08-27
status: complete
---

# Phase 4 Plan 04: Facilities and Tax Exemptions — Cost-Side Honesty for the Never-Sourced Categories Summary

**The last five cost categories (stages, equipment, permits, locations, trucking) now price for both committed cities at the low bound of a disclosed range, schema-enforced to never claim `basis: sourced`; New York and Los Angeles each gain one stackable tax exemption that reduces a cost line and is structurally proven unreachable from the incentive figure — `not_priced` is now empty for both cities and both totals report `basis: modelling_assumption`.**

## Performance

- **Duration:** ~24 min
- **Started:** 2026-08-26T23:46:00Z (approximate)
- **Completed:** 2026-08-27T00:10:00Z
- **Tasks:** 3
- **Files modified:** 15 (8 created, 7 modified)

## Accomplishments

- **`engine/facilities.py`** — `FacilitiesTable`/`FacilitiesEntry`, glob-discovered `FACILITIES_PATH_BY_ID` (mirroring `engine.per_diem`'s exact convention to avoid the JUR-05 substring-scan collision a literal dict of city-shaped ids would trip), and `facilities_lines()`. A Pydantic validator rejects `basis: "sourced"` outright with a message naming COST-06 — the structural guarantee the plan required, not a review convention.
- **Committed `data/facilities/{us-ny-new-york,us-ca-los-angeles}.yaml`** — all five categories, every entry `basis: "modelling_assumption"` (see Decisions below for why none reached `basis: "estimated"` with a named anchor this session).
- **`engine/exemptions.py`** — `ExemptionsTable`/`ExemptionEntry`, glob-discovered `EXEMPTIONS_PATH_BY_ID`, and `exemption_reductions()`. Matching is by `applies_to_category` string equality against the closed `CostCategory` vocabulary, never a positional index; an unmatched or ambiguous category raises naming the exemption id.
- **Committed `data/tax_exemptions/{us-ny-new-york,us-ca-los-angeles}.yaml`** — New York's sales-tax exemption on production equipment (against the Equipment line) and Los Angeles's 30-night extended-stay hotel-occupancy exemption (against the Housing line), both `basis: "estimated"`.
- **`engine/cost_localizer.py::localize()`** widened: a facilities-category cost line prices dynamically from the shoot calendar's day counts (stage/location/total, per Task 2's explicit mapping) exactly mirroring the travel-category dispatch shape; when a profile declares `exemptions_id`, every matched reduction is appended to `LocalizedBudget.lines` after every other line is priced.
- **`not_priced` is now empty for both New York and Los Angeles** — every one of the ten `COST_CATEGORIES` is genuinely priced. A new test proves this is a measurement, not a claim: removing one category from a real committed profile makes it reappear in `not_priced`.
- **Both cities' `total_landed_cost.basis` now reports `"modelling_assumption"`** — the weakest tier across all ten categories, correctly propagated by the pre-existing `combined_basis` weakest-wins logic with zero code changes needed there.
- **D-76's four guarantees are proven as tests, against the real committed New York data**, not just a synthetic fixture: exemption Figure ids are disjoint from `price_jurisdiction`'s returned incentive DAG; the gross credit is strictly lower with the exemption present than without; the cost-total delta equals the summed reduction exactly; and an exemption naming an absent category raises rather than being silently dropped.
- **34 new tests** across `tests/test_engine_facilities.py` (19) and `tests/test_engine_exemptions.py` (15), plus updates to 3 pre-existing tests in `tests/test_engine_cost_localizer.py` and `tests/test_app_spec_route.py` whose expected values changed as a direct, correct consequence of `not_priced` emptying and the weakest-basis shift.

## Task Commits

Each task was committed atomically (Tasks 2 and 3 combined into one commit — see Decisions below for why):

1. **Task 1: Facilities reference tables, non-sourced by schema** — `cf929cd` (feat)
2. **Task 2 + Task 3: Wire facilities into the localized budget, empty not_priced, and land INC-10 exemptions** — `8bc9a19` (feat)

**Plan metadata:** commit hash recorded after this SUMMARY is committed.

## Pricing Treatment — Low Bound, Chosen Uniformly

Research row A5 flagged this phase's facilities anchors as individual marketing listings with no standardization (a $19/hr equipment-rental listing next to a $3,500/shoot-day standing-set rate, neither representative). The plan required choosing ONE treatment — midpoint or low bound — and applying it uniformly across all five categories in both cities.

**Low bound was chosen**, for three reasons:
1. A midpoint between two arbitrary, wildly-variable marketing numbers is not meaningfully more "central" than either endpoint — averaging noise does not produce signal.
2. A low-bound figure reads honestly as a floor a producer should expect to exceed, rather than implying a single best-guess point estimate the range itself disclaims.
3. It is the more conservative choice for a landed-cost comparison tool whose stated purpose is catching cases where a naive headline number understates the true cost (PROJECT.md's own thesis) — a low-bound facilities figure is less likely to be read as "the number," since the disclosed upper bound sits directly in the same Figure's derivation.

Every facilities Figure's derivation states the low bound used, the disclosed high bound, and that the low-bound treatment was applied uniformly.

## Sourcing Gap — Why Nothing Here Reached `basis: "estimated"` With a Named Anchor

The plan's own preferred path was `basis: "estimated"` with a named anchor wherever a defensible public reference point exists (a specific studio's published day rate, a city film office's published permit fee schedule). This executor session had **no live document-fetch tool available** (no WebFetch or WebSearch tool in the harness) — every prior plan in this phase that reached `basis: "sourced"` did so via a direct `curl`/API fetch performed in a session that had that capability. Rather than fabricate a `source_url` or `anchor_note` pointing at a document never actually retrieved this session, every facilities and exemption entry is honestly tagged `basis: "modelling_assumption"` or `basis: "estimated"` (informed by disclosed general industry/tax knowledge, not a verified primary document) and the gap is recorded in `.planning/WINDOWS.md` (entries 15–16) rather than presented as more sourced than it is. This is the honest outcome the plan's own fallback instruction anticipated ("If you cannot obtain the primary document, tag estimated and record the gap").

## Files Created/Modified

- `engine/facilities.py` — new; `FacilitiesTable`, `FacilitiesEntry`, `load_facilities`, `facilities_lines`, glob-discovered `FACILITIES_PATH_BY_ID`
- `engine/exemptions.py` — new; `ExemptionsTable`, `ExemptionEntry`, `load_exemptions`, `exemption_reductions`, glob-discovered `EXEMPTIONS_PATH_BY_ID`
- `engine/cost_profile.py` — `_DYNAMICALLY_PRICED_CATEGORIES` widened to the five facilities categories; `CityCostProfile.facilities_id`/`.exemptions_id`
- `engine/cost_localizer.py` — `localize()` widened with a facilities-category dispatch branch (mirroring travel) and post-loop exemption wiring
- `data/facilities/us-ny-new-york.yaml`, `us-ca-los-angeles.yaml` — new, all `basis: "modelling_assumption"`
- `data/tax_exemptions/us-ny-new-york.yaml`, `us-ca-los-angeles.yaml` — new, both `basis: "estimated"`
- `data/cost_profiles/us-ny-new-york.yaml`, `us-ca-los-angeles.yaml` — `facilities_id`/`exemptions_id` fields, five new facilities cost lines each
- `tests/test_engine_facilities.py`, `tests/test_engine_exemptions.py` — new
- `tests/test_engine_cost_localizer.py` — `not_priced`-empty test (replacing the five-category expectation), the new basis-is-modelling_assumption test, the category-removal-reintroduces-it-to-not_priced test, and an updated line-count assertion (23 → 29)
- `tests/test_app_spec_route.py` — updated `cost_total.basis` expectation (`"estimated"` → `"modelling_assumption"`)
- `.planning/WINDOWS.md` — three new entries (facilities sourcing gap, exemptions sourcing gap, lint-warning delta)

## Decisions Made

See `key-decisions` in the frontmatter for the full list. The two most consequential:

- **Low-bound pricing treatment, uniform across every facilities category and both cities** — see the dedicated section above.
- **No facilities or exemption entry reached `basis: "estimated"` with a named public anchor** because this session had no live document-fetch tool — recorded honestly to `.planning/WINDOWS.md` rather than fabricated.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `engine/cost_profile.py`'s `_DYNAMICALLY_PRICED_CATEGORIES` required widening**
- **Found during:** Task 1, immediately after writing the committed facilities cost lines
- **Issue:** The five facilities cost lines in `data/cost_profiles/*.yaml` omit `unit_rate`/`rate_unit`/`basis` by design (priced dynamically through `facilities_id`, exactly like travel and labour before them) — but `CostLine`'s pre-existing validator required all three fields for any category not already on the dynamic-pricing list, which at the time only named `labour`, `housing`, `per_diem`, `flights`.
- **Fix:** Widened `_DYNAMICALLY_PRICED_CATEGORIES` to add `stages`, `equipment`, `permits`, `locations`, `trucking` — the exact widening the plan's own artifact list implies but does not spell out as a required code change.
- **Files modified:** `engine/cost_profile.py`
- **Verification:** `uv run pytest tests/test_engine_cost_profile.py tests/test_engine_facilities.py -q` — all pass; both committed profiles load without error.
- **Committed in:** `cf929cd` (Task 1 commit)

**2. [Rule 3 - Blocking] Three pre-existing tests required updating for the correct, plan-required behavior change**
- **Found during:** Task 2, after wiring facilities into `localize()`
- **Issue:** `tests/test_engine_cost_localizer.py::test_every_labour_department_produces_two_figures_with_different_labels` asserted a fixed line count (23) that necessarily grew once five facilities lines plus one exemption reduction were added (29); `tests/test_engine_cost_localizer.py::test_both_committed_profiles_not_priced_names_only_five_facilities_categories` asserted the OLD (pre-this-plan) `not_priced` set, which the plan explicitly requires to become empty; `tests/test_app_spec_route.py`'s Route A test asserted `cost_total.basis == "estimated"`, which correctly becomes `"modelling_assumption"` once the weakest-tier facilities lines are the weakest input in the combined-basis calculation (exactly Task 2's own stated acceptance criterion).
- **Fix:** Updated all three assertions to the new, plan-required values; renamed the `not_priced` test to `test_both_committed_profiles_not_priced_is_now_empty` and added two new tests (`test_both_committed_profiles_total_landed_cost_basis_is_modelling_assumption`, `test_removing_a_facilities_category_reintroduces_it_to_not_priced`) to prove the new behavior is measured, not asserted.
- **Files modified:** `tests/test_engine_cost_localizer.py`, `tests/test_app_spec_route.py`
- **Verification:** `uv run --frozen pytest tests/ -q` — 398 passed, 0 failed.
- **Committed in:** `8bc9a19` (Task 2+3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking issues necessary to keep the full test suite green while implementing exactly what the plan specified). No scope creep.

## Issues Encountered

- **No live document-fetch tool was available this executor session** (no WebFetch/WebSearch tool in the harness), unlike prior plans in this phase that fetched and archived primary documents directly (GSA per-diem bulk file, IATSE/DGA/WGA rate cards, in 04-02/04-03). This meant every facilities and exemption entry stayed at `basis: "estimated"` or `"modelling_assumption"` rather than reaching `basis: "sourced"` or a named-anchor `"estimated"` for the categories most likely to carry a genuine public reference (permit fee schedules, NY's sales-tax exemption, LA's TOT exemption). Recorded honestly to `.planning/WINDOWS.md` (entries 15–16) rather than routed around with a fabricated citation.
- **Repo-wide ruff baseline grew from 343 to 394** (net +51) from this plan's new files — the same pre-existing FURB157/ISC004 patterns already tracked across the repo (entries 2, 10, 11, 14), not a new category. Out of scope per the executor scope-boundary rule; recorded to `.planning/WINDOWS.md` (entry 17).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **The new `cost_total` (pre-incentive) for the fixed test spec** (feature, 10 stage + 5 location shoot days, `crew_size=50`, 10 imported crew + 1 imported principal cast, "New York, NY", start Q2 2026): `$758,427` (facilities add `$73,000` across the five categories; the sales-tax exemption reduces Equipment by `$2,396`; `total_landed_cost` after New York's modelled incentive is `$758,427` less the priced credit).
- **`not_priced` is empty for both New York and Los Angeles** — every one of the ten `COST_CATEGORIES` this project's canonical vocabulary declares is now genuinely priced by both committed cost profiles. `permanent_exclusions` is unchanged and still names all six D-60 acknowledged gaps (overtime, turnaround penalties, meal penalties, kit fees, non-union local differentials, negotiated hotel rates).
- **Both cities' `total_landed_cost.basis` reports `"modelling_assumption"`** — the honest weakest-tier consequence of adding facilities lines, correctly propagated with zero changes needed to `engine/landed_cost.py`'s existing `combined_basis` call.
- **`FacilitiesTable`/`ExemptionsTable` and their glob-discovery pattern are reusable as-is** for any later plan widening more cities — a new committed YAML file under `data/facilities/` or `data/tax_exemptions/` with its own declared id is automatically discovered, no code change required.
- **Ready for 04-05 (currency/FX) and 04-06/04-07 (ranker/gap/sensitivity)** — this plan closes the last cost-side seam CONTEXT.md's phase boundary named; the ten-category budget is now genuinely complete for both floor cities, which is the structural precondition the ranker and gap decomposer both need.
- No blockers for 04-05.

---
*Phase: 04-cost-localization-landed-cost-outputs*
*Completed: 2026-08-27*

## Self-Check: PASSED

- All 8 created files confirmed present on disk (`[ -f ]`): `engine/facilities.py`, `engine/exemptions.py`, `data/facilities/us-ny-new-york.yaml`, `data/facilities/us-ca-los-angeles.yaml`, `data/tax_exemptions/us-ny-new-york.yaml`, `data/tax_exemptions/us-ca-los-angeles.yaml`, `tests/test_engine_facilities.py`, `tests/test_engine_exemptions.py`.
- Both task commits (`cf929cd`, `8bc9a19`) confirmed present in `git log --oneline --all`.
- `uv run --frozen pytest tests/ -q` re-run fresh: 398 passed, 0 failed (baseline was 362; +36 new tests, +2 updated pre-existing assertions net zero count change... actually net +34 from new files plus the 2 new tests added inline in test_engine_cost_localizer.py, totaling +36 over the 362 baseline).
- Plan-level `<verification>`: `grep -rn "\.quantize(" engine/ | grep -v "engine/rounding.py"` returns no hits; `git diff --stat pyproject.toml uv.lock` is empty; both city profiles' `not_priced` confirmed empty; both cities' `total_landed_cost.basis` confirmed `"modelling_assumption"`; no facilities entry loads with `basis: "sourced"` (schema-enforced); `permanent_exclusions` confirmed to still name all six D-60 items.
- Task-level acceptance criteria re-verified individually: `grep -nE '"us-ny"|"us-ca"' engine/facilities.py engine/exemptions.py engine/cost_localizer.py` returns no hits; the repo-wide JUR-05 gate (`tests/test_engine_jurisdiction_additivity.py`) passes unmodified; D-76's four proof points (disjoint DAG, never-greater credit, exact cost-total delta, raise-on-absent-category) all pass against the real committed New York data.
