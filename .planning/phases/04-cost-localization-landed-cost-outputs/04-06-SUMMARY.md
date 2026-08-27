---
phase: 04-cost-localization-landed-cost-outputs
plan: 06
subsystem: cost-localization
tags: [ranker, gap-decomposition, golden-test, d-55, d-56, d-75, d-78, out-01, out-02]

requires:
  - phase: 04-cost-localization-landed-cost-outputs
    provides: "04-01's basis provenance axis, CityCostProfile schema, landed_cost.aggregate; 04-02/04-03/04-04's full ten-category pricing (labour, fringe, housing, per_diem, flights, stages, equipment, permits, locations, trucking) plus INC-10 exemptions; 04-05's engine.fx, aggregate(..., reporting_currency=), and London as the third floor city"
provides:
  - "engine.ranker — RankedCity, rank(): the two-band ranked list (OUT-01, D-55). A city enters net_ranked only when a committed rule file exists AND price_jurisdiction succeeds; every other city enters incentive_not_modelled carrying its cost-only total, never a fabricated $0 (D-56). rank() REQUIRES reporting_currency — bands never sort a raw GBP number against a raw USD one."
  - "engine.gap — GapDecomposition, decompose_gap(), largest_component(): component-by-component gap decomposition matched by cost-line label (OUT-02), a first-class Currency component when either city required an FX conversion (D-75), and a fold step that absorbs a city-specific INC-10 exemption reduction into the cost line it targets before matching (a real discovery this plan made and fixed)."
  - "tests/test_golden_cost.py — exact Decimal totals for New York ($758,427), Los Angeles ($693,521) and London (£548,595 / $747,735), the New York vs Los Angeles headline gap ($64,906) and every component, all independently hand-derived from the committed data files before the pipeline was ever run against them (D-78). Non-vacuity proven by perturbing a committed IATSE rate by one unit in memory."
  - "app/services/spec.py::SpecResult.ranked_cities/.gap — Route A's headline outputs, reachable over HTTP as two separate JSON keys (net_ranked_cities/incentive_not_modelled_cities) plus a gap object."
affects: ["Phase 6 (interface renders the two bands and the gap table)", "Phase 8 (proof panel walks RankedCity/GapDecomposition Figure trees)", "Phase 10 (published index reuses rank()/decompose_gap() on the reference production)"]

actuals:
  tokens: 26024
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Two-band ranked list, sorted independently and concatenated (ranked band first) — never a single merged sort, mirroring engine.net_cash.transferable's refuse-rather-than-invent shape for the unranked branch."
    - "Gap components computed at FACE VALUE (before FX conversion) so the entire currency effect lands on one dedicated 'Currency' component — engine.gap._conversion_effect / _fold_reductions_into_targets — keeping 'sum of components == headline' an exact identity by construction rather than a coincidence."
    - "A stackable cost reduction (INC-10 exemption) is identified structurally for gap-matching purposes — by its negative value and its inputs[0] target reference — never by sniffing its label text. This is what let two cities with genuinely DIFFERENT exemption types (NY: sales tax on equipment; LA: hotel occupancy tax on housing) still match on the ten real cost categories."
    - "A golden CI test derives its expected values by hand from the raw committed data files BEFORE running the pipeline, records the arithmetic beside each assertion, and proves non-vacuity with an in-memory (monkeypatch, auto-reverted) rate perturbation — never a snapshot of whatever the code currently outputs."

key-files:
  created:
    - engine/ranker.py
    - engine/gap.py
    - tests/test_engine_ranker.py
    - tests/test_engine_gap.py
    - tests/test_golden_cost.py
    - tests/fixtures/cost_profiles/synthetic-ranked.yaml
    - tests/fixtures/cost_profiles/synthetic-unranked.yaml
  modified:
    - app/services/spec.py
    - app/routers/spec.py
    - app/templates/spec_result.html
    - tests/test_app_spec_route.py
    - tests/test_route_a_basis_walk.py
    - tests/test_engine_cost_localizer.py
    - .planning/WINDOWS.md

