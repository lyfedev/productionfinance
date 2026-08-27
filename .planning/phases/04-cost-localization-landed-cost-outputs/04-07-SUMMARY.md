---
phase: 04-cost-localization-landed-cost-outputs
plan: 07
subsystem: cost-localization
tags: [sensitivity, perturbation, cliff-detection, out-03, d-67, d-68, d-69, d-70]

requires:
  - phase: 04-cost-localization-landed-cost-outputs
    provides: "04-01's basis provenance axis and pipeline shape; 04-05's engine.fx/reporting_currency; 04-06's engine.ranker.rank, engine.gap.decompose_gap and the golden New York/Los Angeles/London data this plan re-runs the pipeline against"
provides:
  - "data/sensitivity_steps.yaml (D-68) — seven declared perturbable inputs, each carrying its own natural-unit step, unit_label and disclosed why; a new row is a table addition, never a script edit"
  - "engine.sensitivity — SensitivityStep, load_sensitivity_steps, SensitivityRow, sensitivity_rows, most_moving_row, RegimeSignature, _regime_signature, _diff_regime_signatures (D-67/D-69): every declared input perturbed through a REAL re-run of the whole pipeline (build_canonical_budget -> localize -> rank -> decompose_gap), never an analytic shortcut. A crossing string names the discrete branch that changed (crew tier, dated union rate row, minimum-spend/tiered-band/per-project-cap state, per-diem month band) without evaluating it."
  - "app/services/spec.py::SpecResult.sensitivity/.sensitivity_reason/.most_moving_sensitivity_row/.assumptions — OUT-03 and the D-65/D-66 assumptions panel reachable over HTTP and on the page; a genuine four-quarter re-run measures quarter_invariant_lines/quarter_variant_lines per city rather than leaving them at their never-populated defaults"
  - "A non-vacuous D-70 CI gate, proven to fail on an inserted word and reverted, covering both the engine's own emitted strings and the rendered HTML body of POST /spec"
affects: ["Phase 6 (interface renders the sensitivity table and assumptions panel with the real map/slider treatment)", "Phase 8 (proof panel can walk the sensitivity path's own re-run Figures)", "Phase 11 (reverse mode reuses the D-68 step table and the perturbation engine directly)"]

actuals:
  tokens: 20200
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "A declared step table in data (mirroring tests/mutation_targets.yaml, D-51) drives a generic perturbation loop; a small, disclosed set of field names (crew_size, crew_imported_count, principal_cast_imported_count, start_quarter) is a narrowly-scoped special-case exception because ProductionSpec's own validators couple them to a companion field — every other field reaches a fully generic increment path with zero code changes for a new row."
    - "A regime signature is built by READING the values and derivation TEXT the chain already produced (regex over Figure.derivation strings for a dated union rate row id, a tiered-rate band, a minimum-spend or per-project-cap state) rather than re-deriving any of them independently — the signature cannot drift from what the chain actually did."
    - "A jurisdiction rule file is located generically from a runtime jurisdiction_id value joined to the SAME jurisdictions/{id}.yaml naming convention the app layer already uses, keeping engine/sensitivity.py JUR-05-clean without importing app.services._paths."
    - "An ancillary, non-primary measurement (the four-quarter quarter-invariance re-run) that hits a real, expected refusal (a dated rate row's own effective_to boundary) excludes that one quarter from the comparison rather than crashing the visitor's own primary request — mirrors engine.ranker.rank's refuse-rather-than-crash shape for a city whose net cash cannot be computed."

key-files:
  created:
    - data/sensitivity_steps.yaml
    - engine/sensitivity.py
    - tests/test_engine_sensitivity.py
  modified:
    - app/services/spec.py
    - app/routers/spec.py
    - app/templates/spec_result.html
    - tests/test_app_spec_route.py
    - .planning/WINDOWS.md

