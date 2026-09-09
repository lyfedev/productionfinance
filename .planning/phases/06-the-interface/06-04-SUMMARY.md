---
phase: 06-the-interface
plan: 04
subsystem: ui
tags: [fastapi, jinja2, permalink, currency, honesty-gates, d-74, d-78, ui-08, ui-11, ui-12]

requires:
  - phase: 06-the-interface
    provides: "06-01's /compare tracer (CompareInputs, Comparison, build_comparison, to_geojson), 06-02's slider/gap picker (SLIDER_QUARTERS, resolve_gap_selection), 06-03's provenance layer (app.services.provenance.collect_rate_figures, _figure.html)"
  - phase: 04-cost-localization-landed-cost-outputs
    provides: "engine.landed_cost.aggregate/_convert_cost_lines's per-line currency conversion structure, engine.fx.convert/D-74's refuse-rather-than-derive discipline"
  - phase: 07-live-research-caching-durable-jobs
    provides: "app.services.cache_policy.resolve_fx (the sanctioned live-or-fallback FX entry point), app.services.live_fx.FxResolution"
provides:
  - "app/services/permalink.py — encode_permalink/decode_permalink (UI-08's only persistence mechanism), compute_diff/build_diff_view (UI-12's three-way change verdict)"
  - "app/services/currency_display.py — build_city_displays (UI-11's chosen-currency conversion) and build_original_currency_figures (UI-11's unconditional original-currency disclosure)"
  - "CompareInputs.display_currency — a pure display-layer field, additive to 06-01/06-02's CompareInputs contract"
  - "GET /compare?permalink=<token> — the reproduce-and-diff entry point; every render offers a fresh share token"
affects: [phase-7-live-research, phase-8-proof-panel]

actuals:
  tokens: 25822
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "A permalink token is a deterministic (sort_keys=True) base64 encoding of the FULL CompareInputs field set PLUS a creation-time recorded-rates snapshot — decode_permalink requires every CompareInputs field present explicitly and refuses (PermalinkDecodeError) rather than letting CompareInputs' own field defaults silently paper over a dropped one."
    - "UI-12's diff matches a recorded rate to a current one by Figure.label (the only stable business key across a figure_id's fresh-UUID-per-construction lifetime) — a 0-match or >1-match resolves to an explicit 'cannot_determine' status, never collapsed into 'unchanged'."
    - "UI-11 has TWO structurally distinct honesty mechanisms, not one: (1) a visitor's chosen-display-currency forward conversion via app.services.cache_policy.resolve_fx, applied per DISTINCT source currency per request (never per figure); (2) an UNCONDITIONAL 'as originally priced' disclosure for a city whose total is itself already a converted figure (e.g. London, GBP source vs USD reporting currency) — reconstructed via a one-level, non-deduplicating walk over cost_only_total.inputs matching engine.landed_cost._convert_cost_lines' own exact structure, never engine.figure re-derivation, never touching engine/."
    - "display_currency travels as a hidden form field inside every carry-forward form (slider, gap picker) — app/static/compare.js needed ZERO changes, since its FormData-based collectFormFields() is already generic over whatever fields a form declares."

key-files:
  created:
    - app/services/permalink.py
    - app/services/currency_display.py
    - tests/test_app_permalink.py
    - tests/test_app_permalink_diff.py
    - tests/test_app_currency_display.py
  modified:
    - app/routers/compare.py
    - app/services/compare.py
    - app/services/cache_policy.py
    - app/templates/compare.html
    - app/templates/_ranked_list.html
    - app/static/prodfin.css

