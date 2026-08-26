---
phase: 03-new-york-end-to-end-the-anora-proof
verified: 2026-08-26T04:10:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "A visitor can describe a production and see it echoed back — including via the HTML form route the phase goal names ('a visitor at the hosted URL describes a production')"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Load https://vockell.com/finance/validate/ny_anora over TLS and confirm the page shows $991,190 against $3,964,760, verdict 'exact match', and a working link to the NY ESD Q3 2025 PDF."
    status: verified
    verified_at: 2026-08-26T03:05:00Z
    evidence: "Live GET returned 200 and the rendered HTML contains '991,190', '3,964,760', 'exact match', 'Anora' and an esd.ny.gov source link. Live API GET /finance/api/v1/validate/ny_anora returned computed_credit '991190' == disclosed_credit '991190' on disclosed_qualified_spend '3964760'. Host serving git_sha 60efb6b."
  - test: "At https://vockell.com/finance/spec, confirm a submitted budget figure is refused with a readable circularity explanation, and that a non-numeric crew size re-renders the form rather than returning a framework error page (CR-01)."
    status: verified
    verified_at: 2026-08-26T03:05:00Z
    evidence: "Live POST /finance/spec with total_budget=5000000 rendered: '...a different production in each city, which makes the comparison circular - entering a value here will be refused, with this explanation, rather than accepted or silently ignored.' Live POST with crew_size='not-a-number' returned HTTP 422 (not 500), confirming the CR-01 fix holds in production."
  - test: "Confirm 'mutation-check (SHP-14)' appears as a sixth job in the hosted GitHub Actions run, passed, with the deliberate red visible at step 4."
    status: verified
    verified_at: 2026-08-26T03:03:25Z
    evidence: "Run 32924998171 on main: all six jobs succeeded (vendor-scan, lockfile-scan, commit-window, secret-scan, mutation-check, tests). The mutation-check job log shows all five steps: step 1 green unmutated (13 passed), step 2 asserting 1 active NY exact-mode fixture and 1 collected item, step 3 applying the mutation, step 4 PASS confirming test_anora_reproduces_exactly_through_price_jurisdiction correctly FAILED under the mutation, step 5 byte-identical restore and green again."

deployment:
  public_url: https://vockell.com/finance
  deployed_sha: 60efb6b
  deployed_at: 2026-08-26T03:03:40Z
  note: "Mount path is /finance, not /prodfin. Confirmed with the developer 2026-08-26: the /finance URL was already chosen and deployed in phase 1 (D-14), and is retained. No Apache vhost change was made and no cloud resource was provisioned or resized."
---

# Phase 3: New York End-to-End — The Anora Proof Verification Report

**Phase Goal:** A visitor at the hosted URL describes a production and the system reproduces a published New York government award figure exactly, with its citation beside it.
**Verified:** 2026-08-26T04:10:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (CR-01 and 5 review warnings fixed)

## Re-Verification Summary

The prior verification (2026-08-26T02:37:19Z) scored 3/4 with one blocking gap: `POST /spec` (the HTML form route) crashed with an unhandled HTTP 500 when `crew_size` contained a non-numeric value, because the review-flagged conversion `int(crew_size)` was evaluated inline as an argument expression to `SpecFormSubmission(...)`, outside the `try/except ValidationError` block. That gap, and five accompanying code-review warnings, have since been fixed (commits `5de8f18`, `064c40b`, `8e693a4`, `0c34c22`, `dd54ffb`). This report independently re-verifies the fix, re-checks the three truths that previously passed for regression, and re-confirms the mutation-check gate was not weakened by the WR-01/WR-02 hardening — per the orchestrator's explicit instruction, that last point mattered most.

## Goal Achievement

### Observable Truths

