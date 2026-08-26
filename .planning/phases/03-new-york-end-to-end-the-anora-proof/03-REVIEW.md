---
phase: 03-new-york-end-to-end-the-anora-proof
reviewed: 2026-08-25T00:00:00Z
depth: standard
files_reviewed: 25
files_reviewed_list:
  - .github/scripts/mutation-check.sh
  - .github/workflows/ci.yml
  - app/main.py
  - app/routers/__init__.py
  - app/routers/spec.py
  - app/routers/validate.py
  - app/services/__init__.py
  - app/services/city_lookup.py
  - app/services/spec.py
  - app/services/validate.py
  - app/templates/base.html
  - app/templates/index.html
  - app/templates/spec_form.html
  - app/templates/spec_result.html
  - app/templates/validate_form.html
  - app/templates/validate_result.html
  - data/crew_tiers.yaml
  - engine/figure_serialize.py
  - engine/spec.py
  - pyproject.toml
  - tests/mutation_targets.yaml
  - tests/test_app_spec_route.py
  - tests/test_app_validate_route.py
  - tests/test_engine_spec.py
  - uv.lock
findings:
  critical: 1
  warning: 5
  info: 1
  total: 7
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-08-25
**Depth:** standard
**Files Reviewed:** 25
**Status:** issues_found

## Summary

Phase 3 wires up Route A ("Price a production") and Route B ("Reproduce a disclosure") end to end, plus the mutation non-vacuity CI gate. The project's core monetary-correctness and honesty invariants generally hold up under direct inspection: every `Decimal` crossing the JSON boundary in both routers goes through `str(...)` (`app/routers/validate.py::_validate_result_to_json`, `engine/figure_serialize.py::figure_to_dict`), no `float(` appears anywhere in the reviewed `app/` or `engine/` code, Route A structurally never imports `engine.pipeline`/`engine.qualifying_base` and derives no dollar figure, the closed-set `pair_id` membership check in `reproduce_disclosure` genuinely runs before any path is built (verified by reading the code, not just trusting the docstring), Jinja2 autoescape is on throughout with no `|safe` filter anywhere in the five templates, and a grep across every phase-3 file for the full forbidden-vendor list (Textract, Bedrock, Comprehend, Rekognition, Transcribe, Polly, Kendra, SageMaker, OpenAI, Anthropic, LangChain, llama_index, crewai) turned up nothing, including inside `uv.lock`.

