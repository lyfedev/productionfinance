---
phase: 05-curated-breadth-the-validation-loop
plan: 03
subsystem: ai-integration
tags: [fastapi, jinja2, threading, contextvars, job1, eligibility, deploy]

requires:
  - phase: 05-curated-breadth-the-validation-loop
    provides: "05-01's agent/ package (settings, telemetry, schema, parallel_client, gemini_client, job1) and 05-02's widened run_job1 (every-award extraction, D-86 taxonomy, run_mode, injectable seams)"
provides:
  - "agent/runs.py — JSON persistence for a Job1Run (var/job1/{run_id}.json + latest.json; run_id validated against a strict 32-hex pattern before any path is built, T-05-12)"
  - "agent/telemetry.py::collecting() — an ambient contextvars collector so sdk_call's D-84 log line and the on-page SDK-call evidence block are provably the same record, with zero signature change at the existing parallel_client.py/gemini_client.py call sites"
  - "app/routers/job1.py — GET/POST /job1, GET/POST /api/v1/job1, GET /job1/{run_id}: single-flight lock + MIN_SECONDS_BETWEEN_RUNS bound anonymous-triggered spend (T-05-04); the pipeline runs on a daemon background thread so the Apache proxy timeout is never held open; a non-live run's awards/accuracy are never placed in the render context at all (T-05-15, enforced in the router)"
  - "https://vockell.com/finance/job1 — live, deployed (git_sha 9af46b0), reachable by an anonymous visitor"
affects: [phase-8-reverification]

actuals:
  tokens: 14400
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Ambient contextvars.ContextVar collector (agent.telemetry.collecting) lets a caller several layers up (agent.job1.run_job1) capture records from sdk_call() invocations inside modules it doesn't control the internals of (agent.parallel_client, agent.gemini_client) with zero signature change at those call sites"
    - "Server-side enforcement of a rendering gate by omission, not by flag: app/routers/job1.py's _run_render_context never puts awards/accuracy into the Jinja2 context for a non-live run — a template rewrite literally has no data to leak, not just a flag it could ignore (T-05-15)"
    - "Background-thread + 303-redirect + polling pattern for a tens-of-seconds pipeline behind a reverse proxy with a request timeout — POST returns immediately, GET /job1/{run_id} renders the named in-flight stage and self-refreshes every 3s until terminal"

key-files:
  created:
    - agent/runs.py
    - app/routers/job1.py
    - app/templates/job1_result.html
    - tests/test_app_job1_route.py
  modified:
    - agent/job1.py
    - agent/telemetry.py
    - app/main.py
    - app/templates/index.html
    - .gitignore
    - tests/test_agent_job1_offline.py
    - deploy/README.md
    - .planning/WINDOWS.md

key-decisions:
  - "Job 1's SDK-call evidence block reuses agent.telemetry.sdk_call via an ambient contextvars collector, not a signature change at the existing parallel_client.py/gemini_client.py call sites -- the D-84 log line and the on-page evidence are provably the same record."
  - "The non-live rendering guard (T-05-15) is enforced in app/routers/job1.py itself: for a non-live run, awards/accuracy are never placed in the Jinja2 context at all, so a template rewrite cannot leak an accuracy figure for data it was never handed."
  - "Deployed to vockell.com/finance (git_sha 9af46b0) with no API keys on the box (Path B, confirmed by grep -c on /opt/prodfin/.env immediately before deploying). SHP-05 and SHP-06 were left Pending in REQUIREMENTS.md despite the mechanical shared-ID gate reporting them ready -- both are live-outcome claims (\"genuinely called at runtime\") that remain false. Only AGT-02 (a mechanism claim: does Job 1 re-run the model and report accuracy? yes, proven and now deployed) was marked complete. WINDOWS.md entry #28 names SHP-05, SHP-06 and AGT-03 and spells out the exact human action required."
  - "Widened the D-87 AST gate's sanctioned-construction exception (tests/test_agent_job1_offline.py) to also permit agent/runs.py's ExtractedAward.model_validate(...) deserialization site -- reading back a run this process already saved is not fabrication, but the existing gate (05-02) only recognized gemini_client.py's real-response parse. This is a Rule 1 fix, not a plan file, but was necessary for the standing full suite to stay green."