key-decisions:
  - "rank() takes reporting_currency as a REQUIRED keyword argument, not a default — a Rule 1 bug caught and fixed before this plan's Task 3: without it, London's raw GBP total would have sorted against Los Angeles's raw USD total as though they were the same unit, exactly the error D-55 exists to prevent. RankedCity also gained a landed_cost field (the full aggregate() output) so app/services/spec.py never has to re-run pricing to decompose the gap."
  - "decompose_gap() matches cost lines at FACE VALUE (pre-FX) and carries the entire currency effect on one dedicated 'Currency' component, rather than diffing already-converted values per label — this is the only way to keep 'sum(components) == headline' an exact identity while still surfacing currency as its own first-class row (D-75)."
  - "Exemption reductions are folded into the cost line they target BEFORE label-matching, identified structurally (negative value + inputs[0] target reference) rather than by label text — a real discovery this plan made against the real committed New York/Los Angeles data (each city's exemption has a DIFFERENT label), fixed inline as a Rule 1 bug rather than routed around."
  - "The JSON contract splits the two ranked-list bands into separate top-level keys (net_ranked_cities/incentive_not_modelled_cities) rather than one list with a band flag — resolving an internal contradiction between 04-06-PLAN.md's action prose (which described one ranked_cities list) and its own acceptance criteria (which explicitly names 'one list with a flag' as the anti-pattern to avoid). The acceptance criteria governed; the Python-level SpecResult.ranked_cities stays one ordered tuple, matching engine.ranker.rank's own natural shape, with the JSON split happening only at the serialization boundary."
  - "app/services/spec.py's old CityCost dataclass and city_costs field are fully removed, not kept alongside the new ranked_cities/gap shape — tests/test_route_a_basis_walk.py and tests/test_engine_cost_localizer.py (not in this plan's declared files_modified) needed updating to keep D-63's basis-walk gate genuinely exercising the real Figure tree rather than silently going stale."
  - "Every golden-cost expected value was derived by hand from the committed data files (crew_tiers.yaml shares, union rate cards, GSA/State Dept per-diem tables, facilities low bounds, exemption rates, the FX snapshot) before this session ever ran the pipeline against this plan's fixed spec — every one agreed exactly with the code's own output; no discrepancy was found or silently reconciled."

requirements-completed: [OUT-01, OUT-02]