key-decisions:
  - "CompareInputs.display_currency was added to app/services/compare.py — a file the plan's own files_modified list did NOT declare. Necessary because CompareInputs is the single query-string/JSON contract POST /api/v1/compare already validates against; a router-only display_currency parameter would be invisible to the settled-slider's JS-collected POST body, silently reverting a visitor's chosen currency the moment they dragged the slider. Documented as a deviation (Rule 2) rather than silently expanding scope."
  - "The original-currency reconstruction (mechanism 2 of UI-11) deliberately does NOT use app.services.provenance.collect_rate_figures' recursive walk — that function DEDUPES leaves by content for a printable rate list, which silently UNDERCOUNTS a genuine reconstruction sum whenever the same underlying rate object legitimately contributes to more than one cost line. Discovered by cross-checking against the documented golden London figure (£548,595): the deduplicating walk reconstructed only £491,419. Fixed by a one-level, non-deduplicating walk over cost_only_total.inputs matching engine.landed_cost._convert_cost_lines' own exact structure — verified to reconstruct the documented £548,595/$747,735 pairing exactly."
  - "A netted-incentive total (RankedCity.total_landed_cost when incentive_figure is not None) is NEVER reconstructed to its original currency — only cost_only_total (always a pure sum, by engine.landed_cost.aggregate's own construction) is safely reconstructible. This never arises against the real committed floor-city set (London, the only city needing reconstruction, has no modelled incentive) but is guarded defensively and proven against a synthetic fixture, per this project's refuse-rather-than-guess discipline (D-74's own precedent)."
  - "When the visitor's chosen display currency EQUALS a city's true original currency (e.g. GBP chosen for London), the chosen-currency forward-conversion entry is DROPPED in favor of the more precise original-currency reconstruction — showing both would present two slightly different GBP figures (one exact, from disclosed leaves; one a fresh resolve_fx conversion from the already-rounded USD total) for the identical total."
  - "Updated app/services/cache_policy.py's docstring (one line, outside files_modified) — it claimed 'app/services/spec.py (and nothing else) calls resolve_fx', which currency_display.py's new legitimate second call site made inaccurate. No test enforces exclusivity (test_cache_policy_live.py's own gate only asserts a fixed allow-list of modules IMPORT from cache_policy, never that no OTHER module may also call resolve_fx), so this is a documentation accuracy fix, not a behavior change."
  - "Three commits instead of a strict one-per-task mapping: get_compare()/post_compare_json() serve all three tasks from the SAME function bodies (the permalink branch and the currency-display computation share one comparison object and one render context), so a byte-perfect per-task split of app/routers/compare.py and app/templates/compare.html would risk non-passing intermediate commits. Committed by dependency order instead — permalink.py standalone, currency_display.py+compare.py+cache_policy.py standalone, then the router/template/CSS wiring plus all three test files together (the earliest point every test can actually run) — mirroring 06-02's own documented precedent for tightly-coupled task work."

requirements-completed: [UI-08, UI-11, UI-12]

