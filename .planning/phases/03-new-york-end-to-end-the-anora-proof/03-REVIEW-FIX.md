---
phase: 03-new-york-end-to-end-the-anora-proof
fixed_at: 2026-08-26T02:54:49Z
review_path: .planning/phases/03-new-york-end-to-end-the-anora-proof/03-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-08-26T02:54:49Z
**Source review:** .planning/phases/03-new-york-end-to-end-the-anora-proof/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (CR-01, WR-01, WR-02, WR-03, WR-04, WR-05 — Critical + Warning per fix_scope; IN-01 is Info-tier and out of scope, left untouched)
- Fixed: 6
- Skipped: 0

Full suite: 219 passed before this run -> 228 passed after (9 new regression tests added across the fixes). `bash .github/scripts/mutation-check.sh` re-run three times during this session (baseline, mid-run after WR-01/WR-02, and final), exits 0 each time, all five steps pass, `git status --porcelain` byte-identical before/after each run.

## Fixed Issues

### CR-01: Non-numeric `crew_size` on `POST /spec` crashes with an unhandled 500

**Files modified:** `app/routers/spec.py`, `tests/test_app_spec_route.py`
**Commit:** `5de8f18`
**Applied fix:** `crew_size` was converted with a bare `int(crew_size)` evaluated as an inline argument expression to `SpecFormSubmission(...)`, so a non-numeric value raised an uncaught `ValueError` before the surrounding `except ValidationError` block could catch it. Reproduced first with `TestClient(app, raise_server_exceptions=False).post("/spec", ...)` -> confirmed `500`. Applied the review's more specific suggested fix: `crew_size` is now defensively pre-parsed into `crew_size_value` before `SpecFormSubmission(...)` is constructed; a `ValueError` from that parse returns the same readable 422 form re-render path every other bad-input case already uses, naming the bad value (`f"Crew size must be a whole number; got {crew_size_text!r}."`). Re-ran the same reproduction after the fix -> confirmed `422`, body contains `not-a-number`. Added `test_post_spec_form_non_numeric_crew_size_never_500s`, which posts the exact form payload from the review's reproduction steps and asserts `status_code == 422` (not 500) and that the response names the bad value.

### WR-01 / WR-02: `mutation-check.sh`'s `sed` substitution has no exit-status check, no escaping, and the "one occurrence" check doesn't prove a substitution occurred

**File modified:** `.github/scripts/mutation-check.sh`
**Commit:** `064c40b`
**Applied fix:** Combined both findings into one fix on the same lines (step 3 of the script), per the review's own adjacent, overlapping fix suggestions. `FIND`/`REPLACE` are now escaped for `/` before interpolation into `sed`'s `s///` (`${FIND//\//\\/}` / `${REPLACE//\//\\/}`), sed's own exit status is checked explicitly (`if ! sed ... ; then FAIL; fi`) rather than trusting the `>` redirection to have produced valid output, and the post-mutation occurrence count is now compared against a pre-mutation `BEFORE_COUNT` snapshot (`ACTUAL_COUNT -ne BEFORE_COUNT + 1`) instead of a bare `-ne 1` check — closing the "no-op sed + coincidentally pre-existing REPLACE string" false-proof gap. Per the task constraints, verified the script itself after the change: `bash .github/scripts/mutation-check.sh` still exits 0, still runs all five ordered steps for the one active row, and `git status --porcelain` is byte-identical before/after (verified three separate times across this session, including once more after all six fixes landed).

### WR-03: Several `reproduce_disclosure` failure paths raise uncaught exceptions that would 500, not refuse gracefully

