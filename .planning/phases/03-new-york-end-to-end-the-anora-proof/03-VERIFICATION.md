---
phase: 03-new-york-end-to-end-the-anora-proof
verified: 2026-08-26T02:37:19Z
status: gaps_found
score: 3/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "A visitor can describe a production and see it echoed back — including via the HTML form route the phase goal names ('a visitor at the hosted URL describes a production')"
    status: failed
    reason: "POST /spec crashes with an unhandled HTTP 500 when the crew_size form field contains a non-numeric value (e.g. crew_size=abc). engine/routers/spec.py converts crew_size with a bare int(crew_size) as an inline argument expression to SpecFormSubmission(...), which runs and raises ValueError BEFORE the surrounding try/except ValidationError block can catch it. Every other integer field (shoot_days_stage, start_year, etc.) is typed int = Form(...) and gets FastAPI's automatic 422; crew_size is the one hand-rolled exception with no safety net. This directly contradicts the plan's own repeatedly-stated invariant ('never a 500, never a bare framework error page') and the honesty posture the whole phase is built on. Independently reproduced with TestClient(app, raise_server_exceptions=False): POST /spec with crew_size='not-a-number' returns 500 / 'Internal Server Error'. Confirmed identically by the phase's own code reviewer (03-REVIEW.md CR-01)."
    artifacts:
      - path: "app/routers/spec.py"
        issue: "Lines ~105-122: int(crew_size) evaluated as an argument expression to SpecFormSubmission(...), outside the try/except ValidationError block that is supposed to catch bad input and re-render the form with a readable message"
    missing:
      - "Catch ValueError alongside ValidationError around the SpecFormSubmission(...) construction in post_spec_form, or defensively parse crew_size before construction and return a 422 form re-render naming the bad value"
      - "A regression test posting a non-numeric crew_size and asserting response.status_code == 422 (not 500) — none of the 355 lines in tests/test_app_spec_route.py currently cover this path"
deferred: []
human_verification:
  - test: "From a logged-out browser on a different network, load https://vockell.com/finance/, follow 'Reproduce a disclosure', submit with Anora selected, and confirm the page shows $991,190 against $3,964,760, verdict 'exact match', and a working link to the NY ESD Q3 2025 PDF."
    expected: "Identical result to the in-process TestClient behavior verified in this report — computed_credit == disclosed_credit == '991190', clickable NY ESD source link."
    why_human: "This is a property of the live Lightsail deployment (TLS, reverse proxy, PUBLIC_PATH mount under /finance), not the in-process TestClient. Deferred end-of-phase per 03-01-SUMMARY.md's D4 (workflow.human_verify_mode=end-of-phase) — no deploy or live check occurred in this verification run."
  - test: "From a logged-out browser at https://vockell.com/finance/, follow 'Price a production', fill the form for a feature shooting in New York, type a number into Total budget, submit, confirm the readable circularity explanation renders; then clear budget, resubmit, confirm the spec echoes back, New York shows cited rule terms, an unrecognized city shows 'no curated model' with no suggestion, and SPEND_NOT_DERIVED renders with no dollar figure anywhere."
    expected: "Same behavior as verified in-process in this report, now confirmed live and over TLS at the public URL."
    why_human: "Property of the live deployment (03-02-SUMMARY.md D7); not executed by this verification run. Also the exact surface where the CR-01 500 bug (see gaps) would be hit by a real, non-numeric crew-size submission."
  - test: "Push the branch, open the GitHub Actions run, confirm 'mutation-check (SHP-14)' appears as a sixth job, that it passed, and that its log shows the deliberate red at step 4."
    expected: "mutation-check (SHP-14) job visible and green in the hosted GitHub Actions run, log showing the step-4 red against test_anora_reproduces_exactly_through_price_jurisdiction before the restore."
    why_human: "Property of the hosted GitHub Actions run (03-03-SUMMARY.md D5), not the local script invocation this report re-ran. The local run's exit-0 and byte-identical git status were independently confirmed in this session, but the hosted CI log was not inspected."
---

# Phase 3: New York End-to-End — The Anora Proof Verification Report