The one confirmed BLOCKER is a real, reproduced crash: `POST /spec` with a non-numeric `crew_size` field (e.g. `crew_size=abc`, trivially sent by anything other than the HTML form's client-side `type="number"` constraint) raises an uncaught `ValueError` and returns an unhandled 500, directly contradicting this same file's own repeated comments that a bad submission "is never a 500... never a bare framework error page." This was verified by direct reproduction with `TestClient`, not inferred from reading alone.

The mutation-check.sh gate (SHP-14's non-vacuity proof) is well-constructed and its headline claims hold for the one active row, but it has two structural soft spots worth tracking before a second row is added under time pressure: the `sed` substitution interpolates `FIND`/`REPLACE` with no escaping or exit-status check, and the "exactly one occurrence of REPLACE outside comments" check does not, by itself, prove a substitution actually happened (a no-op `sed` combined with a coincidentally pre-existing REPLACE string would pass step 3 without ever mutating anything) — both are pre-existing risks the plan's own decision notes already flagged as deferred, not new discoveries, but they are real gaps in the "verified rather than trusted" claim and belong in the review record.

## Critical Issues

### CR-01: Non-numeric `crew_size` on `POST /spec` crashes with an unhandled 500

**File:** `app/routers/spec.py:105-122`
**Issue:** `crew_size` is deliberately typed as `str = Form("")` (not `int`) so the router can distinguish "field left blank" from "field supplied," but the conversion to `int` is done inline as an argument expression to `SpecFormSubmission(...)`:
```python
raw = SpecFormSubmission(
    ...
    crew_size=int(crew_size) if crew_size.strip() else None,
    ...
)
```
This expression is evaluated *before* `SpecFormSubmission.__init__` ever runs, so a non-numeric value (e.g. `crew_size=abc`) raises a bare Python `ValueError` from `int()`, not a `pydantic.ValidationError`. The surrounding `try/except` only catches `ValidationError` (line 122), so the `ValueError` propagates unhandled out of the route handler and FastAPI returns a 500.

Reproduced directly:
```
$ uv run python -c "..." (TestClient POST /spec, crew_size='not-a-number')
RAISED (uncaught by app, TestClient re-raises server exceptions): ValueError invalid literal for int() with base 10: 'not-a-number'
```
Every other integer-typed form field (`shoot_days_stage`, `start_year`, etc.) is declared `int = Form(...)` directly in the route signature, so FastAPI/Pydantic validates and 422s those automatically before the handler body runs — `crew_size` is the sole field with a hand-rolled conversion, and it is the one field missing the safety net. This directly contradicts the "never a 500, never a bare framework error page" invariant stated in this exact function's own surrounding comments and in `app/routers/validate.py`'s equivalent handler.

**Fix:** Catch `ValueError` alongside `ValidationError` (minimal, one-line fix consistent with the existing 422 rendering path already in place):
```python
except (ValidationError, ValueError) as exc:
    return templates.TemplateResponse(
        request=request,
        name="spec_form.html",
        context={
            "public_path": PUBLIC_PATH,
            "refusal_reason": None,
            "validation_error": str(exc),
        },
        status_code=422,
    )
```
or, for a more specific message, parse `crew_size` defensively before constructing `SpecFormSubmission`:
```python
crew_size_text = crew_size.strip()
try:
    crew_size_value = int(crew_size_text) if crew_size_text else None
except ValueError:
    return templates.TemplateResponse(
        request=request,
        name="spec_form.html",
        context={
            "public_path": PUBLIC_PATH,
            "refusal_reason": None,
            "validation_error": f"Crew size must be a whole number; got {crew_size_text!r}.",
        },
        status_code=422,
    )
```
Add a regression test posting a non-numeric `crew_size` and asserting `response.status_code == 422` (not `500`).

## Warnings

### WR-01: `mutation-check.sh`'s `sed` substitution has no exit-status check and no escaping of `FIND`/`REPLACE`

**File:** `.github/scripts/mutation-check.sh:171-172`
**Issue:**
```bash
sed "s/${FIND}/${REPLACE}/" "$FILE" > "$FILE.mut"
mv "$FILE.mut" "$FILE"
```
`FIND` and `REPLACE` are interpolated directly into the `sed` script with no delimiter-collision escaping and no regex-metacharacter escaping (the current row's `find`/`replace` values happen to be delimiter-safe, and this was already flagged as a known, deferred risk in 03-03-SUMMARY.md's own decision notes — this finding formalizes that same risk for the review record rather than discovering something new). More concretely: `sed`'s exit status is never checked. If a future row's `find`/`replace` value breaks the `s///` syntax (e.g. contains an unescaped `/`), `sed` fails, and `$FILE.mut` — created by the `>` redirection regardless of whether `sed` itself succeeds — can be empty or truncated; that broken content is then `mv`'d directly over the real target file inside the scratch copy. In practice this is caught one step later by the occurrence-count check in step 3 (an empty/broken file won't contain the expected `REPLACE` string, so the script does correctly `FAIL`), so this is not currently a silent-pass hole — but the failure message it produces (`"found 0 occurrence(s)"`) would misleadingly look like a data problem rather than what actually happened (a `sed` syntax error), costing debugging time for a future row author under the 17-day deadline.
**Fix:** Check `sed`'s own exit status explicitly and use a delimiter unlikely to collide (or escape `/` occurrences in `FIND`/`REPLACE` before substitution):
```bash
if ! sed "s/${FIND//\//\\/}/${REPLACE//\//\\/}/" "$FILE" > "$FILE.mut"; then
  echo "FAIL: [$ID] step 3 — sed itself failed while applying the declared mutation to '$FILE'" >&2
  exit 1
fi
mv "$FILE.mut" "$FILE"
```

### WR-02: The "one occurrence of REPLACE" check does not, by itself, prove a substitution occurred

**File:** `.github/scripts/mutation-check.sh:174-181`
**Issue:** Step 3's non-vacuity check is:
```bash
ACTUAL_COUNT=$(grep -v '^[[:space:]]*#' "$FILE" | grep -Fc -- "$REPLACE" || true)
if [ "$ACTUAL_COUNT" -ne 1 ]; then
  echo "FAIL: ..." >&2
  exit 1
fi
```
This counts occurrences of the `REPLACE` text in the post-`sed` file; it does not check that the pre-`sed` file lacked that text (i.e. it doesn't confirm the count went from 0 to 1). If `FIND` fails to match anything in the file (a no-op `sed`, silently exiting 0) and the file coincidentally already contained the literal `REPLACE` string once elsewhere (unlikely for the current row's `base_rate: "0.2501"`, but not structurally impossible for a future row with a shorter or more generic `find`/`replace` pair), step 3 would report `PASS` on a mutation that never actually applied — which is precisely the "false proof" class of bug this whole script exists to rule out for the *validation suite*, just one level up, in the mutation-application step itself.
**Fix:** Snapshot the pre-mutation occurrence count of `REPLACE` (expected 0, or count `FIND` before / `REPLACE` after and diff), e.g.:
```bash
BEFORE_COUNT=$(grep -v '^[[:space:]]*#' "$FILE.orig" | grep -Fc -- "$REPLACE" || true)
...
if [ "$ACTUAL_COUNT" -ne "$((BEFORE_COUNT + 1))" ]; then
  echo "FAIL: [$ID] step 3 — REPLACE occurrence count did not increase by exactly one" >&2
  exit 1
fi
```

### WR-03: Several `reproduce_disclosure` failure paths raise uncaught exceptions that would 500, not refuse gracefully

**File:** `app/services/validate.py:150 (assertion = pair["assertion"])`, `184-193 (unmatched program_id)`, `203-204 (missing tolerance_bps)`, `205 (division by qualified_spend)`, `213-214 (unrecognized assertion.mode)`
**Issue:** `reproduce_disclosure` catches `price_jurisdiction`'s `ValueError` explicitly (documented as WINDOWS.md #3's honest-refusal path), but several other internal-consistency checks in the same function raise bare `ValueError`/`KeyError` that the router (`app/routers/validate.py`) does not catch — only `UnknownPairError` is caught there. A validation-pair fixture with a missing `assertion` key, a `program_id` that doesn't match any programme in the ruleset, a `bounded` mode missing `tolerance_bps`, an unrecognized `assertion.mode`, or (for the bounded-verdict arithmetic) a `qualified_spend` of `0` would all propagate out as an unhandled 500 for that pair's route, rather than the graceful refusal this same module goes out of its way to provide for the one case it does guard. These are trusted, repo-committed fixtures today (not attacker input), and none of the active fixtures currently trigger any of these paths, so this is not exploitable through the live HTTP surface right now — but it is a real gap against a future fixture-authoring mistake (a typo'd `program_id` in a new pair, or a copy-pasted `bounded` block missing `tolerance_bps`), and it directly contradicts the "never a 500" posture this file states for the sibling case it does handle.
**Fix:** Wrap `reproduce_disclosure`'s body (or at least the `program_id` match, `assertion` parsing, and bounded-mode arithmetic) so these conditions raise a typed, catchable exception (e.g. a `MalformedFixtureError` alongside `UnknownPairError`) and have the router convert it to a 500-avoiding response — or, at minimum, add a fixture-integrity CI check (parallel to `mutation-check.sh`) that asserts every active fixture's `assertion` block and `program_id` are internally consistent with its ruleset, so a bad fixture never reaches production in the first place.

### WR-04: `REPO_ROOT` / `RULESET_PATH_BY_JURISDICTION` duplicated verbatim across two service modules

**File:** `app/services/spec.py:44-50`, `app/services/validate.py:39-47`
**Issue:** Both files independently declare:
```python
REPO_ROOT = Path(__file__).resolve().parents[2]
RULESET_PATH_BY_JURISDICTION: dict[str, Path] = {
    "us-ny": REPO_ROOT / "jurisdictions" / "us-ny.yaml",
}
```
byte-for-byte identical in intent (both comments even say "matches app/services/validate.py's identical jurisdiction scoping" / vice versa). Phase 4+ adding a second jurisdiction requires remembering to update this dict in two separate files identically — a missed update in one would silently desync Route A's rule-terms display from Route B's pricing path for the new jurisdiction, with no test currently guarding that the two dicts stay in sync.
**Fix:** Extract `REPO_ROOT` and `RULESET_PATH_BY_JURISDICTION` into a single shared module (e.g. `app/services/_paths.py` or `app/services/__init__.py`) that both `spec.py` and `validate.py` import from.

### WR-05: `SelectablePair.jurisdiction_id: str` (non-Optional) can actually be `None` at runtime

**File:** `app/services/validate.py:55-61`, `100`
**Issue:** `SelectablePair.jurisdiction_id` is typed `str` (not `str | None`), but it is populated from `data.get("jurisdiction_id")` (line 100), which returns `None` for any fixture missing the key. Nothing in `selectable_pairs()` enforces the key's presence before constructing `SelectablePair`, so a malformed fixture would silently produce a `SelectablePair` whose type contract is violated at runtime (Python dataclasses don't enforce annotations). This wouldn't crash today — `None not in RULESET_PATH_BY_JURISDICTION` just resolves to the "no curated rule model" branch — but the type hint is actively misleading to a future reader/reviewer who trusts it, and the same shape of drift (annotated `str`, actually `str | None`) is likely to recur wherever fixture data is read without a schema.
**Fix:** Type it `jurisdiction_id: str | None` to match reality, and/or add a fixture-loading guard that fails loudly (naming the fixture file) when `jurisdiction_id` is absent rather than silently defaulting to `None`.

