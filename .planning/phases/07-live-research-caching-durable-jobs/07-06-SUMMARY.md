---
phase: 07-live-research-caching-durable-jobs
plan: 06
subsystem: tooling
tags: [ast, call-graph, ci-gate, audit, d-96]

requires:
  - phase: 07-live-research-caching-durable-jobs
    provides: "07-01's app/routers/research.py POST /research entry point and
      agent/job2.py loop; 07-02/07-05's edits to agent/job2.py (the _real_search
      call site); 07-04's agent/live_checks.py (a third search call site added
      after the phase was planned); Phase 5's agent/parallel_client.py search and
      extract call sites reached through app/routers/job1.py."
provides:
  - "scripts/audit_sdk_call_sites.py — an import-aware AST call-graph audit that
    proves every search-SDK call site is reached by a FastAPI route handler,
    exiting non-zero if any is reachable only from a build or prep script"
  - "docs/sdk-call-sites.md — the generated file:line -> endpoint table, the
    artifact the project owner asked for by name"
  - ".github/workflows/ci.yml::sdk-call-sites — a CI job running --check, so the
    table cannot silently go stale"

requirements: [SHP-06, AGT-05, AGT-11, UI-10]
---

# Plan 07-06 Summary — the D-96 call-site audit

## What this closes

The project owner's stated acceptance test for this phase, verbatim:

> **VERIFY BEFORE REPORTING DONE**
> Confirm every parallel-web call site sits on a request handler, not in a build
> or prep script. List the file and line of each call site and which endpoint
> reaches it.

## Result

Four call sites; **zero failing**. None sits in a build or prep script.

| # | Call site | Method | Enclosing function | Reaching endpoint(s) |
|---|---|---|---|---|
| 1 | `agent/job2.py:412` | `.search()` | `_real_search` | `POST /research`, `POST /api/v1/research` |
| 2 | `agent/live_checks.py:119` | `.search()` | `_search_excerpts` | `POST /spec`, `POST /api/v1/spec` |
| 3 | `agent/parallel_client.py:78` | `.search()` | `search_for_disclosure` | `POST /job1`, `POST /api/v1/job1` |
| 4 | `agent/parallel_client.py:108` | `.extract()` | `extract_document` | `POST /job1`, `POST /api/v1/job1` |

Call sites 3 and 4 are **also** reachable through a command-line entry point in
`agent/job1.py`. That does not violate D-89 — the requirement is that the call
executes on a live user request, which the route satisfies — but the generated
artifact discloses the dual reachability rather than omitting it.

## How it works

`scripts/audit_sdk_call_sites.py` parses `agent/` and `app/`, seeds a call graph
with FastAPI route decorators (`@router.get/post/...`), and walks backwards from
each SDK call site to find every endpoint that reaches it. It follows two hops
that a naive scanner misses:

1. **`threading.Thread(target=...)`** — both background-job routes start their
   work on a thread, so the target function is an edge.
2. **Function-as-value references** — this codebase passes real implementations
   as injectable test seams (`search = search_fn or search_for_disclosure`), so a
   bare `ast.Name` load of a known function is an edge too.

## Two bugs found while building it, both producing confidently wrong output

Recorded because an audit that is wrong is worse than no audit, and both of these
would have shipped a false result in opposite directions.

1. **A `Call`-only edge scan reported three false FAILs.** `search_for_disclosure`
   and `extract_document` are referenced as values at `agent/job1.py:322-323`,
   never called by name, so the graph never connected them to `POST /job1`. Caught
   only because an earlier hand audit contradicted the tool.
2. **Bare-name resolution over-attributed across modules.** It claimed
   `POST /research` reached `job1`'s call sites. `agent/job2.py` imports nothing
   from `agent.parallel_client`, so this was a name collision between same-named
   functions. Resolution is now import-aware: an edge is followed only when the
   calling module actually defines or imports the name.

## Verification performed

- **Mutation test.** Disabling the two `@router.post` decorators in
  `app/routers/research.py` flipped `agent/job2.py:412` to `— none —` / **FAIL**
  and exited non-zero. Reverted.
- **Drift test.** Appending a line to `docs/sdk-call-sites.md` made `--check`
  exit 1; regenerating restored exit 0.
- **Cross-check.** The generated table matches an independent hand audit of the
  same tree, endpoint for endpoint.
- Full suite **745 passed, 0 failed**; `vendor-scan.sh` and `lockfile-scan.sh`
  both exit 0.

## A finding worth carrying forward

The audit discovered a **third** search call site that was not in the phase plan:
`agent/live_checks.py:119`, added by plan 07-04 for live programme-status checks
and reached from `POST /spec`. It passes, but it is a reminder that the call-site
inventory is a moving target — which is exactly why the CI job byte-compares the
regenerated table rather than trusting a table written once by hand.

## Still open

`PARALLEL_API_KEY` and `GEMINI_API_KEY` remain unset, so no live call has fired
through any of these four paths. This audit proves **reachability**, not
**execution**. Execution proof is the `PRODFIN_SDK_CALL` production-log grep,
tracked in WINDOWS.md #26/#28.
