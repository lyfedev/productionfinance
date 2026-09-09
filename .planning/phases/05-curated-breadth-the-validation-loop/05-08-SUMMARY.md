---
phase: 05-curated-breadth-the-validation-loop
plan: 08
subsystem: validation
tags: [validate-route, disclosure-stage, honest-refusal, jur-02, jur-03, jur-04, jinja2, fastapi]

requires:
  - phase: 05-curated-breadth-the-validation-loop
    provides: "jurisdictions/us-ca.yaml (05-04), jurisdictions/us-nj.yaml (05-05), jurisdictions/us-ct.yaml's full band coverage (05-06) — the three rule files this plan wires into the hosted surface"
provides:
  - "app/services/_paths.py — RULESET_PATH_BY_JURISDICTION carrying all four curated jurisdictions (us-ny, us-ca, us-nj, us-ct), shared by app.services.spec and app.services.validate"
  - "app/services/validate.py — ValidateResult and SelectablePair both carrying disclosure_stage, populated from each fixture's own field"
  - "app/routers/validate.py — disclosure_stage in the JSON view"
  - "app/templates/validate_result.html and validate_form.html — stage-aware labelling, distinguishing allocated/estimated/issued"
  - "tests/test_engine_against_validation_pairs.py — a generic four-jurisdiction sweep (ACTIVE_PAIRS_BY_JURISDICTION built by one dict comprehension) plus a two-test acceptance gate"
affects: [phase-8-reverification]

actuals:
  tokens: 7038
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "A widened security-relevant allowlist (RULESET_PATH_BY_JURISDICTION) is proven, not just declared, by re-running the honest-refusal path for real committed pairs — a guard rail written in Phase 3 (WINDOWS.md #3) that no active pair had ever triggered until this plan's data made it reachable"
    - "disclosure_stage flows through the SAME common_kwargs dict reproduce_disclosure already builds for both the computed and the refused ValidateResult branches, so a refused result is never missing provenance fields it already has"
    - "A jurisdiction-widening test change stays honest by re-deriving the sweep from a dict comprehension (ACTIVE_PAIRS_BY_JURISDICTION) rather than hand-copying a fourth per-jurisdiction block — the acceptance gate then checks the dict's OWN completeness, not a hardcoded jurisdiction list"

key-files:
  created: []
  modified:
    - app/services/_paths.py
    - app/services/validate.py
    - app/routers/validate.py
    - app/templates/validate_result.html
    - app/templates/validate_form.html
    - tests/test_app_validate_route.py
    - tests/test_engine_against_validation_pairs.py

key-decisions:
  - "Widened RULESET_PATH_BY_JURISDICTION to all four curated jurisdictions in one dict literal edit (app/services/_paths.py), replacing the stale 'New York only' comment — app.services.spec and app.services.validate both import this one object, so the widening reaches /spec and /validate identically and the existing dict-identity test (test_ruleset_path_by_jurisdiction_is_shared_between_spec_and_validate) still guards it."
  - "Did NOT touch data/cost_profiles/us-ca-los-angeles.yaml's jurisdiction_id: null (the documented Phase 4 scope boundary) — widening the RULESET_PATH_BY_JURISDICTION dict does not, by itself, route California into the /spec ranker; that route is gated separately by each city cost profile's own jurisdiction_id field, confirmed unchanged by this plan's empty `git diff --stat -- data/cost_profiles/`."
  - "Replaced the 'Credit issued' table label in validate_result.html's Disclosed section with 'Credit disclosed ({{ stage }})', and the Computed section's 'Credit issued' with 'Computed credit (matching the {{ stage }} disclosure)' — the word 'issued' is now reserved for pairs whose disclosure_stage genuinely is issued, never displayed unconditionally beside an allocation- or estimate-stage figure."
  - "tests/test_app_validate_route.py's test_post_validate_with_unselectable_pair_names_it_and_states_reason_not_500 was rewritten from ct_christmas_always (now selectable, since Connecticut is wired in) to ma_dont_look_up (genuinely unselectable: us-ma has no curated rule model AND its own fixture status is blocked) — corrected to the new truth rather than loosened, per the plan's explicit instruction."
  - "tests/test_engine_against_validation_pairs.py's ACTIVE_PAIRS_BY_JURISDICTION is a single dict comprehension over the widened RULESET_PATH_BY_JURISDICTION; NY_ACTIVE_PAIRS/CT_ACTIVE_PAIRS are kept as named views onto it (not a second filter) so the four named single-production anchor tests (Anora, Christmas Always, both direct and pipeline-routed) read exactly as before and stay unchanged in substance."
  - "Added two per-jurisdiction minimum-count tests (California, New Jersey) alongside the existing New York/Connecticut ones for uniformity, AND two separate generic acceptance-gate tests that loop over the map rather than hand-copying a fifth jurisdiction check — the loop is what makes a future fifth jurisdiction's coverage gap self-detecting."

