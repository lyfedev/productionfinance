---
phase: 06-the-interface
plan: 03
subsystem: ui
tags: [fastapi, jinja2, provenance, honesty-gates, d-58, d-59, d-60, d-70, prv-04, prv-05, ui-06]

requires:
  - phase: 04-cost-localization-landed-cost-outputs
    provides: "D-58/D-59/D-60's basis vocabulary, engine.figure.Figure/combined_basis, engine.landed_cost.aggregate's not_priced/PERMANENT_EXCLUSIONS"
  - phase: 06-the-interface
    provides: "06-01's app.services.compare.build_comparison/Comparison, prodfin.css's design tokens (reused, not edited)"
provides:
  - "GET /assumptions — the consolidated printable assumptions panel (PRV-04), one rate row per leaf Figure the current comparison's engine actually used"
  - "GET /methodology — a stable, comparison-independent page explaining how figures are computed (PRV-05)"
  - "app/templates/_figure.html — the one Jinja macro every money figure on these surfaces renders through (UI-06)"
  - "app/services/provenance.py — figure_provenance_state, collect_distinct_figures, collect_rate_figures, build_rate_sheet(s)"
affects: [06-04, 06-05, 08-proof-panel]

actuals:
  tokens: 15838
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "A figure's reachable-provenance state is a THREE-way classification (sourced / computed / unavailable), never a boolean — an aggregate with no source_url of its own but real .inputs is 'computed' (its provenance IS its input tree), never falsely 'unavailable'; only a true leaf dead end (no inputs, no source_url) is 'unavailable'"
    - "basis and confidence are rendered as two structurally separate <span> elements with distinct CSS classes and distinct background tints — never concatenated into one string or one badge (RD-02)"
    - "The assumptions panel's rate list is DERIVED, never hand-maintained: app.services.provenance.collect_rate_figures walks the real recursive Figure DAG (the same walk shape tests/test_route_a_basis_walk.py already established as a test helper, now moved into product code) and returns only LEAF figures, deduplicated by content"
    - "GET /assumptions reuses app.services.compare.build_comparison completely unchanged — the identical pipeline /compare calls — so the rate list is provably the one the current comparison actually used"
    - "D-60 gaps (not_priced, permanent_exclusions) are read straight off engine.landed_cost.aggregate's own LandedCost object per city — never re-declared as a template-local list"

key-files:
  created:
    - app/services/provenance.py
    - app/templates/_figure.html
    - app/routers/methodology.py
    - app/templates/assumptions.html
    - app/templates/methodology.html
    - app/static/provenance.css
    - tests/test_app_provenance.py
    - tests/test_app_methodology.py
  modified:
    - app/main.py

key-decisions:
  - "Both new routes (/assumptions and /methodology) live in one router file, app/routers/methodology.py, matching the plan's own files_modified list (no separate router file was named for /assumptions) — /assumptions reuses CompareInputs/build_comparison with a deliberately duplicated Query(...) parameter list mirroring app/routers/compare.py::get_compare's own signature, following this repo's established per-module duplication discipline (the D-70 vocabulary constant is already duplicated per test file the same way)."
  - "A 'rate' for PRV-04's panel is defined as a LEAF Figure (no further .inputs) — an aggregate/subtotal is never listed as a rate, since its own provenance is the disclosure of its inputs, not a citable rate in its own right. Documented in app/services/provenance.py's own docstring."
  - "figure_provenance_state is a three-way classification (sourced/computed/unavailable), not the two-way reading a literal first pass at the plan's wording suggested. An aggregate Figure (e.g. total_landed_cost) deliberately carries source_url=None because its source IS its disclosed input tree — labelling that 'provenance unavailable' would itself be dishonest in the opposite direction (claiming a dead end that isn't one). Only a genuine leaf with no source_url is 'unavailable'."
  - "Added app/static/provenance.css as this plan's OWN stylesheet rather than editing prodfin.css, per the file_ownership instructions (06-02 owns prodfin.css this wave) — loaded alongside prodfin.css so this plan's templates still get the shared design tokens (--pf-ink, --pf-space-*, --pf-font-*) without a merge conflict."
  - "Verification for Task 1's 'walks the rendered comparison HTML' criterion is realized against GET /assumptions (an owned file, itself a rendering of the current comparison's figures) plus standalone macro rendering via Jinja's Template.module — not against /compare or _ranked_list.html, which 06-02 owns exclusively this wave and this plan does not touch."