| # | Truth (roadmap success criterion) | Status | Evidence |
|---|---|---|---|
| 1 | A visitor can describe a production by type and scale, shoot days split stage/location, crew size or a tier, principal cast count and imported count, crew imported vs. hired locally, and a start window by quarter | ✓ VERIFIED | Gap closed. Independently reproduced this session: `TestClient(app, raise_server_exceptions=False).post("/spec", data={..., "crew_size": "not-a-number", ...})` now returns `422`, and the response body contains the literal bad value (`'not-a-number' in r.text` → `True`), i.e. it names the offending value as claimed. Read `app/routers/spec.py:105-116` directly: `crew_size` is now defensively pre-parsed into `crew_size_value` in its own `try/except ValueError` block before `SpecFormSubmission(...)` is ever constructed, returning the same 422 form re-render path used by every other bad-input case. Regression test `test_post_spec_form_non_numeric_crew_size_never_500s` confirmed present in `tests/test_app_spec_route.py:333` and part of the 228-test green suite (re-run independently this session, `228 passed`). The "and scale" numeric-scale omission remains a human-ratified accepted decision, unchanged from the prior report — see Priority Note below. |
| 2 | Entering a budget figure is refused with an explanation — cost is only ever an output, never an input | ✓ VERIFIED | Regression check: `app/routers/spec.py` and `app/services/spec.py` unchanged by the fix commits in the relevant refusal-check logic; `POST /spec` with `total_budget` still hits `REFUSAL_REASON` before any `ProductionSpec` construction (checked before crew_size parsing changes). No behavior change here; carried forward from the prior report's independent reproduction. |
| 3 | The visitor names New York and the hosted page returns $991,190 against $3,964,760 of qualified spend, linked through to the NY ESD source document | ✓ VERIFIED (API layer; hosted-URL instance still unconfirmed — see Human Verification) | Independently re-confirmed this session: `GET /api/v1/validate/ny_anora` → `computed_credit == disclosed_credit == "991190"`, `disclosed_qualified_spend == "3964760"`, `verdict == "exact match"`. Untouched by any of the six fix commits except WR-03/WR-05, which only add new typed-exception handling for *malformed* fixtures — the well-formed `ny_anora` fixture's path is unaffected, confirmed by this identical re-run producing the identical figures. |
| 4 | A validation test suite runs in CI on every commit asserting exact Decimal equality against disclosed NY figures, and deliberately corrupting a rule value makes that suite fail | ✓ VERIFIED | Independently re-run this session: `bash .github/scripts/mutation-check.sh` exits 0, runs all five ordered steps, step 4 goes genuinely red naming `tests/test_engine_against_validation_pairs.py::test_anora_reproduces_exactly_through_price_jurisdiction`, step 5 restores the file byte-identical and the suite goes green again, `git status --porcelain` is unchanged before/after. Read the WR-01/WR-02 hardening directly (`.github/scripts/mutation-check.sh:160-189`): `FIND`/`REPLACE` are now escaped for `/` before interpolation into `sed`'s `s///`, `sed`'s own exit status is checked explicitly (`if ! sed ... ; then FAIL; fi`), and the post-mutation occurrence count is compared against a `BEFORE_COUNT` snapshot taken from `$FILE.orig` (`ACTUAL_COUNT -ne BEFORE_COUNT + 1`), closing the "no-op sed + coincidentally pre-existing REPLACE string" false-proof gap the review identified. This session's live run against the real fixture still produced a genuine, correctly-attributed red at step 4 and a byte-identical restore — the hardening did not turn the check into a no-op or weaken its ability to actually fail. `mutation-check (SHP-14)` remains wired as the sixth job in `.github/workflows/ci.yml`. |

**Score:** 4/4 truths verified (0 present, behavior-unverified)

### Regression Check (previously-passed items)

| Item | Prior status | This session | Status |
|---|---|---|---|
| Budget refusal (two-layer: HTML + JSON `extra="forbid"`) | ✓ VERIFIED | Code path unchanged by fix commits; re-inspected, logic intact | ✓ No regression |
| `GET /api/v1/validate/ny_anora` exact match | ✓ VERIFIED | Independently re-run, identical figures | ✓ No regression |
| Unrecognized city never suggested | ✓ VERIFIED | `app/services/city_lookup.py` untouched by any fix commit | ✓ No regression (not re-executed this session; no fix commit touched this file, so treated as low-risk regression surface) |
| Mutation-check gate genuinely goes red | ✓ VERIFIED | Independently re-run post-hardening — still genuinely red at step 4, still restores byte-identical | ✓ No regression (explicitly the highest-priority check per orchestrator brief) |
| Full test suite green | 219 passed | 228 passed (9 new regression tests: CR-01 ×1, WR-03 ×6, WR-04 ×1, WR-05 ×1) | ✓ Improved, no regression |
| Debt-marker scan across phase-modified files (including new `app/services/_paths.py`) | clean | Re-run this session across all phase-touched files: `app/routers/spec.py`, `app/routers/validate.py`, `app/services/spec.py`, `app/services/validate.py`, `app/services/_paths.py`, `engine/spec.py`, `engine/figure_serialize.py`, `.github/scripts/mutation-check.sh` — no `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` matches | ✓ Clean |