coverage:
  - id: D1
    description: "UI-08: a comparison is shareable as a permalink URL encoding its inputs; opening it in a fresh session (no cookie) reproduces the same comparison"
    requirement: "UI-08"
    verification:
      - kind: integration
        ref: "tests/test_app_permalink.py#test_reopening_the_shared_permalink_reproduces_the_same_totals"
        status: pass
      - kind: integration
        ref: "tests/test_app_permalink.py#test_get_compare_carries_no_session_cookie_ever"
        status: pass
      - kind: unit
        ref: "tests/test_app_permalink.py#test_decode_of_encode_reproduces_every_input_field"
        status: pass
    human_judgment: false
  - id: D2
    description: "UI-08 round-trip: encode(decode(url)) == url, asserted as a property over a generated matrix of CompareInputs combinations (production type, crew, cities, start window, display currency, gap selection), not one example"
    requirement: "UI-08"
    verification:
      - kind: unit
        ref: "tests/test_app_permalink.py#test_encode_of_decode_is_byte_identical_to_the_original_token"
        status: pass
      - kind: unit
        ref: "tests/test_app_permalink.py#test_state_matrix_is_non_trivial"
        status: pass
    human_judgment: false
  - id: D3
    description: "UI-08 honesty: a permalink that would silently drop an input REFUSES to decode (never falls back to CompareInputs' own defaults), proven for every single CompareInputs field individually, plus end-to-end as a 422"
    requirement: "UI-08"
    verification:
      - kind: unit
        ref: "tests/test_app_permalink.py#test_decode_refuses_when_every_input_field_but_one_is_present"
        status: pass
      - kind: integration
        ref: "tests/test_app_permalink.py#test_get_compare_permalink_with_dropped_field_returns_422"
        status: pass
    human_judgment: false
  - id: D4
    description: "UI-12: reopening a shared link names, individually, which rates changed since it was created; a genuinely unchanged link says so explicitly rather than showing nothing"
    requirement: "UI-12"
    verification:
      - kind: unit
        ref: "tests/test_app_permalink_diff.py#test_genuinely_unchanged_rate_reports_unchanged_explicitly"
        status: pass
      - kind: integration
        ref: "tests/test_app_permalink_diff.py#test_reopening_an_unchanged_link_shows_the_explicit_no_changes_banner"
        status: pass
      - kind: integration
        ref: "tests/test_app_permalink_diff.py#test_reopening_a_link_with_a_fabricated_changed_rate_shows_it_named_individually"
        status: pass
    human_judgment: false
  - id: D5
    description: "UI-12 honesty: a rate the diff cannot resolve (renamed, removed, or ambiguous) is reported as 'cannot determine what changed', NEVER as 'unchanged' — proven as a property across match-count 0/1/2/3, not one example"
    requirement: "UI-12"
    verification:
      - kind: unit
        ref: "tests/test_app_permalink_diff.py#test_property_every_non_single_match_scenario_is_never_reported_unchanged"
        status: pass
      - kind: integration
        ref: "tests/test_app_permalink_diff.py#test_reopening_a_link_with_an_unresolvable_recorded_rate_says_cannot_determine_never_unchanged"
        status: pass
    human_judgment: false
  - id: D6
    description: "UI-11: costs display in a chosen currency; wherever a government figure is denominated in another currency, the original is ALWAYS shown alongside the converted one, never replaced"
    requirement: "UI-11"
    verification:
      - kind: unit
        ref: "tests/test_app_currency_display.py#test_reconstruct_source_currency_total_matches_the_real_committed_london_figure"
        status: pass
      - kind: unit
        ref: "tests/test_app_currency_display.py#test_build_original_currency_figures_always_present_regardless_of_display_currency"
        status: pass
      - kind: integration
        ref: "tests/test_app_currency_display.py#test_get_compare_default_usd_shows_londons_original_gbp_figure_unconditionally"
        status: pass
    human_judgment: false
  - id: D7
    description: "UI-11 honesty: a converted figure is visibly marked as converted and carries its FX rate, the rate's date, and whether the rate was live or the committed-snapshot fallback; a pair with no live result and no fallback refuses rather than fabricates"
    requirement: "UI-11"
    verification:
      - kind: unit
        ref: "tests/test_app_currency_display.py#test_display_figure_live_rate_converts_and_marks_origin"
        status: pass
      - kind: unit
        ref: "tests/test_app_currency_display.py#test_display_figure_fallback_rate_marks_snapshot_origin"
        status: pass
      - kind: unit
        ref: "tests/test_app_currency_display.py#test_display_figure_no_live_and_no_fallback_snapshot_refuses_never_fabricates"
        status: pass
      - kind: integration
        ref: "tests/test_app_currency_display.py#test_get_compare_gbp_display_refuses_never_fabricates_when_live_fails"
        status: pass
    human_judgment: false
  - id: D8
    description: "D-78 golden totals byte-identical; tests/test_golden_cost.py and tests/test_route_a_basis_walk.py both unedited"
    verification:
      - kind: unit
        ref: "tests/test_golden_cost.py"
        status: pass
      - kind: unit
        ref: "tests/test_route_a_basis_walk.py"
        status: pass
      - kind: integration
        ref: "tests/test_app_currency_display.py#test_get_compare_golden_totals_unaffected_by_display_currency"
        status: pass
    human_judgment: false
  - id: D9
    description: "D-70 prescriptive-vocabulary gate covers the new currency/share/diff sections and the new prodfin.css rules"
    verification:
      - kind: integration
        ref: "tests/test_app_currency_display.py#test_get_compare_currency_section_d70_vocabulary_gate"
        status: pass
      - kind: unit
        ref: "tests/test_app_currency_display.py#test_static_prodfin_css_d70_vocabulary_gate_over_new_currency_rules"
        status: pass
    human_judgment: false
  - id: D10
    description: "The rendered permalink/currency sections' visual layout and print/mobile behavior in a real browser"
    human_judgment: true
    rationale: "Automated tests assert HTML structure, class names, and text content but cannot judge visual layout, spacing, or responsive behavior of the new sections (share-link input, currency selector, diff table) in a real browser — mirrors 06-01/06-02's own established human-judgment carve-out for this page's visual surface."

duration: 95min
completed: 2026-09-09
status: complete
---

# Phase 6 Plan 4: Permalink, What-Changed Diff, and Dual-Currency Display Summary

**A deterministic, no-login permalink that refuses to decode a token missing even one input field; a per-rate "what's changed since this link was created" diff that names zero-match and ambiguous-match rates as "cannot determine" rather than ever claiming "unchanged"; and a chosen-currency display that always discloses London's true £548,595 GBP original alongside its $747,735 USD reporting-currency total, reconstructed from the engine's own disclosed Figure tree rather than re-derived.**