**Phase Goal:** A visitor at the hosted URL describes a production and the system reproduces a published New York government award figure exactly, with its citation beside it.
**Verified:** 2026-08-26T02:37:19Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (roadmap success criterion) | Status | Evidence |
|---|---|---|---|
| 1 | A visitor can describe a production by type and scale, shoot days split stage/location, crew size or a tier, principal cast count and imported count, crew imported vs. hired locally, and a start window by quarter | ✗ FAILED (partial) | `ProductionSpec` (engine/spec.py:60-120) correctly models every dimension except a numeric "scale"; that omission is a deliberate, human-ratified decision (03-02-PLAN.md Task 1, resolved to option A) and is not treated as a gap here per the verification brief. However, the HTML submission path — the literal "visitor at the hosted URL describes a production" flow — crashes with an unhandled HTTP 500 on a non-numeric `crew_size` value. Independently reproduced: `TestClient(app).post("/spec", data={..., "crew_size": "not-a-number", ...})` → `500 Internal Server Error`. Confirmed identically by 03-REVIEW.md CR-01. This is a genuine functional break in describing a production, not a documentation gap. |
| 2 | Entering a budget figure is refused with an explanation — cost is only ever an output, never an input | ✓ VERIFIED | Independently reproduced: `POST /spec` with `total_budget=5000000` returns 200 with the circularity explanation text in the body (`REFUSAL_REASON`, checked before `ProductionSpec` is constructed — app/services/spec.py `handle_spec_submission` step 1). `POST /api/v1/spec` with any unnamed extra field returns 422 from Pydantic's `extra="forbid"` structurally, independent of the visible-field layer. Both layers of D-35 confirmed present and distinct. |
| 3 | The visitor names New York and the hosted page returns $991,190 against $3,964,760 of qualified spend, linked through to the NY ESD source document | ✓ VERIFIED | Orchestrator-independently confirmed: `GET /api/v1/validate/ny_anora` → `computed_credit == disclosed_credit == "991190"`, `disclosed_qualified_spend == "3964760"`, `verdict == "exact match"`, `source_url` pointing to the NY ESD Q3-2025 PDF (sha256 `824e2f32...`), `report_period 2025-Q3`. `engine/figure_serialize.py:33` confirms every `Figure.value` crosses the JSON boundary via `str(figure.value)`, never a JSON number. This is the API-layer proof; the *hosted-URL* instance of this claim is un-deployed in this verification run (see Human Verification). |
| 4 | A validation test suite runs in CI on every commit asserting exact Decimal equality against the disclosed New York figures, and deliberately corrupting a rule value makes that suite fail | ✓ VERIFIED | Orchestrator-independently confirmed: `bash .github/scripts/mutation-check.sh` exits 0, runs all five ordered steps, asserts a non-zero count of active NY exact-mode fixtures (1 — Anora) and a non-zero collected-item count for the declared test before mutating, applies the one-basis-point `base_rate` mutation, observes the suite fail naming `test_anora_reproduces_exactly_through_price_jurisdiction` (not a collection/import error), restores byte-identical (`cmp`-verified), and leaves `git status --porcelain` unchanged before/after. `mutation-check (SHP-14)` is wired as the sixth job in `.github/workflows/ci.yml` (confirmed: `grep -n "mutation-check" .github/workflows/ci.yml` shows the job block and its `run:` step), alongside the pre-existing `tests` job that runs the exact-equality suite on every push/PR. |

