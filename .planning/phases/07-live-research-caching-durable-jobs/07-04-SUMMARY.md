---
phase: 07-live-research-caching-durable-jobs
plan: 04
subsystem: agent
tags: [httpx, frankfurter, parallel-web, google-genai, fastapi, jinja2, ast-gate]

requires:
  - phase: 07-live-research-caching-durable-jobs
    provides: "07-01's app/services/cache_policy.py DataClass/POLICY/
      may_use_cache/assert_live, extended (not replaced) by this plan"
provides:
  - "app/services/live_fx.py::resolve_fx — live Frankfurter FX check with
    a disclosed committed-snapshot fallback"
  - "app/services/cache_policy.py::resolve_fx/resolve_cap_consumption/
    resolve_programme_status — the three new AGT-10 sanctioned entry
    points completing all five data classes"
  - "agent/live_checks.py::check_cap_consumption/check_programme_open —
    single-shot (not D-90-loop-shaped) live checks"
  - "tests/test_cache_policy_live.py — the standing AGT-10 single-point-
    of-truth AST gate, proven non-vacuous"
  - "the /spec uncurated-city -> /research?city= entry path (AGT-05)"
affects: [07-05, 07-06]

actuals:
  tokens: 17256
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Live-check-as-disclosure, not live-check-as-arithmetic: resolve_fx's
      outcome is rendered as its own separately-labelled check next to the
      /spec total, but engine.landed_cost.aggregate -> engine.fx.convert
      (committed snapshot only, untouched) is what actually computes the
      rendered dollar figure — the ONLY design that satisfies both 'attempt
      a live fetch on every request that needs a conversion' (D-89) and
      'the pinned golden totals hold regardless of live network
      availability' (D-78) simultaneously, since engine/fx.py's own
      docstring and this plan's own file list forbid modifying the engine
      conversion path."
    - "Second, structurally separate price_jurisdiction call for
      availability only: app/services/spec.py::_resolve_live_programme_checks
      calls engine.pipeline.price_jurisdiction a SECOND time (never
      through engine.ranker.rank's own internal call) purely to obtain a
      correctly-computed three-state Availability once a live cap-remaining
      figure is resolved — its output feeds nothing into RankedCity, so no
      rendered dollar figure or confidence stamp is reachable from it."
    - "Defense-in-depth assert_live: agent/live_checks.py and
      app/services/live_fx.py both call assert_live themselves (in
      addition to app/services/cache_policy.py's own resolver functions
      calling it) — mirrors agent/job2.py's dual-validation pattern from
      07-01, and is also what makes both modules AGT-10 'consumer' modules
      for the AST gate."

key-files:
  created:
    - app/services/live_fx.py
    - agent/live_checks.py
    - tests/test_cache_policy_live.py
  modified:
    - app/services/cache_policy.py
    - app/services/spec.py
    - app/templates/spec_result.html
    - pyproject.toml
    - uv.lock

key-decisions:
  - "Confirmed the live Frankfurter endpoint against the real service
    before writing the parser (not from memory): `GET
    https://api.frankfurter.dev/v1/{YYYY-MM-DD}?base=GBP&symbols=USD` ->
    `{\"amount\":1.0,\"base\":\"GBP\",\"date\":\"2024-06-03\",\"rates\":
    {\"USD\":1.2729}}`. Also confirmed `.../v1/latest?base=GBP&symbols=USD`
    returns today's rate (1.3546 on 2026-09-09) — used as the live
    'attempt' branch's real transcript, distinct from the committed
    snapshot's 1.363."
  - "The FX resolver's outcome is deliberately NOT wired into the actual
    money arithmetic /spec renders. engine/fx.py and engine/landed_cost.py
    are both outside this plan's file list and the plan's own interface
    contract calls them an unchanged engine seam; duplicating the
    per-line conversion/quantize/Figure-citation logic outside engine
    (to let a live rate feed the total) would create a SECOND arithmetic
    implementation for the same money value — a worse honesty violation
    than the alternative. resolve_fx is therefore a genuine, request-time,
    D-89-satisfying live check, rendered as its own disclosure, kept
    structurally apart from the pinned, reproducible engine computation —
    proven directly in test_golden_totals_pinned_regardless_of_live_fx_outcome
    (same $747,735 London total whether the live fetch actually succeeds
    against the real Frankfurter service or is mocked to fail)."
  - "agent/live_checks.py is a NEW module, not an extension of
    agent/parallel_client.py/agent/gemini_client.py (Phase 5's Job 1
    clients) or agent/job2.py (Job 2's loop, 07-01/07-02's file, off-limits
    per file_ownership). Both response schemas
    (_CapConsumptionJudgment/_ProgrammeStatusJudgment) are defined inside
    it, matching the plan's own instruction to keep agent/research_schema.py
    owned solely by the Job 2 loop that 07-02 is editing concurrently."
  - "Per-task commits deliberately re-stage each shared file's content in
    three passes (Task 1's FX-only slice, Task 1+2 combined, then the
    Task 3 additions) rather than one combined diff per file, so each of
    the three commits is independently buildable and independently
    test-green — verified by re-running the targeted test/golden suite
    after each intermediate stage, not only at the end."

requirements-completed: [AGT-10]

coverage:
  - id: D1
    description: "Live FX resolved on every /spec submission needing a conversion, through the single sanctioned app.services.cache_policy.resolve_fx entry point (D-89)"
    requirement: "AGT-10"
    verification:
      - kind: unit
        ref: "tests/test_cache_policy_live.py#test_resolve_fx_attempts_live_first_and_succeeds"
        status: pass
      - kind: integration
        ref: "manual session run against the REAL Frankfurter service (no mock) — see key-decisions"
        status: pass
    human_judgment: false
  - id: D2
    description: "A failed live FX fetch falls back to the committed dated snapshot and discloses the failure and the snapshot's own date, visibly, on the page — never a silently-substituted stale rate (T-07-24)"
    requirement: "AGT-10"
    verification:
      - kind: unit
        ref: "tests/test_cache_policy_live.py#test_resolve_fx_falls_back_and_names_the_snapshot_date_on_failure"
        status: pass
      - kind: unit
        ref: "tests/test_cache_policy_live.py#test_resolve_fx_never_derives_a_cross_rate_or_inverts_on_a_missing_snapshot"
        status: pass
    human_judgment: false
  - id: D3
    description: "The pinned golden totals (NY $758,427 / LA $693,521 / London $747,735 / gap $64,906) hold exactly, whether the live FX fetch succeeds or fails"
    requirement: "AGT-10"
    verification:
      - kind: unit
        ref: "tests/test_cache_policy_live.py#test_golden_totals_pinned_regardless_of_live_fx_outcome"
        status: pass
      - kind: unit
        ref: "tests/test_golden_cost.py (unchanged, all 6 pass) + tests/test_route_a_basis_walk.py (unchanged, all 3 pass)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Cap consumption is resolved live only for a programme declaring cap_consumption_check.method == \"live_research\" (New York), never fabricates a remaining balance, and feeds only engine.credit.assess_availability's three-state answer (AGT-10/D-94)"
    requirement: "AGT-10"
    verification:
      - kind: unit
        ref: "tests/test_cache_policy_live.py#test_resolve_cap_consumption_returns_none_when_method_is_not_live_research"
        status: pass
      - kind: unit
        ref: "tests/test_cache_policy_live.py#test_check_cap_consumption_never_coerces_an_unparseable_figure"
        status: pass
      - kind: unit
        ref: "tests/test_cache_policy_live.py#test_resolve_cap_consumption_and_resolve_programme_status_never_fabricate_availability"
        status: pass
    human_judgment: false
  - id: D5
    description: "The live programme-status answer is carried alongside the priced result and is NEVER written into Jurisdiction.status, never passed to assess_eligibility, and never changes a Figure.confidence value — the critical constraint this plan exists to hold"
    requirement: "AGT-10"
    verification:
      - kind: unit
        ref: "tests/test_route_a_basis_walk.py::test_no_validated_confidence_anywhere_in_the_dag (unchanged, still passes)"
        status: pass
      - kind: other
        ref: "grep -rn 'jurisdiction.status\\s*=' app/ agent/ engine/ — zero writes found, only reads in engine/pipeline.py and engine/credit.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "Exactly one module (app.services.cache_policy) declares DataClass/POLICY/may_use_cache/assert_live across app/, agent/, engine/; every one of the four consumer modules imports from it; a second definition anywhere makes the gate fail (proven, not asserted)"
    requirement: "AGT-10"
    verification:
      - kind: unit
        ref: "tests/test_cache_policy_live.py#test_policy_names_defined_in_exactly_one_module"
        status: pass
      - kind: unit
        ref: "tests/test_cache_policy_live.py#test_every_consumer_module_imports_from_cache_policy"
        status: pass
      - kind: other
        ref: "manual non-vacuity mutation this session (scratch second DataClass, observed RED, reverted, observed GREEN) — see Deviations"
        status: pass
    human_judgment: false
  - id: D7
    description: "An uncurated candidate city on the /spec result page links to /research?city=<urlencoded name>; a curated city renders no such link (AGT-05's entry path)"
    requirement: "AGT-10"
    verification:
      - kind: e2e
        ref: "tests/test_cache_policy_live.py#test_uncurated_city_renders_a_urlencoded_research_link"
        status: pass
      - kind: e2e
        ref: "tests/test_cache_policy_live.py#test_curated_city_renders_no_research_link"
        status: pass
    human_judgment: false
  - id: D8
    description: "No AI package enters pyproject.toml; httpx is promoted from dev-only to a runtime dependency, already resolved transitively, and uv.lock's resolved-package count is unchanged (D-95)"
    requirement: "AGT-10"
    verification:
      - kind: other
        ref: "git diff uv.lock (httpx moves from [package.dev-dependencies] to [package.dependencies]/requires-dist only; 43 resolved packages before and after)"
        status: pass
      - kind: other
        ref: "bash .github/scripts/lockfile-scan.sh"
        status: pass
    human_judgment: false
  - id: D9
    description: "The rendered /spec 'Live FX check' and 'Live programme checks' sections read clearly to a producer and do not reintroduce prescriptive vocabulary (D-70)"
    verification:
      - kind: unit
        ref: "tests/test_app_spec_route.py::test_d70_vocabulary_condition_holds_over_rendered_html_body (unchanged, still passes over the extended template)"
        status: pass
    human_judgment: true
    rationale: "The D-70 vocabulary gate is proven mechanically, but whether the new sections' wording and table layout actually read well to a producer (not just pass a forbidden-word grep) is a genuine UX judgment call no automated test captures."

duration: ~55min
completed: 2026-09-09
status: complete
---

# Phase 7 Plan 4: The AGT-10 Caching Boundary Made Real Summary

**Live FX (Frankfurter, confirmed against the real endpoint), live cap consumption, and live programme status now all resolve through three new `app.services.cache_policy` entry points on the request itself; an AST gate proves exactly one module owns the cached-versus-live decision, and it survived a genuine non-vacuity mutation this session.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-09 (approx., session start)
- **Completed:** 2026-09-09T09:19:46Z
- **Tasks:** 3
- **Files modified:** 8 (3 created, 5 modified)

## Accomplishments

- `app/services/live_fx.py::resolve_fx` attempts a live Frankfurter fetch
  (`GET https://api.frankfurter.dev/v1/{date}?base=...&symbols=...`, no key
  required — confirmed against the real service this session) on every
  currency pair a `/spec` submission's candidate cities need converted.
  On success the resolution carries `origin="live"`, the fetched rate as a
  `Decimal` built via `str(...)` (never a float hop), and a plain-language
  disclosure naming the rate and the fetch moment. On ANY failure
  (connection error, timeout, non-2xx, unparseable body, unsupported pair)
  it falls back to `engine.fx.load_fx_snapshot` — the committed, dated,
  cited snapshot — and discloses the failure reason plus the snapshot's
  own date directly on the page (T-07-24): a stale rate is never presented
  as a live one.
- The rendered dollar totals (`total_landed_cost`/`cost_only_total`) stay
  wired exclusively to `engine.landed_cost.aggregate` ->
  `engine.fx.convert`, the committed-snapshot-only path this plan's own
  interface contract names as an unchanged engine seam. This is what keeps
  the D-78 golden totals exact regardless of live network availability —
  proven directly by submitting a London candidate through
  `handle_spec_submission` twice in the same test, once with the live
  Frankfurter call mocked to succeed (a different rate, 1.4, than the
  committed 1.363) and once mocked to fail, and asserting the SAME
  `$747,735` total both times.
- `agent/live_checks.py::check_cap_consumption`/`check_programme_open` are
  single-shot (one `parallel-web` Search plus one `google-genai` structured
  judgment) — deliberately NOT Job 2's D-90 self-terminating loop shape,
  since the question each answers ("what's the remaining cap right now" /
  "is this programme open right now") is narrow enough to be answerable or
  not in one pass. Both call `agent.settings.integration_status()` first
  and return an immediate, reason-naming undetermined result with no SDK
  import at all when either key is absent — proven both by direct
  assertion and by a fresh-subprocess `sys.modules` check.
- `app/services/cache_policy.py` gained its final two sanctioned entry
  points: `resolve_cap_consumption` (returns `None` — never a fabricated
  balance — unless the programme's `cap_consumption_check.method ==
  "live_research"`, which only `jurisdictions/us-ny.yaml` currently
  declares) and `resolve_programme_status` (always attempts the live
  check, returns a `ProgrammeStatusCheck` with a three-value `state`). All
  five AGT-10 data classes are now genuinely enforced.
- **The critical constraint held:** the live programme-status answer is
  carried in a new `LiveProgrammeCheck` dataclass, rendered as its own
  "Live programme checks" section on the `/spec` page — never written into
  `Jurisdiction.status`, never passed to `assess_eligibility`, never
  touching a `Figure.confidence` value. A cap-remaining figure reaches
  `engine.credit.assess_availability` only through a second, structurally
  separate `engine.pipeline.price_jurisdiction` call inside
  `_resolve_live_programme_checks` — never through `engine.ranker.rank`'s
  own internal pricing call that actually produces the rendered
  `RankedCity` Figures. `tests/test_route_a_basis_walk.py`'s D-63 gate is
  byte-for-byte unchanged and still passes.
- `tests/test_cache_policy_live.py` is the standing AGT-10 single-point-
  of-truth gate: an `ast`-based scan (never a text grep) proves
  `DataClass`/`POLICY`/`may_use_cache`/`assert_live` are defined in
  exactly `app/services/cache_policy.py` across all of `app/`, `agent/`,
  `engine/`, and that all four consumer modules
  (`agent/job2.py`, `agent/live_checks.py`, `app/services/live_fx.py`,
  `app/services/spec.py`) import from it. **Non-vacuity performed by hand
  this session:** a scratch file declaring a second `DataClass` under
  `app/services/` was added, the gate re-run and observed RED
  (`AssertionError: 'DataClass' must be defined in exactly
  app/services/cache_policy.py, found in: [...both files...]`), then
  deleted and the gate confirmed GREEN again.
- A `/spec` result page's uncurated candidate city (where
  `resolve_city_to_jurisdiction` returns `None`) now links to
  `/research?city=<urlencoded name>` — AGT-05's entry path, one click from
  naming an uncurated city to starting live research. A curated city
  renders no such link. `GET /research?city=` already prefilled and
  escaped the form (plan 07-01); this task added no router code.
- `httpx` promoted from `[dependency-groups].dev` to `[project.dependencies]`
  in `pyproject.toml`. `uv.lock` gained no new package: 43 resolved
  packages both before and after — `httpx` simply moved TOML sections
  (`[package.dev-dependencies]` -> `[package.dependencies]`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Live FX on the request, with a visible fallback** — `bb4d6cf` (feat)
2. **Task 2: Live cap consumption and live programme status** — `f6a59e6` (feat)
3. **Task 3: The single-point gate, and the uncurated-city path into live research** — `19ecbcf` (test)

**Plan metadata:** committed alongside this SUMMARY.

## Files Created/Modified

- `app/services/live_fx.py` — live Frankfurter FX resolver with the disclosed committed-snapshot fallback
- `agent/live_checks.py` — `check_cap_consumption`/`check_programme_open`, both response schemas
- `app/services/cache_policy.py` — `resolve_fx`, `resolve_cap_consumption`, `resolve_programme_status`, `ProgrammeStatusCheck`
- `app/services/spec.py` — `LiveProgrammeCheck`, `_resolve_fx_for_localized_cities`, `_resolve_live_programme_checks`, `SpecResult` field additions
- `app/templates/spec_result.html` — "Live FX check" / "Live programme checks" sections, the uncurated-city `/research` link
- `pyproject.toml` / `uv.lock` — `httpx` promoted to a runtime dependency, no new resolved package
- `tests/test_cache_policy_live.py` — the full AGT-10 Task 1/2/3 proof suite (24 tests)

## Decisions Made

See `key-decisions` in frontmatter. In short: the live FX check is a
genuine, disclosed, request-time check kept structurally apart from the
committed-snapshot arithmetic engine renders (the only design that
satisfies both D-89's "attempt live" and D-78's "golden totals pinned
regardless of network" simultaneously without touching the engine seams
this plan's own interface contract forbids); cap-consumption's
availability answer is obtained through a second, side, price_jurisdiction
call kept structurally apart from `engine.ranker.rank`'s own pricing call;
`agent/live_checks.py` is a new module, deliberately not extending
`agent/job2.py` or `agent/research_schema.py` (both 07-02's concurrent
files); and the three task commits each re-stage the shared files'
content incrementally so every commit is independently test-green.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `date.today()` replaced with a timezone-aware UTC date**
- **Found during:** Task 1 (`ruff check` flagged `DTZ011` on the initial `on_date = date.today()` call in `_resolve_fx_for_localized_cities`)
- **Issue:** A naive `date.today()` call is implicitly server-timezone-dependent — the live FX check's "today" must be well-defined independent of host timezone, matching every other UTC-timestamp pattern already established in `app/services/live_fx.py` and `agent/live_checks.py`.
- **Fix:** Changed to `datetime.now(UTC).date()`, importing `UTC`/`datetime` alongside the existing `date` import.
- **Files modified:** `app/services/spec.py`
- **Verification:** Full suite re-run, all green.
- **Committed in:** `bb4d6cf` (Task 1 commit)

**2. [Rule 1 - Bug] Removed an unused `TYPE_CHECKING` import**
- **Found during:** Task 1/2 boundary (`ruff check --select F401` flagged `ProgrammeStatusCheck` imported into `app/services/spec.py`'s `TYPE_CHECKING` block but never referenced — the intermediate authoring pass added it speculatively before the final annotation shape settled)
- **Issue:** Dead import, no functional effect but a lint failure.
- **Fix:** `ruff check --select F401,UP037 --fix` removed it (and normalized quoted forward-ref type annotations to bare names, safe under this module's existing `from __future__ import annotations`).
- **Files modified:** `app/services/cache_policy.py`, `app/services/spec.py`
- **Verification:** `ruff check` clean on touched files; full suite re-run, all green.
- **Committed in:** `bb4d6cf` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 correctness/lint fixes).
**Impact on plan:** Both are minor code-quality/correctness fixes. No scope creep, no behavior change to any tested path.

## Issues Encountered

- The uncurated-city `/research` link test initially asserted the
  prefilled form's HTML directly, but this environment has no API keys
  configured, so `GET /research` renders `app/routers/research.py`'s
  own pre-existing "not configured" message instead of the form (plan
  07-01's own gate, unrelated to this plan). Resolved by monkeypatching
  `app.routers.research.integration_status` inside that one test to force
  the configured branch, purely to prove the link lands on a form
  carrying the decoded prefill — no production code changed.
- `git status` showed `tests/test_engine_against_validation_pairs.py` as
  modified throughout this session — a concurrent agent's (07-02 or
  07-03) uncommitted in-flight work in the same shared checkout
  (`isolation=none`). Never touched, never staged, never committed by
  this plan's work.

## User Setup Required

None — no new environment variable is introduced. `PARALLEL_API_KEY` and
`GEMINI_API_KEY`/`GOOGLE_API_KEY` were already required by Job 1/Job 2 and
are reused unchanged by `agent/live_checks.py`. Frankfurter needs no key
and was called against the real live service during this session to
confirm the endpoint shape (see key-decisions).

## Next Phase Readiness

**Live SDK call-site audit (this plan's new call sites, in the spirit of
07-CONTEXT.md's D-96 requirement):**

| File:line | Call | Reachable from |
|---|---|---|
| `agent/live_checks.py:119` (`client.search(...)`, inside `_search_excerpts`) | `parallel-web` Search | `check_cap_consumption`/`check_programme_open` <- `app/services/cache_policy.py::resolve_cap_consumption`/`resolve_programme_status` <- `app/services/spec.py::_resolve_live_programme_checks` <- `handle_spec_submission` <- `POST /spec` and `POST /api/v1/spec` (`app/routers/spec.py`) |
| `agent/live_checks.py:193` (`generate_content(...)`, inside `check_cap_consumption`) | `google-genai` | same chain as above |
| `agent/live_checks.py:293` (`generate_content(...)`, inside `check_programme_open`) | `google-genai` | same chain as above |

No call site here is reachable only from a CLI `__main__`, a build step,
or a prep script — `agent/live_checks.py` has no such entry point and is
only ever imported from `app/services/cache_policy.py`'s two lazy
function-body imports.

**Unverified pending API keys (honestly stated):** neither
`PARALLEL_API_KEY` nor `GEMINI_API_KEY`/`GOOGLE_API_KEY` is set in this
environment. Every claim above about `check_cap_consumption`/
`check_programme_open`'s live-judgment parsing is proven through
`tests/test_cache_policy_live.py`'s injected-fake seams
(`monkeypatch.setattr` on `parallel.Parallel`/`google.genai.Client`) —
never a real Parallel or Gemini response. The live FX check is the one
genuinely-real live SDK call this plan proves directly, since Frankfurter
needs no key. A real `PRODFIN_SDK_CALL sdk=parallel-web ...` and
`sdk=google-genai ...` line pair for the cap-consumption/programme-status
checks remains to be produced once keys exist.

**Ready for 07-05/07-06:** all five AGT-10 data classes are now enforced
by the single `app.services.cache_policy` choke point; a future plan
adding a sixth live data class need only add one `DataClass` member, one
`POLICY` entry, and one sanctioned resolver function here — the AST gate
will catch a definition placed anywhere else.

---
*Phase: 07-live-research-caching-durable-jobs*
*Completed: 2026-09-09*

## Self-Check: PASSED

All 3 created files confirmed present on disk (`app/services/live_fx.py`,
`agent/live_checks.py`, `tests/test_cache_policy_live.py`). All 3 task
commit hashes confirmed in `git log` (`bb4d6cf`, `f6a59e6`, `19ecbcf`).
Full suite: 720 passed, 0 failed. `tests/test_golden_cost.py` (6/6) and
`tests/test_route_a_basis_walk.py` (3/3) both pass unchanged. Vendor-scan
and lockfile-scan both clean. `uv.lock` gained no new resolved package (43
before, 43 after) — `git diff --stat -- uv.lock` shows only the `httpx`
dependency-group relocation, already committed in `bb4d6cf`.