requirements-completed: [AGT-02]
# SHP-05 and SHP-06 are NOT marked complete despite being declared by this
# plan's frontmatter and reported "ready" by requirements.ready-ids (no
# sibling still blocks them). Both requirement texts are live-outcome
# claims ("genuinely called at runtime, verified by a timestamped log
# line") that remain FALSE in production: /opt/prodfin/.env has neither
# key, confirmed live on the box immediately before this plan's deploy,
# and `journalctl -u prodfin` after the deploy contains zero
# PRODFIN_SDK_CALL lines. Marking them [x] here while WINDOWS.md entry #28
# (committed in the SAME plan) calls them open would be the exact
# same-commit contradiction CLAUDE.md's Honesty constraint forbids -- the
# same judgment call 05-02 made for AGT-03, applied here to SHP-05/SHP-06.
# AGT-02 ("Job 1 re-runs the model against each extracted pair and reports
# accuracy") is a mechanism claim, not a live-outcome claim -- proven true
# by tests/test_agent_job1_offline.py and tests/test_app_job1_route.py,
# and now genuinely deployed and reachable -- so it was marked complete.

coverage:
  - id: D1
    description: "An anonymous, logged-out visitor at /job1 sees the most recent Job 1 run's document URL, bucket counts, and per-award disclosed-vs-computed comparison, with a trigger form always rendered (AGT-02)"
    requirement: AGT-02
    verification:
      - kind: integration
        ref: "tests/test_app_job1_route.py#test_get_job1_with_persisted_live_run_shows_bucket_counts_and_every_award"
        status: pass
      - kind: integration
        ref: "tests/test_app_job1_route.py#test_get_job1_with_no_keys_names_both_env_vars"
        status: pass
    human_judgment: true
    rationale: "Route-tested exhaustively against fixture runs built through the real offline seam and the real serialiser; the live page was independently confirmed via an anonymous curl/browser check against https://vockell.com/finance/job1 with git_sha=9af46b0. What remains unverified is a genuine SDK-driven run producing that content in production -- see 'API keys reality' below and WINDOWS.md #28."
  - id: D2
    description: "Triggering a run shows a named in-flight stage and reaches a legible terminal state without holding a request across the Apache proxy timeout -- POST returns a 303 immediately, background daemon thread runs the pipeline"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/test_app_job1_route.py#test_post_job1_rate_limit_html_then_json_429 (exercises the 303 path on the first POST)"
        status: pass
    human_judgment: true
    rationale: "The stage-naming and self-refresh behavior is implemented (on_stage callback threaded through run_job1, meta http-equiv=refresh in the template) and structurally tested via the fast-fake-run path, but no test exercises tens-of-seconds of genuine in-flight polling end to end -- that requires a real key-driven run."
  - id: D3
    description: "The page shows the two PRODFIN_SDK_CALL evidence records for a run, sourced from the same collector the D-84 log line is built from (D-84)"
    requirement: null
    verification:
      - kind: unit
        ref: "verified directly: agent.telemetry.collecting() collector receives an identical record to the logged line, confirmed by direct interpreter session during this plan's execution"
        status: pass
    human_judgment: true
    rationale: "The mechanism is proven correct in isolation and the template renders run.sdk_calls when present, but no fixture run in this plan's tests carries non-empty sdk_calls (fakes never call sdk_call) -- a live run is what would actually populate and render this block end to end."
  - id: D4
    description: "A run whose run_mode is not live can never be rendered as an accuracy figure; the router refuses before the template is reached, and a test proves the refusal"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/test_app_job1_route.py#test_get_job1_with_persisted_replay_run_never_shows_accuracy"
        status: pass
    human_judgment: false
  - id: D5
    description: "With no keys on the box, /job1 renders a legible not-configured state naming both environment variables, and /, /spec, /validate and /health keep serving exactly as they do today"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/test_app_job1_route.py#test_get_job1_with_no_keys_names_both_env_vars"
        status: pass
      - kind: unit
        ref: "tests/test_app_job1_route.py#test_pre_existing_routes_still_return_200"
        status: pass
      - kind: e2e
        ref: "curl -s -o /dev/null -w '%{http_code}' https://vockell.com/finance/{,health,spec,validate,job1} — all 200, run live on 2026-09-09"
        status: pass
    human_judgment: false
  - id: D6
    description: "After deploy, journalctl -u prodfin on the box contains one PRODFIN_SDK_CALL sdk=parallel-web line and one sdk=google-genai line produced by a logged-out request, OR the gap is recorded in WINDOWS.md naming SHP-05, SHP-06 and AGT-03"
    requirement: null
    verification:
      - kind: other
        ref: ".planning/WINDOWS.md entry #28 (kind: unmet-truth, phase 05, names SHP-05, SHP-06, AGT-03)"
        status: pass
    human_judgment: true
    rationale: "Green via the WINDOWS.md path, not a live artifact -- /opt/prodfin/.env carries neither key. A human must install both keys and re-run the journalctl grep before this becomes a live-artifact pass. See 'API keys reality' below."
  - id: D7
    description: "https://vockell.com/finance still returns 200 for every route it served before this phase; the deploy is reversible to the previous commit with a documented command"
    requirement: null
    verification:
      - kind: e2e
        ref: "curl -s -o /dev/null -w '%{http_code}' https://vockell.com/finance/ -> 200, verified live after deploy"
        status: pass
      - kind: other
        ref: "deploy/README.md 'Phase 5 plan 05-03 deploy — rollback position recorded before deploying' (rollback SHA 60efb6b, tested-ready command sequence)"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-09-09