**Score:** 3/4 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `engine/figure_serialize.py` | Recursive Figure → JSON-safe dict | ✓ VERIFIED | 42 lines, exports `figure_to_dict`, `str(figure.value)` confirmed, recurses over `inputs` with no depth cap |
| `app/services/validate.py` | Route B business logic | ✓ VERIFIED | 222 lines, exports `reproduce_disclosure`, `selectable_pairs`, `UnknownPairError`, `ValidateResult`; closed-set membership check confirmed as first statement of `reproduce_disclosure` |
| `app/routers/validate.py` | GET/POST /validate, GET /api/v1/validate/{pair_id} | ✓ VERIFIED | 116 lines, all four routes present, calls `reproduce_disclosure` and `figure_to_dict` |
| `app/templates/validate_result.html` | Disclosed vs computed vs verdict + derivation tree | ✓ VERIFIED | 103 lines, both provenance chains rendered as separate blocks (confirmed via orchestrator's independent API/HTML check) |
| `tests/test_app_validate_route.py` | Route B coverage | ✓ VERIFIED | 158 lines, part of the 219-test green suite |
| `engine/spec.py` | ProductionSpec domain model | ✓ VERIFIED | 171 lines, exports `ProductionSpec`, `CrewTier`, `CrewHeadcount`, `resolve_crew_tier`, `CREW_TIERS_PATH`; no money field confirmed by direct field inspection |
| `data/crew_tiers.yaml` | Tier → headcount range, modelling assumption | ✓ VERIFIED | 43 lines, present as a new top-level `data/` directory |
| `app/services/city_lookup.py` | Free-text city → jurisdiction id or None | ✓ VERIFIED | 59 lines, exports `resolve_city_to_jurisdiction`, `CITY_ALIASES`; independently reproduced "Reykjavik" → `jurisdiction_id: None`, `status: "no curated model"` |
| `app/services/spec.py` | Route A: budget refusal, spec validation, per-city status, NY rule terms | ⚠️ ORPHANED-PARTIAL (wired but has an unguarded caller-side bug) | 255 lines, exports match the plan; the service itself is sound — the crash (CR-01) lives in the caller (`app/routers/spec.py`), not this module |
| `app/routers/spec.py` | GET /spec, POST /spec, POST /api/v1/spec | ✗ STUB-EQUIVALENT DEFECT on one input path | 164 lines; three routes wired to `handle_spec_submission` as required, but the `POST /spec` handler's manual `int(crew_size)` conversion (lines ~105-122) is unguarded and crashes with 500 on non-numeric input — see Gaps |
| `tests/test_engine_spec.py` | ProductionSpec validation matrix | ✓ VERIFIED | 327 lines, part of the green suite |
| `tests/test_app_spec_route.py` | Route A HTTP coverage | ✓ VERIFIED (but incomplete) | 355 lines, part of the green suite; does **not** cover the non-numeric-`crew_size` 500 path — this is exactly why CR-01 shipped undetected by the plan's own acceptance criteria |
| `tests/mutation_targets.yaml` | Declared mutation table (D-51) | ✓ VERIFIED | 36 lines, one active row, all eight required keys present |
| `.github/scripts/mutation-check.sh` | SHP-14 non-vacuity gate | ✓ VERIFIED | 227 lines, executable, exits 0 on independent re-run in this session |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `app/services/validate.py` | `engine/pipeline.py` | `price_jurisdiction(...)` | ✓ WIRED | `from engine.pipeline import price_jurisdiction` + call at line 170 |
| `app/routers/validate.py` | `app/services/validate.py` | `reproduce_disclosure(...)` | ✓ WIRED | Called at lines 51, 62, 93 — all three routes share one call site |
| `app/routers/validate.py` | `engine/figure_serialize.py` | `figure_to_dict(...)` | ✓ WIRED | `from engine.figure_serialize import figure_to_dict`, applied to `result.computed_figure` |
| `app/main.py` | `app/routers/validate.py` | `include_router` | ✓ WIRED | `app.include_router(validate_router.router)` (app/main.py:75) |
| `app/services/spec.py` | `engine/spec.py` | `ProductionSpec.model_validate` | ✓ WIRED | Confirmed via service inspection |
| `app/services/spec.py` | `app/services/city_lookup.py` | `resolve_city_to_jurisdiction(...)` | ✓ WIRED | `from app.services.city_lookup import resolve_city_to_jurisdiction`, called at line 160 |
| `app/routers/spec.py` | `app/services/spec.py` | `handle_spec_submission(...)` | ✓ WIRED | Called at lines 121, 157, and in the JSON route |
| `app/main.py` | `app/routers/spec.py` | `include_router` | ✓ WIRED | `app.include_router(spec_router.router)` (app/main.py:74) |
| `.github/workflows/ci.yml` | `.github/scripts/mutation-check.sh` | `run: bash .github/scripts/mutation-check.sh` | ✓ WIRED | Confirmed present in job `mutation-check` |
| `.github/scripts/mutation-check.sh` | `tests/mutation_targets.yaml` | declared table read, never hard-coded | ✓ WIRED | Confirmed by orchestrator's independent script run |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Anora reproduces exactly via JSON route | `GET /api/v1/validate/ny_anora` | `computed_credit == disclosed_credit == "991190"`, `verdict == "exact match"` | ✓ PASS (orchestrator-confirmed) |
| Money crosses JSON boundary as string | inspect `engine/figure_serialize.py` | `str(figure.value)` at line 33 | ✓ PASS |
| Budget field always refused | `POST /spec` with `total_budget=5000000` | 200, body contains circularity explanation | ✓ PASS (independently reproduced this session) |
| Unrecognized city never suggested | `POST /api/v1/spec` naming `Reykjavik` | 200, `jurisdiction_id: null`, `status: "no curated model"` | ✓ PASS (independently reproduced this session) |
| Non-numeric crew_size on HTML form route | `POST /spec` with `crew_size=not-a-number` | 500 Internal Server Error | ✗ FAIL (independently reproduced this session; see Gaps) |
| Mutation non-vacuity gate | `bash .github/scripts/mutation-check.sh` | exits 0, all five steps pass, git status unchanged | ✓ PASS (orchestrator-confirmed) |
| Full test suite | `uv run pytest tests/ -q` | 219 passed | ✓ PASS (independently re-run this session) |
| Debt-marker scan | `grep -rn TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER` across all phase-modified files | no matches | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| JUR-01 | 03-01 | New York validated model, reproducing NY ESD figures | ✓ SATISFIED | Orchestrator-confirmed exact match at the API layer |
| INP-01 | 03-02 | Production type and scale | ⚠️ PARTIAL | Type enum present; "scale" deliberately not modeled as a separate field (human-ratified decision, see Priority Note below) |
| INP-02 | 03-02 | Shoot days stage/location | ✓ SATISFIED | `shoot_days_stage`, `shoot_days_location` fields, boundary tests pass |
| INP-03 | 03-02 | Crew size or tier | ✗ BLOCKED (on the HTML route only) | The JSON route (`POST /api/v1/spec`) validates this correctly via Pydantic; the HTML route (`POST /spec`) crashes with 500 on a non-numeric `crew_size` — see CR-01 |
| INP-04 | 03-02 | Principal cast count / imported count | ✓ SATISFIED | Boundary tests confirmed passing (imported == total accepted, one over rejected) |
| INP-05 | 03-02 | Crew imported vs. hired locally | ✓ SATISFIED | Cross-field validator confirmed, guarded to explicit-crew_size branch |
| INP-06 | 03-02 | Start window by quarter and year | ✓ SATISFIED | `start_quarter`/`start_year` fields with 2024-2036 bound |
| INP-07 | 03-02 | Candidate cities, never suggested | ✓ SATISFIED | Independently reproduced no-suggestion behavior |
| INP-08 | 03-02 | Budget rejected as input | ✓ SATISFIED | Independently reproduced two-layer refusal |
| SHP-14 | 03-03 | Validation suite non-vacuity | ✓ SATISFIED | Orchestrator-confirmed mutation-check gate |

No orphaned requirements — all 10 IDs declared across the three plans' frontmatter (`JUR-01`, `INP-01`…`INP-08`, `SHP-14`) match REQUIREMENTS.md's Phase 3 mapping exactly (`grep` of the traceability table returned exactly this set, `status: Complete`).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `app/routers/spec.py` | ~105-122 | Unguarded `int(crew_size)` inline argument expression, outside the `try/except ValidationError` block | 🛑 Blocker | Reproducible unhandled HTTP 500 on a foreseeable, realistic input; directly contradicts the phase's own stated "never a 500" invariant, repeated in this same file's comments |
| `app/services/validate.py` | 150, 184-214 | Several internal-consistency checks (`assertion` key access, `program_id` match, missing `tolerance_bps`, division by `qualified_spend`, unrecognized `assertion.mode`) raise bare `ValueError`/`KeyError` not caught by the router | ⚠️ Warning | Not exploitable via the live surface today (all active fixtures are well-formed), but a future fixture-authoring mistake would 500 rather than refuse gracefully (03-REVIEW.md WR-03) |
| `app/services/spec.py` + `app/services/validate.py` | 44-50, 39-47 | `REPO_ROOT`/`RULESET_PATH_BY_JURISDICTION` duplicated verbatim | ⚠️ Warning | No test guards the two dicts staying in sync as jurisdictions are added (03-REVIEW.md WR-04) |
| `app/services/validate.py` | 55-61, 100 | `SelectablePair.jurisdiction_id: str` typed non-Optional but populated from `.get(...)`, actually `str \| None` | ⚠️ Warning | Misleading type hint, not a runtime crash today (03-REVIEW.md WR-05) |
| `.github/scripts/mutation-check.sh` | 171-181 | `sed` substitution unescaped, no exit-status check; "1 occurrence" check doesn't confirm a 0→1 transition | ⚠️ Warning | Currently masked by the occurrence-count check catching a broken/no-op substitution as a `FAIL`, but the failure message would misattribute the cause for a future mutation row (03-REVIEW.md WR-01/WR-02) |

No debt markers (`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`) found in any phase-modified file — clean grep.

## Priority-Note Assessment: the "and scale" dimension (Success Criterion 1)

`ProductionSpec` (engine/spec.py) carries `production_type: Literal["feature", "limited_series", "episodic"]` and no separate numeric scale field (no `episode_count`, no `scale_note`). This is not an oversight: 03-02-PLAN.md Task 1 is a `checkpoint:decision, gate="blocking"` task that explicitly names this ambiguity — whether INP-01's "and scale" is a second dimension beyond the type enum — lays out three options, and states option A (type-only) is both "the research recommendation" and "the correct answer if you want to move fastest." 03-02-SUMMARY.md documents that this was resolved to option A, and the orchestrator's brief for this verification confirms "the user was consulted and ratified this retroactively."

**Assessed as accepted-and-documented, not a gap**, because: (1) the decision was surfaced as a blocking checkpoint rather than silently skipped, (2) it was human-ratified per the orchestrator's brief, (3) the plan explicitly frames it as additive-later (a scale/episode-count field can be added without breaking any existing consumer), and (4) INP-01's own text — "production type and scale (feature / limited series / episodic)" — is genuinely ambiguous about whether the parenthetical *is* the scale axis. This is recorded here for visibility per the verification brief's instruction, not folded silently into a passing score, but it does not independently fail Success Criterion 1 given the explicit human sign-off.

## Gaps Summary

One blocking gap: **`POST /spec` (the HTML form route — the literal path a "visitor at the hosted URL" would use to describe a production) crashes with an unhandled 500 when `crew_size` is a non-numeric string.** This was found by the phase's own code reviewer (03-REVIEW.md CR-01) and independently reproduced in this verification session with `TestClient(app, raise_server_exceptions=False).post("/spec", data={..., "crew_size": "not-a-number", ...})` → `500 Internal Server Error`. The root cause is a single unguarded `int(crew_size)` expression evaluated as an argument to `SpecFormSubmission(...)`, outside the `try/except ValidationError` block meant to catch exactly this class of bad input. Every sibling integer field (`shoot_days_stage`, `start_year`, etc.) is typed `int = Form(...)` and gets FastAPI's automatic 422; `crew_size` alone was hand-rolled and is the one field missing the safety net.

This is scored as a genuine failure of Success Criterion 1 ("a visitor can describe a production ... crew size or a tier") rather than a cosmetic defect, because: it is on the primary demo path (the HTML form, not just the JSON API); it is trivially reachable (any client that doesn't enforce the HTML `type="number"` client-side constraint — curl, a judge's manual test, a mobile browser edge case); and it directly contradicts the phase's own repeatedly-stated "never a 500, never a bare framework error page" invariant. The fix is small (catch `ValueError` alongside `ValidationError`, or defensively pre-parse `crew_size`) and is fully scoped in 03-REVIEW.md CR-01's suggested fix.

Three items are deferred to human verification because they are properties of the live Lightsail deployment that no automated check in this session (or in the executing plans, per their own D4/D7/D5 deferrals) has exercised: the hosted `/finance/validate` page, the hosted `/finance/spec` page (which is also where the CR-01 crash would actually be hit by a real visitor), and the hosted GitHub Actions run showing `mutation-check (SHP-14)` as a green sixth job with the deliberate red visible in its log. The phase goal explicitly says "a visitor at the hosted URL" — none of that surface has been deployed or checked live in this verification run, so these are recorded as open human-verification items regardless of the gaps_found status, to be re-checked once CR-01 is fixed and a deploy happens.

---

*Verified: 2026-08-26T02:37:19Z*
*Verifier: Claude (gsd-verifier)*