patterns-established:
  - "A per-pair honest-refusal assertion is written directly against real committed fixtures (nj_joker, nj_trial_of_the_chicago_7, ct_christmas_always) rather than a synthetic/mocked pair — proving the refusal fires for the exact data a visitor can actually select, not a hypothetical."

requirements-completed: [JUR-02, JUR-03, JUR-04]

coverage:
  - id: D1
    description: "All four curated jurisdictions (New York, California, New Jersey, Connecticut) are wired into RULESET_PATH_BY_JURISDICTION and reachable from /validate; every active pair from all four is selectable; the honest-refusal path is proven to fire for real committed New Jersey and Connecticut pairs rather than staying hypothetical"
    requirement: "JUR-02"
    verification:
      - kind: unit
        ref: "tests/test_app_validate_route.py#test_reproduce_disclosure_completes_for_a_pair_from_each_curated_jurisdiction"
        status: pass
      - kind: unit
        ref: "tests/test_app_validate_route.py#test_new_jersey_and_connecticut_pairs_honestly_refuse_via_the_route"
        status: pass
      - kind: unit
        ref: "tests/test_app_spec_route.py#test_ruleset_path_by_jurisdiction_is_shared_between_spec_and_validate"
        status: pass
    human_judgment: false
  - id: D2
    description: "disclosure_stage is carried on ValidateResult and SelectablePair, exposed in the JSON view, and rendered on both the result page (beside the title and the verdict) and the pair-selection form (beside each pair's title) — with allocation and estimate stages explained in plain words distinct from an issued credit"
    requirement: "JUR-03"
    verification:
      - kind: unit
        ref: "tests/test_app_validate_route.py#test_disclosure_stage_present_on_json_view_for_three_distinct_stages"
        status: pass
      - kind: unit
        ref: "tests/test_app_validate_route.py#test_rendered_result_page_names_the_stage_for_ny_ca_and_nj"
        status: pass
      - kind: unit
        ref: "tests/test_app_validate_route.py#test_rendered_result_page_explains_non_issued_stages_without_issued_wording"
        status: pass
      - kind: unit
        ref: "tests/test_app_validate_route.py#test_selection_form_shows_each_pairs_stage_beside_its_title"
        status: pass
      - kind: unit
        ref: "tests/test_app_validate_route.py#test_disclosure_stage_present_on_refused_result_too"
        status: pass
    human_judgment: false
  - id: D3
    description: "The cross-jurisdiction sweep in tests/test_engine_against_validation_pairs.py covers all four curated jurisdictions from one generic dict comprehension, and a two-test acceptance gate fails loudly, naming the jurisdiction, if any curated jurisdiction loses active-pair coverage or loses reachability from app.services._paths.RULESET_PATH_BY_JURISDICTION"
    requirement: "JUR-04"
    verification:
      - kind: unit
        ref: "tests/test_engine_against_validation_pairs.py#test_every_curated_jurisdiction_in_this_modules_map_has_an_active_pair"
        status: pass
      - kind: unit
        ref: "tests/test_engine_against_validation_pairs.py#test_every_active_fixture_jurisdiction_is_reachable_from_the_hosted_surface"
        status: pass
      - kind: unit
        ref: "tests/test_engine_against_validation_pairs.py#test_at_least_one_california_pair_exercised"
        status: pass
      - kind: unit
        ref: "tests/test_engine_against_validation_pairs.py#test_at_least_one_new_jersey_pair_exercised"
        status: pass
      - kind: unit
        ref: "uv run --frozen pytest -q — 720 passed, 0 failed"
        status: pass
    human_judgment: false
  - id: D4
    description: "The pinned golden totals (NY $758,427 / LA $693,521 / London £548,595 / gap $64,906) and the live basis-walk honesty gate do not regress; engine/ and data/cost_profiles/ are byte-identical to their committed state"
    verification:
      - kind: unit
        ref: "tests/test_golden_cost.py tests/test_route_a_basis_walk.py — 9 passed"
        status: pass
      - kind: other
        ref: "git diff --stat -- engine/ data/cost_profiles/ (empty)"
        status: pass
      - kind: other
        ref: "bash .github/scripts/vendor-scan.sh && bash .github/scripts/lockfile-scan.sh — both exit 0"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-09-09
