---
phase: 07-live-research-caching-durable-jobs
plan: 01
subsystem: agent
tags: [parallel-web, google-genai, fastapi, jinja2, pydantic, agent-loop]

requires:
  - phase: 05-curated-breadth-the-validation-loop
    provides: agent/parallel_client.py and agent/gemini_client.py's lazy-import
      pattern, agent/telemetry.py's PRODFIN_SDK_CALL log line and collecting()
      ambient collector, agent/runs.py's job_id/path-traversal discipline —
      all reused verbatim by this plan's Job 2 modules.
provides:
  - "agent/job2.py::run_job2 — the D-90 self-terminating research loop"
  - "agent/research_schema.py — SufficiencyVerdict/FieldFinding/SufficiencyField,
    the single Job-2 schema source (D-83 pattern, D-91's closed five-field set)"
  - "agent/research_runs.py — durable var/job2/{job_id}.json records with
    atomic append_round writes (D-92) and a strict job_id allowlist (T-07-04)"
  - "app/services/cache_policy.py — the AGT-10 DataClass/POLICY table,
    may_use_cache, assert_live, CacheBoundaryViolation"
  - "app/routers/research.py — POST /research, GET /research/{job_id}, and
    their /api/v1 JSON pair, the one live D-89 call-site entry point"
  - "app/templates/research_result.html — round-by-round in-flight/terminal
    rendering (UI-10)"
affects: [07-02, 07-03, 07-04, 07-05, 07-06]

actuals:
  tokens: 15547
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Agent loop, not fixed pipeline: while True: driven entirely by a
      model-returned Literal decision (SufficiencyVerdict.decision), never
      a range()/counter — the D-90 shape, structurally distinct from
      agent/job1.py's fixed D-82 sequence."
    - "One session_id minted per job, threaded through every round's Search
      call via session_id= — the 07-SDK-FINDINGS spine."
    - "Durable-before-next-round: agent.research_runs.append_round writes
      atomically (temp file + os.replace) after every round, before the
      loop's next Search call — proven by a fake search_fn that reads its
      own job's file mid-run and asserts the round count already on disk."
    - "Single cache-policy choke point (app/services/cache_policy.py) that
      imports nothing from agent/ or engine/; agent/job2.py calls
      assert_live() once, before its first Search, and turns a
      CacheBoundaryViolation into a terminal record rather than letting the
      Search fire."

key-files:
  created:
    - agent/research_schema.py
    - agent/job2.py
    - agent/research_runs.py
    - app/services/cache_policy.py
    - app/routers/research.py
    - app/templates/research_result.html
    - tests/test_cache_policy.py
    - tests/test_agent_job2_offline.py
  modified:
    - agent/settings.py
    - app/main.py
    - app/templates/index.html

key-decisions:
  - "Task 1's tracer committed job2.py WITHOUT the cache-policy assertion
    (that module didn't exist yet); Task 2 added it as its own TDD
    RED (3abd825) -> GREEN (2524c28) pair, keeping the AGT-10 mutation
    proof isolated in its own commit per the plan's task boundaries."
  - "Both real SDK calls (client.search, generate_content) are wrapped in
    agent.telemetry.sdk_call INSIDE agent/job2.py's own _real_search/
    _real_judge functions (job2 has no separate parallel_client-for-job2
    module) — collecting(sdk_calls) wraps the whole loop exactly as
    run_job1 does, so fakes injected via search_fn/judge_fn never emit a
    PRODFIN_SDK_CALL line (an offline/replay run must never look like
    live SDK evidence)."
  - "City-input validation happens in TWO places: app/routers/research.py's
    _start_job (so an invalid POST never mints a job_id or starts a
    thread) and again inside agent/job2.py::run_job2 itself (defense in
    depth for any future caller that invokes run_job2 directly)."
  - "GET /research?city= prefill validation swallows InvalidCityInputError
    to an empty prefill rather than 422ing a plain browse; POST /research
    and POST /api/v1/research both reject invalid input before minting a
    job_id (never a truncated-and-used string), with the JSON route
    surfacing it as 422."
  - "The wall-clock ceiling (JOB2_WALL_CLOCK_CEILING_SECONDS) is declared
    in agent/settings.py and stored on every record for display, but its
    enforcement mechanism is explicitly deferred to 07-02 per the plan —
    07-01 adds no round-count bound of any kind."

requirements-completed: [AGT-05, SHP-06, UI-10, AGT-10]

coverage:
  - id: D1
    description: "POST /research executes a real parallel-web Search call inside the HTTP request lifecycle (D-89)"
    requirement: "SHP-06"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_offline.py#test_job2_imports_parallel_inside_a_function"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_offline.py#test_app_serves_every_route_with_no_keys_present"
        status: pass
    human_judgment: true
    rationale: "No API keys are available in this environment (verified — see Next Phase Readiness). The offline suite proves the call site, the request-lifecycle wiring, and the lazy-import contract exhaustively, but a live PRODFIN_SDK_CALL line with a real Search response has not been produced and needs a human to run it once keys exist."
  - id: D2
    description: "The D-90 loop terminates only on the model's own decision value — no round counter, no range()"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "07-01-PLAN.md task-1 <verify> AST gate (ast.walk over run_job2 for ast.For/range)"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_offline.py#test_scripted_four_continues_then_give_up_produces_exactly_five_rounds"
        status: pass
    human_judgment: false
  - id: D3
    description: "Sufficiency is judged against the closed five-field D-91 set; a sixth field is a validation error"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_offline.py#test_a_sixth_sufficiency_field_fails_validation"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_offline.py#test_sufficiency_field_has_exactly_five_members"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every round is durable on disk before the next round's Search fires (D-92)"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_offline.py#test_final_record_on_disk_matches_the_returned_run"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_offline.py (durability assertion embedded in _scripted_seams's fake search_fn, exercised by every scripted-round test)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The live research path asserts its live classification via app/services/cache_policy.py before its first Search (AGT-10)"
    requirement: "AGT-10"
    verification:
      - kind: unit
        ref: "tests/test_cache_policy.py#test_run_job2_reports_a_cache_boundary_violation_and_fires_no_search"
        status: pass
    human_judgment: false
  - id: D6
    description: "The in-flight page names the round, that round's objective, unmet field names, and the wall-clock ceiling (UI-10)"
    requirement: "UI-10"
    verification: []
    human_judgment: true
    rationale: "Verified by a manual end-to-end smoke test through the real TestClient + Jinja2 template during this session (GET /research/{job_id} rendered round count, terminal reason, and the refined objective correctly), but no automated assertion exercises the in-flight (status=='running') branch of research_result.html specifically — a human should confirm the in-flight page visually once a live run can be driven past round 1."
  - id: D7
    description: "No dependency is added; vendor-scan and lockfile-scan both pass; pyproject.toml is byte-identical"
    requirement: "AGT-05"
    verification:
      - kind: other
        ref: "bash .github/scripts/vendor-scan.sh"
        status: pass
      - kind: other
        ref: "bash .github/scripts/lockfile-scan.sh"
        status: pass
      - kind: other
        ref: "git diff --stat pyproject.toml (empty)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-09
status: complete
---

# Phase 7 Plan 1: Job 2 Tracer — Live Research Agent Loop Summary

**A genuine self-terminating research agent (`agent/job2.py`) reaches Parallel Search and `google-genai` from inside `POST /research`'s own request lifecycle, judges sufficiency against D-91's five named fields, persists every round to `var/job2/{job_id}.json` before the next round starts, and asserts its own live-vs-cache classification through a new single-choke-point policy module — all proven offline with no API key present.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-09T18:05:00Z (approx.)
- **Completed:** 2026-09-09T19:00:00Z (approx.)
- **Tasks:** 3 (plus one TDD RED/GREEN pair inside Task 2)
- **Files modified:** 11 (8 created, 3 modified)

## Accomplishments

- `agent/job2.py::run_job2` is a `while True:` loop whose only exit
  condition is `SufficiencyVerdict.decision` — no `range()`, no round
  counter compared against a constant (D-90). The plan's own AST gate
  (`ast.walk` over the `run_job2` function body) proves this mechanically,
  and three scripted-decision tests (`["sufficient"]` -> 1 round,
  `["continue","sufficient"]` -> 2 rounds, four `"continue"`s then
  `"give_up"` -> 5 rounds) prove the round count is a property of the
  model's own judgment, never the driver.
- One `session_id` is minted per job (`uuid.uuid4().hex`) and threaded
  through every Search call in that run via `session_id=` — verified by a
  test asserting the same id appears on every scripted call. Round 2's
  Search is proven to receive round 1's `next_objective`/`next_queries`
  from the verdict, never round 1's own objective (the refinement hop the
  07-SDK-FINDINGS spine describes).
- `agent/research_runs.py::append_round` persists each round to
  `var/job2/{job_id}.json` atomically (sibling temp file + `os.replace`)
  BEFORE the loop's next Search call fires — proven by a fake `search_fn`
  that itself reads the file mid-run from a second vantage point and
  asserts the round count and `status=="running"` it finds there.
  `load_run` rejects path traversal and every non-32-hex `job_id` shape
  before building any path (T-07-04).
- `app/services/cache_policy.py` is the single AGT-10 choke point: a
  closed five-member `DataClass` enum, a rationale-carrying `POLICY`
  table, `may_use_cache`, and `assert_live`. `run_job2` calls
  `assert_live(DataClass.uncurated_city_research)` before its first
  Search; a mutation test flips the policy table to `"cached"` and proves
  the assertion is load-bearing — no Search call fires, and the run
  terminates naming the violation.
- `POST /research` (and its `POST /api/v1/research` JSON twin) validate
  the visitor's city string, mint a `job_id`, write the initial durable
  record, and start `run_job2` on a background thread before returning a
  303 — the Search call therefore executes inside the POST's own request
  lifecycle (D-89), the same shape `app/routers/job1.py` already proved
  out. There is no CLI entry point anywhere in this chain (D-96's "must be
  reachable only from a request handler" requirement).
- `app/templates/research_result.html` renders the round number, that
  round's objective, the still-unmet field names, and the wall-clock
  ceiling in seconds for an in-flight job — never a bare spinner (UI-10) —
  and a full round-by-round table plus the terminal reason for a finished
  one.
- Every pre-existing route, plus the three new `/research` routes, serves
  200/303 with all four key environment variables deleted; importing
  `app.main` in a subprocess still leaves neither `google.genai` nor
  `parallel` in `sys.modules` even with the new router wired in.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end live research tracer** — `033002e` (feat)
2. **Task 2 RED: failing cache-policy test** — `3abd825` (test)
2. **Task 2 GREEN: cache-policy module + wiring** — `2524c28` (feat)
3. **Task 3: offline proof suite** — `bba7f79` (test)
4. **Formatting fix** — `3836de7` (style, deviation — see below)

**Plan metadata:** committed alongside this SUMMARY.

## Files Created/Modified

- `agent/research_schema.py` — `SufficiencyVerdict`/`FieldFinding`/`SufficiencyField`, the single Job-2 reasoning schema source
- `agent/job2.py` — the D-90 loop driver, `validate_city_input`, `_real_search`/`_real_judge` (both lazy-importing their SDK)
- `agent/research_runs.py` — `var/job2/{job_id}.json` persistence: `save_run`, `append_round`, `load_run`, `new_job_id`, `boot_id`
- `app/services/cache_policy.py` — `DataClass`, `POLICY`, `may_use_cache`, `assert_live`, `CacheBoundaryViolation`
- `app/routers/research.py` — `GET/POST /research`, `GET/POST /api/v1/research`, `GET /research/{job_id}`, `GET /api/v1/research/{job_id}`
- `app/templates/research_result.html` — in-flight and terminal rendering
- `agent/settings.py` — `JOB2_WALL_CLOCK_CEILING_SECONDS`, `JOB2_MAX_CHARS_PER_SEARCH` (declared only; enforcement is 07-02's)
- `app/main.py` — wires in `research_router`
- `app/templates/index.html` — adds the Job 2 landing-page link
- `tests/test_cache_policy.py` — AGT-10 policy table + mutation test
- `tests/test_agent_job2_offline.py` — the full offline proof suite (24 tests)

## Decisions Made

See `key-decisions` in frontmatter. In short: the cache-policy assertion
was deliberately built as its own TDD pair (Task 2) separate from Task 1's
tracer, matching the plan's task boundaries even though both land in
`agent/job2.py`; both real SDK calls stay wrapped in `sdk_call` inside
`agent/job2.py` itself (no separate client module for Job 2); city
validation is defense-in-depth at both the router and the loop entry
point; and the wall-clock ceiling is declared but deliberately left
unenforced pending 07-02's guard.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `ruff format` reformatted four of this plan's files**
- **Found during:** final plan-level verification (`uv run ruff format --check`)
- **Issue:** Four newly-written files (`agent/job2.py`, `app/routers/research.py`, `app/services/cache_policy.py`, `tests/test_agent_job2_offline.py`) had a small number of lines exceeding the project's 100-char preferred wrap that `ruff format` would reformat (list comprehensions and `TemplateResponse(...)` calls collapsed onto one line each).
- **Fix:** Ran `uv run ruff format` on exactly those four files. Purely cosmetic — no logic changed.
- **Files modified:** `agent/job2.py`, `app/routers/research.py`, `app/services/cache_policy.py`, `tests/test_agent_job2_offline.py`
- **Verification:** `uv run ruff format --check` clean on all plan files; full suite re-run, 574 passed unchanged.
- **Commit:** `3836de7`

---

**Total deviations:** 1 auto-fixed (1 Rule 1 formatting fix).
**Impact on plan:** Cosmetic only. No scope creep, no behavior change.

## TDD Gate Compliance

- **Task 2** (`app/services/cache_policy.py` + the `assert_live` wiring)
  followed the RED/GREEN gate literally: `3abd825` (test, RED — confirmed
  failing via `ModuleNotFoundError` since `app/services/cache_policy.py`
  did not yet exist) then `2524c28` (feat, GREEN — all 8 tests in
  `tests/test_cache_policy.py` pass, including the non-vacuity mutation
  test).
- **Task 3** (`tests/test_agent_job2_offline.py`, also `tdd="true"`) did
  NOT produce a RED state: all 24 tests passed on first run. This is
  because Task 3's role — proving already-shipped Task 1/2 behavior
  offline, analogous to `tests/test_agent_job1_offline.py`'s relationship
  to the already-built `agent/job1.py` — is a verification/proof task over
  production code deliberately built correctly in the preceding tracer and
  TDD tasks, not a feature being introduced test-first. Per the executor's
  fail-fast rule, this was investigated before proceeding: every assertion
  in the file corresponds to behavior already exercised and inspected
  during Task 1/2's own manual smoke tests (a scripted round-count run, a
  session_id/objective-refinement check, and a direct HTTP round-trip
  through `TestClient` — all run and shown passing before Task 3's test
  file was written), so the immediate pass reflects genuinely-correct
  prior implementation, not a test that fails to test anything. No
  production code changed as a result of writing Task 3.

## Issues Encountered

None beyond the formatting deviation documented above.

## User Setup Required

None — no new environment variable or external service configuration is
introduced. `PARALLEL_API_KEY` and `GEMINI_API_KEY`/`GOOGLE_API_KEY` were
already required by Job 1 (Phase 5) and are reused unchanged by Job 2; see
Next Phase Readiness for their current unconfigured state in this
environment.

## Next Phase Readiness

**D-96 call-site audit (as required by 07-CONTEXT.md):**

| File:line | Call | Reachable from |
|---|---|---|
| `agent/job2.py:209` (`client.search(...)`, inside `_real_search`) | `parallel-web` Search | `agent.job2.run_job2` <- `app/routers/research.py::_start_job`'s background thread <- `POST /research` (line 187) and `POST /api/v1/research` (line 214) |

No call site in this plan is reachable only from a CLI `__main__`, a build
step, or a prep script — `agent/job2.py` and `app/routers/research.py`
both carry no such entry point (`tests/test_agent_job2_offline.py::test_job2_module_has_no_main_entry_point`).
The pre-existing Job 1 call sites (`agent/parallel_client.py:78,108`,
reachable from `agent/job1.py`'s CLI `__main__` per 07-SDK-FINDINGS.md)
are unchanged by this plan and remain a Phase 5 concern, not this one's.

**Unverified pending API keys (honestly stated, per the executor's
`api_keys_reality` contract):** neither `PARALLEL_API_KEY` nor
`GEMINI_API_KEY`/`GOOGLE_API_KEY` is set in this environment or in
`/opt/prodfin/.env` as checked during this session. Every claim in this
SUMMARY about the D-90 loop, D-91's sufficiency contract, D-92's
durability, and AGT-10's cache boundary is proven through the offline
fake-seam suite (`tests/test_agent_job2_offline.py`, `tests/test_cache_policy.py`)
and a manual end-to-end smoke test run through `TestClient` with fakes
during this session — never through a real Parallel or Gemini response. A
real `PRODFIN_SDK_CALL sdk=parallel-web ...` and `sdk=google-genai ...`
line pair, plus a `var/job2/{job_id}.json` artifact gaining a round while
a real request is in flight, remain to be produced once keys exist (the
plan's own `<verification>` block names this explicitly). This is the one
item of the plan's `<verification>` list not exercised in this session.

**Ready for 07-02** (the wall-clock enforcement guard and its AST gate):
`JOB2_WALL_CLOCK_CEILING_SECONDS` is already declared and stored on every
record; 07-02 needs only to add the enforcement check and its own AST gate
proving no round-count constant was introduced alongside it.

**Ready for 07-03** (interrupted-job recovery): `boot_id` and `status`
(`"running"`/`"terminal"`) are already written on every record, per the
plan's explicit "fixed once, here" instruction.

**Ready for 07-04** (uncurated-city linking from `/spec`): `GET /research`
already accepts and validates an optional `city=` query parameter for
prefill, per this plan's contract with that future plan.

**Ready for 07-05** (pricing the researched model): `ResearchRun` already
declares `findings`, `undetermined_disclosures`, `ruleset_path`, and
`priced` fields (currently `None`) so the record shape does not churn when
07-05 fills them in.

---
*Phase: 07-live-research-caching-durable-jobs*
*Completed: 2026-09-09*

## Self-Check: PASSED

All 8 created files confirmed present on disk (`agent/research_schema.py`,
`agent/job2.py`, `agent/research_runs.py`, `app/services/cache_policy.py`,
`app/routers/research.py`, `app/templates/research_result.html`,
`tests/test_cache_policy.py`, `tests/test_agent_job2_offline.py`). All 5
task/deviation commit hashes confirmed in `git log`
(`033002e`, `3abd825`, `2524c28`, `bba7f79`, `3836de7`). Full suite:
574 passed. Vendor-scan and lockfile-scan both clean. `pyproject.toml` and
`uv.lock` byte-identical to pre-plan state.
