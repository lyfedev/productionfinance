---
phase: 07-live-research-caching-durable-jobs
plan: 03
subsystem: agent
tags: [fastapi, jinja2, lifespan, durability, boot-id, agent-loop]

requires:
  - phase: 07-live-research-caching-durable-jobs
    provides: "07-01's agent/research_runs.py record format (schema_version,
      status, boot_id already fixed in the shape), app/routers/research.py's
      GET/POST /research routes, app/templates/research_result.html's
      pre-existing rounds table — this plan builds on all three without
      duplicating them."
provides:
  - "agent/research_runs.py::BOOT_ID (public) and
    reclassify_interrupted_jobs() — the AGT-11 boot-identity restart-recovery
    sweep, centrally stamped onto every save_run/append_round write"
  - "app/main.py's FastAPI lifespan hook — the sweep runs on every process
    boot with no operator action"
  - "app/templates/research_result.html's per-round reasoning-trail blocks —
    D-92 rendered as a product surface: objective, queries, sources,
    summary, newly-determined/still-missing fields, and what it searched
    next, for every round in order"
  - "app/routers/research.py::_elapsed_seconds() and the elapsed_seconds
    context var — UI-10's in-flight page names round/elapsed/ceiling"
  - "runs/job2/README.md — the committed (non-gitignored) directory for the
    one human-verified live run artifact"
affects: [07-05, 07-06]

actuals:
  tokens: 10300
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Centralized stamping: save_run/append_round overwrite boot_id and
      updated_at themselves on every write, so no caller (router or
      agent/job2.py) can drift from the writing process's own identity —
      AGT-11's correctness depends on every record's boot_id genuinely
      naming its last writer."
    - "Boot-identity comparison, never a timeout: reclassify_interrupted_jobs()
      rewrites status=='running' records whose boot_id != the CURRENT
      process's BOOT_ID. A record carrying this process's own BOOT_ID is
      left alone — a job this process is running must never be reclassified
      out from under itself."
    - "PRODFIN_JOB2_RUNS_DIR env var, read once at import, exists ONLY for
      test isolation (a subprocess-isolated test can point a child process
      at the same tmp_path its parent uses) — unset in production, same
      pattern agent/settings.py already uses for other test-only knobs."
    - "The JSON and HTML surfaces read the identical record dict
      (GET /api/v1/research/{job_id} returns result['record'] verbatim,
      the same object the template renders), so D-92's two consumers
      (UI, written submission) cannot diverge on what happened."

key-files:
  created:
    - tests/test_agent_job2_durability.py
    - runs/job2/README.md
  modified:
    - agent/research_runs.py
    - app/main.py
    - app/routers/research.py
    - app/templates/research_result.html

key-decisions:
  - "BOOT_ID is now the public module-level constant (was a private
    _BOOT_ID plus a boot_id() accessor). boot_id() is kept as a thin
    wrapper for the existing call sites in agent/job2.py and
    app/routers/research.py — neither was touched, since both are owned
    by concurrently-running 07-02 per this plan's file-ownership fence."
  - "save_run/append_round overwrite boot_id/updated_at themselves rather
    than trusting the caller's value — a test
    (test_save_run_stamps_this_processs_own_boot_id) proves a
    caller-supplied bogus boot_id is discarded, not persisted."
  - "The 'objective it searched next' shown on round N's block is round
    N+1's own persisted objective (record.rounds[N].objective via Jinja
    list indexing), not a separately-stored field — this keeps D-92's
    trail derived from data that already exists once, so the two can never
    disagree."
  - "TDD ordering note (Rule 1/honesty): Task 1 and Task 2's tests
    (tests/test_agent_job2_durability.py) were written together with the
    implementation rather than strictly RED-first. Non-vacuity was
    still proven directly: reclassify_interrupted_jobs() was temporarily
    stubbed to 'return []' and 6 of the sweep/lifespan tests were
    confirmed to fail against that stub, then the stub was reverted and
    the full suite re-confirmed green — see 'TDD Gate Compliance' below."

requirements-completed: [AGT-11, UI-10]