coverage:
  - id: D1
    description: "The two-band ranked list: a city enters net_ranked only when a rule file exists and net cash converts; every other city enters incentive_not_modelled with a non-zero cost-only total, never a fabricated $0 (OUT-01, D-55/D-56)"
    requirement: OUT-01
    verification:
      - kind: unit
        ref: "tests/test_engine_ranker.py#test_ranked_and_unranked_bands_never_interleave_even_when_unranked_total_is_lower"
        status: pass
      - kind: unit
        ref: "tests/test_engine_ranker.py#test_unranked_total_landed_cost_equals_cost_only_total_and_is_never_zero"
        status: pass
      - kind: unit
        ref: "tests/test_engine_ranker.py#test_both_unranked_reason_shapes_are_produced_by_the_conditions_that_cause_them"
        status: pass
      - kind: unit
        ref: "tests/test_engine_ranker.py#test_rule_file_exists_but_net_cash_refuses_falls_into_unranked_without_raising"
        status: pass
      - kind: integration
        ref: "tests/test_engine_ranker.py#test_real_committed_profiles_produce_exactly_one_net_ranked_city"
        status: pass
    human_judgment: false
  - id: D2
    description: "Ranking never sorts a raw GBP total against a raw USD total — reporting_currency is required and every city's total is expressed in the same currency before comparison"
    requirement: OUT-01
    verification:
      - kind: unit
        ref: "tests/test_engine_ranker.py#test_unranked_band_compares_a_gbp_city_and_a_usd_city_in_the_same_currency"
        status: pass
    human_judgment: false
  - id: D3
    description: "The gap between any two cities decomposes into components matched by label that sum exactly to the headline, with currency as its own first-class component when a conversion applied (OUT-02, D-75)"
    requirement: OUT-02
    verification:
      - kind: unit
        ref: "tests/test_engine_gap.py#test_components_sum_exactly_to_the_headline_gap"
        status: pass
      - kind: unit
        ref: "tests/test_engine_gap.py#test_component_identical_in_both_cities_is_present_with_zero_delta"
        status: pass
      - kind: unit
        ref: "tests/test_engine_gap.py#test_one_sided_label_raises_naming_the_label_and_both_city_ids"
        status: pass
      - kind: integration
        ref: "tests/test_engine_gap.py#test_every_ordered_pair_among_the_three_committed_cities_sums_exactly"
        status: pass
      - kind: integration
        ref: "tests/test_engine_gap.py#test_london_pairs_carry_a_currency_component_ny_vs_la_does_not"
        status: pass
    human_judgment: false
  - id: D4
    description: "A fixed ProductionSpec priced against the committed cost profiles produces exact Decimal totals for New York, Los Angeles and London and an exact New York vs Los Angeles gap, pinned in CI and proven non-vacuous (D-78)"
    verification:
      - kind: unit
        ref: "tests/test_golden_cost.py#test_new_york_golden_cost_total"
        status: pass
      - kind: unit
        ref: "tests/test_golden_cost.py#test_los_angeles_golden_cost_total"
        status: pass
      - kind: unit
        ref: "tests/test_golden_cost.py#test_london_golden_cost_total_converted_to_usd"
        status: pass
      - kind: unit
        ref: "tests/test_golden_cost.py#test_new_york_vs_los_angeles_golden_gap"
        status: pass
      - kind: unit
        ref: "tests/test_golden_cost.py#test_perturbing_a_committed_rate_by_one_unit_moves_the_golden_total"
        status: pass
    human_judgment: false
  - id: D5
    description: "The ranked list and gap are reachable over HTTP as separate JSON keys per band, with the unranked entry non-zero and reasoned, and gap components summing exactly to the headline in JSON"
    requirement: OUT-01
    verification:
      - kind: integration
        ref: "tests/test_app_spec_route.py#test_post_api_v1_spec_ny_and_la_returns_separate_bands_and_a_gap"
        status: pass
      - kind: integration
        ref: "tests/test_app_spec_route.py#test_post_api_v1_spec_single_city_has_no_gap"
        status: pass
      - kind: manual_procedural
        ref: "app/templates/spec_result.html renders two separately-headed band sections plus a gap table (verified via a live TestClient POST to /spec rendering all three committed cities)"
        status: pass
    human_judgment: false

duration: 220min
completed: 2026-08-27
status: complete
---

# Phase 4 Plan 06: The Ranked List, the Decomposed Gap, and Golden Totals Pinned in CI

**A two-band ranked list that refuses to compare an unmodelled incentive against a modelled one, a component-by-component gap decomposer with currency as its own first-class line, and exact Decimal golden totals for all three committed cities pinned in CI — New York $758,427, Los Angeles $693,521, London £548,595 / $747,735, and their gaps, reachable over HTTP as two separately-keyed JSON bands.**

## Performance

- **Duration:** ~220 min
- **Started:** 2026-08-27T00:44:36Z (approximate)
- **Completed:** 2026-08-27T01:22:00Z (approximate)
- **Tasks:** 3
- **Files modified:** 14 (7 created, 7 modified)

## Accomplishments