status: complete
---

# Phase 5 Plan 08: Four Jurisdictions Live on /validate Summary

**California, New Jersey and Connecticut are now reachable alongside New York at `/validate` — every result carries and renders its disclosure stage (allocated/estimated/issued), New Jersey's and Connecticut's transferable programmes honestly refuse to compute a net-cash figure for want of a sourced transfer-discount ceiling (proven for five real committed pairs, not hypothetical), and the cross-jurisdiction test sweep is now one generic loop over all four with a two-test acceptance gate guarding against silent coverage loss.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3
- **Files modified:** 7 (no new files — every deliverable is an edit to an existing surface)

## Accomplishments

- **All four curated jurisdictions wired into RULESET_PATH_BY_JURISDICTION** (`app/services/_paths.py`), the single dict `app.services.spec` and `app.services.validate` both import — so `/validate` and `/spec` can never drift apart on which jurisdictions are curated. The stale "New York only" comment beside this security-relevant allowlist is replaced.
- **The honest-refusal path fired for real committed data for the first time.** `engine.net_cash.transferable`'s refusal to convert at an unsourced discount range — written in Phase 3, never triggered by an active pair until this plan's data made New Jersey's and Connecticut's fixtures reachable — now fires for `nj_joker`, `nj_trial_of_the_chicago_7`, `ct_christmas_always`, `ct_colony_video_2015_productions`, and `ct_mako_games`. Every one of the five returns `verdict == "cannot be computed"` with a non-empty `refusal_reason` naming `transfer_discount`, through both the JSON view (`GET /api/v1/validate/{pair_id}`) and the HTML view (`GET /validate/{pair_id}`) — never a 500, never an invented rate.
- **`disclosure_stage` carried end to end.** `ValidateResult` and `SelectablePair` both carry it, populated from each fixture's own `disclosure_stage` field (present on both the computed and the refused result branch — a refusal does not blank out provenance it already has). The JSON view exposes it; the result page names it beside the production title and again beside the verdict, with plain-words explanations for `allocated` ("an approval to draw against... not yet an audited post-production issuance") and `estimated` ("a pre-certification figure... the same disclosure later supersedes it"); the selection form shows each pair's stage beside its title so a visitor chooses with the stage already visible.
- **No non-issued figure uses issued-credit wording.** The result page's table labels are stage-aware: "Credit disclosed (allocated)" / "Credit disclosed (estimated)" / "Credit disclosed (issued)" on the disclosed side, "Computed credit (matching the {stage} disclosure)" on the computed side — the literal string "Credit issued" only ever appears for a pair whose `disclosure_stage` genuinely is `issued`.
- **The cross-jurisdiction sweep generalized.** `tests/test_engine_against_validation_pairs.py`'s `RULESET_PATH_BY_JURISDICTION` now covers all four; `ACTIVE_PAIRS_BY_JURISDICTION` is built by one dict comprehension (a fifth jurisdiction is now a one-line map addition, not a copied test block); `ALL_ACTIVE_PAIRS` flattens it for the parametrized sweep. The four named single-production anchors (`test_anora_reproduces_exactly`, `test_christmas_always_reproduces_exactly`, and their pipeline-routed variants) are unchanged in substance.
- **The four-jurisdiction acceptance gate added**, as two generic tests (not four hand-copied per-jurisdiction checks): one asserts every jurisdiction in this module's own map has at least one active pair, naming any that does not; the other imports `app.services._paths.RULESET_PATH_BY_JURISDICTION` and asserts every jurisdiction an active fixture declares is reachable from the hosted surface, naming any that is not. Plus the two missing per-jurisdiction minimum-count guards (California, New Jersey), matching the existing New York/Connecticut pattern for uniformity.