status: complete
---

# Phase 5 Plan 3: Job 1 Live on `/job1` — Deployed with the SHP-05/SHP-06 Gap Recorded Honestly

**FastAPI/Jinja2 `/job1` route (single-flight background-thread trigger, contextvars-collected SDK evidence, a router-enforced non-live guard) deployed to `https://vockell.com/finance/job1` — with no API keys on the box, so the eligibility-proving SDK calls remain unverified in production and that gap is recorded, not hidden.**

## Performance

- **Duration:** ~30 min (approx.)
- **Started:** ~2026-09-09T07:30:00Z (approx.)
- **Completed:** 2026-09-09T07:59:00Z (approx., matching the final `docs(05-03)` commit at 07:52:41Z plus post-commit verification)
- **Tasks:** 3
- **Files touched:** 12 (4 created, 8 modified)

## CRITICAL — read before treating SHP-05/SHP-06 as done

**`PARALLEL_API_KEY` and `GEMINI_API_KEY`/`GOOGLE_API_KEY` are STILL NOT
SET — neither locally nor in `/opt/prodfin/.env` on the Lightsail box.**
Both were checked again at the start of this plan (per the dispatch
instructions) and confirmed absent again immediately before deploying, via
a direct `grep -c` on the box:

```
ENV_FILE_EXISTS
0   # PARALLEL_API_KEY
0   # GEMINI_API_KEY or GOOGLE_API_KEY
```

This is Path B, the only honest path available. No live SDK call was
made, no `journalctl` line was produced, and no `runs/job1/` artifact was
committed. `.planning/WINDOWS.md` entry **#28** records this explicitly,
naming SHP-05, SHP-06 and AGT-03 and the exact human action required:

```bash
# On the box, as a user with sudo:
sudo -u prodfin vi /opt/prodfin/.env   # add PARALLEL_API_KEY=... and GEMINI_API_KEY=...
sudo chmod 600 /opt/prodfin/.env
sudo systemctl restart prodfin

# Then, from a machine that is NOT the box, anonymous, logged out:
curl -X POST https://vockell.com/finance/job1   # follow the 303, poll until terminal

# On the box, verify:
sudo journalctl -u prodfin --since "15 min ago" | grep PRODFIN_SDK_CALL
# expect one "sdk=parallel-web" line and one "sdk=google-genai" line

# Then copy the run artifact into runs/job1/{timestamp}.json and commit it.
```

Everything this plan built is proven correct up to that exact boundary —
the code path is complete, deployed, and tested; only the live call
itself is missing, and it cannot be manufactured by an agent (no key, no
account).

## Three memory readings (D-22-style measurement, first real reading with the AI SDKs resolved)

Recorded on the live box, `nano_2_0` (472Mi), immediately before, immediately
after, and once more after a POST /job1 trigger attempt:

| When | `free -m` available | `MemoryCurrent` (prodfin.service) |
|---|---|---|
| Before `uv sync` (pre-deploy) | 347Mi | 17,362,944 bytes (~16.6 MB) |
| After `uv sync --frozen` + restart | 317Mi | 57,516,032 bytes (~54.9 MB) |
| After a POST /job1 trigger attempt | 316Mi | 59,109,376 bytes (~56.4 MB) |

Swap stayed essentially flat (108Mi → 80Mi used, well under the 634Mi
total). The box never dropped near the 150Mi stop threshold at any point.
**Honest caveat:** because `google-genai`/`parallel-web` are lazily
imported (inside functions, only at actual call time — the pattern 05-01
established and this plan preserved), the ~40 MB RSS increase measured
above is dominated by loading the much larger codebase Phases 4 and 5 add
(engine/, agent/, dozens of new modules and templates), not by the SDK
import itself — no code path in this session ever executed
`import parallel` or `from google import genai`. The genuine SDK-import
footprint remains unmeasured until a real key-driven run occurs; this is
flagged for Phase 8/Milestone 2, which STATE.md already notes needs this
number.

## Accomplishments

- **`agent/runs.py`** — JSON persistence for a `Job1Run`: `var/job1/{run_id}.json`
  + `latest.json`, `runs/job1/` as the separate committed evidence
  directory, `run_id` validated against a strict 32-hex-character pattern
  BEFORE any path is built (T-05-12, mirroring `app/services/validate.py`'s
  `pair_id` allowlist check). `run_to_dict`/`run_from_dict` round-trip
  every field, converting every `Decimal` via `str(...)` and every enum
  via `.value`.
- **`agent/telemetry.py::collecting()`** — an ambient `contextvars`
  collector activated only for the duration of one `run_job1` call, so
  `agent/parallel_client.py` and `agent/gemini_client.py`'s existing
  `sdk_call(...)` sites need zero signature change to feed the on-page
  evidence block. Verified directly in this session: the collected record
  and the logged line are built from the exact same values.
- **`agent/job1.py`** widened: `run_job1` gains `on_stage` (searching /
  extracting / reading / pricing) and threads the D-84 collector, so
  `Job1Run.sdk_calls` carries the evidence tuple.
- **`app/routers/job1.py`** — `GET/POST /job1`, `GET/POST /api/v1/job1`,
  `GET /job1/{run_id}`, `GET /api/v1/job1/{run_id}`. A module-level
  single-flight `threading.Lock` plus `MIN_SECONDS_BETWEEN_RUNS` (env
  `PRODFIN_JOB1_MIN_INTERVAL_S`, default 60) bound anonymous-triggered
  spend (T-05-04). `POST /job1` starts the pipeline on a `daemon=True`
  background thread and returns a 303 immediately — the Apache reverse
  proxy timeout is never held open. **T-05-15 enforced in the router, not
  only the template:** `_run_render_context` never places `awards`/
  `accuracy` into the Jinja2 context unless `run.run_mode == "live"` — a
  template rewrite has no data to leak.
