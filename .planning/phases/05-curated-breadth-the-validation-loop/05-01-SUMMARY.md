---
phase: 05-curated-breadth-the-validation-loop
plan: 01
subsystem: ai-integration
tags: [google-genai, parallel-web, structured-extraction, tracer, eligibility]

requires:
  - phase: 04-cost-localization-landed-cost-outputs
    provides: engine/ pricing spine, jurisdictions/us-ny.yaml, app/services/_paths.py REPO_ROOT anchoring
provides:
  - "agent/ package: settings, telemetry, schema, parallel_client, gemini_client, job1"
  - "agent.job1.run_job1() — the fixed D-82 Search -> Extract -> Gemini -> engine.pipeline sequence"
  - "python -m agent.job1 CLI (--limit, --json, --require-live)"
affects: [05-02, 05-03, phase-8-reverification]

actuals:
  tokens: 10470
  tasks: 3
  commits: 3

tech-stack:
  added: ["google-genai==2.19.0", "parallel-web>=1.0.1"]
  patterns:
    - "Lazy-import SDK clients (import inside the function, never at module top) to keep FastAPI process footprint unchanged until a run fires"
    - "D-84 unconditional PRODFIN_SDK_CALL log line via a context manager, no debug/verbosity gate"
    - "One Pydantic model -> model_json_schema() -> response_json_schema, never a second hand-written JSON schema (D-83)"

key-files:
  created:
    - agent/__init__.py
    - agent/settings.py
    - agent/telemetry.py
    - agent/schema.py
    - agent/parallel_client.py
    - agent/gemini_client.py
    - agent/job1.py
    - tests/test_agent_eligibility.py
    - .planning/phases/05-curated-breadth-the-validation-loop/COVERAGE.md
  modified:
    - pyproject.toml
    - uv.lock
    - deploy/README.md

key-decisions:
  - "Search/Extract call signatures resolved by introspecting the installed parallel-web 1.3.3 SDK, not written from memory — client.search(objective=, search_queries=, ...) -> SearchResult(results: list[WebSearchResult(url, excerpts, title, publish_date)]); client.extract(urls=, objective=, ...) -> ExtractResponse(results: list[ExtractResult(url, full_content, excerpts, ...)])"
  - "google-genai 2.19.0's GenerateContentConfig confirmed to expose response_mime_type and response_json_schema directly; response.text carries the JSON string parsed via ExtractedAwardSet.model_validate_json"
  - "Task 2's tests found no correctness gap requiring hardening beyond ruff lint (import ordering / __all__ sort / datetime.UTC alias) in agent/settings.py and agent/telemetry.py — folded into the Task 2 commit as trivial, non-behavioral fixes"

requirements-completed: [SHP-05, SHP-06, AGT-09, AGT-01]

