---
phase: 08-demo-proof-export-submission
plan: 02
subsystem: ui
tags: [fastapi, jinja2, export, demo, honesty-refusal, D-101]

requires:
  - phase: 06-comparison-surface-and-currency
    provides: "app/services/compare.py::build_comparison, CompareInputs, GapSelection/resolve_gap_selection — the unchanged pipeline both /export and /demo's DMO-02/03 build on"
  - phase: 06-comparison-surface-and-currency
    provides: "app/services/provenance.py::build_rate_sheets/collect_rate_figures, app/templates/_figure.html::render_figure — reused verbatim for every figure UI-09 renders"
  - phase: 08-demo-proof-export-submission
    provides: "08-01's /proof panel (DMO-01) and Phase 7's /research page (DMO-04) — both linked to from /demo rather than rebuilt"
provides:
  - "GET /export — UI-09's self-contained, server-rendered export document (the two-band ranked list, the decomposed gap or its stated refusal, every figure's source and date, the model-wide assumptions, the D-60 acknowledged-gaps list)"
  - "GET /demo — the four demo beats (DMO-01..04) staged on one page"
  - "app.services.export.build_export_document / app.services.demo.naive_arithmetic_example / app.services.demo.rate_ranking_inversion"
affects: ["08-03", "SHP-11/SHP-12 (the written description can now point at a live, showable /demo URL)"]

actuals:
  tokens: 16000
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Split router file across two atomic commits (Task 1's /export alone, then Task 2+3's /demo added to the same file) rather than one combined commit — each commit independently imports and passes tests, no half-broken intermediate state."
    - "DMO-02/DMO-03 reuse two ALREADY-ESTABLISHED direct-engine-call patterns rather than inventing a third: price_jurisdiction (DMO-02, mirrors tests/test_engine_net_cash.py's own UK worked-example regression) and the compute_qualifying_base + compute_gross_credit two-step app/services/proof.py established for a gross-credit-only comparison (DMO-03, applied here across all four curated jurisdictions on one shared illustrative spend instead of one pair's own disclosed spend)."
    - "DMO-03's honesty gate: convert_to_net_cash is attempted in its own try/except, separate from the always-computable qualifying-base/gross-credit step — the identical ValueError app/services/validate.py::reproduce_disclosure already catches for New Jersey/Connecticut's unsourced transfer-discount ceiling (WINDOWS.md #3), reused rather than re-derived."

key-files:
  created:
    - app/services/export.py
    - app/services/demo.py
    - app/routers/export.py
    - app/templates/export_document.html
    - app/templates/demo.html
    - app/static/export.css
    - app/static/demo.css
    - tests/test_app_export.py
    - tests/test_demo_beats.py
  modified:
    - app/main.py
    - app/templates/index.html

key-decisions:
  - "DMO-02 uses the committed engine-correctness regression fixture tests/fixtures/jurisdictions/synthetic-uk-style.yaml (the exact £18M worked example PROJECT.md/feasibility-incentives.md cite) rather than fabricating a new one or omitting the beat — its own header comment forbids presenting it as a model of the UK's real programme, so every render carries an explicit illustrative-arithmetic-example disclaimer naming that constraint; the naive/correct/overstatement figures are all computed live via engine.pipeline.price_jurisdiction, never hardcoded (verified: naive 9,540,000, correct net cash 5,382,000, 43.6% overstatement — rounds to the brief's cited 44%)."
  - "DMO-03's inversion is built from real, currently-priceable data rather than an invented ranking: only New York (of the four curated jurisdictions) has a headline rate below New Jersey/Connecticut's, yet is one of only two jurisdictions (with California) whose real net cash is confirmable at this spend — New Jersey and Connecticut's transferable mechanism has an unsourced/partial discount ceiling and the engine correctly refuses to convert. New York moving from LAST (headline rate) to tied-second (real net cash), overtaking two higher-headline-rate jurisdictions once honesty is required, is the inversion shown — genuinely computed, not staged."
  - "DMO-04 renders agent.settings.integration_status().not_configured_message() verbatim rather than a custom message — this is the SAME text /research itself renders, so the two surfaces can never tell a diverging story about why the beat is unavailable. Verified both branches directly: unconfigured (real, current state) and configured (test-only, monkeypatched) to prove the conditional is real, not a permanently-hardcoded unavailable state."
  - "Split the router-file commit into two (Task 1: /export alone; Task 2+3: /demo added to the same file) rather than the plan's literal Task 2/Task 3 boundary — DMO-02/03 and DMO-04 share one route function and one template by design ('stage the four demo beats... on one page'), and an artificial split would have required committing app/routers/export.py in a state that ImportErrors (app/services/demo.py not yet existing) — every intermediate commit imports cleanly and passes its own tests."