- **`app/templates/job1_result.html`** — terminal/in-flight state, search
  result + primary-domain check, document sha256/char-count/truncation
  notice, three honest bucket counts with denominator (D-86, never a
  percentage), every award row including every unexplained one, and the
  SDK-call evidence table. Jinja2 autoescaping untouched (T-05-13).
- **`app/main.py`** includes the new router; **`app/templates/index.html`**
  links `/job1` in the same voice as the other two routes.
- **`tests/test_app_job1_route.py`** — 13 tests, all green with no API
  keys, covering the not-configured state, the non-live guard (verified to
  actually trip by temporarily monkeypatching the guard away and
  confirming the assertion catches it), the rate limit on both the HTML
  and JSON views, invalid/unknown run-id 404s including a percent-encoded
  traversal case, JSON money-as-strings with no secret leakage, and
  HTML-escaping of a malicious extracted title.
- Full suite: **542 passed** (529 pre-existing + 13 new), 0 failed, no API
  keys in the environment. `vendor-scan.sh` and `lockfile-scan.sh` both
  exit 0. CI (`Compliance Gates`, all 5 checks) green on the pushed commit.
- **Deployed** to `https://vockell.com/finance` — git_sha `9af46b0`.
  Rollback SHA `60efb6b` and the exact restore command recorded in
  `deploy/README.md` *before* deploying. Every pre-existing route plus
  `/job1` verified 200 from an anonymous, off-box request after the
  deploy.

## Task Commits

1. **Task 1: Persist a run, and put it on the page an anonymous visitor can reach** — `485f78f` (feat)
2. **Task 2: Route tests — the anonymous path, the refusals, and the non-live guard** — `9af46b0` (test)
3. **Task 3: Deploy, and produce the production log evidence for SHP-05 and SHP-06 — or record the gap** — `4caed01` (docs)

## Files Created/Modified

