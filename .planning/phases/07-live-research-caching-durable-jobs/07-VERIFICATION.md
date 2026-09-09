---
phase: 07-live-research-caching-durable-jobs
status: gaps_found
verified_by: orchestrator (main thread, independent of the executing agents)
verified_at: 2026-09-09
plans: 6
summaries: 6
---

# Phase 7 Verification — Live Research, Caching & Durable Jobs

Verified against the codebase, not against the plan summaries. Every check below
was run directly on the tree at commit `55a5fa5`.

## The owner's stated requirements

These were given verbatim by the project owner and recorded as D-89..D-96.

| # | Requirement | Verdict | Evidence |
|---|---|---|---|
| D-89 | Parallel Search executes on a live user request, not data prep | **PASS** | `docs/sdk-call-sites.md` — 4 call sites, 0 failing; every one reached by a FastAPI route. CI job `sdk-call-sites (D-96)` enforces it. |
| D-89 | The live research path must not read from cache | **PASS** | `agent/job2.py:661` calls `assert_live(DataClass.uncurated_city_research)`; the search loop begins at line 730. The check genuinely precedes the first search. |
| D-90 | The agent decides when it has enough; retry count not fixed in advance | **PASS** | `while True:` at `agent/job2.py:730`. Grep for `for … in range(`, `max_rounds`, `MAX_ROUNDS` inside the module returns nothing. Two AST gates in `tests/test_agent_job2_loop.py` enforce it, and the orchestrator mutation-tested them: rewriting the loop as `for _mutant in range(50):` fails the gate. |
| D-91 | Sufficiency judged on five named fields | **PASS** | Closed five-value `SufficiencyField` enum in `agent/research_schema.py`. |
| D-92 | Every iteration recorded and persisted | **PASS** | `agent/research_runs.py::append_round` writes atomically (temp file + `os.replace`) with `schema_version`, `status`, `boot_id`. Rendered round-by-round in `app/templates/research_result.html`. |
| D-93 | Live results labelled unvalidated, distinct from validated | **PASS** | `agent/job2.py:566` — `price_jurisdiction(..., spend_confidence="researched")`. A recursive Figure-tree walk test asserts every node in a researched run is `researched`. |
| D-94 | Fail open; never fabricate a rate | **PASS** | 11-value closed `TerminalReason` taxonomy including `no_programme_found`, `pricing_refused`, `rule_schema_violation`. `agent/rule_coercion.py` refuses on an undeterminable rate/base/mechanism/cap rather than defaulting. |
| D-95 | google-genai for reasoning, parallel-web for search, no other AI dependency | **PASS** | `pyproject.toml` declares exactly `google-genai==2.19.0` and `parallel-web>=1.0.1`. Grep of `uv.lock` for openai / anthropic / langchain / llama-index / crewai / google-generativeai returns **0 matches**. |
| D-96 | Every call site proven to sit on a request handler, listed with file, line and endpoint | **PASS** | `scripts/audit_sdk_call_sites.py` + `docs/sdk-call-sites.md`, regenerated and byte-compared in CI. |

## Phase requirements

| ID | Verdict | Note |
|---|---|---|
| AGT-05 | **PASS (offline-proven)** | The loop researches, judges, refines and terminates. No live run has fired. |
| AGT-06 | **PASS** | `no_programme_found` is a first-class terminal reason, not an error. |
| AGT-07 | **PASS** | `agent/` imports exactly two names from `engine/` — `engine.models.load_ruleset` and `engine.pipeline.price_jurisdiction` — in both `job1.py` and `job2.py`. `agent/rule_coercion.py` imports nothing from `engine/` at all. An AST gate enforces the boundary. |
| AGT-10 | **PASS** | `app/services/cache_policy.py` is the single choke point; an AST gate proves `DataClass` is defined in exactly one module. |
| AGT-11 | **PASS** | `boot_id` comparison (not a timeout) drives `reclassify_interrupted_jobs()` from a FastAPI lifespan hook, proven by a real two-process `SIGKILL` test and against a separately launched uvicorn. |
| UI-10 | **PASS** | In-flight pages name round/elapsed/ceiling and refresh; terminal pages carry no refresh tag and state the reason in plain words. |
| SHP-06 | **GAP** | See below. |

## Gaps

**SHP-06 — Parallel's Search API genuinely called at runtime, verified by a
timestamped log line at the call site.**

The code is complete and the call sites are proven reachable from live request
handlers. **No live call has ever fired**, because `PARALLEL_API_KEY` and
`GEMINI_API_KEY` are not configured locally or in `/opt/prodfin/.env`. Verified
again during this verification pass.

This audit proves **reachability**, not **execution**. The execution proof is a
`journalctl -u prodfin` grep for `PRODFIN_SDK_CALL` following a request from a
logged-out session. Tracked honestly in `WINDOWS.md` #26 and #28.

Installing the two credentials and triggering one live run is a human action no
agent in this project can perform.

## Not verified

- The rendered research page has not been reviewed by a human in a real browser.
- No live research run has been observed end to end, for the reason above.