requirements-completed: [UI-09, DMO-02, DMO-03, DMO-04]

coverage:
  - id: D1
    description: "A comparison exports as a self-contained, server-rendered document (GET /export): the two-band ranked list, the decomposed gap or its stated refusal, every figure's source and date, the model-wide assumptions, and the D-60 acknowledged-gaps list — complete without JavaScript."
    requirement: "UI-09"
    verification:
      - kind: integration
        ref: "tests/test_app_export.py#test_get_export_contains_no_script_tag_at_all"
        status: pass
      - kind: integration
        ref: "tests/test_app_export.py#test_get_export_renders_the_golden_default_comparison_totals"
        status: pass
      - kind: integration
        ref: "tests/test_app_export.py#test_get_export_names_every_d60_permanent_exclusion"
        status: pass
      - kind: integration
        ref: "tests/test_app_export.py#test_get_export_never_shows_a_zero_dollar_incentive_for_an_unmodelled_city"
        status: pass
      - kind: integration
        ref: "tests/test_app_export.py#test_get_export_every_figure_carries_a_provenance_state"
        status: pass
      - kind: unit
        ref: "tests/test_app_export.py#test_build_export_document_generated_at_is_a_real_fresh_timestamp"
        status: pass
    human_judgment: false
  - id: D2
    description: "DMO-02: a case where naive percentage arithmetic is badly wrong, showing both the naive and correct figures and the reason for the divergence, using real committed data (the exact £18M UK worked example), never a fabricated overstatement percentage."
    requirement: "DMO-02"
    verification:
      - kind: unit
        ref: "tests/test_demo_beats.py#test_naive_arithmetic_example_matches_the_real_engine_regression_value"
        status: pass
      - kind: unit
        ref: "tests/test_demo_beats.py#test_naive_arithmetic_example_overstatement_is_approximately_44_percent"
        status: pass
      - kind: unit
        ref: "tests/test_demo_beats.py#test_naive_arithmetic_example_never_claims_to_model_the_real_uk_programme"
        status: pass
      - kind: integration
        ref: "tests/test_demo_beats.py#test_get_demo_renders_the_naive_and_correct_uk_example_figures"
        status: pass
    human_judgment: false
  - id: D3
    description: "DMO-03: a ranking that inverts once net cash replaces headline rate, with both orderings rendered so the inversion is legible rather than asserted, and no fabricated net-cash figure for a jurisdiction whose conversion is unsourced."
    requirement: "DMO-03"
    verification:
      - kind: unit
        ref: "tests/test_demo_beats.py#test_rate_ranking_inversion_headline_order_matches_declared_rates"
        status: pass
      - kind: unit
        ref: "tests/test_demo_beats.py#test_rate_ranking_inversion_new_york_moves_up_once_net_cash_is_required"
        status: pass
      - kind: unit
        ref: "tests/test_demo_beats.py#test_rate_ranking_inversion_never_fabricates_a_net_cash_figure_for_an_unsourced_discount"
        status: pass
      - kind: integration
        ref: "tests/test_demo_beats.py#test_get_demo_renders_both_orderings"
        status: pass
    human_judgment: false
  - id: D4
    description: "DMO-04: a city with no curated model researched live, wired onto the demo page — and, because PARALLEL_API_KEY/GEMINI_API_KEY are absent on this host, an explicit unavailable state naming the missing credential (D-101), never faked, pre-recorded, or stubbed."
    requirement: "DMO-04"
    verification:
      - kind: integration
        ref: "tests/test_demo_beats.py#test_get_demo_dmo04_renders_the_not_configured_state_when_credentials_absent"
        status: pass
      - kind: integration
        ref: "tests/test_demo_beats.py#test_get_demo_dmo04_never_shows_a_progress_bar_or_spinner_when_unconfigured"
        status: pass
      - kind: integration
        ref: "tests/test_demo_beats.py#test_get_demo_dmo04_states_the_same_reason_the_research_page_itself_states"
        status: pass
      - kind: integration
        ref: "tests/test_demo_beats.py#test_get_demo_dmo04_offers_the_live_path_when_credentials_are_present"
        status: pass
    human_judgment: true
    rationale: "The absence of credentials is proven both automatically (a real environment check, exercised in both directions via monkeypatch) and by direct verification in this session (`env | grep` returned no PARALLEL_API_KEY/GEMINI_API_KEY on this host). D-101's actual stakes are visual/product-judgment ('does this read as an honest refusal, not a disguised failure, to a cold visitor') — a human should still look at the rendered /demo page before submission, per the ROADMAP's own SHP-13 cold-verification step."