requirements-completed: [UI-06, PRV-04, PRV-05]

coverage:
  - id: D1
    description: "UI-06 — every money figure on the provenance surfaces renders through _figure.html; a figure with no reachable provenance never renders as a bare number, and basis/confidence are two structurally distinct labels, never merged into one badge"
    requirement: "UI-06"
    verification:
      - kind: unit
        ref: "tests/test_app_provenance.py#test_figure_with_full_provenance_shows_source_link_and_date_checked"
        status: pass
      - kind: unit
        ref: "tests/test_app_provenance.py#test_leaf_figure_with_no_source_and_sourced_basis_shows_unavailable_state"
        status: pass
      - kind: unit
        ref: "tests/test_app_provenance.py#test_leaf_figure_modelling_assumption_names_the_specific_reason"
        status: pass
      - kind: unit
        ref: "tests/test_app_provenance.py#test_aggregate_figure_with_no_source_url_is_never_labelled_unavailable"
        status: pass
      - kind: unit
        ref: "tests/test_app_provenance.py#test_basis_and_confidence_are_two_distinct_elements_never_merged"
        status: pass
      - kind: integration
        ref: "tests/test_app_provenance.py#test_get_assumptions_no_bare_numbers_every_figure_has_provenance_or_unavailable_state"
        status: pass
    human_judgment: false
  - id: D2
    description: "PRV-04 — GET /assumptions: a consolidated, printable panel listing every rate the CURRENT comparison actually used (source URL + date-checked each), derived from the real Figure tree rather than a hand-maintained list, plus the D-60 acknowledged-gaps list (never a $0 line)"
    requirement: "PRV-04"
    verification:
      - kind: integration
        ref: "tests/test_app_provenance.py#test_get_assumptions_bare_request_returns_200_with_default_floor_cities"
        status: pass
      - kind: integration
        ref: "tests/test_app_provenance.py#test_get_assumptions_rate_list_matches_the_real_figure_tree_independently"
        status: pass
      - kind: integration
        ref: "tests/test_app_provenance.py#test_get_assumptions_gaps_are_a_named_list_never_a_dollar_line"
        status: pass
      - kind: unit
        ref: "tests/test_app_provenance.py#test_build_rate_sheet_carries_the_engines_own_not_priced_and_exclusions"
        status: pass
    human_judgment: true
    rationale: "The print stylesheet's actual page-break/URL-visibility behavior on a real printed or PDF-exported page cannot be asserted by an automated test running headless — a human should confirm app/static/provenance.css's @media print rules produce a legible, non-clipped printed panel with visible source URLs in an actual browser print preview."
  - id: D3
    description: "D-58/D-59 — the basis axis is shown on every figure, and a total containing one modelling_assumption input is itself labelled modelling_assumption, never a stronger tier, using real (non-synthetic) computed data"
    requirement: "PRV-04"
    verification:
      - kind: integration
        ref: "tests/test_app_provenance.py#test_get_assumptions_default_comparison_contains_a_real_modelling_assumption_rate"
        status: pass
      - kind: integration
        ref: "tests/test_app_provenance.py#test_get_assumptions_totals_never_present_a_mixed_basis_total_as_sourced"
        status: pass
    human_judgment: false
  - id: D4
    description: "PRV-05 — GET /methodology: a stable, linkable page explaining how figures are computed, that persists independently of any comparison (query-string-invariant)"
    requirement: "PRV-05"
    verification:
      - kind: integration
        ref: "tests/test_app_methodology.py#test_get_methodology_returns_200_with_no_query_string_at_all"
        status: pass
      - kind: integration
        ref: "tests/test_app_methodology.py#test_get_methodology_is_identical_regardless_of_query_string"
        status: pass
      - kind: integration
        ref: "tests/test_app_methodology.py#test_get_methodology_permanent_exclusions_are_read_from_engine_not_hand_typed"
        status: pass
      - kind: integration
        ref: "tests/test_app_methodology.py#test_get_methodology_cost_categories_are_read_from_engine_not_hand_typed"
        status: pass
    human_judgment: false
  - id: D5
    description: "Figure.confidence (validated|researched) is never conflated with the four-tier source-document-reliability vocabulary — both axes render distinctly, and the confidence label never leaks the unrelated vocabulary"
    verification:
      - kind: unit
        ref: "tests/test_app_provenance.py#test_confidence_label_never_carries_the_four_tier_source_vocabulary"
        status: pass
    human_judgment: false
  - id: D6
    description: "D-70 prescriptive-vocabulary gate covers /assumptions, /methodology, and app/static/provenance.css"
    verification:
      - kind: integration
        ref: "tests/test_app_provenance.py#test_get_assumptions_d70_vocabulary_gate_over_rendered_html"
        status: pass
      - kind: integration
        ref: "tests/test_app_methodology.py#test_get_methodology_d70_vocabulary_gate_over_rendered_html"
        status: pass
      - kind: integration
        ref: "tests/test_app_methodology.py#test_static_provenance_css_d70_vocabulary_gate"
        status: pass
    human_judgment: false
  - id: D7
    description: "D-78 golden totals unchanged; golden test file and D-63 basis-walk guard file both unedited"
    verification:
      - kind: unit
        ref: "tests/test_golden_cost.py"
        status: pass
      - kind: unit
        ref: "tests/test_route_a_basis_walk.py"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-09-09