## Performance

- **Duration:** 95 min
- **Started:** 2026-09-09T14:20:00Z (approx.)
- **Completed:** 2026-09-09T15:55:00Z (approx.)
- **Tasks:** 3
- **Files modified:** 11 (5 created, 6 modified)

## Accomplishments

- **UI-08 — the permalink.** `app/services/permalink.py`'s `encode_permalink`/`decode_permalink` are the ONLY persistence mechanism: a deterministic (`sort_keys=True`) base64 token carrying every `CompareInputs` field plus a creation-time recorded-rates snapshot. `decode_permalink` reads `CompareInputs.model_fields` to require every field present explicitly — a token missing even one field raises `PermalinkDecodeError` naming it, rather than letting `CompareInputs`' own defaults silently reproduce a different comparison under the same URL. The round-trip property (`encode(decode(token)) == token`) is asserted across a generated matrix of 108 `CompareInputs` combinations (production type × crew × cities × start window × display currency × gap selection), not one example. `GET /compare?permalink=<token>` reproduces the exact same totals in a genuinely separate `TestClient` (no shared cookie jar) — and no `/compare` response ever carries a `Set-Cookie` header at all.
- **UI-12 — the honest diff.** `compute_diff`/`build_diff_view` match a permalink's recorded rates against the freshly-rebuilt comparison's current rates by `Figure.label` (the only stable key across a `figure_id`'s fresh-UUID lifetime). A 1:1 match reports `"unchanged"` explicitly or `"changed"` with each differing field (`value`/`source_url`/`date_checked`) named individually; a 0-match or ambiguous >1-match reports `"cannot_determine"` — proven as a property across match counts 0/1/2/3, never collapsed into `"unchanged"`. End-to-end: reopening a real link within the same test run shows an explicit "No changes" banner; a link with a hand-tampered recorded value shows that specific rate as `"changed"` with both values visible; a link recording a rate that no longer exists anywhere in the current data shows `"cannot determine what changed"`, never `"unchanged"`.
- **UI-11 — dual-currency display, two distinct mechanisms.** `app/services/currency_display.py` provides (1) the visitor's chosen-currency forward conversion (`build_city_displays`/`display_figure`, via `app.services.cache_policy.resolve_fx` — never `httpx`/`engine.fx` directly, one call per distinct currency per request) and (2) the UNCONDITIONAL original-currency disclosure (`build_original_currency_figures`/`reconstruct_source_currency_total`) for a city whose reporting-currency total is itself already a converted figure. Discovered mid-build that the obvious approach — walking `app.services.provenance.collect_rate_figures`'s deduplicated leaves — silently undercounts a genuine reconstruction sum (it reconstructed London's total as £491,419, not the documented £548,595) because that function dedupes by content for a printable rate list, which is the wrong tool for a summation. Fixed with a one-level, non-deduplicating walk over `cost_only_total.inputs` matching `engine.landed_cost._convert_cost_lines`'s own exact structure — verified to reconstruct the documented golden pairing exactly: £548,595 GBP / $747,735 USD.
- **`CompareInputs.display_currency`** travels as a hidden form field inside every carry-forward form (the slider, the gap picker) — `app/static/compare.js` needed zero changes, since its `FormData`-based `collectFormFields()` is already generic over whatever fields a form declares, so the settled-slider's JS-collected POST body preserves a visitor's chosen currency automatically.
- Golden totals confirmed byte-identical regardless of `display_currency`: NY $758,427 / LA $693,521 / London $747,735 (USD, reporting currency; £548,595 shown as the unconditional original) / NY-vs-LA gap $64,906.

## Task Commits

Each production-code group was committed atomically, by dependency order rather than a strict 1:1 task mapping (see Decisions Made — `get_compare()`/`post_compare_json()` serve all three tasks from the same function bodies):

1. **Task 1+2 foundation: the permalink module (UI-08, UI-12)** — `be25737` (feat) — `app/services/permalink.py`
2. **Task 3 foundation: the currency-display module (UI-11)** — `50248a5` (feat) — `app/services/currency_display.py`, `app/services/cache_policy.py`, `app/services/compare.py`
3. **Integration wiring + all coverage** — `d9c6c4c` (feat) — `app/routers/compare.py`, `app/templates/compare.html`, `app/templates/_ranked_list.html`, `app/static/prodfin.css`, `tests/test_app_permalink.py`, `tests/test_app_permalink_diff.py`, `tests/test_app_currency_display.py`

**Plan metadata:** committed alongside this SUMMARY.

## Files Created/Modified

- `app/services/permalink.py` - `encode_permalink`/`decode_permalink`, `PermalinkState`/`RecordedFigure`, `compute_diff`/`build_diff_view`/`RateDiff`/`FieldDiff`
- `app/services/currency_display.py` - `build_city_displays`/`display_figure`/`DualCurrencyDisplay`, `build_original_currency_figures`/`reconstruct_source_currency_total`/`OriginalCurrencyFigure`, `DISPLAY_CURRENCIES`
- `app/services/compare.py` - `CompareInputs.display_currency` (additive field)
- `app/services/cache_policy.py` - Docstring accuracy fix (currency_display.py is now a second legitimate `resolve_fx` caller)
- `app/routers/compare.py` - `permalink`/`display_currency` query params on `GET /compare`; the permalink-exclusive input-resolution branch; `_currency_display_context`/`_current_rate_figures`/`_share_permalink_token` helpers shared by both routes
- `app/templates/compare.html` - The "what's changed" diff banner, the "share this comparison" permalink section, the display-currency selector form
- `app/templates/_ranked_list.html` - `dual_currency()`/`original_currency()` macros wired into every money cell
- `app/static/prodfin.css` - Styling for the new sections
- `tests/test_app_permalink.py` - 16 tests: round-trip property matrix, per-field dropped-input refusal, end-to-end reopen/no-cookie/422 coverage
- `tests/test_app_permalink_diff.py` - 16 tests: `compute_diff`'s three-way verdict as a property, `build_diff_view`'s `all_unchanged` aggregate, end-to-end tampered/unresolvable-rate rendering
- `tests/test_app_currency_display.py` - 20 tests: both currency mechanisms, live/fallback/refusal FX paths, the real London reconstruction, D-70 gate

## Decisions Made

See frontmatter `key-decisions` for full detail. Summary:
- `CompareInputs.display_currency` added to `app/services/compare.py` (outside the plan's declared `files_modified`) — necessary for POST/GET contract parity and JS-free carry-forward; documented as a Rule 2 deviation.
- The original-currency reconstruction uses a one-level, non-deduplicating walk over `cost_only_total.inputs`, not `collect_rate_figures`'s recursive deduplicated walk — the latter silently undercounts (discovered via cross-check against the documented golden London figure).
- A netted-incentive total is never reconstructed to its original currency (refuse-rather-than-guess, D-74's own precedent) — guarded defensively, proven against a synthetic fixture, never reachable against real committed data today.
- A redundant chosen-currency conversion is dropped when it would duplicate an already-shown original-currency reconstruction for the same figure.
- `app/services/cache_policy.py`'s docstring corrected (one line, outside `files_modified`) for accuracy — no test depended on the old wording.
- Three commits by dependency order rather than a strict 1:1 task mapping, mirroring 06-02's own documented precedent for tightly-coupled work.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `CompareInputs.display_currency` to `app/services/compare.py`**
- **Found during:** Task 3, wiring the currency selector into both `GET /compare` and `POST /api/v1/compare`
- **Issue:** The plan's `files_modified` list did not include `app/services/compare.py`, but `POST /api/v1/compare` validates its JSON body directly against `CompareInputs` (`extra="forbid"`) — a router-only `display_currency` query parameter would be invisible to that endpoint, and therefore invisible to the settled-slider's JS-collected POST body (`compare.js`'s `collectFormFields()` reads whatever fields the slider form declares and POSTs them as JSON). Without this field, a visitor who picked a display currency and then dragged the slider would see their choice silently revert to USD the moment the JS-injected fragment replaced the ranked list.
- **Fix:** Added `display_currency: Literal["USD", "GBP"] = "USD"` to `CompareInputs`, carried forward as a hidden form field inside the slider and gap-picker forms (mirroring `reporting_currency`'s own existing pattern) — zero changes to `app/static/compare.js` were needed, since its form-field collection is already generic.
- **Files modified:** `app/services/compare.py`, `app/templates/compare.html`
- **Verification:** `tests/test_app_currency_display.py` — the full round trip through both `GET`/`POST` with `display_currency` set
- **Committed in:** `50248a5` (field), `d9c6c4c` (form wiring)

**2. [Rule 1 - Bug] `collect_rate_figures`-based reconstruction silently undercounted London's original GBP total**
- **Found during:** Task 3, cross-checking the reconstructed original-currency total against the documented golden figure (£548,595)
- **Issue:** The first implementation walked `app.services.provenance.collect_rate_figures`'s deduplicated leaves and summed those matching the source currency — this function dedupes by CONTENT for a printable rate list (correct for its own purpose, 06-03), which silently undercounts a genuine reconstruction sum whenever the identical underlying rate object legitimately contributes to more than one cost line. The bug reconstructed £491,419, not £548,595.
- **Fix:** Rewrote `reconstruct_source_currency_total` as a one-level, non-deduplicating walk over `cost_only_total.inputs`, matching `engine.landed_cost._convert_cost_lines`'s own exact, documented structure (each converted line carries exactly one input — the untouched pre-conversion original) — verified to reconstruct the exact documented golden pairing.
- **Files modified:** `app/services/currency_display.py`
- **Verification:** `tests/test_app_currency_display.py#test_reconstruct_source_currency_total_matches_the_real_committed_london_figure` — asserts the exact £548,595 value against real committed data
- **Committed in:** `50248a5`

**3. [Rule 1 - Bug] Documentation accuracy: `app/services/cache_policy.py`'s docstring claimed a sole caller for `resolve_fx`**
- **Found during:** Task 3, adding `currency_display.py` as a second `resolve_fx` caller
- **Issue:** The docstring stated "`app/services/spec.py` (and nothing else) calls `resolve_fx`" — now inaccurate.
- **Fix:** Updated the one line to name both legitimate callers.
- **Files modified:** `app/services/cache_policy.py`
- **Verification:** `tests/test_cache_policy_live.py`'s own gate only asserts a fixed allow-list of modules IMPORT from `cache_policy` (never that no other module may also call `resolve_fx`) — unaffected, still passes.
- **Committed in:** `50248a5`

---

**Total deviations:** 3 auto-fixed (1 missing-critical field addition, 1 correctness bug caught by cross-checking against documented golden data, 1 documentation accuracy fix)
**Impact on plan:** All three were necessary for correctness/honesty. No scope creep beyond the two files this plan's own POST/GET contract required touching; deviation 2 in particular is the kind of self-check this project's own honesty discipline exists to catch before it ships.

## Issues Encountered

- **The engine already normalizes every city's totals to `reporting_currency` (USD) before `RankedCity` is even built** — a fact not obvious from the plan text's own framing ("costs display in a chosen currency... wherever a government figure is denominated in another currency"). A first-pass implementation comparing `figure.unit` directly against the visitor's chosen display currency was FUNCTIONALLY INERT for the real committed data set: every `RankedCity.total_landed_cost`/`cost_only_total`/`incentive_figure` is already USD, so nothing ever needed converting at that level under the default USD display currency — the flagship "London GBP 548,595 = $747,735" case documented throughout this repo's own summaries and STATE.md was invisible on the rendered page. Resolved by adding the SECOND, unconditional mechanism (original-currency reconstruction) described above, which is what actually surfaces the documented pairing regardless of any visitor choice.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `app/services/permalink.py` and `app/services/currency_display.py` are both generic over any `CompareInputs`/`RankedCity` — a later plan widening the committed city set (e.g. a second non-USD jurisdiction, or a third `DISPLAY_CURRENCIES` member once a third `data/fx/*.yaml` snapshot is committed) needs no changes to either module.
- Golden totals (NY $758,427 / LA $693,521 / London GBP 548,595 = $747,735 / NY-vs-LA gap $64,906) confirmed byte-identical; `tests/test_golden_cost.py` and `tests/test_route_a_basis_walk.py` are both unedited.
- Full suite: 909 passed. `vendor-scan.sh`/`lockfile-scan.sh` both clean. `scripts/audit_sdk_call_sites.py --check` clean — no new SDK call site (Frankfurter reached via `app.services.cache_policy.resolve_fx`, unrelated to the Parallel/Google SDK this audit tracks).
- No blockers. This is the last plan in Phase 6's declared scope (`06-05-PLAN.md` does not exist).

---
*Phase: 06-the-interface*
*Completed: 2026-09-09*

## Self-Check: PASSED