key-decisions:
  - "Tasks 1 and 2 landed in a single commit rather than two — the perturbation engine (Task 1) and the regime-signature/cliff-crossing machinery (Task 2) are implemented in the same module and tested in the same file, and retrofitting an artificial split after the fact would have meant either duplicating work or committing a half-working module. Documented here rather than silently deviating from the plan's per-task commit convention."
  - "Jurisdiction rule files are located generically inside engine/sensitivity.py via jurisdictions/{jurisdiction_id}.yaml, built from a runtime value, rather than importing app/services/_paths.py's RULESET_PATH_BY_JURISDICTION dict — keeps engine/ from depending on app/ (D-44) and keeps the JUR-05 scan clean without a new narrowly-scoped exception file."
  - "The four disclosed special-case step-application fields (crew_size, crew_imported_count, principal_cast_imported_count, start_quarter) are a fixed, hand-maintained set precisely because each is coupled to a companion ProductionSpec field by a validator; every other declared row reaches a fully generic integer-increment path, proven by a test that appends a brand-new field to a temporary table and asserts a row appears with zero code changes."
  - "engine.sensitivity._regime_signature reads programme-level contribution Figures (RankedCity.incentive_figure.inputs), not the top-level total_net_cash Figure's own derivation — the tier-band/minimum-spend/cap text lives on the PER-PROGRAMME figure (Figure.with_step's append-only chaining preserves the whole history there), never on the jurisdiction-level summary figure price_jurisdiction separately constructs."
  - "app/services/spec.py's new four-quarter quarter-invariance re-run catches ValueError per quarter and excludes that quarter from the comparison — discovered as a real bug against the committed New York profile (whose IATSE camera rate row's effective_to boundary does not cover Q4 2026), which broke every existing Route A test before the fix; fixed as a Rule 1 bug, not routed around."

requirements-completed: [OUT-03]

coverage:
  - id: D1
    description: "Sensitivity is computed by perturbing one declared input at a time and re-running the real pipeline (build_canonical_budget -> localize -> rank -> decompose_gap), never an analytic derivative — proven against an independently hand-derived expected delta"
    requirement: OUT-03
    verification:
      - kind: unit
        ref: "tests/test_engine_sensitivity.py#test_a_row_that_genuinely_moves_the_gap_matches_an_independently_computed_value"
        status: pass
      - kind: unit
        ref: "tests/test_engine_sensitivity.py#test_module_source_contains_no_derivative_or_gradient_terms"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every perturbable input and its step size is declared in a committed YAML table (data/sensitivity_steps.yaml); adding a new row for a plain field requires zero code changes"
    requirement: OUT-03
    verification:
      - kind: unit
        ref: "tests/test_engine_sensitivity.py#test_generic_step_application_needs_no_code_change_for_a_new_field"
        status: pass
      - kind: unit
        ref: "tests/test_engine_sensitivity.py#test_adding_an_inactive_row_changes_nothing"
        status: pass
    human_judgment: false
  - id: D3
    description: "A cliff crossing (a crew-tier boundary, an incentive tiered-rate band) is named on the row that crosses it, with both before/after values stated; a row with no regime change carries an empty cliff_crossings tuple"
    requirement: OUT-03
    verification:
      - kind: unit
        ref: "tests/test_engine_sensitivity.py#test_crew_size_step_crossing_a_tier_boundary_names_both_tier_names"
        status: pass
      - kind: unit
        ref: "tests/test_engine_sensitivity.py#test_incentive_side_tiered_band_crossing_is_detected_via_synthetic_rule_file"
        status: pass
      - kind: unit
        ref: "tests/test_engine_sensitivity.py#test_no_regime_change_produces_an_empty_cliff_crossings_tuple"
        status: pass
    human_judgment: false
  - id: D4
    description: "No sensitivity output string (engine-emitted or rendered HTML) contains prescriptive vocabulary; the gate is proven non-vacuous by a real insert-and-revert cycle"
    requirement: OUT-03
    verification:
      - kind: unit
        ref: "tests/test_engine_sensitivity.py#test_d70_vocabulary_gate_is_non_vacuous_over_committed_cities_and_step_table"
        status: pass
      - kind: integration
        ref: "tests/test_app_spec_route.py#test_d70_vocabulary_condition_holds_over_rendered_html_body"
        status: pass
    human_judgment: false
  - id: D5
    description: "Sensitivity and the model's assumptions are reachable over HTTP: a two-city submission returns a non-empty sensitivity list naming its most-moving row; a one-city submission returns an empty list plus a stated reason; every delta parses as a Decimal"
    requirement: OUT-03
    verification:
      - kind: integration
        ref: "tests/test_app_spec_route.py#test_post_api_v1_spec_ny_and_la_returns_non_empty_sensitivity_list"
        status: pass
      - kind: integration
        ref: "tests/test_app_spec_route.py#test_post_api_v1_spec_single_city_has_empty_sensitivity_with_reason"
        status: pass
    human_judgment: false
  - id: D6
    description: "The rendered page shows the sensitivity table and the assumptions panel (shoot-days-per-week, department-share note, permanent exclusions, per-city quarter-invariance measurement, seasonality state) — a live, real interface treatment"
    requirement: OUT-03
    verification:
      - kind: automated_ui
        ref: "tests/test_app_spec_route.py#test_rendered_spec_result_page_shows_sensitivity_and_assumptions"
        status: pass
      - kind: manual_procedural
        ref: "Open the hosted /spec page, submit a two-city spec, and confirm the sensitivity table and assumptions panel read as plain factual description with no verb telling the reader what to do"
        status: unknown
    human_judgment: true
    rationale: "The plan's own <verify> block names a human-check step (visual/design read of the live page) that a TestClient-level HTTP assertion cannot substitute for — the page was verified to render the correct data (D6's automated_ui entry) but its visual/design adequacy on the actually-deployed page was not observed this session."