coverage:
  - id: D1
    description: "A stale running record (written by a process that no longer exists) is rewritten to interrupted, with terminal_reason=interrupted_by_restart and a message naming the round reached (AGT-11)"
    requirement: "AGT-11"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_durability.py#test_sweep_rewrites_stale_running_job_to_interrupted"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_durability.py#test_sweep_names_the_round_reached_in_the_message"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_durability.py#test_sweep_names_round_zero_before_any_round_completed"
        status: pass
    human_judgment: false
  - id: D2
    description: "Reclassification is decided by boot_id comparison, never a timeout — this process's own running job is left untouched, a different process's is rewritten"
    requirement: "AGT-11"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_durability.py#test_sweep_leaves_this_processs_own_running_job_untouched"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_durability.py#test_boot_id_is_32_hex_characters"
        status: pass
    human_judgment: false
  - id: D3
    description: "The sweep runs on FastAPI startup via a lifespan handler, with no operator action, on both TestClient and a genuine uvicorn process"
    requirement: "AGT-11"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_durability.py#test_lifespan_reclassifies_stale_job_on_app_startup"
        status: pass
      - kind: other
        ref: "manual: real uvicorn process on 127.0.0.1:8901/8902 against a seeded stale record, GET /research/{job_id} confirmed interrupted on first boot"
        status: pass
    human_judgment: false
  - id: D4
    description: "The sweep is idempotent and never rewrites a record already terminal or already interrupted"
    requirement: "AGT-11"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_durability.py#test_sweep_is_idempotent"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_durability.py#test_sweep_never_touches_a_terminal_record"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_durability.py#test_sweep_never_touches_an_already_interrupted_record"
        status: pass
    human_judgment: false
  - id: D5
    description: "A genuine two-process SIGKILL restart never hangs: a real child process is killed mid-round, a fresh process reclassifies the orphaned record, and GET /research/{job_id} renders a terminal page on the first load (AGT-11's own required proof)"
    requirement: "AGT-11"
    verification:
      - kind: integration
        ref: "tests/test_agent_job2_durability.py#test_sigkill_mid_run_is_reclassified_by_a_fresh_process_and_renders_terminal"
        status: pass
      - kind: other
        ref: "manual: real uvicorn process kill -9'd and restarted twice against the same runs directory; record stayed interrupted and idempotent across both restarts"
        status: pass
    human_judgment: false
  - id: D6
    description: "Every round's objective, queries (with normalization flag), mode, source titles linked to their URLs, one-sentence summary, newly-determined fields, still-missing fields, and what it searched next are rendered in order, plus the total round count (D-92)"
    requirement: "UI-10"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_durability.py#test_terminal_page_renders_the_full_round_trail_and_no_refresh_tag"
        status: pass
    human_judgment: false
  - id: D7
    description: "An in-flight page names the current round, elapsed seconds, and the declared wall-clock ceiling, and refreshes; a terminal page carries no auto-refresh tag and names the terminal reason in plain words — proven against a real running uvicorn process, not only TestClient"
    requirement: "UI-10"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_durability.py#test_in_flight_page_names_round_elapsed_ceiling_and_carries_refresh_tag"
        status: pass
      - kind: other
        ref: "manual: curl against a live uvicorn process — terminal page confirmed to contain no 'refresh' string at all"
        status: pass
    human_judgment: false
  - id: D8
    description: "The HTML page and the JSON mirror (GET /api/v1/research/{job_id}) can never diverge on the rounds shown, because both read the identical persisted record dict"
    requirement: "UI-10"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_durability.py#test_terminal_page_renders_the_full_round_trail_and_no_refresh_tag (asserts the JSON payload's rounds match the HTML content)"
        status: pass
    human_judgment: false
  - id: D9
    description: "The trail is legible without the app (cat var/job2/{job_id}.json | python -m json.tool), and runs/job2/ is a committed directory ready to carry the one human-verified example for the written submission"
    requirement: "UI-10"
    verification:
      - kind: other
        ref: "manual: cat'd the seeded record through python -m json.tool during the live uvicorn verification pass; runs/job2/README.md committed"
        status: pass
    human_judgment: true
    rationale: "No PARALLEL_API_KEY/GEMINI_API_KEY is set in this environment (unchanged from 07-01/07-02), so no genuinely live-SDK-driven run has been produced to copy into runs/job2/ yet — the directory holds only the README and its runbook. A human must run the app with real keys, verify one output, and copy the record in by hand before the written submission can point at it. Logged as an open stub in .planning/WINDOWS.md."
  - id: D10
    description: "pyproject.toml is unchanged (D-95) — no dependency was added by this plan"
    requirement: "AGT-11"
    verification:
      - kind: other
        ref: "git diff --stat pyproject.toml (empty)"
        status: pass
      - kind: other
        ref: "bash .github/scripts/vendor-scan.sh"
        status: pass
      - kind: other
        ref: "bash .github/scripts/lockfile-scan.sh"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-09