duration: 70min
completed: 2026-09-09
status: complete
---

# Phase 8 Plan 2: The Export Document and the Four Demo Beats Summary

**A self-contained server-rendered export document (UI-09) plus a `/demo` page staging all four demo beats — the £18M UK worked example's real 43.6% overstatement, a genuine ranking inversion where New York overtakes New Jersey and Connecticut once real net cash replaces headline rate, and an explicit "not configured" state for the live-research beat since PARALLEL_API_KEY/GEMINI_API_KEY are absent on this host.**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-09-09T07:50:00-07:00
- **Completed:** 2026-09-09T09:00:00-07:00
- **Tasks:** 3
- **Files modified:** 11 (9 created, 2 modified)

## Accomplishments

- `GET /export` — a comparison's two-band ranked list, its decomposed gap (or, for the default candidate set today, the honest band-mismatch refusal — only New York has both a cost profile and a wired incentive rule model, so a real decomposition needs a second net-ranked city not yet in the repo), every figure rendered through the established `_figure.html` provenance component, the model-wide assumptions, and the full D-60 acknowledged-gaps list. Contains zero `<script>` tags, asserted directly in tests.
- `GET /demo` — DMO-01 (links to `/proof`) and DMO-04 (links to `/research`, or renders the exact `IntegrationStatus.not_configured_message()` text since credentials are absent) both reuse existing surfaces. DMO-02 prices the committed UK-style worked-example fixture through `engine.pipeline.price_jurisdiction` live: naive `9,540,000 GBP` vs a fully-derived, sourced `5,382,000 GBP` net cash figure, a **43.6%** overstatement computed at request time (rounds to the brief's cited 44%). DMO-03 prices all four curated jurisdictions (`us-ny`, `us-ca`, `us-nj`, `us-ct`) against one shared `$10,000,000` illustrative spend: by headline rate, California leads and New York sits last (25%, lowest); by real, computed net cash, only California and New York resolve at all — New Jersey and Connecticut's `transferable` mechanism has an unsourced/partial discount ceiling and the engine correctly refuses to convert (the same `ValueError` `app/services/validate.py::reproduce_disclosure` already catches for the identical reason, WINDOWS.md #3). New York moves from last to tied-second, overtaking both higher-headline-rate jurisdictions — a real inversion, both orderings rendered together.
- `app/services/demo.py` — new module (Rule 2-adjacent, disclosed below) holding DMO-02/03's assembly logic, introducing no new pricing logic of its own: every real number comes from `engine.pipeline.price_jurisdiction` or the identical `compute_qualifying_base` + `compute_gross_credit` two-step `app/services/proof.py` already established.

## Task Commits

1. **Task 1: the export document (UI-09)** — `ff3a5d6` (feat) — `app/services/export.py`, `app/routers/export.py`, `app/templates/export_document.html`, `app/static/export.css`, `app/main.py`, `app/templates/index.html`, `tests/test_app_export.py`
2. **Task 2+3: the four demo beats (DMO-02/03/04)** — `9d9d472` (feat) — `app/services/demo.py`, `app/routers/export.py` (extended with `/demo`), `app/templates/demo.html`, `app/static/demo.css`, `app/templates/index.html`, `tests/test_demo_beats.py`

**Plan metadata:** (this commit)

_Note: Tasks 2 and 3 landed in a single commit — see "Deviations from Plan" below for why an artificial split was rejected._

## Files Created/Modified

- `app/services/export.py` — `ExportDocument` dataclass + `build_export_document()`; reuses `app.services.compare.build_comparison` and `app.services.provenance.build_rate_sheets` unchanged.
- `app/services/demo.py` — `NaiveArithmeticExample`/`naive_arithmetic_example()` (DMO-02) and `JurisdictionRateRanking`/`RankingInversion`/`rate_ranking_inversion()` (DMO-03).
- `app/routers/export.py` — `GET /export`, `GET /demo`.
- `app/templates/export_document.html`, `app/templates/demo.html` — the two new pages, each with its own stylesheet.
- `app/static/export.css`, `app/static/demo.css` — new stylesheets (a sibling plan owns `prodfin.css` this wave); reuse `prodfin.css`'s custom properties and `provenance.css`'s established `.pf-figure`/`.pf-rate-sheet`/`.pf-gaps`/`.pf-noprint` classes rather than redefining them.
- `app/main.py` — registered the export router (1-line diff).
- `app/templates/index.html` — added "Demo" and "Export a comparison" links for discoverability.
- `tests/test_app_export.py`, `tests/test_demo_beats.py` — 33 tests total.

## Decisions Made

See `key-decisions` in the frontmatter above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Split the router-file commit into Task 1 / Task 2+3 rather than the plan's literal three-task boundary**
- **Found during:** preparing to commit Task 2 alone
- **Issue:** DMO-02/03 (Task 2) and DMO-04 (Task 3) share one route function (`GET /demo`) and one template (`demo.html`) by design — the plan itself frames all four beats as staged "on the demo page." `app/routers/export.py` imports `app.services.demo` at module level; committing only Task 2's half of `get_demo` (or Task 3's) would leave either an incomplete function or a commit that ImportErrors when checked out alone, breaking `app/main.py`'s import chain for the whole app.
- **Fix:** Committed Task 1 (`/export` alone, self-consistent, all its own tests passing) first, then Tasks 2 and 3 together as one commit (the complete `/demo` route, `app/services/demo.py`, `demo.html`, `demo.css`, and all DMO-02/03/04 tests) — every commit in this plan imports cleanly and its own tests pass when checked out in isolation.
- **Files modified:** `app/routers/export.py` (temporarily stripped of `get_demo` for the Task 1 commit, restored for Task 2+3), `app/templates/index.html` (temporarily stripped of the "Demo" link for the same reason)
- **Verification:** at the time of the Task 1 commit, `uv run python -c "import app.main"` succeeded and `pytest tests/test_app_export.py` passed 12/12 against the working tree in its Task-1-only state (before `get_demo`/`app/services/demo.py` were added back). Re-confirmed after the fact via `git show ff3a5d6:app/routers/export.py` and `git show ff3a5d6:app/templates/index.html` — neither references `app.services.demo`, `get_demo`, or a `/demo` link, proving the commit as recorded is self-consistent. Task 2+3's own `pytest tests/test_demo_beats.py` passed 21/21 against the final state.
- **Committed in:** `ff3a5d6`, `9d9d472`

**2. [Rule 2 - Missing Critical] Added `app/services/demo.py` as a new file not named in the plan's `files_modified`**
- **Found during:** Task 2 (DMO-02/03 assembly)
- **Issue:** The plan's `files_modified` names `app/services/export.py` but DMO-02/03's business logic is unrelated to the export document — putting it there would misname the module and blur its scope. No sibling-owned file conflicts with a new `app/services/demo.py`.
- **Fix:** Added `app/services/demo.py`, mirroring the established one-module-per-surface convention (`app/services/proof.py`, `app/services/validate.py`, `app/services/compare.py`).
- **Files modified:** `app/services/demo.py` (new)
- **Verification:** `git status --short` confirmed no sibling-owned files (`app/services/{permalink,currency_display,compare}.py`, `app/routers/compare.py`, `app/templates/{compare.html,_ranked_list.html}`, `app/static/prodfin.css`) were touched at any point in this plan.
- **Committed in:** `9d9d472`

**3. [Rule 2 - Missing Critical] Added "Demo" and "Export a comparison" links to `app/templates/index.html`**
- **Found during:** Task 1 and Task 2+3
- **Issue:** Without a link from the landing page, `/export` and `/demo` would be unreachable by a cold anonymous visitor — the same discoverability gap 08-01-SUMMARY.md documents fixing for `/proof`, and directly relevant to the ROADMAP's SHP-13 cold-verification step this phase exists to pass.
- **Fix:** Added two short linked sections in the same style as the existing route links on that page.
- **Files modified:** `app/templates/index.html`
- **Verification:** Manual `curl` of `/` confirms both links render; `tests/test_demo_beats.py::test_get_demo_dmo01_and_dmo04_link_to_their_own_existing_pages` confirms the reverse direction (the demo page itself links to `/proof` and `/research`).
- **Committed in:** `ff3a5d6`, `9d9d472`

---

**Total deviations:** 3 (1 blocking commit-ordering fix, 2 auto-added missing functionality). **Impact:** All three necessary for a working, atomically-committed plan with no import-breaking intermediate state and no undiscoverable route. No unrelated code changed — confirmed via `git diff --stat` against `engine/` (empty) and against every sibling-owned file (empty).

## Known Stubs

None. Every figure on `/export` and `/demo` is computed live from committed data (either the real `Comparison` pipeline, the committed UK-style engine-correctness fixture, or the four curated jurisdiction rule files) — nothing is hardcoded, cached, or simulated. DMO-04's unavailable state is the honest, current, live-checked outcome (`agent.settings.integration_status()` reading the real process environment), not a placeholder.

## Threat Flags

None. `/export` and `/demo` are both read-only `GET` routes with no path or body parameters that reach a filesystem path directly — `/export`'s query parameters flow through the same `CompareInputs` Pydantic validation `/compare` already uses; `/demo` takes no input at all.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None for this plan's own deliverables. DMO-04's live path requires `PARALLEL_API_KEY` and `GEMINI_API_KEY`/`GOOGLE_API_KEY` to be installed on the deployment host before the live-research beat itself becomes reachable — this is the SAME pre-existing credential gap Phase 7 and 08-01 already document (D-101, WINDOWS.md #26/#28), not a new requirement this plan introduces. No `{phase}-USER-SETUP.md` generated, since this plan's own scope (the honest unavailable-state render) is complete without it.

## Next Phase Readiness

- Ready for 08-03 (submission verification / SHP-11..14).
- `/demo` is a single, linkable, no-query-string URL — the correct target for the written description's "watch it happen" links and for the ROADMAP's SHP-13 cold, logged-out verification step.
- If `PARALLEL_API_KEY`/`GEMINI_API_KEY` are installed on the host before submission, DMO-04 automatically switches to its live path with zero code changes — verified directly in this session via monkeypatch (`test_get_demo_dmo04_offers_the_live_path_when_credentials_are_present`).
- A future session wiring California's cost profile to its curated `jurisdictions/us-ca.yaml` rule model (currently `jurisdiction_id: null` in `data/cost_profiles/us-ca-los-angeles.yaml`, Phase 4's own disclosed scope note) would let `/export`'s default comparison render a real gap decomposition instead of the current band-mismatch refusal — noted here as a real, well-understood opportunity, not a blocker (D-78 forbids touching golden-tested data as part of this plan).

---
*Phase: 08-demo-proof-export-submission*
*Completed: 2026-09-09*

## Self-Check: PASSED

All created files confirmed present on disk (`app/services/export.py`, `app/services/demo.py`, `app/routers/export.py`, `app/templates/export_document.html`, `app/templates/demo.html`, `app/static/export.css`, `app/static/demo.css`, `tests/test_app_export.py`, `tests/test_demo_beats.py`). Both task commits confirmed present in `git log` (`ff3a5d6`, `9d9d472`). Full suite: 942/942 passing (up from 893 at plan start — 49 new tests, zero regressions). Golden regression (`tests/test_golden_cost.py`, `tests/test_route_a_basis_walk.py`): 9/9 passing, byte-identical, unedited. `vendor-scan.sh` and `lockfile-scan.sh`: both PASS. `engine/` directory: zero diff for this plan (`git diff --stat` against `engine/` is empty).