coverage:
  - id: D1
    description: "agent/ package wires Parallel Search -> primary-domain filter -> Parallel Extract -> google-genai structured extraction -> engine.pipeline.price_jurisdiction, in that fixed order (D-82)"
    requirement: AGT-01
    verification:
      - kind: unit
        ref: "tests/test_agent_eligibility.py#test_sdk_call_prefix_used_at_both_call_sites"
        status: pass
      - kind: unit
        ref: "tests/test_agent_eligibility.py#test_gemini_client_uses_model_json_schema_never_a_hand_written_schema"
        status: pass
    human_judgment: true
    rationale: "The live end-to-end run (a real Search result, a real Extract, a real Gemini call, a real priced Decimal) cannot be exercised in this environment — PARALLEL_API_KEY and GEMINI_API_KEY are not set. The tests prove every call site is real and correctly wired; only a human with both keys can prove the live path actually produces a correct number end to end. See 'API keys reality' below."
  - id: D2
    description: "D-84 unconditional PRODFIN_SDK_CALL log line at both SDK call sites, timestamped, with elapsed_ms, surviving uvicorn's logging reconfiguration"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/test_agent_eligibility.py#test_sdk_call_emits_one_line_with_elapsed_and_ok_outcome"
        status: pass
      - kind: unit
        ref: "tests/test_agent_eligibility.py#test_sdk_call_reraises_and_logs_error_outcome"
        status: pass
      - kind: unit
        ref: "tests/test_agent_eligibility.py#test_sdk_call_implementation_has_no_verbosity_guard"
        status: pass
    human_judgment: false
  - id: D3
    description: "Missing keys produce a legible not-configured state naming both variables, never a crash and never a fabricated award (D-87); the app keeps serving every pre-existing route"
    requirement: SHP-05
    verification:
      - kind: unit
        ref: "tests/test_agent_eligibility.py#test_app_serves_all_pre_existing_routes_with_no_keys"
        status: pass
      - kind: unit
        ref: "tests/test_agent_eligibility.py#test_not_configured_message_names_both_variables_no_values"
        status: pass
      - kind: unit
        ref: "tests/test_agent_eligibility.py#test_app_main_import_leaves_sdks_unimported"
        status: pass
    human_judgment: false
  - id: D4
    description: "Both dependencies resolved cleanly via uv add, no forbidden package or extras marker entered the lockfile, no forbidden AWS-AI-service token entered the source tree"
    requirement: null
    verification:
      - kind: other
        ref: "bash .github/scripts/lockfile-scan.sh"
        status: pass
      - kind: other
        ref: "bash .github/scripts/vendor-scan.sh"
        status: pass
    human_judgment: false
  - id: D5
    description: "Phase 5 COVERAGE.md and deploy/README.md credential runbook document the flipped opt-outs and the exact human steps to install both keys"
    requirement: null
    verification:
      - kind: other
        ref: "grep -q parallel.search / google-genai.structured-extraction / PARALLEL_API_KEY / GEMINI_API_KEY (see plan Task 3 <verify>)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-09
status: complete
---

# Phase 5 Plan 1: SHP-05/SHP-06 Eligibility Spine Summary

**`agent/` package wires Parallel Search, Parallel Extract, and `google-genai` structured extraction into one fixed pipeline feeding the existing pricing engine — verified correct end to end except the live network calls, which require API keys no agent can obtain.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-09T06:11:00Z (approx.)
- **Completed:** 2026-09-09T07:06:16Z
- **Tasks:** 3
- **Files modified:** 12 (9 created, 3 modified)

## CRITICAL: API keys reality — read before treating this as "done"

**`PARALLEL_API_KEY` and `GEMINI_API_KEY`/`GOOGLE_API_KEY` are NOT set in this
environment, and no live SDK call was made during this execution.** Every
claim below about the code being "wired correctly" is proven by:
1. Method-signature introspection of the actually-installed SDKs
   (`parallel-web==1.3.3`, `google-genai==2.19.0`) — not memory, not the
   plan's prose.
2. `tests/test_agent_eligibility.py` — 14 tests proving both SDK imports
   sit inside a function body on the real call path, that the D-84 log
   line is unconditional and correctly shaped, that the schema is sourced
   from `model_json_schema()`, and that the app degrades legibly with no
   keys.
3. Running `python -m agent.job1 --limit 1 [--require-live]` with no keys
   present, and confirming it prints the not-configured message and exits
   0 (or 2 with `--require-live`) rather than crashing.

**None of this constitutes a validated live run.** SHP-05 and SHP-06 remain
**UNVERIFIED-IN-PRODUCTION** until a human obtains both keys and runs:

```bash
export PARALLEL_API_KEY=...
export GEMINI_API_KEY=...
uv run --frozen python -m agent.job1 --limit 1 --require-live
```

A successful run must print one real production title, its disclosed
credit, and the engine-computed credit as `Decimal`s, plus exactly one
`PRODFIN_SDK_CALL sdk=parallel-web ...` line and one
`PRODFIN_SDK_CALL sdk=google-genai ...` line on stdout, and exit 0. Until
that command has actually been run once by a human with real keys, no
figure this pipeline would produce has been validated — it has only been
proven correctly *plumbed*.

## Accomplishments

- `agent/` package: `settings.py` (env-only key resolution + D-88 primary-
  government-domain allowlist + `IntegrationStatus`), `telemetry.py` (D-84
  `PRODFIN_SDK_CALL` unconditional log line via a context manager),
  `schema.py` (`ExtractedAward`/`ExtractedAwardSet`, D-83 single schema
  source), `parallel_client.py` (lazy-imported Search + Extract, T-05-01
  domain-suffix filter), `gemini_client.py` (lazy-imported structured
  extraction, T-05-02 no-tools guardrail), `job1.py` (the fixed D-82
  sequence + CLI).