status: complete
---

# Phase 7 Plan 3: Restart Recovery and the Reasoning Trail as a Product Surface Summary

**A `boot_id`-comparison sweep (`agent/research_runs.py::reclassify_interrupted_jobs`) wired into a FastAPI `lifespan` hook reclassifies every Job 2 record orphaned by a dead process to `interrupted` on the next process's startup — proven against a real two-process `SIGKILL` and against a genuinely restarted `uvicorn` process — and `app/templates/research_result.html` now renders every round's objective, queries, sources, summary, and newly-determined/still-missing fields as a visitor-facing trail, never a debug dump.**

## Performance

- **Duration:** 55 min (approx.)
- **Started:** 2026-09-09T08:00:00Z (approx.)
- **Completed:** 2026-09-09T08:57:00Z
- **Tasks:** 3
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- `agent.research_runs.BOOT_ID` is now a public, module-level 32-hex string
  minted once at import. `save_run` and `append_round` stamp it (and
  `updated_at`) onto every write themselves, centrally — a caller-supplied
  `boot_id` is proven to be discarded, never trusted
  (`test_save_run_stamps_this_processs_own_boot_id`).
- `reclassify_interrupted_jobs()` scans `RESEARCH_RUNS_DIR` and rewrites
  every record still `status == "running"` whose `boot_id` names a
  different process to `status: "interrupted"`,
  `terminal_reason: "interrupted_by_restart"`, with a message naming the
  round it reached. It leaves this process's own running jobs,
  already-`terminal`, and already-`interrupted` records untouched; is
  idempotent; and skips a corrupt neighbor JSON file without raising
  (T-07-16). 9 unit tests prove each of these independently.
- `RESEARCH_RUNS_DIR` now resolves from an optional
  `PRODFIN_JOB2_RUNS_DIR` environment variable, read once at import
  (unset in production) — this is what let the SIGKILL test's child
  process share `tmp_path` with its parent across a real process
  boundary.
- `app/main.py` wires the sweep into a FastAPI `lifespan` hook (replacing
  nothing — the app previously had none), so a `systemctl restart
  prodfin` performs the sweep with no operator action. Importing
  `app.main` still leaves neither `google.genai` nor `parallel` in
  `sys.modules`.