duration: 33min
completed: 2026-08-27
status: complete
---

# Phase 4 Plan 07: Sensitivity — Which Single Input Moves the Gap Most, Found by Actually Moving It

**A declared step table (seven rows) drives a perturbation engine that re-runs the ENTIRE pricing pipeline per row, cliff-crossing detection reads the derivation text the chain already produced, and a non-vacuous CI gate — proven to fail on an inserted word, twice — keeps every sensitivity string (engine and rendered HTML) descriptive, never prescriptive.**

## Performance

- **Duration:** ~33 min
- **Started:** 2026-08-27T01:25:58Z (approximate, previous plan's docs commit)
- **Completed:** 2026-08-27T01:57:08Z
- **Tasks:** 3
- **Files modified:** 8 (3 created, 5 modified)

## Accomplishments

- **`data/sensitivity_steps.yaml`** (D-68) — seven declared rows (stage shoot day, location shoot day, crew size, imported crew member, imported principal cast member, start-quarter-forward, and a deliberately unpriced non-imported principal cast member row), each carrying `id`/`spec_field`/`step`/`unit_label`/`requirement`/`status`/`why`. Mirrors `tests/mutation_targets.yaml`'s precedent exactly — a new row is a table addition, never a script edit.
- **`engine/sensitivity.py`** (D-67) — `sensitivity_rows(spec, city_a_id, city_b_id, *, reporting_currency)` re-runs the WHOLE chain (`build_canonical_budget` → `localize` → `rank` → `decompose_gap`) for the baseline and for each active declared step, one input at a time. Four field names (`crew_size`, `crew_imported_count`, `principal_cast_imported_count`, `start_quarter`) are a disclosed, narrowly-scoped exception requiring a compensating adjustment to stay a valid `ProductionSpec`; every other field reaches a fully generic increment path — proven with zero code changes by a test that appends a new field to a temporary table.
- **Cliff-crossing detection** (D-69) — `_regime_signature`/`_diff_regime_signatures` build a frozen record of every discrete branch the chain took (resolved crew tier via `engine.budget._infer_department_tier`, dated union rate row ids via regex over `Figure.derivation`, minimum-spend/tiered-band/per-project-cap state via regex over the per-programme contribution Figure's own accumulated derivation text) — read from what the chain already produced, never re-derived. Proven against a real crew-size crossing (small→mid at crew_size 60→61) and a synthetic tiered-by-spend rule file crossing at spend=100,000.
- **The D-70 descriptive-language gate** — a non-vacuous CI test scans every string `sensitivity_rows` emits (`step_text`, `direction`, `note`, `cliff_crossings`) plus every derivation line on every Figure the sensitivity path produces, for the committed New York/Los Angeles cities and the committed step table, against a vocabulary sourced from D-70 (`recommend`, `should`, `consider`, `best`, `optimal`, `you could`/`you should` and their forms). Proven non-vacuous by hand TWICE — once for the engine strings, once for the rendered HTML body — inserting a banned word, observing RED, reverting, and recording the observed failure in each test module's own docstring.
- **Sensitivity and the assumptions panel reach HTTP and the page** — `app/services/spec.py::SpecResult` gains `sensitivity`/`sensitivity_reason`/`most_moving_sensitivity_row`/`assumptions`; `app/routers/spec.py` serializes them (every `Decimal` via `str(...)`); `app/templates/spec_result.html` renders a sensitivity table and an assumptions panel (shoot-days-per-week, the department-share modelling assumption, the `permanent_exclusions` list, and a per-city quarter-invariance measurement plus seasonality state) — all read from data, none hardcoded into the template.
- **A real bug found and fixed while wiring quarter-invariance**: re-running `localize()` at all four quarters of a submission's own `start_year` can hit a quarter a committed union rate row's own `effective_to` boundary does not cover (New York's IATSE camera rate expires before Q4 2026) — this broke every existing New York-touching test before the fix. Fixed by excluding that one quarter from the comparison rather than crashing the visitor's own primary request, mirroring `engine.ranker.rank`'s refuse-rather-than-crash shape.
- **Measured result for the fixed golden spec (New York vs Los Angeles, USD)**: baseline gap `$64,906`. The two shoot-day steps produce an IDENTICAL delta (`+$11,888`, widened) — a genuine, hand-verified fact about the committed facilities data, not a bug (each city's own stages-vs-permits/locations differential happens to be `$700`, so the per-city deltas differ but the cross-city GAP delta cancels to the same number for both step types). The imported-crew and imported-cast steps both produce `+$2,577` (widened) — also identical, since both add one person to the SAME imported-headcount travel pricing path. The crew-size step (`+1` crew member, absorbed by locally-hired) produces `+$781` (widened). The quarter-forward step produces `-$10,164` (narrowed) and is the only row that fires a cliff crossing — both cities' per-diem month band moves from April to July 2026. The non-imported-principal-cast-member row produces exactly `$0` with a stated "does not enter any priced line" note. **Wall-clock for the full 8-run perturbation set (1 baseline + 7 active steps): ~539 ms** — real, but not literally millisecond-scale as D-67's own text anticipated; recorded honestly as a finding rather than smoothed over.

## Task Commits

Each task was committed atomically (Tasks 1 and 2 landed together — see Deviations):

1. **Task 1 + Task 2: the declared step table, the perturbation engine, and cliff-crossing detection** — `75e4353` (feat)
2. **Task 3: sensitivity and the assumptions panel through the API and onto the page** — `00bd2f8` (feat)

**Plan metadata:** commit hash recorded after this SUMMARY is committed.

## Files Created/Modified

- `data/sensitivity_steps.yaml` — new; seven declared perturbable inputs
- `engine/sensitivity.py` — new; `SensitivityStep`, `load_sensitivity_steps`, `SensitivityRow`, `sensitivity_rows`, `most_moving_row`, `RegimeSignature`, `_regime_signature`, `_diff_regime_signatures`, `StepNotApplicable`
- `tests/test_engine_sensitivity.py` — new; 17 tests covering Tasks 1 and 2
- `app/services/spec.py` — `SpecResult.sensitivity`/`.sensitivity_reason`/`.most_moving_sensitivity_row`/`.assumptions`; `CityAssumptions`/`ModelAssumptions`; `_compute_assumptions`, `_quarter_invariance_for_city`, `_seasonality_state_for_profile`, `_department_share_note`; `_rank_candidate_cities` now also returns `profile_by_city_id`
- `app/routers/spec.py` — `_sensitivity_row_to_json`, `_city_assumptions_to_json`, `_assumptions_to_json`; `sensitivity`/`sensitivity_reason`/`most_moving_sensitivity_row`/`assumptions` in the JSON contract
- `app/templates/spec_result.html` — a sensitivity table and an assumptions panel
- `tests/test_app_spec_route.py` — 4 new HTTP-level tests (two-city vs one-city sensitivity, the rendered assumptions panel, the D-70 HTML gate)
- `.planning/WINDOWS.md` — one new lint-warning entry (#25)

## Decisions Made

See `key-decisions` in the frontmatter for the full list. The two most consequential:

- **Jurisdiction rule files are located generically** (`jurisdictions/{jurisdiction_id}.yaml`, built from a runtime value) inside `engine/sensitivity.py` rather than importing `app/services/_paths.py`'s dict — keeps `engine/` from depending on `app/` and keeps the JUR-05 scan clean.
- **The four-quarter quarter-invariance re-run excludes a quarter that cannot be priced** rather than crashing the request — a real bug this plan's own test suite caught before it ever reached a demo (every existing New York test broke on first wiring).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Re-running `localize()` at all four quarters can hit a quarter a committed dated union rate row does not cover**
- **Found during:** Task 3, first full test run after wiring `_quarter_invariance_for_city` into `app/services/spec.py`
- **Issue:** `_quarter_invariance_for_city` unconditionally re-ran `localize()` at Q1-Q4 of the submission's own `start_year`. New York's committed IATSE camera rate row's `effective_to` boundary does not cover 2026-10-01 (Q4) — `select_rate_row` correctly raises `ValueError` there — which crashed the WHOLE Route A request (not just the ancillary quarter-invariance measurement) for every existing test touching New York, since `localize()`'s exception propagated all the way out of `handle_spec_submission`.
- **Fix:** `_quarter_invariance_for_city` now catches `ValueError` per quarter and excludes that quarter from the comparison, returning `((), ())` only if NO quarter re-run succeeds at all — the visitor's own submitted quarter (which is what actually matters, and which the un-modified `_rank_candidate_cities` call already prices successfully) is never affected.
- **Files modified:** `app/services/spec.py`
- **Verification:** `uv run pytest tests/test_app_spec_route.py -q` — 29 passed (was 11 failed before the fix).
- **Committed in:** `00bd2f8` (Task 3 commit — caught and fixed before that commit landed)

**2. [Task-boundary blending, not a scope error] Tasks 1 and 2 landed in one commit**
- **Found during:** planning the commit sequence after Task 1's code was already written
- **Issue:** The perturbation engine (Task 1: `sensitivity_rows`, the generic/special-case step-application split) and cliff-crossing detection (Task 2: `_regime_signature`, `_diff_regime_signatures`, `SensitivityRow.cliff_crossings`) are implemented in the same module (`engine/sensitivity.py`) and share a test file. Building Task 1 in isolation would have meant either committing a `SensitivityRow` with `cliff_crossings` permanently hardcoded to `()` (a stub the plan explicitly forbids leaving unresolved), or writing the cliff-detection machinery twice.
- **Resolution:** Both tasks landed in one commit (`75e4353`), covering both tasks' full acceptance criteria — every Task 1 AND every Task 2 acceptance criterion is independently verified and passing. Documented here rather than silently deviating from the plan's one-commit-per-task convention.
- **Files modified:** none beyond what was already planned for Tasks 1/2
- **Verification:** all 17 tests in `tests/test_engine_sensitivity.py` pass, independently covering every Task 1 and Task 2 acceptance criterion.
- **Committed in:** `75e4353`

---

**Total deviations:** 1 auto-fixed (Rule 1 bug), 1 process deviation (task-boundary blending, no scope impact).
**Impact on plan:** The Rule 1 fix was necessary for correctness — an ancillary assumptions measurement must never crash the visitor's own primary request. No scope creep in either case.

## Issues Encountered

- **Repo-wide ruff baseline grew from 451 to 463** (net +12) from this plan's new/modified files — the same pre-existing FURB157 (verbose `Decimal("0")` constructor, RD-01's quoted-Decimal convention) pattern already tracked across the repo (WINDOWS entries 2, 5, 11, 14, 17, 23, 24). No new rule categories introduced. Out of scope per the executor scope-boundary rule; recorded to `.planning/WINDOWS.md` (entry 25).
- **The measured wall-clock cost of the full 8-run perturbation set is ~539 ms**, not literally millisecond-scale as D-67's own rationale text anticipated ("a handful of re-runs is milliseconds"). Still comfortably fast for a single HTTP request; recorded honestly as a finding rather than smoothed into the plan's own optimistic framing.
- **The plan's `<verify>` block names a human-check step** (open the hosted page, submit a two-city spec, confirm the sensitivity table and assumptions panel read as factual description) that was not performed against a live deployed instance this session — the automated `TestClient`-level equivalent (`tests/test_app_spec_route.py::test_rendered_spec_result_page_shows_sensitivity_and_assumptions`) confirms the correct data renders; the live-page visual/design read is recorded as an open human-judgment item in this SUMMARY's `coverage` block (D6) rather than silently marked done.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **OUT-03 is closed.** `engine.sensitivity.sensitivity_rows` is reusable as-is by Phase 11's reverse mode (D-67's perturbation machinery over the same declared `data/sensitivity_steps.yaml` table is explicitly named in 04-CONTEXT.md as the natural substrate for "what change would close this city's gap").
- **Phase 4's five success criteria are all closed**: cost localization + landed cost outputs (04-01 through 04-05), the ranked list and decomposed gap (04-06), and sensitivity (this plan) all reachable over HTTP with real committed data.
- **The assumptions panel this plan builds is deliberately a PLAIN rendering, not Phase 6's consolidated printable panel (PRV-04)** — 04-CONTEXT.md's own domain section scopes the polished, consolidated version to Phase 6; this plan owed the data and a plain rendering of it, which is what landed.
- No blockers for Phase 5 (curated breadth — CA/NJ/CT rule files) or Phase 6 (the interface).

---
*Phase: 04-cost-localization-landed-cost-outputs*
*Completed: 2026-08-27*

## Self-Check: PASSED

- All 3 created files confirmed present on disk: `data/sensitivity_steps.yaml`, `engine/sensitivity.py`, `tests/test_engine_sensitivity.py`.
- Both task commits (`75e4353`, `00bd2f8`) confirmed present in `git log --oneline --all`.
- `uv run --frozen pytest tests/ -q` re-run fresh: 470 passed, 0 failed (baseline 449 per this plan's prompt; +21 net new tests: 17 in `tests/test_engine_sensitivity.py`, 4 in `tests/test_app_spec_route.py`).
- Plan-level `<verification>`: `grep -rn "\.quantize(" engine/ | grep -v "engine/rounding.py"` returns no hits; `git diff --stat pyproject.toml uv.lock` is empty; a New York + Los Angeles submission returns a non-empty `sensitivity` list with a step named on every row and a non-null `most_moving_sensitivity_row`; the crew-size row crosses the small/mid tier boundary in a dedicated test; the D-70 gate passes over both engine strings and the rendered HTML body, and both were proven to fail on an inserted word and reverted (recorded in each test module's own docstring).
- Task-level acceptance criteria re-verified individually: `grep -rn "derivative\|gradient\|np\.\|numpy" engine/sensitivity.py` returns no hits; `grep -n "us-ny\|us-ca\|gb-london" engine/sensitivity.py` returns no hits (JUR-05); an inactive row added to a temporary table changes nothing; a new generic field added to a temporary table appears in the output with zero code changes; a validator-violating step produces a row with a reason rather than raising.