- `tests/test_agent_eligibility.py` — 14 tests, the standing CI gate for
  SHP-05/SHP-06, all passing with no keys in the environment.
- Phase 5 `COVERAGE.md` and a `deploy/README.md` credential runbook.
- `google-genai==2.19.0` and `parallel-web>=1.0.1` resolved via `uv add`;
  both CI scan scripts (`lockfile-scan.sh`, `vendor-scan.sh`) still exit 0.
- Full pre-existing test suite stays green: 490 passed (476 before this
  plan + 14 new).

## Task Commits

1. **Task 1: End-to-end — Parallel Search, Parallel Extract, google-genai, engine, one award** - `d2ce048` (feat)
2. **Task 2: The eligibility gate** - `a9835fc` (test)
3. **Task 3: Phase 5 COVERAGE.md and the credential runbook** - `8c45601` (docs)

_Task 2 carried `tdd="true"`. In practice it was write-tests-against-
already-tracer-built-code rather than a literal RED-then-GREEN two-commit
cycle: Task 1's tracer already implemented the full pipeline, so Task 2's
job was to write a test suite that COULD fail (and initially did — see
Deviations) against that existing code, then harden anything it exposed.
No separate failing-test commit was created; the single `test(05-01)`
commit lands with all 14 tests already green, which is the intended shape
for this plan (see plan Task 2 `<action>`: "harden anything the tests
expose")._

## Files Created/Modified

- `agent/__init__.py` - package docstring, no top-level SDK import
- `agent/settings.py` - env-only key resolution, D-88 domain allowlist, `IntegrationStatus`
- `agent/telemetry.py` - D-84 `sdk_call()` context manager + stdout handler
- `agent/schema.py` - `ExtractedAward`, `ExtractedAwardSet`, `gemini_response_schema()`
- `agent/parallel_client.py` - `search_for_disclosure()`, `extract_document()`, T-05-01 filter
- `agent/gemini_client.py` - `extract_awards()`, T-05-02 no-tools guardrail
- `agent/job1.py` - `run_job1()`, `Job1Run`/`PricedAward` dataclasses, `__main__` CLI
- `tests/test_agent_eligibility.py` - 14-test SHP-05/SHP-06 CI gate
- `.planning/phases/05-curated-breadth-the-validation-loop/COVERAGE.md` - Phase 5 capability matrix
- `pyproject.toml` - added `google-genai`, `parallel-web`; added `agent` to hatch wheel packages
- `uv.lock` - resolved the two new dependencies (43 packages total)
- `deploy/README.md` - "Phase 5 — agent credentials" runbook section

## Decisions Made

- **Parallel SDK shape (resolved by introspection, not memory):**
  `parallel.Parallel(api_key=...)` exposes `.search(...)` and `.extract(...)`
  directly on the client (not under a `resources` submodule namespace for
  the top-level call). `client.search(objective=str, search_queries=list[str], ...)`
  returns `SearchResult(results: list[WebSearchResult])`, where
  `WebSearchResult` has `url: str`, `excerpts: list[str]`, `title: str | None`,
  `publish_date: str | None`. Results are pre-ranked by the API; this code
  takes the first one that passes the D-88 domain filter.
  `client.extract(urls=list[str], objective=str, ...)` returns
  `ExtractResponse(results: list[ExtractResult])`, where `ExtractResult`
  has `full_content: str | None` (the clean markdown/text — the field this
  pipeline actually consumes) plus `excerpts`, `url`, `title`,
  `publish_date`.
- **google-genai shape (resolved by introspection):**
  `genai.Client(api_key=...).models.generate_content(model=str, contents=str, config=GenerateContentConfig)`
  returns `GenerateContentResponse` with a `.text` property carrying the
  raw JSON string when `response_mime_type="application/json"` is set.
  `GenerateContentConfig` accepts `response_json_schema` directly (verified
  present in `GenerateContentConfig.model_fields` on the installed 2.19.0
  build) — no `response_schema` (Pydantic-model) indirection was needed;
  `ExtractedAwardSet.model_json_schema()` is passed straight through.
- No architectural deviations from the plan (Rule 4 was never invoked).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a self-invalidating source-scan test before it shipped**
- **Found during:** Task 2 (writing `tests/test_agent_eligibility.py`)
- **Issue:** The first draft of `test_gemini_client_imports_google_genai_inside_a_function`
  matched the substring `"from google import genai"` anywhere in the
  stripped source, including inside the module's own docstring prose (which
  quotes that exact import for documentation purposes). That draft failed
  immediately — a false positive the task's own instructions warned about
  ("a grep that counts a comment is a self-invalidating gate").
