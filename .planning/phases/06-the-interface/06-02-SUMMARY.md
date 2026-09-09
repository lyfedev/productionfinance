---
phase: 06-the-interface
plan: 02
subsystem: ui
tags: [fastapi, jinja2, maplibre-gl, honesty-gates, d-55, d-56, ui-03, ui-05]

requires:
  - phase: 06-the-interface
    provides: "06-01's /compare tracer — CompareInputs, Comparison, build_comparison, to_geojson, the D-55 two-band ranked list, compare.html/_ranked_list.html, prodfin.css, compare.js"
  - phase: 04-cost-localization-landed-cost-outputs
    provides: "engine.gap.decompose_gap, engine.cost_localizer.localize/quarter_start_date's quarter-level date resolution, the GSA month-banded per-diem data New York's own seasonal swing rides on"
provides:
  - "UI-03: a start-date slider (POST /api/v1/compare + a no-JS GET /compare?start_index=N fallback) that re-ranks live against a real, server-priced date — never a client-computed figure"
  - "UI-05: a two-city gap picker (GapOption/GapSelection/resolve_gap_selection) that refuses to compute a gap across the D-55 band boundary, rendering an explicit reason instead of a number"
  - "app/services/compare.py — SLIDER_QUARTERS, slider_options, resolve_start_index, resolve_gap_selection, CompareInputs.start_index/gap_city_a/gap_city_b, Comparison.gap_selection/slider_options/slider_current_index"
  - "POST /api/v1/compare's JSON response now also carries ranked_list_html (a server-rendered fragment) and gap/slider blocks"
affects: [06-03, 06-04, 06-05]

actuals:
  tokens: 14866
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "A settled slider position is sent to the server as an index into a fixed, committed SLIDER_QUARTERS sequence, never a raw date the client derived itself — the server resolves index -> (start_quarter, start_year) via the SAME CompareInputs validator both the GET query-string path and the POST JSON path share, so there is exactly one date-resolution code path, not two."
    - "The settled-slider JS update injects a server-rendered HTML fragment (Jinja's own _ranked_list.html, rendered standalone via templates.get_template(...).render(...)) rather than re-implementing this page's own formatting/templating logic in JavaScript — the client never becomes a second, divergent source of truth for what a figure looks like, only for what DOM node it lands in."
    - "UI-05's band-honesty gate is a product-level policy layered ON TOP of engine.gap.decompose_gap (which has no opinion about D-55 bands at all) — resolve_gap_selection checks both selected cities are net_ranked BEFORE ever calling decompose_gap, so a cross-band gap is structurally unreachable through this surface, not merely discouraged."

key-files:
  created:
    - tests/test_app_compare_slider.py
    - tests/test_app_compare_gap.py
  modified:
    - app/services/compare.py
    - app/routers/compare.py
    - app/templates/compare.html
    - app/static/compare.js
    - app/static/prodfin.css

key-decisions:
  - "SLIDER_QUARTERS is 3 quarters (Q4 2025, Q1 2026, Q2 2026), not the 4 originally planned. Q3 2026 was excluded after discovering that engine.sensitivity.sensitivity_rows' own 'start_quarter advanced by one' mutation row re-prices the NEXT quarter forward uncaught — for a Q3 2026 base date that lands on Q4 2026 (Oct 1), past data/union_rates/iatse.yaml's committed us-ny camera row's effective_to: 2026-08-01 boundary (WINDOWS #9), raising an unhandled ValueError. This is a genuine, reproducible pre-existing gap in engine/sensitivity.py (outside this plan's files_modified), not something introduced by this plan — recorded as WINDOWS #34 rather than routed around silently or fixed out of scope."
  - "UI-05's refusal is a NEW policy layer in app/services/compare.py (resolve_gap_selection), not a change to engine.gap.decompose_gap — that function already computes a genuinely cost-only, apples-to-apples gap regardless of band (it never touches an incentive figure at all), and app/services/spec.py's own pre-existing _gap_for_ranked_cities (untouched by this plan, protects the golden NY-vs-LA $64,906 regression figure) already relies on that band-agnostic behavior. The NEW two-city SELECTOR this plan adds is a different UX than /spec's fixed first-two-cities gap — it lets a visitor pick ANY pair, including a mismatched one, so THIS surface adds its own gate rather than widening decompose_gap's own contract."
  - "The settled-slider JS update injects a server-rendered HTML fragment for the ranked list, but does NOT live-update the gap section — the gap picker is a separate form with its own GET submit, and its own rendered section states which start date its numbers reflect. Scoped intentionally: the plan's own Task 2 names only 'the ranked list and the map colour ramp' as what the slider updates live."