## Which committed pairs now trigger the honest-refusal path, and why

| Pair | Jurisdiction | Mechanism | Why it refuses |
|---|---|---|---|
| `nj_joker` | us-nj | transferable | `transfer_discount.typical_rate_low` is sourced (0.75, four independent NJ documents); `typical_rate_high` is an explicit, deliberate `null` — no NJ source states a ceiling |
| `nj_trial_of_the_chicago_7` | us-nj | transferable | same gap as Joker — same rule file, same partially-sourced range |
| `ct_christmas_always` | us-ct | transferable | `transfer_discount.typical_rate_low` and `typical_rate_high` are both `null` — CGS 12-217jj(e)(1) confirms the credit is transferable but the statute states no market discount rate at all |
| `ct_colony_video_2015_productions` | us-ct | transferable | same wholly-unsourced gap as Christmas Always |
| `ct_mako_games` | us-ct | transferable | same wholly-unsourced gap as Christmas Always |

All five refuse for the identical underlying reason: `engine.net_cash.transferable` requires `applies=True` AND both `typical_rate_low` and `typical_rate_high` to be non-null before it will convert a gross credit to a cash range — a full range, sourced, or no conversion at all, never a fabricated midpoint or a half-sourced guess. This is `engine/net_cash.py`'s pre-existing behavior (unmodified by this plan — `git diff --stat -- engine/` is empty); this plan is the first to prove it fires for real, hosted-surface-reachable pairs rather than remaining an untriggered guard rail (WINDOWS.md #3, still open by design).

## Stage wording chosen for each non-issued stage

- **`allocated`** (California): *"an allocation is an approval to draw against — the commission has approved the amount, but it is not yet an audited post-production issuance, and the final issued credit may differ."*
- **`estimated`** (New Jersey): *"an estimate is a pre-certification figure — the same disclosure later supersedes it with an adjusted certification once the production's spend is audited."*
- **`issued`** (New York, Connecticut): *"issued means the credit has cleared the jurisdiction's full audit and certification process — this is the final figure, not a projection."* (Rendered for completeness/contrast; the non-issued-stage caveat paragraph near the verdict is suppressed entirely when the stage is `issued`.)

## The cost-profile scope boundary this plan deliberately did not cross

`data/cost_profiles/us-ca-los-angeles.yaml` keeps `jurisdiction_id: null`, exactly as the plan's `<scope_boundary>` specified. Widening `RULESET_PATH_BY_JURISDICTION` to include `us-ca` does **not**, by itself, route California's new credit into the `/spec` ranker or the ranked net-cash figures — that routing is gated by each city cost profile's own `jurisdiction_id` field, which this plan left untouched (`git diff --stat -- data/cost_profiles/` is empty, confirmed). `app.services.spec`'s existing LA-related tests (`test_post_api_v1_spec_ny_and_la_returns_separate_bands_and_a_gap` and the pinned golden gap in `tests/test_golden_cost.py`) continue to route Los Angeles into `incentive_not_modelled_cities`, unaffected by this plan. JUR-02, JUR-03 and JUR-04 each ask for a validated model against a government disclosure — the `/validate` surface this plan wires up — not that the model be applied to a candidate city in the ranker; that remains a deliberate, documented, unrequested boundary.

## Task Commits

1. **Task 1: Wire all four curated jurisdictions into the validation surface** — `bd59ab8` (feat)
2. **Task 2: Carry disclosure stage through to what a visitor reads** — `98a0e18` (feat)
3. **Task 3: Generalize the cross-jurisdiction sweep and add the four-jurisdiction acceptance gate** — `dffc16a` (test)

## Files Created/Modified