status: complete
---

# Phase 6 Plan 3: Provenance — Every Figure Opens Its Own Source Summary

**Every money figure on the assumptions panel and methodology page renders through one honest component (`_figure.html`) that never shows a bare number; `GET /assumptions` derives its rate list from the real, recursively-walked `Figure` tree the engine actually produced for the current comparison, never a hand-maintained list; `GET /methodology` is a stable, comparison-independent page explaining the pipeline and the `basis`/`confidence` vocabularies grounded in the engine's own docstrings and data.**

## Performance

- **Duration:** 70 min
- **Started:** 2026-09-09T14:05:00Z (approx.)
- **Completed:** 2026-09-09T15:15:00Z (approx.)
- **Tasks:** 3
- **Files modified:** 9 (8 created, 1 modified)

## Accomplishments

- Built `app/templates/_figure.html`, one Jinja macro every money figure on this plan's surfaces renders through. A figure never renders as a bare number: the value is always immediately followed by two visually and structurally distinct labels (`basis`, `confidence` — RD-02, never merged into one badge) plus one of three states — a source link with date-checked, a "computed from N input figures" note (an aggregate's own provenance IS its input tree, never falsely called unavailable), or an explicit "provenance unavailable" statement naming what's missing (a genuine leaf dead end).
- Built `app/services/provenance.py`: `figure_provenance_state` classifies a figure's reachable provenance into exactly that three-way split; `collect_distinct_figures`/`collect_rate_figures` walk the real recursive `Figure` DAG (mirroring `tests/test_route_a_basis_walk.py`'s own established walk shape, moved from a test-only helper into product code) to derive the leaf-level rate list, deduplicated by content rather than `figure_id`.
- Built `GET /assumptions` (PRV-04) in `app/routers/methodology.py`: reuses `app.services.compare.build_comparison` completely unchanged (the identical pipeline `/compare` calls), then renders every city's totals and every rate that fed into them via `_figure.html`, plus the D-60 acknowledged-gaps list (`permanent_exclusions` + per-city `not_priced`) read straight off `engine.landed_cost.aggregate`'s own `LandedCost` — never re-declared, never a `$0` line.
- Built `app/static/provenance.css`, this plan's own stylesheet (06-02 owns `prodfin.css` this wave) — distinct basis/confidence tints, and a real print stylesheet: `break-inside: avoid` on every figure/row/section, `orphans`/`widows` control, and every source/methodology link prints its full URL as plain text after the link so a printed or PDF-exported copy stays auditable off-screen.
- Built `GET /methodology` (PRV-05) in the same router: a stable, query-string-invariant page (byte-identical regardless of query params) explaining the eight pipeline stages (grounded in each engine module's own `Stage [N]` docstring, nothing invented), the `sourced`/`estimated`/`modelling_assumption` basis vocabulary and why a total inherits its weakest input, why the two confidence vocabularies are never the same field, the three honest-refusal states, and the D-60 gap list (rendered from `engine.landed_cost.PERMANENT_EXCLUSIONS`/`COST_CATEGORIES` directly, never hand-typed).
- Proved, against real non-synthetic data (the default New York/Los Angeles/London floor comparison, confirmed via `data/cost_profiles/*.yaml`'s own comments to genuinely reach a `modelling_assumption`-basis leaf through `data/crew_tiers.yaml`'s department crew-share ratios): no bare numbers anywhere on the rendered assumptions page; the rendered rate list matches an INDEPENDENTLY re-walked Figure tree (a non-vacuity proof, not a tautological check against the same function under test); a city's `Total landed cost` never reports `sourced` when its own rate list contains a `modelling_assumption` input (D-59); the D-60 gaps list never renders a `$0` line.

## Task Commits

Each task was committed atomically:

1. **Task 1: `_figure.html` — the reusable provenance component (UI-06)** — `96fa30d` (feat) — app/templates/_figure.html, app/services/provenance.py, app/main.py
2. **Task 2: consolidated printable assumptions panel (PRV-04)** — `b3adfee` (feat) — app/routers/methodology.py, app/templates/assumptions.html, app/static/provenance.css, tests/test_app_provenance.py
3. **Task 3: methodology page (PRV-05)** — `720b42e` (feat) — app/templates/methodology.html, tests/test_app_methodology.py

**Plan metadata:** committed alongside this SUMMARY.

## Files Created/Modified

- `app/templates/_figure.html` - The one macro every money figure on these surfaces renders through; three-way provenance state, two distinct basis/confidence labels
- `app/services/provenance.py` - `figure_provenance_state`, `collect_distinct_figures`, `collect_rate_figures`, `CityRateSheet`, `build_rate_sheet(s)` — the Figure-tree walk
- `app/routers/methodology.py` - `GET /assumptions` (PRV-04) and `GET /methodology` (PRV-05); no pricing logic of its own
- `app/templates/assumptions.html` - Per-city totals, every rate used, and the D-60 gaps list, all rendered through `_figure.html`
- `app/templates/methodology.html` - The stable, comparison-independent explanation page
- `app/static/provenance.css` - This plan's own stylesheet, including a real print stylesheet
- `app/main.py` - One import + one `include_router` line registering the new router
- `tests/test_app_provenance.py` - 21 tests covering the macro, the Figure-tree walk, and `GET /assumptions`
- `tests/test_app_methodology.py` - 12 tests covering `GET /methodology`

## Decisions Made

- **Both new routes live in one router file (`app/routers/methodology.py`)** — the plan's `files_modified` list named only this one router file for both new provenance surfaces; `/assumptions` deliberately duplicates `app/routers/compare.py::get_compare`'s own `Query(...)` parameter-by-parameter signature rather than importing a shared dependency from a sibling-owned file, following this repo's established per-module duplication discipline (the same pattern `_PRESCRIPTIVE_VOCABULARY` already uses across multiple test files).
- **A "rate" for PRV-04's panel is a LEAF Figure only** (no further `.inputs`) — an aggregate/subtotal is never listed as a rate, since its own provenance is the disclosure of its inputs, not a citable rate in its own right. Documented in `app/services/provenance.py`'s own docstring.
- **`figure_provenance_state` is a three-way classification** (`sourced` / `computed` / `unavailable`), refining a literal first reading of the plan's "no reachable provenance renders as unavailable" wording. An aggregate Figure (e.g. `total_landed_cost`) deliberately carries `source_url=None` because its source IS its disclosed input tree (per `engine/landed_cost.py`'s own construction); labelling that "provenance unavailable" would be dishonest in the opposite direction — claiming a dead end that isn't one. Only a genuine leaf with no `source_url` is `unavailable`.
- **`app/static/provenance.css` is a separate stylesheet**, not an edit to `prodfin.css` (06-02 owns it this wave per the file-ownership instructions) — loaded alongside `prodfin.css` so this plan's templates still inherit the shared design tokens without a merge conflict.
- **Task 1's "walks the rendered comparison HTML" verify criterion is realized against `GET /assumptions`** (a file this plan owns, and itself a rendering of the current comparison's figures) plus standalone macro rendering via Jinja's `Template.module` — not against `/compare` or `_ranked_list.html`, which 06-02 owns exclusively this wave and this plan never touches.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pydantic v2's `ValidationError.errors()` crashes the JSON encoder with a 500 instead of returning the intended 422**
- **Found during:** Task 2, writing `test_get_assumptions_query_string_bounds_candidate_cities`
- **Issue:** `CompareInputs`'s `_candidate_city_count_within_bound` model validator raises a plain `ValueError`, which pydantic v2 wraps into a `ValidationError` whose default `.errors()` embeds the ORIGINAL raw exception object under `ctx.error`. Passing that dict straight to `HTTPException(detail=exc.errors())` crashes Starlette's JSON encoder (`TypeError: Object of type ValueError is not JSON serializable`) — a 500, not the intended readable 422.
- **Fix:** `exc.errors(include_context=False)` in `app/routers/methodology.py::get_assumptions` — strips the non-serializable `ctx` field, keeping `type`/`loc`/`msg`/`input`.
- **Files modified:** app/routers/methodology.py
- **Verification:** `test_get_assumptions_query_string_bounds_candidate_cities` passes (422, not 500)
- **Committed in:** b3adfee