- **The real restart test (AGT-11's own required proof):**
  `tests/test_agent_job2_durability.py::test_sigkill_mid_run_is_reclassified_by_a_fresh_process_and_renders_terminal`
  starts a genuine child `subprocess.Popen` running a scripted `run_job2`
  that writes round 1 then blocks in round 2's `search_fn`, waits for the
  round-1 record to land on disk, `SIGKILL`s the child, then has the
  parent process call `reclassify_interrupted_jobs()` and serve
  `GET /research/{job_id}` through a real `TestClient` — confirming HTTP
  200, no `http-equiv="refresh"` tag, and the interrupted status/round
  count in both the HTML and the JSON mirror. This mirrors
  `tests/test_agent_eligibility.py`'s existing subprocess-isolation
  pattern, which already establishes that an in-process assertion cannot
  prove a claim like this one.
- **Beyond the automated suite:** the same mechanism was additionally
  verified against a real, separately-launched `uvicorn` process (not
  `TestClient`) on `127.0.0.1:8901`/`8902` — a stale record was seeded on
  disk, `uvicorn` was started and confirmed to reclassify it to
  `interrupted` on its own first boot, then the process was `kill -9`'d
  and restarted a second time against the same directory, confirming the
  record stayed `interrupted` and unchanged (idempotent across a genuine
  OS-level restart, not just a Python-level one).
- `app/templates/research_result.html` renders the D-92 record as a
  visitor-facing product surface: one block per round, in order, showing
  the objective it searched under, the queries issued (flagged if
  normalized), the mode (flagged if normalized), every source title
  linked to its URL, the agent's own one-sentence summary, the field
  names newly determined that round, the field names still missing, and
  what it went on to search next (round N+1's own objective, or the
  terminal outcome for the last round). A sentence above the rounds
  states plainly what the trail is; a sentence below states the total
  round count. An in-flight page names the current round, elapsed
  seconds, and the wall-clock ceiling and carries the refresh tag; a
  terminal page names the terminal reason in plain words (underscores
  rendered as spaces) and carries no refresh tag at all — proven both by
  `TestClient` tests and by `curl` against the live `uvicorn` process
  above.
- `app/routers/research.py` gains `_elapsed_seconds()` (parses
  `record["started_at"]`, degrades to `None` rather than crashing on a
  malformed timestamp) and passes it into the template context.
  `GET /api/v1/research/{job_id}` already returned the identical record
  dict the HTML template renders — verified directly by a test asserting
  the JSON payload's `rounds` match what the HTML page shows, so the two
  surfaces cannot diverge on what happened.
- `runs/job2/README.md` is the committed (non-gitignored) directory for
  the one human-verified live run artifact, mirroring
  `agent/runs.py`'s `COMMITTED_RUNS_DIR` convention and documenting the
  exact copy-in runbook by hand.

## Task Commits

Each task was committed atomically (Tasks 1 and 2 share one commit — both
build the same `agent/research_runs.py` boot-identity mechanism and its
test file):

1. **Tasks 1+2: Boot identity, the reclassification sweep, and the real SIGKILL restart test** — `5944c67` (feat)
2. **Task 3: The reasoning trail as a product surface** — `3f8652b` (feat)

**Plan metadata:** committed alongside this SUMMARY.

## Files Created/Modified

- `agent/research_runs.py` — `BOOT_ID`, `reclassify_interrupted_jobs()`, centralized `boot_id`/`updated_at` stamping in `save_run`/`append_round`, `PRODFIN_JOB2_RUNS_DIR` env-var override
- `app/main.py` — FastAPI `lifespan` hook running the sweep on startup
- `app/routers/research.py` — `_elapsed_seconds()`, `elapsed_seconds` in template context, JSON-mirror docstring note
- `app/templates/research_result.html` — per-round reasoning-trail blocks, in-flight round/elapsed/ceiling, terminal-reason plain-words rendering
- `tests/test_agent_job2_durability.py` — 18 tests: boot-identity, the sweep (unit-level), the FastAPI lifespan hook, the real two-process SIGKILL restart, and the rendered trail (in-flight and terminal)
- `runs/job2/README.md` — the committed directory + runbook for the one human-verified example

## Decisions Made

See `key-decisions` in frontmatter. In short: `BOOT_ID` became public
while keeping `boot_id()` as a compatibility wrapper so `agent/job2.py`
and the router (both owned by concurrently-running 07-02) never needed
touching; `save_run`/`append_round` now stamp `boot_id`/`updated_at`
centrally rather than trusting callers; the "searched next" field on each
round is derived from the next round's own persisted objective rather
than stored redundantly; and the TDD ordering for Tasks 1/2 was
implementation-and-tests-together rather than strict RED-first, compensated
by a direct non-vacuity check (see TDD Gate Compliance below).

## Deviations from Plan

None — plan executed exactly as written. The manual live-`uvicorn`
verification pass (beyond the plan's own `<verification>` checklist item)
was added for extra rigor, not as a deviation from any task's scope.

## TDD Gate Compliance

- **Tasks 1 and 2** (`tdd="true"`) did not follow strict RED-then-GREEN:
  `agent/research_runs.py` and `app/main.py` were implemented first, then
  `tests/test_agent_job2_durability.py` was written against that
  implementation, and all tests passed on first run — no failing-test
  commit exists for these tasks.
  **Non-vacuity was proven directly instead of via commit history:**
  `reclassify_interrupted_jobs()` was temporarily stubbed to
  `return []` (an unconditional no-op), and
  `uv run --frozen pytest tests/test_agent_job2_durability.py -q -k "sweep or lifespan"`
  was re-run — 6 tests failed against the stub
  (`test_sweep_rewrites_stale_running_job_to_interrupted`,
  `test_sweep_names_the_round_reached_in_the_message`,
  `test_sweep_names_round_zero_before_any_round_completed`,
  `test_sweep_is_idempotent`, `test_sweep_skips_corrupt_json_without_raising`,
  `test_lifespan_reclassifies_stale_job_on_app_startup`), confirming the
  gate is genuinely load-bearing. The stub was then reverted and the full
  18-test file re-confirmed green before proceeding. This mirrors 07-01's
  own precedent (its Task 3 also documented an immediate pass as
  reflecting already-correct prior implementation rather than faking a
  RED commit that never happened) — the honest record here is that the
  tests were written to prove behavior already built, and that proof was
  performed mechanically rather than skipped.
- **Task 3** (not `tdd="true"`) added its two rendering tests
  (`test_in_flight_page_names_round_elapsed_ceiling_and_carries_refresh_tag`,
  `test_terminal_page_renders_the_full_round_trail_and_no_refresh_tag`)
  alongside the template/router changes, following the plan's own
  structure (Task 3 has no `tdd="true"` attribute).

## Issues Encountered

None. One self-caught mistake during the manual live-`uvicorn`
verification: the first hand-typed job id was 31 characters, not 32, so
`GET /research/{job_id}` correctly 404'd under `InvalidJobIdError`'s
strict 32-hex check (T-07-04) rather than finding the seeded record —
this was a test-setup error, not a code defect, and confirmed the
validation path is working as designed before the id was corrected and
the verification re-run cleanly.

## User Setup Required

None — no new environment variable or external service configuration is
introduced. `PRODFIN_JOB2_RUNS_DIR` exists solely for test isolation and
is documented as unset in production; `deploy/prodfin.service` sets no
such variable.

## Known Stubs

- **`runs/job2/README.md` only — no verified run artifact yet.**
  `runs/job2/` is committed and documented, but holds only its own
  README: no genuinely live-SDK-driven Job 2 run has been produced in
  this environment (no `PARALLEL_API_KEY`/`GEMINI_API_KEY` set), so
  nothing has been copied in by hand yet. This is intentional and
  documented in the README's own runbook — logged as an open stub in
  `.planning/WINDOWS.md` (entry #32, kind `stub`) so it stays visible at
  ship time.

## Next Phase Readiness

**AGT-11 and UI-10 are both complete** for this plan's scope. The one
honest gap — a real `runs/job2/{job_id}.json` example, produced by an
actual live Search + `google-genai` run and verified by a human — remains
open pending API keys, exactly as 07-01 and 07-02 already documented for
their own live-SDK claims. Nothing in this plan changed `agent/job2.py`,
`agent/research_schema.py`, or the file set 07-02 owns.

**Ready for 07-05** (pricing the researched model, `depends_on: ["07-02",
"07-03"]`): this plan's `agent/research_runs.py` changes are additive
(a new public constant, a new function, centralized stamping that
callers already satisfied) — no field 07-05 depends on changed shape.

**Ready for 07-06** (the D-96 call-site audit script and CI wiring,
`depends_on: [..., "07-03", ...]`): this plan added no new
`parallel-web`/`google-genai` call site — the only real SDK calls remain
`agent/job2.py:209` (`_real_search`) and inside `_real_judge`, both
already inventoried by 07-01's D-96 audit and unchanged here.

---
*Phase: 07-live-research-caching-durable-jobs*
*Completed: 2026-09-09*

## Self-Check: PASSED

All 2 created files confirmed present on disk
(`tests/test_agent_job2_durability.py`, `runs/job2/README.md`). Both
task commit hashes confirmed in `git log` (`5944c67`, `3f8652b`). Full
suite: 679 passed. `tests/test_agent_job2_durability.py` alone: 18
passed. Vendor-scan and lockfile-scan both clean. `pyproject.toml`
byte-identical to pre-plan state (`git diff --stat pyproject.toml`
empty).