- `agent/runs.py` — JSON persistence for a `Job1Run`, `run_id` traversal guard (T-05-12)
- `app/routers/job1.py` — GET/POST /job1, GET/POST /api/v1/job1, GET /job1/{run_id}
- `app/templates/job1_result.html` — the single shared view for all Job 1 render contexts
- `tests/test_app_job1_route.py` — 13 route tests, offline-seam-built fixtures
- `agent/job1.py` — `on_stage` callback, `sdk_calls` field, `collecting()` wrap
- `agent/telemetry.py` — `collecting()` ambient contextvars collector
- `app/main.py` — includes `job1_router`
- `app/templates/index.html` — links `/job1`
- `.gitignore` — `var/` (job1's ephemeral persistence dir)
- `tests/test_agent_job1_offline.py` — widened D-87 AST gate exception to cover `agent/runs.py`'s `.model_validate(...)` deserialization site
- `deploy/README.md` — rollback position recorded before deploying, plus the Phase 5 plan 05-03 deploy record
- `.planning/WINDOWS.md` — entry #28, naming SHP-05, SHP-06, AGT-03

## Decisions Made

See `key-decisions` in frontmatter above (contextvars-based SDK-call
collector; router-level, not template-level, enforcement of the non-live
guard; the SHP-05/SHP-06-vs-AGT-02 requirements-marking judgment call).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Widened the D-87 AST gate's sanctioned-construction exception to cover `agent/runs.py`**
- **Found during:** Task 1, first full-suite run after writing `agent/runs.py`
- **Issue:** `tests/test_agent_job1_offline.py::test_no_module_outside_schema_constructs_an_extracted_award_object` (05-02's D-87 gate) failed — `agent/runs.py::_award_from_dict` constructed `ExtractedAward(...)` directly to deserialize a saved run, which the gate correctly flagged as "extracted-award construction outside schema.py". The gate's sanctioned-exception list only recognized `agent/gemini_client.py`'s real-response `.model_validate*` parse.
- **Fix:** Changed `agent/runs.py::_award_from_dict` to construct via `ExtractedAward.model_validate({...})` (the same Pydantic-classmethod shape `gemini_client.py` uses) instead of the bare constructor, and widened the test's exception check to permit `runs.py` alongside `gemini_client.py` for `.model_validate*` calls specifically. Reading back a run this process already saved is not fabrication — the underlying D-87 intent (never invent an award to fill a gap) is unaffected; only the AST gate's exception list was too narrow for a legitimate persistence round-trip it didn't anticipate.
- **Files modified:** `agent/runs.py`, `tests/test_agent_job1_offline.py`
- **Verification:** `uv run --frozen pytest tests/ -q` — 542 passed
- **Committed in:** `485f78f` (Task 1 commit — caught and fixed before commit, no separate fix commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 — a pre-existing test's exception list didn't anticipate a new legitimate call site this plan's Task 1 needed)
**Impact on plan:** Necessary for the standing D-87 gate to keep meaning what it claims to mean, without weakening its protection against genuine fabrication. No scope creep.

## Issues Encountered

None beyond the deviation above. The deploy itself went cleanly: `git pull
--ff-only` fast-forwarded 60efb6b → 9af46b0 (139 files, all of Phases 4 and
5 that had never been deployed before — the box had not been redeployed
since early Phase 3), `uv sync --frozen` resolved `google-genai` and
`parallel-web` cleanly, `systemctl restart` came back active, and
`/health` returned 200 (a few transient "Connection refused" lines during
the restart's own polling loop are uvicorn's normal startup window, not a
failure — the script's own retry loop absorbed them and the final health
check passed).

## User Setup Required

**Unchanged from 05-01/05-02, now with a live confirmation of the exact
gap — see `deploy/README.md` "Phase 5 — agent credentials (SHP-05 /
SHP-06)" and `.planning/WINDOWS.md` entry #28.** A human must:
1. Obtain both `PARALLEL_API_KEY` and `GEMINI_API_KEY` (or `GOOGLE_API_KEY`).
2. Write them into `/opt/prodfin/.env` as the `prodfin` user, mode `600`.
3. `sudo systemctl restart prodfin`.
4. Trigger `/job1` from a logged-out browser and confirm the `journalctl`
   evidence per the command block above.
5. Copy the resulting run artifact into `runs/job1/` and commit it —
   that is what turns AGT-03 green and lets WINDOWS.md entry #28 (and #26)
   move to `fixed`.

This is a hard Stage One eligibility concern (SHP-05/SHP-06) and now also
the last blocker for AGT-03, unchanged in kind from 05-01/05-02 but now
confirmed against the actual production environment rather than just this
development environment.

## Next Phase Readiness

- The `/job1` page, the persistence layer, and the deploy path are all
  complete and live. Nothing further needs to be built in code for
  SHP-05/SHP-06/AGT-03 to close — only the human credential step above.
- Phase 6, 7, 8 can proceed independently of this blocker; Phase 8's
  re-verification sweep is exactly the `journalctl` grep this plan already
  ran once (and will find nothing until the human step above happens).
- **Blocker for full SHP-05/SHP-06/AGT-03 verification (not for further
  building):** a human must complete the 5-step credential runbook above.

## Self-Check: PASSED

All 4 created artifacts confirmed present on disk (`[ -f ]`): `agent/runs.py`,
`app/routers/job1.py`, `app/templates/job1_result.html`,
`tests/test_app_job1_route.py`. All 3 task commit hashes (`485f78f`,
`9af46b0`, `4caed01`) confirmed present in `git log --oneline --all`. Full
acceptance-criteria re-run: `uv run --frozen pytest tests/ -q` (542
passed, no API keys in environment), `bash .github/scripts/vendor-scan.sh`
(PASS), `bash .github/scripts/lockfile-scan.sh` (PASS), anonymous `curl`
against `https://vockell.com/finance/{,health,spec,validate,job1}` (all
200), `grep -c "SHP-05" .planning/WINDOWS.md` (2, entry #28 present), CI
run `34325808353` on the pushed commit (5/5 checks passed).

---
*Phase: 05-curated-breadth-the-validation-loop*
*Completed: 2026-09-09*