---

**Total deviations:** 1 auto-fixed (1 bug, discovered while writing a new test — genuinely new coverage, not a regression in existing behavior)
**Impact on plan:** Necessary for correctness (a crash on invalid input is worse than the readable 422 it was meant to be). No scope creep.

## Issues Encountered

- **The identical pattern exists in `app/routers/compare.py::get_compare`** (06-02's file, not owned or edited by this plan): its own `except ValidationError as exc: raise HTTPException(status_code=422, detail=exc.errors())` has the SAME `ctx`-embeds-a-raw-exception bug, confirmed by direct reproduction — `GET /compare` with more than `MAX_CANDIDATE_CITIES` (12) candidate cities currently 500s instead of returning a 422. This plan does not fix it (file ownership: `app/routers/compare.py` is 06-02's file this wave) but flags it here for visibility — the fix, if wanted, is the identical one-line change: `exc.errors(include_context=False)`.
- **No auth gates.** No external service was reached; both new routes are pure server-rendered Jinja over already-computed data.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `app/services/provenance.py`'s `figure_provenance_state`/`collect_rate_figures`/`build_rate_sheet(s)` are generic over any `RankedCity`/`Figure` and carry no dependency on `/assumptions` or `/methodology` specifically — later plans (06-04, 06-05, or Phase 8's proof panel) can reuse them directly.
- `app/templates/_figure.html`'s `render_figure` macro is import-ready from any template via `{% from "_figure.html" import render_figure %}` — a future plan that widens `_ranked_list.html` or `compare.html` with per-figure provenance links (beyond the current inline basis/confidence spans 06-01 already added) can adopt it without new plumbing.
- Golden totals (NY $758,427 / LA $693,521 / London GBP 548,595 = $747,735 / NY-vs-LA gap $64,906) are confirmed byte-identical; `tests/test_golden_cost.py` and `tests/test_route_a_basis_walk.py` are both unedited (empty diff confirmed against the pre-plan commit).
- Full suite: 803 passed (up from the 06-01 tracer's baseline of 770 — this plan added 33 tests). `vendor-scan.sh` and `lockfile-scan.sh` both clean.
- One discovered issue outside this plan's ownership is documented above under "Issues Encountered" for the next plan/reviewer to see: `app/routers/compare.py`'s over-limit `candidate_cities` path currently 500s where a 422 is intended.

---
*Phase: 06-the-interface*
*Completed: 2026-09-09*

## Self-Check: PASSED