coverage:
  - id: D1
    description: "UI-03: a settled slider position re-ranks live via POST /api/v1/compare, and every figure returned matches an independent, direct build_comparison rebuild at the exact same resolved date"
    requirement: "UI-03"
    verification:
      - kind: integration
        ref: "tests/test_app_compare_slider.py#test_two_different_start_indices_price_new_york_differently"
        status: pass
      - kind: integration
        ref: "tests/test_app_compare_slider.py#test_settled_slider_position_matches_a_direct_server_side_rebuild"
        status: pass
    human_judgment: true
    rationale: "The live drag-and-debounce interaction (compare.js) and the map colour ramp's visual re-render were exercised via the JSON contract and the fallback GET path in automated tests, but the actual dragging feel, debounce timing and MapLibre re-paint require a human in a real, non-headless WebGL2 browser to confirm — same caveat 06-01's own map coverage (D2) already carries."
  - id: D2
    description: "UI-03 (no-JS): the slider exists as a genuine native <input type=\"range\"> inside a plain <form method=\"get\">, and a plain GET carrying start_index re-ranks the fully server-rendered page with no script engine involved at all"
    requirement: "UI-03"
    verification:
      - kind: integration
        ref: "tests/test_app_compare_slider.py#test_slider_is_a_genuine_native_range_input_never_js_only"
        status: pass
      - kind: integration
        ref: "tests/test_app_compare_slider.py#test_get_compare_start_index_no_js_path_reranks_the_server_rendered_page"
        status: pass
    human_judgment: false
  - id: D3
    description: "UI-05: selecting any two cities renders the decomposed gap — headline plus named, signed components summing exactly to the headline"
    requirement: "UI-05"
    verification:
      - kind: unit
        ref: "tests/test_app_compare_gap.py#test_two_net_ranked_cities_produce_components_summing_exactly_to_the_headline"
        status: pass
      - kind: unit
        ref: "tests/test_app_compare_gap.py#test_resolve_gap_selection_defaults_to_the_first_two_ranked_ids_in_order"
        status: pass
    human_judgment: false
  - id: D4
    description: "UI-05 honesty: a gap may only be computed between two net_ranked cities — an unmodelled city in the pair renders an explicit refusal, never a computed number. Proven against the REAL committed floor-city set, where this is the default state (only New York is net_ranked)."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "tests/test_app_compare_gap.py#test_default_comparison_gap_picker_refuses_the_only_real_pair_available"
        status: pass
      - kind: integration
        ref: "tests/test_app_compare_gap.py#test_explicit_modelled_and_unmodelled_selection_also_refuses"
        status: pass
      - kind: integration
        ref: "tests/test_app_compare_gap.py#test_json_endpoint_carries_the_refusal_and_no_decomposition"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-78 golden totals byte-identical; golden test file and D-63 basis-walk guard file both unedited"
    verification:
      - kind: unit
        ref: "tests/test_golden_cost.py"
        status: pass
      - kind: unit
        ref: "tests/test_route_a_basis_walk.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "[Rule 1] POST /api/v1/compare's 422 error path no longer 500s on a validator-raised ValueError (pydantic-core's ctx.error embeds the raw exception object, which json.dumps cannot serialize)"
    verification:
      - kind: integration
        ref: "tests/test_app_compare_slider.py#test_post_compare_json_invalid_payload_returns_422_json_never_a_500"
        status: pass
      - kind: integration
        ref: "tests/test_app_compare_slider.py#test_get_compare_over_cap_candidate_cities_returns_422_json_never_a_500"
        status: pass
    human_judgment: false

duration: ~70min
completed: 2026-09-09
status: complete
---

# Phase 6 Plan 2: The Start-Date Slider and the Decomposed Two-City Gap Summary

**A start-date slider that re-ranks live against a real server-priced quarter (never a client-computed figure), and a two-city gap picker whose refusal — not a number — is what the live default floor-city set actually shows, because only New York is net_ranked today.**

## Performance