- `app/services/_paths.py` — `RULESET_PATH_BY_JURISDICTION` widened to all four curated jurisdictions; stale comment replaced
- `app/services/validate.py` — `disclosure_stage: str | None` added to `ValidateResult` and `SelectablePair`, populated from `data.get("disclosure_stage")` in both `selectable_pairs()` and `reproduce_disclosure`'s `common_kwargs`
- `app/routers/validate.py` — `disclosure_stage` added to `_validate_result_to_json`
- `app/templates/validate_result.html` — a `stage_explanation` macro; stage rendered beside the title and the verdict; disclosed/computed table labels made stage-aware
- `app/templates/validate_form.html` — each pair's stage rendered beside its title
- `tests/test_app_validate_route.py` — corrected the now-stale unselectable-pair test (`ct_christmas_always` → `ma_dont_look_up`); added 7 new tests across Tasks 1 and 2
- `tests/test_engine_against_validation_pairs.py` — `RULESET_PATH_BY_JURISDICTION` widened to all four; `ACTIVE_PAIRS_BY_JURISDICTION` dict comprehension replacing hand-rolled per-jurisdiction lists; 4 new tests (2 minimum-count, 2 acceptance-gate); module docstring rewritten

## Decisions Made

See `key-decisions` in frontmatter.

## Deviations from Plan

None — plan executed exactly as written. All three tasks completed, all `<verify>` commands pass on the first attempt, `engine/` and `data/cost_profiles/` are both untouched.

### Auto-fixed Issues

None.

---

**Total deviations:** 0 auto-fixed. **Impact:** None — plan executed as written.

## Issues Encountered

**Concurrent sibling agent WIP, confirmed out of scope.** `git status --short` throughout this plan's execution showed a concurrently-running agent's uncommitted work in `app/services/cache_policy.py`, `app/services/spec.py`, `app/templates/spec_result.html`, `pyproject.toml`, `uv.lock`, plus untracked `agent/live_checks.py`, `app/services/live_fx.py`, `tests/test_cache_policy_live.py` — all on this plan's `<file_ownership>` forbidden-touch list (07-04's caching boundary and live FX work). None of these files were staged or committed by this plan. The full suite (`uv run --frozen pytest -q`) ran clean at **720 passed, 0 failed** both mid-plan and at final verification, meaning the concurrent WIP was never in a state that broke this plan's own test runs — no concurrency noise to report beyond the presence of those uncommitted files in `git status`.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- JUR-02, JUR-03 and JUR-04 are all marked complete in `REQUIREMENTS.md` — this was the last of the three plans (05-01, 05-04/05-05/05-06, 05-08) declaring each, so the shared-ID gate (#2388) cleared and `requirements.ready-ids` reported 3/3 ready.
- All four curated jurisdictions are live and inspectable at `/validate` for an anonymous visitor — the "a validated model nobody can run from the hosted URL is a claim in a test file" gap this plan's objective named is closed.
- The transfer-discount gaps for New Jersey (ceiling) and Connecticut (both bounds) remain genuinely open (WINDOWS.md #3, #31) — this plan did not attempt to source them, and correctly did not: inventing either would violate D-87.
- No blockers for any other sibling plan in this phase.

## Self-Check: PASSED

- All 7 modified files confirmed present and containing the expected changes (`git show --stat` on each of the 3 task commits).
- All 3 task commits (`bd59ab8`, `98a0e18`, `dffc16a`) confirmed present in `git log`.
- Every `<verify>` and `<acceptance_criteria>` command from all three tasks re-run and passing: `tests/test_app_validate_route.py tests/test_app_spec_route.py` (50 passed), the `RULESET_PATH_BY_JURISDICTION` path-existence check, `tests/test_golden_cost.py tests/test_route_a_basis_walk.py` (9 passed), the disclosure-stage Python snippet (`['allocated', 'estimated', 'issued']`), `tests/test_engine_against_validation_pairs.py tests/test_jurisdiction_us_ca.py tests/test_jurisdiction_us_nj.py tests/test_jurisdiction_us_ct.py tests/test_validation_pair_fixtures.py` (78 passed), the full suite (`uv run --frozen pytest -q` — 720 passed, 0 failed), both CI scan scripts (exit 0), `git diff --stat -- engine/ data/cost_profiles/` (empty), and `python -c "import app.main"` (succeeds, no SDK loaded).

---
*Phase: 05-curated-breadth-the-validation-loop*
*Completed: 2026-09-09*