**Files modified:** `app/services/validate.py`, `app/routers/validate.py`, `tests/test_app_validate_route.py`
**Commit:** `8e693a4`
**Applied fix:** Introduced `MalformedFixtureError`, a new typed exception distinct from `price_jurisdiction`'s existing `ValueError` (WINDOWS.md #3's honest-refusal path, left untouched). All five named failure paths in `reproduce_disclosure` now raise it instead of a bare `ValueError`/`KeyError`: a missing/malformed `assertion` block, an `assertion.mode` missing entirely, an unmatched `program_id` (also switched to `.get()` so a missing key doesn't `KeyError` first), a `bounded` assertion missing `tolerance_bps`, a `qualified_spend` of `0` (previously an unguarded `ZeroDivisionError`, not actually a `ValueError` as the review's classification suggested — added an explicit guard), and an unrecognized `assertion.mode`. Both `GET` routes (`/api/v1/validate/{pair_id}`, `/validate/{pair_id}`) now catch `MalformedFixtureError` and convert it to a handled `HTTPException(status_code=500, ...)` with a readable detail message — genuinely a server-side data problem, but a caught, readable one, never an unhandled crash with a bare stack trace. `POST /validate` catches it and re-renders `validate_form.html` naming the reason, matching the existing `UnknownPairError` re-render pattern used for the sibling case. Added six regression tests that monkeypatch the real, repo-committed `ny_anora.yaml` fixture in-memory (via a `_mutate_ny_anora_fixture` helper) to exercise each of the five malformed-fixture paths plus the POST re-render path, without ever committing a bad fixture to the repo.

### WR-04: `REPO_ROOT` / `RULESET_PATH_BY_JURISDICTION` duplicated verbatim across two service modules

**Files modified:** `app/services/_paths.py` (new), `app/services/spec.py`, `app/services/validate.py`, `tests/test_app_spec_route.py`
**Commit:** `0c34c22`
**Applied fix:** Extracted `REPO_ROOT` and `RULESET_PATH_BY_JURISDICTION` into a new shared module `app/services/_paths.py` (the exact path the review suggested). Both `app/services/spec.py` and `app/services/validate.py` now import from it instead of declaring their own copies; both modules continue to re-export the names in their own `__all__` for backward compatibility (nothing outside the two modules imported these names directly, confirmed by grep before making the change). Added `test_ruleset_path_by_jurisdiction_is_shared_between_spec_and_validate`, which asserts `spec_dict is validate_dict` (object identity, not just equal contents) — this is what actually proves a single source of truth rather than two dicts that merely happen to match today.

### WR-05: `SelectablePair.jurisdiction_id: str` (non-Optional) can actually be `None` at runtime

**Files modified:** `app/services/validate.py`, `tests/test_app_validate_route.py`
**Commit:** `dd54ffb`
**Applied fix:** Retyped `SelectablePair.jurisdiction_id` from `str` to `str | None` to match what `data.get("jurisdiction_id")` actually returns for a fixture missing the key. Deliberately did **not** apply the review's optional second half of the fix (a fail-loud loading guard) — see reasoning below. Added `test_selectable_pairs_handles_missing_jurisdiction_id_as_none`, which monkeypatches the `ny_anora` fixture to drop `jurisdiction_id` and confirms the documented runtime behavior actually holds: no crash, the pair comes back `selectable=False` with reason `"no curated rule model for None in this phase"`.

**Deliberate deviation from the review's suggested fix, recorded per the task instructions:** the review's `Fix:` offered "Type it `jurisdiction_id: str | None` to match reality, and/or add a fixture-loading guard that fails loudly (naming the fixture file) when `jurisdiction_id` is absent rather than silently defaulting to `None`." I applied only the type fix. Reasoning: `selectable_pairs()` deliberately lists **every** committed fixture, including malformed/unselectable ones, specifically so a bad fixture is shown with a readable reason rather than silently dropped (see the function's own docstring: "An unselectable pair is never dropped from the returned tuple"). `selectable_pairs()` is called by every `/validate` route, including the `GET /validate` listing page that must show all the *other*, valid pairs too. Making a missing `jurisdiction_id` raise inside this function would mean one future fixture-authoring mistake takes down the entire `/validate` listing for every pair, not just the bad one — trading a documented-safe fallback (today's actual, verified behavior) for a new whole-page crash risk, which directly contradicts this same review's own "never a 500" theme running through CR-01 and WR-03. The type-only fix delivers the review's stated goal (the annotation now matches reality, so a future reader/reviewer is no longer misled) without introducing that regression risk. This is not a disagreement with the finding — it's real and the type was wrong — just a narrower scope than one of the two "and/or" options offered.

## Skipped Issues

None — all six in-scope findings were fixed.

---

_Fixed: 2026-08-26T02:54:49Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