## Info

### IN-01: `date_checked` typing relies entirely on YAML authors quoting date values

**File:** `app/services/validate.py:80` (`date_checked: str | None`), `166` (`"date_checked": pair.get("date_checked")`)
**Issue:** Every current validation-pair fixture quotes `date_checked` as a string (e.g. `date_checked: "2026-08-24"`), which is the correct convention and is what makes `ValidateResult.date_checked: str | None` accurate today. If a future fixture author omits the quotes, PyYAML's `safe_load` parses an unquoted ISO-8601-shaped scalar as a native `datetime.date` object instead of `str`, silently violating this type hint. This happens not to break anything functionally today — FastAPI's `jsonable_encoder` and Jinja2's implicit `str()` coercion both still render a `date` object as its ISO string — but it is a latent inconsistency with this project's stated "every value crosses the boundary via an explicit conversion, never an implicit one" posture, and the quoting convention is enforced only by comment/convention, not by any test or schema.
**Fix:** Either add a small loader-side assertion (`isinstance(pair.get("date_checked"), str)`) alongside the existing fixture loading, or accept `date | str | None` and normalize explicitly with `str(...)` at the point of use, matching the explicit-conversion pattern already used for `Decimal` and `Figure.date_checked` elsewhere in this same phase's code.

---

_Reviewed: 2026-08-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