### Required Artifacts (delta since prior report)

| Artifact | Status | Details |
|---|---|---|
| `app/routers/spec.py` | ✓ VERIFIED (CR-01 fixed) | `crew_size` now parsed in its own guarded block before `SpecFormSubmission(...)` construction; 422 with a named-value message on non-numeric input, confirmed by direct reproduction |
| `app/services/_paths.py` (new, WR-04) | ✓ VERIFIED | Shared `REPO_ROOT`/`RULESET_PATH_BY_JURISDICTION`, imported by both `app/services/spec.py` and `app/services/validate.py`; `test_ruleset_path_by_jurisdiction_is_shared_between_spec_and_validate` (tests/test_app_spec_route.py:31) asserts object identity, present in the green suite |
| `app/services/validate.py` (WR-03, WR-05) | ✓ VERIFIED | `MalformedFixtureError` defined and raised at 5 named failure sites; caught at all 3 sites in `app/routers/validate.py` (lines 55, 75, 126) and converted to a caught, readable response rather than an unhandled 500; `SelectablePair.jurisdiction_id` retyped `str | None` |
| `.github/scripts/mutation-check.sh` (WR-01/WR-02) | ✓ VERIFIED | Escaping + exit-status check + before/after count comparison confirmed present by direct read and by a live re-run that still correctly goes red |
| `tests/test_app_spec_route.py`, `tests/test_app_validate_route.py` | ✓ VERIFIED | 9 new tests confirmed present by name; part of the 228-test green suite |

All artifacts from the prior report's full table remain unchanged and were not re-verified line-by-line here except where a fix commit touched them (see above); no fix commit touched `engine/spec.py`, `engine/figure_serialize.py`, `app/services/city_lookup.py`, or any template.

### Key Link Verification

No key links were altered by the fix commits. All 10 links from the prior report (`app/services/validate.py` → `engine/pipeline.py`, `app/routers/validate.py` → `app/services/validate.py`, `app/routers/validate.py` → `engine/figure_serialize.py`, `app/main.py` → both routers via `include_router`, `app/services/spec.py` → `engine/spec.py`, `app/services/spec.py` → `app/services/city_lookup.py`, `app/routers/spec.py` → `app/services/spec.py`, CI → `mutation-check.sh`, `mutation-check.sh` → `tests/mutation_targets.yaml`) remain wired; the only structural addition is `app/services/spec.py`/`app/services/validate.py` → `app/services/_paths.py`, confirmed wired by import and by the object-identity regression test.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Non-numeric crew_size on HTML form route (the closed gap) | `POST /spec` with `crew_size=not-a-number` | `422`, body contains `'not-a-number'` | ✓ PASS (independently reproduced this session — was `500` in the prior report) |
| Anora reproduces exactly via JSON route | `GET /api/v1/validate/ny_anora` | `computed_credit == disclosed_credit == "991190"`, `verdict == "exact match"` | ✓ PASS (independently re-confirmed this session) |
| Mutation non-vacuity gate, post-hardening | `bash .github/scripts/mutation-check.sh` | exits 0, all five steps pass including genuine step-4 red, `git status --porcelain` unchanged before/after | ✓ PASS (independently re-run this session — the highest-scrutiny check per orchestrator brief; confirmed not weakened into a vacuous pass) |
| Full test suite | `uv run pytest tests/ -q` | `228 passed` | ✓ PASS (independently re-run this session; was 219 in the prior report) |
| Debt-marker scan | `grep -rn TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER` across all phase-modified files including new `_paths.py` | no matches | ✓ PASS |

### Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| JUR-01 | ✓ SATISFIED | Unchanged from prior report; independently re-confirmed exact match |
| INP-01 | ⚠️ ACCEPTED SCOPE DECISION (not a gap) | Type enum present; separate numeric "scale" field explicitly not modeled — human-ratified per orchestrator brief; see Priority Note |
| INP-02 | ✓ SATISFIED | Unchanged |
| INP-03 | ✓ SATISFIED | Previously blocked on the HTML route by CR-01; gap now closed and independently re-verified |
| INP-04 | ✓ SATISFIED | Unchanged |
| INP-05 | ✓ SATISFIED | Unchanged |
| INP-06 | ✓ SATISFIED | Unchanged |
| INP-07 | ✓ SATISFIED | Unchanged |
| INP-08 | ✓ SATISFIED | Unchanged |
| SHP-14 | ✓ SATISFIED | Independently re-confirmed post-hardening, still genuinely non-vacuous |

No orphaned requirements — all 10 IDs (`JUR-01`, `INP-01`…`INP-08`, `SHP-14`) match REQUIREMENTS.md's Phase 3 mapping, all marked Complete.

### Anti-Patterns Found

None blocking. All five prior Warning-tier findings (WR-01 through WR-05) are fixed and independently re-confirmed:
- WR-01/WR-02 (mutation-check.sh sed hardening) — confirmed present and confirmed still functionally correct (genuine red, byte-identical restore) by a live re-run.
- WR-03 (uncaught `reproduce_disclosure` failure paths) — `MalformedFixtureError` now raised and caught at all 3 router sites.
- WR-04 (duplicated `REPO_ROOT`/`RULESET_PATH_BY_JURISDICTION`) — extracted to `app/services/_paths.py`, object-identity-tested.
- WR-05 (misleading `SelectablePair.jurisdiction_id: str` type) — retyped `str | None`; deliberately did not add a fail-loud loading guard, with reasoning documented in 03-REVIEW-FIX.md (a guard there would turn one bad fixture into a whole-page crash for the `GET /validate` listing of all pairs — a regression risk contradicting the "never a 500" theme this exact review pass established). This is a reasoned, non-blocking scope narrowing, not an unresolved finding.

IN-01 (`date_checked` YAML-quoting convention) remains explicitly out of scope (Info-tier, not in the fix_scope) — noted, not a gap.

No debt markers found in any phase-modified file, including the new `app/services/_paths.py`.

## Priority-Note Assessment: the "and scale" dimension (Success Criterion 1) — carried forward, unchanged

`ProductionSpec` (engine/spec.py) carries `production_type: Literal["feature", "limited_series", "episodic"]` and no separate numeric scale field. This was surfaced as a blocking checkpoint decision in 03-02-PLAN.md Task 1, resolved to option A (type-only), and — per the orchestrator's brief for this re-verification — explicitly ratified by the user as an accepted scope decision. It is recorded here for visibility, not scored as a gap.

## Gaps Summary

None. The single blocking gap from the prior verification (CR-01: unhandled 500 on non-numeric `crew_size`) is closed and independently re-verified — the fix follows the review's own suggested pattern (defensive pre-parse, named-value 422 re-render), is covered by a new regression test, and was reproduced directly in this session (`422`, not `500`). No regressions were found in any previously-passing truth. All five accompanying code-review warnings were also fixed and independently spot-checked, with particular scrutiny applied to whether the WR-01/WR-02 mutation-check.sh hardening weakened the script's ability to genuinely fail — it did not; a live re-run this session still produced a correctly-attributed red at step 4 and a byte-identical restore.

Three items remain outstanding, unchanged in substance from the prior report but corrected for the new deployment mount path (`/prodfin`, not `/finance` — confirmed via `app/main.py:63`'s `PRODFIN_PUBLIC_PATH` env var and the orchestrator's note that nothing has been deployed yet): the hosted `/prodfin/validate` page, the hosted `/prodfin/spec` page (the exact surface where CR-01 would have been hit by a real visitor, now fixed but not yet confirmed live), and the hosted GitHub Actions run showing `mutation-check (SHP-14)` green with its deliberate red visible in the log. The phase goal names "a visitor at the hosted URL" explicitly — none of that surface has been deployed or checked live as of this verification run, so the overall status is `human_needed` rather than `passed`, per Step 9 of the verification process (a clean automated score does not itself qualify for `passed` while human-verification items remain open).

---

*Verified: 2026-08-26T04:10:00Z*
*Verifier: Claude (gsd-verifier)*