- **Duration:** ~70 min (session start time not explicitly captured; estimated from work performed)
- **Started:** ~2026-09-09T12:55:00Z (approx.)
- **Completed:** 2026-09-09T14:05:00Z
- **Tasks:** 3
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- **UI-03 — server-side dated re-ranking.** `CompareInputs.start_index` resolves to a real `(start_quarter, start_year)` pair via `resolve_start_index`, shared identically by the GET query-string path and the POST JSON path (one date-resolution code path, not two). `SLIDER_QUARTERS` is three real, sourced quarters (Q4 2025 / Q1 2026 / Q2 2026) bounded to the exact months `data/per_diem/gsa/us-ny-new-york-county.yaml`'s `lodging_by_month` actually publishes — New York's total genuinely moves (real values: $579,388 / $551,149 / $568,820) across the three positions, proven both via a direct JSON round-trip and an independent `build_comparison` rebuild at the same resolved date.
- **UI-03 — the slider, progressively enhanced.** A native `<input type="range" name="start_index">` inside a plain `<form method="get">`, carrying every other comparison input forward as hidden fields. Works with JavaScript entirely disabled (proven via `TestClient`, which executes no script at all) — the form submits and returns a correctly re-ranked, server-rendered page. `app/static/compare.js` debounces settled positions, POSTs to `/api/v1/compare`, and injects the response's `ranked_list_html` — the SAME `_ranked_list.html` Jinja template a full page load renders, standalone-rendered server-side — rather than re-implementing this page's own formatting in JavaScript. The map's GeoJSON source and colour-ramp min/max are re-pointed from the same response.
- **UI-05 — the decomposed two-city gap.** `resolve_gap_selection` layers a product-level band-honesty gate on top of the already-proven `engine.gap.decompose_gap`: a gap is computed only when both selected cities are `net_ranked`; otherwise an explicit refusal names why, never a number. With the real committed floor-city set (New York, Los Angeles, London) only New York is `net_ranked` — the refusal is what the DEFAULT gap-picker state actually shows on the live surface, proven directly against real data rather than a synthetic-only fixture. A single unpriced/absent-second-city case gets its own distinct refusal reason. The "two genuinely modelled cities" working path is proven with controlled synthetic banding (both real committed NY/LA cost profiles tagged `net_ranked`, mirroring `tests/test_engine_gap.py`'s own established convention): the returned components sum EXACTLY to the headline gap.
- **[Rule 1 deviation, flagged by the orchestrator mid-plan] A pre-existing pydantic-core/FastAPI serialization bug.** `except ValidationError: raise HTTPException(..., detail=exc.errors())` (bare) crashes at RESPONSE-render time on the `GET /compare` path — `json.dumps` cannot serialize the raw `ValueError` instance pydantic-core embeds in a validator error's `ctx.error`. Fixed on both `GET /compare` and `POST /api/v1/compare` with `exc.errors(include_context=False)`, mirroring the identical fix the concurrent 06-03 sibling independently applied in its own router. Tested on both the surface that actually crashed (GET, over-cap `candidate_cities`) and the surface the coordinator specifically asked to cover (POST, both over-cap and out-of-range `start_index`).

## Task Commits

Each task was committed atomically (the two-task split below reflects how the plan's Task 1/Task 2 boundary maps onto the actual, tightly-coupled slider implementation — see Decisions Made):

1. **Task 1: server-side dated re-ranking** — `54971f1` (feat) — `app/services/compare.py`, `app/routers/compare.py`, `tests/test_app_compare_slider.py` (partial: the server-logic tests)
2. **[Rule 1 fix, coordinator-flagged]** — `d32cd7d` (fix) — `app/routers/compare.py`, `tests/test_app_compare_slider.py` (the 422-not-500 tests)
3. **Task 2: the slider, progressively enhanced** — `c880c71` (feat) — `app/templates/compare.html`, `app/static/compare.js`, `app/static/prodfin.css`, `tests/test_app_compare_slider.py` (the remaining markup tests)
4. **Task 3: the decomposed two-city gap** — `d96db11` (test) — `tests/test_app_compare_gap.py` (the gap picker's own production code — `GapOption`/`GapSelection`/`resolve_gap_selection` in `compare.py`, the JSON block in `routers/compare.py`, and the gap form/table in `compare.html`/`prodfin.css` — landed inside commits 1 and 3 above, since it shares the same dataclass/template files as the slider work; this commit adds Task 3's own dedicated test coverage)

**Plan metadata:** (this commit)

_Note: no TDD RED/GREEN split — this plan's tasks are `type="auto"`, not `tdd="true"`._

## Files Created/Modified

- `app/services/compare.py` — `SLIDER_QUARTERS`, `slider_options`, `resolve_start_index`, `_current_slider_index`, `CompareInputs.start_index`/`gap_city_a`/`gap_city_b`, `GapOption`, `GapSelection`, `resolve_gap_selection`, `Comparison.gap_selection`/`slider_options`/`slider_current_index`
- `app/routers/compare.py` — `GET /compare` accepts `start_index`/`gap_city_a`/`gap_city_b`; `POST /api/v1/compare`'s JSON response gains `gap`, `slider`, and `ranked_list_html`; both handlers' error paths fixed (`include_context=False`)
- `app/templates/compare.html` — the slider section (native range input, hidden carry-forward fields, embedded slider-options JSON), the ranked-list container wrapper, the two-city gap-picker form and decomposed-gap/refusal rendering
- `app/static/compare.js` — debounced settled-slider fetch, `ranked_list_html` DOM injection, live map GeoJSON/colour-ramp update
- `app/static/prodfin.css` — slider and gap-picker section styling
- `tests/test_app_compare_slider.py` — UI-03 coverage (created)
- `tests/test_app_compare_gap.py` — UI-05 coverage (created)

## Decisions Made

- **`SLIDER_QUARTERS` is 3 quarters, not 4** — see coverage/deviations. Excluding Q3 2026 is a scope decision (the fix belongs in `engine/sensitivity.py`, outside this plan's `files_modified`), recorded as WINDOWS #34, not silently routed around.
- **UI-05's refusal lives in `app/services/compare.py`, not `engine/gap.py`** — `decompose_gap` itself stays band-agnostic (matching its existing, tested, cost-only contract that `app/services/spec.py`'s pre-existing `_gap_for_ranked_cities` already relies on for the golden NY-vs-LA gap); the NEW two-city picker this plan adds is a different UX (visitor-selectable, not fixed-first-two) and gets its own gate.
- **The settled-slider JS update injects a server-rendered HTML fragment**, not a client-side re-formatting of JSON figures — the one architectural choice in this plan most directly answering "the client must never compute a cost figure": it doesn't even reformat one.
- **The gap section is not live-updated by the slider** — scoped to match the plan's own Task 2 wording ("Update the ranked list and the map colour ramp"); the gap section states which start date its own numbers reflect.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Q3 2026 excluded from `SLIDER_QUARTERS` — a pre-existing `engine/sensitivity.py` gap crashes on it**
- **Found during:** Task 1, while verifying all four originally-planned slider positions priced successfully
- **Issue:** `data/union_rates/iatse.yaml`'s only committed `us-ny` camera row (`iatse-l600-camera-us-ny-2025`) carries `effective_to: "2026-08-01"` with no 2026-2027 successor (WINDOWS #9, pre-existing, unrelated to this plan). `app/services/spec.py::_quarter_invariance_for_city` already catches the resulting `ValueError` gracefully and excludes that quarter from its own measurement — but `engine.sensitivity.sensitivity_rows`' `_price_pair` (the "start_quarter advanced by one" mutation row) does NOT catch it. A base date of Q3 2026 advances to Q4 2026 (Oct 1) for that one sensitivity row, crossing the boundary uncaught, and crashes with an unhandled `ValueError` all the way to a raw exception — reproduced directly on plain `main`, before any of this plan's changes, via `SpecFormSubmission(start_quarter="Q3", start_year=2026)`.
- **Fix:** Scoped `SLIDER_QUARTERS` to the three quarters whose own "advanced by one" sensitivity row stays inside the covered range (Q4 2025, Q1 2026, Q2 2026) — documented inline in `app/services/compare.py` with the exact reasoning. Did NOT touch `engine/sensitivity.py` (outside this plan's `files_modified`; the real fix is a defensive `except ValueError: continue` there, mirroring `_quarter_invariance_for_city`'s own established pattern).
- **Files modified:** `app/services/compare.py`
- **Verification:** all 3 remaining slider positions price successfully with genuinely different New York totals (`tests/test_app_compare_slider.py::test_two_different_start_indices_price_new_york_differently`)
- **Recorded:** WINDOWS ledger entry #34 (`kind: deviation`)
- **Committed in:** `54971f1`

**2. [Rule 1 - Bug] `except ValidationError: raise HTTPException(..., detail=exc.errors())` (bare) 500s instead of 422ing**
- **Found during:** Task 1, writing the out-of-range `start_index` test for `GET /compare`
- **Issue:** pydantic-core embeds the raw `ValueError` instance itself under `ctx.error` for a `model_validator`-raised error constructed via a direct `Model(**kwargs)` call (exactly what `get_compare` does) — `json.dumps` cannot serialize that object, so `http_exception_handler`'s own `JSONResponse(...)` construction raises `TypeError` while rendering the 422, surfacing as an unhandled 500. Confirmed pre-existing and reproducible on plain `main` before this plan's changes, via `GET /compare` with 13 `candidate_cities` (the already-existing `MAX_CANDIDATE_CITIES` validator).
- **Fix:** `exc.errors(include_context=False)` on `GET /compare`'s except block (fixed inline as part of Task 1's own `start_index` bound check). **The coordinator subsequently flagged that the identical bare pattern remained on `POST /api/v1/compare`'s except block** — missed because that block's original text lacked the comment my first `replace_all` edit matched against. Fixed the same way there too, even though the POST JSON-body path did not independently reproduce the crash (FastAPI's own body-validation construction path apparently produces an empty, serializable `ctx.error` for the same validator — the fix is still correct and strictly safer there regardless of which internal pydantic-core code path constructs the model).
- **Files modified:** `app/routers/compare.py`
- **Verification:** `tests/test_app_compare_slider.py::test_post_compare_json_invalid_payload_returns_422_json_never_a_500`, `::test_get_compare_over_cap_candidate_cities_returns_422_json_never_a_500`
- **Committed in:** `54971f1` (GET), `d32cd7d` (POST, coordinator-flagged follow-up)

---

**Total deviations:** 2 auto-fixed (1 blocking scope decision recorded to WINDOWS, 1 bug fix — the second half coordinator-flagged mid-plan)
**Impact on plan:** Both necessary for correctness; the slider ships with 3 real positions instead of 4 (a real, sourced, honestly-scoped range, not a silently narrower one), and the error path is genuinely fixed on both routes this plan owns. No scope creep — neither touched a file outside `files_modified`, and neither touched any pricing engine module.

## Issues Encountered

- **Real committed data never produces two `net_ranked` cities today.** Only New York has a committed rule file among the D-54 floor cities (`data/cost_profiles/us-ca-los-angeles.yaml` and `gb-london.yaml` both deliberately keep `jurisdiction_id: null`, per the regression guard). This means UI-05's "working" (non-refusal) path cannot be demonstrated live through the real `/compare` surface with default data at all — only its refusal path can, which is itself an honest and meaningful default state to ship, not a gap in this plan. The working path is proven via controlled synthetic banding of the same two real committed cost profiles, mirroring `tests/test_engine_gap.py`'s own established convention (see `test_two_net_ranked_cities_produce_components_summing_exactly_to_the_headline`). This will resolve automatically once a later phase/plan commits a second `net_ranked` city (e.g. once California or the UK gain a rule file).
- **`docs/sdk-call-sites.md` `--check` shows DRIFT — not caused by this plan.** The concurrent 06-03 sibling's already-committed `GET /assumptions` route (`afd0eb8`/`bd90adc`, both landed on `main` before this plan started) reaches the same `agent/live_checks.py:119` `.search()` call site `GET /compare`/`POST /api/v1/compare` already reach, but that plan's own commits never regenerated `docs/sdk-call-sites.md` to list it. Confirmed via `git log --oneline -- docs/sdk-call-sites.md` (last touched by 06-01's `55e572a`) and by reverting this plan's own diff entirely and re-running `--check` (drift persists identically). This plan's own reachability set for `GET /compare`/`POST /api/v1/compare` is byte-identical to 06-01's. **Not fixed here** — regenerating and committing it would misattribute the sibling's route to this plan's commit; it is 06-03's own obligation. Flagged for the orchestrator to route back to 06-03 or resolve centrally.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `CompareInputs`/`Comparison` both widen additively — `start_index`/`gap_city_a`/`gap_city_b` and `gap_selection`/`slider_options`/`slider_current_index` are new fields, nothing removed or renamed. 06-04/06-05 extend the same surface unchanged.
- Golden totals (NY $758,427 cost-only / LA $693,521 / London GBP 548,595 = $747,735 / NY-vs-LA gap $64,906) confirmed byte-identical; `tests/test_golden_cost.py` and `tests/test_route_a_basis_walk.py` both unedited.
- `docs/sdk-call-sites.md` drift (pre-existing, from 06-03) should be resolved before `/gsd-ship` — see Issues Encountered.
- WINDOWS #34 (new) documents a real, reproducible `engine/sensitivity.py` gap worth fixing in a future plan that touches `engine/sensitivity.py` — a one-line defensive `except ValueError: continue` in `_price_pair`, mirroring `_quarter_invariance_for_city`'s own established pattern.
- No blockers to 06-03/06-04/06-05.

---
*Phase: 06-the-interface*
*Completed: 2026-09-09*

## Self-Check: PASSED