- **Fix:** Narrowed the match to lines whose *stripped* form equals exactly
  `"from google import genai"` (a real import statement), not a substring
  match against prose. Applied the same tightening to the parallel-client
  import-location test for symmetry.
- **Files modified:** `tests/test_agent_eligibility.py`
- **Verification:** `uv run --frozen pytest tests/test_agent_eligibility.py -q` — all 14 pass
- **Committed in:** `a9835fc` (Task 2 commit — the bug was caught and fixed before the commit, so no separate fix commit exists)

**2. [Rule 1 - Bug] ruff lint cleanup in agent/settings.py and agent/telemetry.py**
- **Found during:** Task 2 (`uv run ruff check`)
- **Issue:** `__all__` in `agent/settings.py` was not alphabetically sorted
  (RUF022); `agent/telemetry.py` imported `Iterator` from `typing` instead
  of `collections.abc` (UP035) and used `datetime.timezone.utc` instead of
  the `datetime.UTC` alias (UP017).
- **Fix:** `uv run ruff check --fix` applied all three; no behavior change
  (confirmed by full-suite pass after the fix).
- **Files modified:** `agent/settings.py`, `agent/telemetry.py`
- **Verification:** `uv run ruff check agent/ tests/test_agent_eligibility.py` — clean; `uv run --frozen pytest tests/ -q` — 490 passed
- **Committed in:** `a9835fc` (folded into the Task 2 commit as a trivial, non-behavioral fix surfaced while writing the gate)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 — a self-caught test bug and a lint cleanup, both caught before commit)
**Impact on plan:** Both trivial, both caught and fixed before their respective commits landed. No scope creep, no architectural change.

## Issues Encountered

None beyond the two self-caught items above.

## User Setup Required

**External services require manual configuration — see `deploy/README.md`
"Phase 5 — agent credentials (SHP-05 / SHP-06)"** for the full runbook:
environment variables to set (`PARALLEL_API_KEY`, `GEMINI_API_KEY` or
`GOOGLE_API_KEY`), where they live on the Lightsail box, and the exact
verification command. **This is not optional — SHP-05 and SHP-06 are
Stage One eligibility gates and remain unverified in production until a
human completes this step.**

## Next Phase Readiness

- Plan 05-02 can widen the same path from one award to every award in the
  document — `run_job1(limit=None)` already supports pricing every
  extracted award, not just one; `--limit` is a CLI convenience, not a
  pipeline constraint.
- Plan 05-03 puts this on the hosted page and proves it in production
  logs — `agent.job1.run_job1()` returns a fully-typed `Job1Run` dataclass
  ready to render, and `deploy/README.md` already documents the exact
  restart-and-verify steps for the box.
- **Blocker for full verification (not for further building):** SHP-05 and
  SHP-06 cannot be marked verified-in-production until a human sets both
  API keys per the runbook above and runs the `--require-live` command
  once, successfully.

## Self-Check: PASSED

All 9 created artifacts confirmed present on disk (`[ -f ]`); all 3 task
commit hashes (`d2ce048`, `a9835fc`, `8c45601`) confirmed present in
`git log --oneline --all`. Full acceptance-criteria re-run: `uv run
--frozen pytest tests/ -q` (490 passed), `lockfile-scan.sh` (PASS),
`vendor-scan.sh` (PASS), `tests/test_agent_eligibility.py` (14 passed),
no-keys `python -m agent.job1 --limit 1` (prints not-configured, exits 0),
`app.main` import with no keys serves `/`, `/spec`, `/validate`, `/health`
all 200.

---
*Phase: 05-curated-breadth-the-validation-loop*
*Completed: 2026-09-09*