- **`engine/ranker.py`** — `RankedCity` and `rank()`. A city whose profile declares a jurisdiction with a committed rule file, and whose net cash converts successfully, enters `net_ranked` with a net total; every other city enters `incentive_not_modelled` carrying its cost-only total, never a fabricated `$0` (D-56). Both distinct unranked reasons are produced by the conditions that actually cause them (no rule file at all; a rule file that refuses to convert, mirroring Connecticut's real transfer-discount gap). Against the three real committed profiles: exactly one `net_ranked` city (New York) and two `incentive_not_modelled` cities (Los Angeles, London) — the asserted expected Phase 4 state.
- **`engine/gap.py`** — `GapDecomposition`, `decompose_gap()`, `largest_component()`. Cost lines are matched by label at face value (before any FX conversion), so the entire currency effect lands on one dedicated `Currency` component (D-75) and `sum(components) == headline_gap` is an exact identity, not a coincidence. A zero delta is emitted, never dropped. A one-sided label raises naming both cities.
- **`tests/test_golden_cost.py`** (D-78) — every expected value hand-derived from the raw committed data files before the pipeline was ever run against this plan's fixed spec: New York `$758,427`, Los Angeles `$693,521`, London `£548,595` / `$747,735` converted, and the New York vs Los Angeles headline gap `$64,906` with every component. Every independently-derived number agreed exactly with the pipeline's own output — no discrepancy found. Non-vacuity proven by perturbing New York's committed IATSE camera rate by one unit in memory (`monkeypatch`, auto-reverted): the total genuinely moves to `$758,597`.
- **Route A wiring** — `app/services/spec.py::SpecResult` now carries `ranked_cities`/`gap` in place of the old flat `city_costs`; `app/routers/spec.py` serializes the two bands as separate JSON keys (`net_ranked_cities`/`incentive_not_modelled_cities`) rather than one list with a flag; `app/templates/spec_result.html` renders two separately-headed band sections plus a gap table.
- **Two genuine discoveries, both fixed inline as Rule 1 bugs, not routed around:** (1) `rank()` was missing a required `reporting_currency` parameter — without it, London's raw GBP total would have sorted against Los Angeles's raw USD total as the same number, exactly the error D-55 exists to prevent. (2) New York and Los Angeles each carry a DIFFERENTLY-labelled INC-10 exemption reduction (sales tax on equipment vs hotel-occupancy tax on housing), which broke naive strict by-label matching against real data — fixed by folding a reduction into the cost line it targets, identified structurally by its negative value and its `inputs[0]` target reference, never by label text.

## Task Commits

Each task was committed atomically:

1. **Task 1: The two-band ranked list** — `94d23e5` (feat)
2. **Task 2: Component-by-component gap decomposition, currency included** — `8697846` (feat)
3. **Task 3: Golden cost totals in CI, and the ranked list plus gap through the API** — `91445b4` (feat)

**Plan metadata:** commit hash recorded after this SUMMARY is committed.

## Files Created/Modified

- `engine/ranker.py` — new; `RankedCity`, `rank()`
- `engine/gap.py` — new; `GapDecomposition`, `decompose_gap()`, `largest_component()`
- `tests/test_engine_ranker.py`, `tests/test_engine_gap.py` — new
- `tests/test_golden_cost.py` — new; the D-78 golden totals and non-vacuity proof
- `tests/fixtures/cost_profiles/synthetic-ranked.yaml`, `synthetic-unranked.yaml` — new synthetic fixtures, never a real committed city or a Phase 5 rule file pulled forward
- `app/services/spec.py` — `CityCost`/`city_costs` removed; `SpecResult.ranked_cities`/`.gap`, `_rank_candidate_cities`, `_gap_for_ranked_cities`, `REPORTING_CURRENCY`
- `app/routers/spec.py` — `_ranked_city_to_json`, `_gap_to_json`; `net_ranked_cities`/`incentive_not_modelled_cities`/`gap` in the JSON contract
- `app/templates/spec_result.html` — two separately-headed band sections, a gap table
- `tests/test_app_spec_route.py`, `tests/test_route_a_basis_walk.py`, `tests/test_engine_cost_localizer.py` — updated for the `CityCost` -> `RankedCity` / `city_costs` -> `ranked_cities` rename
- `.planning/WINDOWS.md` — one new lint-warning entry (#24)

## Decisions Made

See `key-decisions` in the frontmatter for the full list. The two most consequential:

- **`rank()`'s `reporting_currency` parameter is required, not defaulted** — a real bug this plan's own test suite caught before it ever reached a demo: London's raw GBP total would otherwise have been sorted against a raw USD total as the same number.
- **The JSON contract splits the two bands into separate top-level keys**, resolving a genuine contradiction between 04-06-PLAN.md's action prose and its own acceptance criteria — the acceptance criteria (the more specific, testable requirement, and the one explicitly naming "one list with a flag" as the anti-pattern) governed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `engine.ranker.rank` was missing `reporting_currency`, meaning a GBP city would sort against a USD city as the same number**
- **Found during:** Task 3, while wiring `rank()` into `app/services/spec.py` and reasoning about London joining the unranked band alongside Los Angeles
- **Issue:** Task 1's `rank()` called `aggregate(localized)` with no `reporting_currency`, so each city aggregated in its own native currency — a same-currency comparison for New York/Los Angeles but a silent cross-currency comparison the instant London (GBP) entered either band alongside a USD city, exactly the error D-55/the inherited conventions explicitly forbid ("do NOT compare raw GBP against raw USD").
- **Fix:** Added a required `reporting_currency` keyword-only parameter, threaded through all three `aggregate()` call sites in `rank()`; `RankedCity` gained a `landed_cost` field so downstream callers (the gap decomposer) never need to re-run pricing.
- **Files modified:** `engine/ranker.py`, `tests/test_engine_ranker.py` (all existing `rank()` calls updated; one new test added proving the fix — `test_unranked_band_compares_a_gbp_city_and_a_usd_city_in_the_same_currency`)
- **Verification:** `uv run pytest tests/test_engine_ranker.py -q` — 9 passed, including the new cross-currency test asserting London's converted total (not its raw GBP total) is what's compared.
- **Committed in:** `94d23e5` (Task 1 commit — caught and fixed before that commit landed, not a follow-up)

**2. [Rule 1 - Bug] Real committed New York and Los Angeles data each carry a DIFFERENTLY-labelled exemption reduction, breaking naive strict by-label gap matching**
- **Found during:** Task 3, while writing the golden gap test against the real committed profiles (first observed as a `ValueError` from `decompose_gap` when comparing New York and Los Angeles)
- **Issue:** New York's sales-tax exemption reduces "Equipment"; Los Angeles's hotel-occupancy exemption reduces "Housing — imported crew and cast" — two genuinely different exemption Figures with two different labels (`"Sales tax exemption — production equipment (reduces 'Equipment')"` vs `"Hotel occupancy tax exemption — extended stay (30+ consecutive nights) (reduces 'Housing — imported crew and cast')"`). Task 2's original by-label matching treated each as a one-sided label and raised, even though both cities correctly price all ten `COST_CATEGORIES`.
- **Fix:** `engine/gap.py::_fold_reductions_into_targets` identifies a reduction structurally (a negative value whose sole `inputs[0]` names the cost line it targets — never by sniffing the label text) and folds its value into that target's face value BEFORE label matching, carrying the reduction Figure along in the resulting component's `inputs` for full click-through traceability.
- **Files modified:** `engine/gap.py`, `tests/test_engine_gap.py` (real-data exact-sum and currency-component tests added)
- **Verification:** `uv run pytest tests/test_engine_gap.py -q` — 11 passed, including `test_every_ordered_pair_among_the_three_committed_cities_sums_exactly` against the real committed New York/Los Angeles/London data.
- **Committed in:** `8697846` (Task 2 commit — caught and fixed before that commit landed)

**3. [Rule 4-adjacent — resolved via acceptance criteria, not a stop] Internal contradiction in 04-06-PLAN.md's own Task 3 text**
- **Found during:** Task 3, designing `_spec_result_to_json`
- **Issue:** Task 3's action prose describes `ranked_cities` as one JSON list with a `band` field per entry; its own acceptance criteria explicitly requires "the two bands are separate keys in the JSON rather than one list with a flag" — literally naming the action prose's own described shape as the anti-pattern to avoid.
- **Resolution:** Followed the acceptance criteria (the more specific, directly testable requirement) — the JSON response carries `net_ranked_cities`/`incentive_not_modelled_cities` as two separate top-level keys. The Python-level `SpecResult.ranked_cities` stays ONE ordered tuple (matching `engine.ranker.rank`'s own natural, correct shape); the split happens only at the JSON serialization boundary in `app/routers/spec.py`.
- **Files modified:** `app/routers/spec.py`, `tests/test_app_spec_route.py`
- **Verification:** `test_post_api_v1_spec_ny_and_la_returns_separate_bands_and_a_gap` asserts both keys exist and are correctly populated.
- **Committed in:** `91445b4` (Task 3 commit)

---

**Total deviations:** 3 (2 Rule 1 bugs, 1 plan-text contradiction resolved via the more specific acceptance criteria). No scope creep — all three were necessary for the plan's own required behavior to be correct against real data and its own stated acceptance criteria.

## Issues Encountered

- **`tests/test_route_a_basis_walk.py` and `tests/test_engine_cost_localizer.py` needed updating for the `CityCost` -> `RankedCity` rename**, even though neither was in this plan's declared `files_modified` list. The plan's own Task 3 instruction ("replace the flat `city_costs` list with the ranked structure") necessitated it — leaving these two files pointed at a field that no longer exists would have either broken the suite or, worse, left D-63's basis-walk gate silently walking a stale/empty attribute. Both were fixed as Rule 3 (blocking) deviations, not new work — the honesty gate keeps walking the identical Figure trees, now reached through `cost_only_total`/`total_landed_cost` instead of `cost_total`/`total_landed_cost`.
- **Repo-wide ruff baseline grew from 415 to 451** (net +36) from this plan's new/modified files — the same pre-existing FURB157/ISC004 patterns already tracked across the repo (entries 2, 5, 11, 14, 17, 23), plus one RUF022 finding on `app/services/spec.py`'s already-unsorted `__all__` list (a new constant inserted into a list that was already not fully sorted before this plan). No new rule categories introduced. Out of scope per the executor scope-boundary rule; recorded to `.planning/WINDOWS.md` (entry 24).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Phase 4's two headline outputs (OUT-01, OUT-02) are both reachable over HTTP**, proven against the real committed New York/Los Angeles/London data with exact Decimal totals pinned in CI (D-78). A one-character edit to a committed rate now fails CI instead of quietly moving the demo.
- **`engine.ranker.rank` and `engine.gap.decompose_gap` are reusable as-is** for Phase 5's additional jurisdictions (California, New Jersey) — a new committed rule file promotes a city into the `net_ranked` band with zero code change, exactly D-55's own designed degradation path.
- **The D-54 phase-boundary fact holds exactly as CONTEXT.md anticipated:** with only New York carrying a committed rule file, the live ranked band contains exactly one city — asserted as the expected Phase 4 state, not a gap, in `tests/test_engine_ranker.py`.
- No blockers for 04-07 (sensitivity), which builds on `engine.gap.largest_component`'s purely descriptive framing.

---
*Phase: 04-cost-localization-landed-cost-outputs*
*Completed: 2026-08-27*

## Self-Check: PASSED

- All 7 created files confirmed present on disk: `engine/ranker.py`, `engine/gap.py`, `tests/test_engine_ranker.py`, `tests/test_engine_gap.py`, `tests/test_golden_cost.py`, `tests/fixtures/cost_profiles/synthetic-ranked.yaml`, `tests/fixtures/cost_profiles/synthetic-unranked.yaml`.
- All three task commits (`94d23e5`, `8697846`, `91445b4`) confirmed present in `git log --oneline --all`.
- `uv run --frozen pytest tests/ -q` re-run fresh: 449 passed, 0 failed (baseline 421; +28 net new tests across this plan's three tasks).
- Plan-level `<verification>`: `grep -rn "\.quantize(" engine/ | grep -v "engine/rounding.py"` returns no hits; `git diff --stat pyproject.toml uv.lock` is empty; a New York plus Los Angeles submission returns one net-ranked and one unranked city in separate JSON keys (`net_ranked_cities`/`incentive_not_modelled_cities`); gap components sum exactly to the headline gap, verified both in the engine (`tests/test_engine_gap.py`) and in the JSON (`tests/test_app_spec_route.py`); the golden test's non-vacuity perturbation moves `cost_total` from `$758,427` to `$758,597`, confirmed observed and reverted (`monkeypatch`).
- Task-level acceptance criteria re-verified individually: `grep -nE '"us-ny"|"us-ca"|"gb-london"' engine/ranker.py engine/gap.py` returns no hits; against the real committed profiles `rank()` returns exactly one `net_ranked` city and two `incentive_not_modelled` cities; every ordered pair among the three committed cities' gap components sums exactly to its headline.
