---
phase: 07-live-research-caching-durable-jobs
plan: 02
subsystem: agent
tags: [agent-loop, google-genai, parallel-web, ast-gate, pydantic]

requires:
  - phase: 07-live-research-caching-durable-jobs
    provides: "07-01's agent/job2.py tracer (the while True: driver, one
      round), agent/research_schema.py's SufficiencyVerdict/FieldFinding/
      SufficiencyField, agent/research_runs.py's durable append_round, and
      agent/settings.py's declared-but-unenforced
      JOB2_WALL_CLOCK_CEILING_SECONDS — all completed by this plan."
provides:
  - "agent/job2.py::merge_findings/unmet_fields/build_refined_objective/
    normalize_queries/normalize_mode — the pure D-90 refinement layer"
  - "agent/job2.py::TerminalReason — the closed nine-value terminal
    taxonomy (sufficient, agent_gave_up, no_programme_found,
    insufficient_identity, budget_exhausted, contradictory_verdict,
    cache_boundary_violation, not_configured, sdk_error)"
  - "agent/research_schema.py::JurisdictionIdentity — the four identity
    facts required in addition to D-91's five sufficiency fields"
  - "The enforced wall-clock guard (time.monotonic(), checked between
    rounds) and sdk_error handling around both real SDK call sites"
  - "tests/test_agent_job2_loop.py — the standing D-90/D-94 CI gate"
affects: [07-03, 07-05, 07-06]

actuals:
  tokens: 13692
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Monotonic findings merge: agent/job2.py::merge_findings never flips
      determined True back to False, and only accepts a later overwrite of
      an already-determined field when the later finding is itself
      determined AND sourced — an unsourced later value is discarded and
      the discard is recorded on the round (discarded_fields)."
    - "Refinement via restated objective, never query-string editing:
      build_refined_objective takes no query text as input, so it
      structurally cannot reproduce a substring of a previous round's
      search_queries — proven by test, not just asserted in prose."
    - "Wall-clock guard as a resource backstop, not a round bound: checked
      once per loop iteration via time.monotonic() against
      agent.settings.JOB2_WALL_CLOCK_CEILING_SECONDS (read as a live
      module-global, so a test can monkeypatch it), strictly AFTER a
      round's own decision is evaluated and only when that decision is
      'continue' — round N always completes, only round N+1 is denied."
    - "A 'sufficient' claim is never taken on faith: the driver
      cross-checks it against its own merged findings
      (contradictory_verdict) and the new JurisdictionIdentity block
      (insufficient_identity) before accepting TerminalReason.sufficient."

key-files:
  created:
    - tests/test_agent_job2_loop.py
  modified:
    - agent/job2.py
    - agent/research_schema.py
    - agent/settings.py
    - app/routers/research.py
    - tests/test_agent_job2_offline.py

key-decisions:
  - "TerminalReason values are a NEW closed vocabulary distinct from
    SufficiencyVerdict.decision's four literals — e.g. the decision literal
    \"give_up\" maps to TerminalReason.agent_gave_up, not to a terminal
    string named \"give_up\". This is deliberate: the terminal-state space
    also has to express failures the model's own decision can never
    express (contradictory_verdict, insufficient_identity,
    budget_exhausted, sdk_error), so reusing the decision literal verbatim
    would have left no room for those. Required updating two pre-existing
    assertions in tests/test_agent_job2_offline.py (07-01's fixture) to
    match — documented as a Rule 1 deviation below, its own commit."
  - "A 'sufficient' verdict now requires BOTH all five D-91 fields
    determined AND a complete JurisdictionIdentity before the driver
    accepts TerminalReason.sufficient — identity is IN ADDITION TO the
    five fields per the plan, never a substitute. This meant
    tests/test_agent_job2_offline.py's scripted 'sufficient' fixture
    (07-01, no identity, unsourced findings) needed identity and
    source_url added to stay genuinely sufficient under the new check —
    fixed in the same compatibility commit."
  - "The pre-loop InvalidCityInputError path keeps writing the plain
    string \"invalid_input\" as terminal_reason, NOT a TerminalReason
    member. The plan's Task 2 behavior list enumerates TerminalReason as
    'exactly' nine members and invalid_input is not among them — this
    path rejects input before the agent loop ever starts, so it is
    outside the loop's own terminal-state space by design. Left
    unchanged from 07-01 rather than force-fit into the closed enum."
  - "record[\"findings\"]/record[\"undetermined_disclosures\"]/
    record[\"ruleset_path\"]/record[\"priced\"] are now written explicitly
    (not left as absent keys) on every terminal write, so
    no_programme_found's 'constructs nothing' claim is provably true from
    the JSON on disk, not just from the in-process dataclass default.
    record[\"identity\"] is also persisted when known, ready for 07-05 to
    consume without a record-shape change."

patterns-established:
  - "D-90 refinement layer: pure functions (no SDK call, no I/O) compute
    the next round's inputs from the accumulated state; the driver's only
    job is to call them in order and persist the result. Keeps the whole
    refinement policy independently unit-testable from the SDK-calling
    loop shell."

requirements-completed: [AGT-05, AGT-06]

coverage:
  - id: D1
    description: "Findings accumulate monotonically across rounds; a determined field survives a round that says nothing, and an unsourced later value cannot overwrite a sourced one (D-90/D-94)"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_merge_findings_keeps_a_field_determined_after_a_round_that_says_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_merge_findings_never_flips_determined_true_back_to_false"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_merge_findings_discards_an_unsourced_overwrite_of_a_determined_field"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_merge_findings_accepts_a_sourced_overwrite_of_a_determined_field"
        status: pass
    human_judgment: false
  - id: D2
    description: "Round N+1's objective restates the still-unmet fields and never reproduces a previous round's search query (07-SDK-FINDINGS)"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_build_refined_objective_names_the_city_and_every_unmet_field"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_build_refined_objective_never_reproduces_a_previous_search_query"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_round_two_search_receives_round_ones_next_objective_and_queries (tests/test_agent_job2_offline.py, unchanged from 07-01)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The round count is a property of the scripted model verdicts (1, 2, 5, 9 rounds), never a property of the driver code — proven both behaviorally and by AST inspection"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_round_count_is_a_property_of_the_scripted_verdicts_not_the_driver[decisions0-1]"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_round_count_is_a_property_of_the_scripted_verdicts_not_the_driver[decisions3-9]"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_run_job2_source_has_no_range_driven_for_loop"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_run_job2_never_compares_the_round_counter_to_an_int_constant"
        status: pass
    human_judgment: false
  - id: D4
    description: "A 'sufficient' claim is rejected as contradictory_verdict when the agent's own findings admit a gap, and rejected as insufficient_identity when the five fields are complete but the jurisdiction cannot be named (D-91, D-94)"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_sufficient_verdict_leaving_caps_undetermined_is_contradictory"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_sufficient_with_all_five_fields_but_no_identity_is_insufficient_identity"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_sufficient_with_partial_identity_names_only_the_missing_field"
        status: pass
    human_judgment: false
  - id: D5
    description: "'No programme found' is a legitimate terminal result that constructs and prices nothing — proven on the in-process return value and on the record round-tripped through disk (AGT-06, D-94)"
    requirement: "AGT-06"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_no_programme_found_is_a_legitimate_terminal_that_prices_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_no_programme_found_record_round_trips_with_priced_and_ruleset_path_none"
        status: pass
    human_judgment: false
  - id: D6
    description: "The wall-clock ceiling produces budget_exhausted, checked only between rounds (never mid-call), and is structurally distinct from the agent's own agent_gave_up (UI-10)"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_wall_clock_ceiling_stops_between_rounds_not_mid_call"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_budget_exhausted_is_distinguishable_from_agent_gave_up"
        status: pass
    human_judgment: false
  - id: D7
    description: "No numeric rate literal is ever assigned to a rate-bearing identifier anywhere in agent/ — the D-94 no-fabricated-rate AST gate"
    requirement: "AGT-06"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_agent_tree_has_no_rate_literal_assignments"
        status: pass
    human_judgment: true
    rationale: "The gate itself is a passing automated test, but its non-vacuity (that it would actually fail on a real violation) was proven by a manual mutate-observe-revert cycle during this session, not by a permanent test — see 'Non-vacuity mutations performed' below. A human should confirm that written record matches the session's actual terminal output, which is reproduced verbatim in this SUMMARY."
  - id: D8
    description: "An exception raised by either the search or judge SDK seam produces a durable sdk_error terminal record instead of an unhandled crash, with only the exception text (no key, no prompt) recorded"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_exception_in_search_fn_produces_a_durable_sdk_error_record"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_loop.py#test_exception_in_judge_fn_also_produces_sdk_error"
        status: pass
    human_judgment: false
  - id: D9
    description: "Every parallel-web call site is proven reachable only from a request handler (D-96 audit, re-confirmed after this plan's line-number shift)"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_offline.py#test_job2_module_has_no_main_entry_point"
        status: pass
    human_judgment: true
    rationale: "No API keys are available in this environment (verified again this session — see Next Phase Readiness). The D-96 audit table below is a manual line-number re-confirmation after this plan's edits shifted agent/job2.py's call site from line 209 (07-01) to line 391; a human should confirm a live PRODFIN_SDK_CALL line once keys exist, exactly as 07-01 already deferred."

duration: 55min
completed: 2026-09-09
status: complete
---

# Phase 7 Plan 2: The D-90 Loop's Finished Shape — Findings Merge, Refinement, and the Closed Terminal Taxonomy Summary

**`agent/job2.py`'s D-90 research loop now accumulates findings monotonically across rounds, restates its own objective toward what is still missing, cross-checks every "sufficient" claim against its own evidence and a new jurisdiction-identity requirement before believing it, enforces the wall-clock backstop between rounds only, and reaches one of a closed nine-value `TerminalReason` set every time — all proven by a new AST-based standing gate (`tests/test_agent_job2_loop.py`) that a hand-performed, observed-and-reverted mutation shows genuinely has teeth.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-09T19:05:00Z (approx.)
- **Completed:** 2026-09-09T20:00:00Z (approx.)
- **Tasks:** 3
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- **The D-90 refinement layer** — `merge_findings`, `unmet_fields`,
  `build_refined_objective`, `normalize_queries`, `normalize_mode` — is a
  set of pure functions with no SDK call and no I/O, directly unit-tested
  in isolation from the loop that calls them. `merge_findings` never flips
  `determined` back to `False`, and only accepts a later overwrite of an
  already-determined field when the new finding is itself `determined` AND
  carries a `source_url`; every other attempted overwrite is discarded and
  the discard is recorded on the round (`discarded_fields`).
  `build_refined_objective` takes no query text as an input parameter at
  all, so it is structurally incapable of reproducing a substring of a
  previous round's `search_queries` — proven by a test, not asserted only
  in a docstring.
- **The closed nine-value `TerminalReason` taxonomy**
  (`sufficient`, `agent_gave_up`, `no_programme_found`,
  `insufficient_identity`, `budget_exhausted`, `contradictory_verdict`,
  `cache_boundary_violation`, `not_configured`, `sdk_error`) replaces the
  07-01 tracer's direct pass-through of `verdict.decision` as the terminal
  string. A `"sufficient"` decision is now cross-checked by the driver
  against its own merged findings (rejected as `contradictory_verdict` if
  any of the five D-91 fields are still undetermined) and against a new
  `JurisdictionIdentity` block (rejected as `insufficient_identity` if the
  jurisdiction's name, country code, level, or currency cannot be named) —
  D-94's "never believe an unsupported success claim" discipline applied
  to the sufficiency judgment itself, not just to award extraction.
- **`JurisdictionIdentity`** (`agent/research_schema.py`) is the four
  identity facts a rule model needs, spelled out explicitly IN ADDITION
  to D-91's five sufficiency fields, never a substitute for one of them —
  a run can determine all five and still land on `insufficient_identity`
  if it cannot name the jurisdiction. `level`'s vocabulary is written as
  its own `Literal["national", "state", "provincial", "city"]` rather than
  imported from `engine.models`, honoring the AST gate that permits only
  two names from `engine/` into `agent/`.
- **The wall-clock guard is now enforced**, not just declared:
  `time.monotonic()` captured before round 1, compared against
  `agent.settings.JOB2_WALL_CLOCK_CEILING_SECONDS` (read live as a module
  global, so a test can `monkeypatch` it to a small value) strictly
  between rounds — after a round's own decision is evaluated and only when
  that decision is `"continue"`. Round N always finishes; only round N+1
  is denied. This keeps `budget_exhausted` a resource backstop, never a
  round-count bound, and structurally distinct from `agent_gave_up`
  (the agent's own decision) both in the enum and in the rendered message.
- **Both real SDK call sites are now wrapped in `try`/`except`**: an
  exception from either `search()` or `judge()` produces a durable
  `sdk_error` terminal record (the exception's plain text, never a key or
  a prompt) instead of an unhandled crash reaching the background thread
  in `app/routers/research.py`.
- **Every terminal write now explicitly persists** `findings` (the merged
  five-field snapshot), `undetermined_disclosures` (plain-word unmet field
  names), `ruleset_path`, `priced`, and — when known — `identity`, rather
  than leaving them as absent keys relying on in-process defaults. This
  makes `no_programme_found`'s "constructs nothing" claim provable from the
  JSON on disk itself, and leaves the record shape ready for 07-05 to fill
  in `ruleset_path`/`priced` without churn.
- **`tests/test_agent_job2_loop.py`** (34 tests) is the new standing CI
  gate: unit coverage for all five pure functions; behavioral coverage for
  every `TerminalReason` value reachable from a scripted seam (including
  the wall-clock guard via a monkeypatched ceiling plus a sleeping fake,
  and `sdk_error` via a seam that raises); an AST scan proving `run_job2`
  contains no `range()`-driven `for` loop and no comparison between the
  round counter and an integer constant; and an AST scan over the whole
  `agent/` tree proving no numeric literal is ever assigned to any of the
  seven closed rate-bearing identifier names.

## Task Commits

Each task was committed atomically:

1. **Task 1 + Task 2 (combined — see Deviations):** `a6636a6` (feat) — the
   pure refinement layer, `JurisdictionIdentity`, the closed
   `TerminalReason` taxonomy, the enforced wall-clock guard, and
   `sdk_error` handling.
2. **Compatibility fix for 07-01's offline fixture:** `f5451e9` (fix)
3. **Task 3:** `0ddd814` (test) — `tests/test_agent_job2_loop.py`

**Plan metadata:** committed alongside this SUMMARY.

## Files Created/Modified

- `agent/job2.py` — pure refinement layer, `TerminalReason`, enforced
  wall-clock guard, `sdk_error` handling, explicit terminal-record fields
- `agent/research_schema.py` — `JurisdictionIdentity`, `identity` field on
  `SufficiencyVerdict`
- `agent/settings.py` — comment update only (the guard is now landed)
- `app/routers/research.py` — comment update only (terminal-state
  vocabulary now points at `TerminalReason`)
- `tests/test_agent_job2_offline.py` — scripted "sufficient" fixture now
  carries identity and sourced findings; `give_up` assertion updated to
  `agent_gave_up`
- `tests/test_agent_job2_loop.py` — new, the standing D-90/D-94 gate (34
  tests)

## Decisions Made

See `key-decisions` in frontmatter. In short: `TerminalReason` is a
deliberately new vocabulary rather than a pass-through of
`SufficiencyVerdict.decision`; a `"sufficient"` claim now requires BOTH
the five D-91 fields AND a complete jurisdiction identity; the pre-loop
`invalid_input` rejection stays outside the closed `TerminalReason` set by
design (the agent loop never starts on that path); and every terminal
record now explicitly writes `findings`/`undetermined_disclosures`/
`ruleset_path`/`priced`/`identity` rather than relying on absent keys.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 1 and Task 2 landed in a single combined commit rather than two**
- **Found during:** committing after both tasks' code was written
- **Issue:** The plan structures Task 1 (findings merge/refinement) and
  Task 2 (terminal taxonomy) as separate `tdd="true"` tasks with separate
  `<verify>` filters. Both concerns live inside `run_job2`'s single
  function body and interleave directly — the terminal-decision logic
  reads the very `merged`/`unmet` state Task 1's functions produce, and
  splitting the implementation into two sequential edits would have meant
  writing a Task-1-only version of `run_job2` that doesn't yet call
  `_terminal_for_decision`, then immediately rewriting the same function
  body again for Task 2 — pure make-work with no genuine intermediate
  state, unlike 07-01's Task 2 RED/GREEN split (which touched a genuinely
  separable new module, `app/services/cache_policy.py`).
- **Fix:** Wrote both tasks' code as one coherent change to `agent/job2.py`
  (plus `agent/research_schema.py`'s `JurisdictionIdentity` and
  `agent/settings.py`'s comment) and committed it as a single `feat`
  commit (`a6636a6`), verified against BOTH tasks' `<verify>` filters
  (`-k "merge or objective or normalize"` and
  `-k "terminal or ceiling or identity or contradictory"`) before
  committing — both passed.
- **Files modified:** `agent/job2.py`, `agent/research_schema.py`,
  `agent/settings.py`
- **Verification:** both `<verify>` filters pass in isolation (14 and 7
  tests respectively); full suite green at 653 passed.
- **Commit:** `a6636a6`

**2. [Rule 1 - Bug] Updated `tests/test_agent_job2_offline.py` (07-01's fixture) to match the new taxonomy**
- **Found during:** first full-suite run after Task 2's implementation
- **Issue:** 07-01's `_scripted_seams` fixture produced a `"sufficient"`
  decision with unsourced findings and no `identity` — genuinely
  insufficient under Task 2's new contradiction/identity checks — and
  asserted `run.terminal_reason == "give_up"`, the raw decision literal
  Task 2 deliberately does not reuse verbatim (`TerminalReason.agent_gave_up`
  instead).
- **Fix:** Added `source_url` to the scripted findings and a full
  `JurisdictionIdentity` to the scripted "sufficient" verdict; updated the
  `give_up` assertion to `"agent_gave_up"`.
- **Files modified:** `tests/test_agent_job2_offline.py`
- **Verification:** `uv run --frozen pytest tests/test_agent_job2_offline.py tests/test_cache_policy.py -q` — 32 passed (was 3 failed / 29 passed before the fix).
- **Commit:** `f5451e9`

---

**Total deviations:** 2 auto-fixed (1 Rule 1 commit-structure adaptation, 1 Rule 1 compatibility fix to a sibling test file).
**Impact on plan:** No scope creep. Both changes were required for the plan's own `<verification>` block ("full suite green") to hold; neither touched files on the file-ownership exclusion list.

## Non-vacuity mutations performed (Task 3, recorded per plan instruction)

Both mutations were performed by hand against the real files, observed to
fail the relevant gate, then reverted. Neither mutation was ever committed
— confirmed by `git diff --stat agent/settings.py agent/job2.py` against
the prior commit showing only the intended, permanent changes after revert.

**Mutation 1 — round-driving `for`/`range` loop.** Changed
`agent/job2.py`'s `while True:` to
`for round_number in range(50):  # MUTATION-1-NON-VACUITY-PROOF, reverted immediately`
and ran `uv run --frozen pytest tests/test_agent_job2_loop.py -q -k range_driven_for_loop`:

```
FAILED tests/test_agent_job2_loop.py::test_run_job2_source_has_no_range_driven_for_loop
AssertionError: ['line 600: for-loop driven by range(...)']
```

Reverted; re-ran the same filter: `1 passed`.

**Mutation 2 — literal rate assignment.** Added
`base_rate = 25.0  # MUTATION-2-NON-VACUITY-PROOF, reverted immediately`
to the end of `agent/settings.py` and ran
`uv run --frozen pytest tests/test_agent_job2_loop.py -q -k rate_literal_assignments`:

```
FAILED tests/test_agent_job2_loop.py::test_agent_tree_has_no_rate_literal_assignments
AssertionError: rate literal assignment found in agent/:
  settings.py:127: base_rate = 25.0
```

Reverted; re-ran the same filter: `1 passed`.

## Issues Encountered

**Concurrent multi-agent working tree (expected, per orchestrator
instructions — `isolation="none"`).** During this session, another
executor agent was simultaneously landing 07-03's work
(`agent/research_runs.py`'s `BOOT_ID`/`reclassify_interrupted_jobs`,
`app/main.py`'s lifespan hook) directly in this shared checkout. This
plan's file-ownership list correctly excludes `agent/research_runs.py`;
all `git add` calls in this session named files explicitly (never
`git add -A`/`git add .`), and `git status --short` was checked before
each commit to confirm only this plan's own files were staged. One
transient full-suite run mid-session showed unrelated failures
(`tests/test_app_job1_route.py`, then later `tests/test_agent_guardrails.py`)
caused by that other agent's in-flight, uncommitted edits to files outside
this plan's scope (`agent/job1.py`, `tests/test_agent_guardrails.py`) —
neither touched by this plan, both resolved on their own once the other
agent's work landed, and the final full-suite run (653 passed) reflects
the stable state after that.

**Repo-wide `ruff check .` / `ruff format --check .` show pre-existing,
unrelated failures.** Run without a path filter, both report violations
across ~50+ files this plan never touched (e.g.
`tests/test_jurisdiction_us_ct.py`, `tests/test_validation_pair_fixtures.py`)
— accumulated debt from before this plan, out of this plan's scope per
the executor's scope-boundary rule. Confirmed via
`uv run --frozen ruff check . | grep -E '<this plan's six files>'` and the
equivalent for `ruff format --check .`: **zero matches for either** — every
file this plan created or modified is clean under both checks when scoped
to those files directly (`uv run --frozen ruff check agent/job2.py
agent/research_schema.py agent/settings.py app/routers/research.py
tests/test_agent_job2_loop.py tests/test_agent_job2_offline.py` →
"All checks passed!"; the equivalent `ruff format --check` call →
"6 files already formatted"). Not fixed (out of scope); no
`deferred-items.md` created since no prior plan in this project uses that
convention — noted here instead for visibility.

## User Setup Required

None — no new environment variable or external service configuration is
introduced. `PARALLEL_API_KEY` and `GEMINI_API_KEY`/`GOOGLE_API_KEY`
remain the same two variables Job 1 (Phase 5) and Job 2's 07-01 tracer
already required.

## Next Phase Readiness

**D-96 call-site audit, re-confirmed after this plan's edits:**

| File:line | Call | Reachable from |
|---|---|---|
| `agent/job2.py:391` (`client.search(...)`, inside `_real_search`) | `parallel-web` Search | `agent.job2.run_job2` <- `app/routers/research.py::_start_job`'s background thread <- `POST /research` and `POST /api/v1/research` |

The line number moved from 07-01's `agent/job2.py:209` to `391` purely
because this plan added code above it (the pure refinement functions and
`TerminalReason`); reachability is unchanged — still only from the
request-handler chain, still no CLI entry point
(`tests/test_agent_job2_offline.py::test_job2_module_has_no_main_entry_point`
still passes unmodified).

**Unverified pending API keys (honestly stated, per the executor's
`api_keys_reality` contract):** neither `PARALLEL_API_KEY` nor
`GEMINI_API_KEY`/`GOOGLE_API_KEY` is set in this environment, re-checked at
both the start and end of this session (`env | grep` — no matches either
time). Every claim in this SUMMARY about the finished D-90 loop, the
closed `TerminalReason` taxonomy, the wall-clock guard, and the
no-fabricated-rate gate is proven through the offline scripted-seam suite
(`tests/test_agent_job2_loop.py`, `tests/test_agent_job2_offline.py`) —
never through a real Parallel or Gemini response. This is the same gap
07-01 named and remains open for whenever real keys are provisioned on the
Lightsail box.

**Ready for 07-03** (interrupted-job recovery, landing concurrently as
this plan was written): this plan did not touch `agent/research_runs.py`
or `app/main.py`; `run_job2`'s calls to `save_run`/`append_round` pass
plain dicts and are unaffected by 07-03's centralized `boot_id`/
`updated_at` stamping observed mid-session.

**Ready for 07-05** (pricing the researched model): the terminal record
now explicitly carries `findings` (the merged five-field snapshot),
`undetermined_disclosures` (plain-word unmet names), and — when the model
supplied one — `identity` (the `JurisdictionIdentity` dict), all directly
consumable without a record-shape change. `ruleset_path`/`priced` stay
`None` on every path this plan can reach, exactly as 07-05 will expect
before it starts writing them.

---
*Phase: 07-live-research-caching-durable-jobs*
*Completed: 2026-09-09*

## Self-Check: PASSED

All 1 created file confirmed present on disk
(`tests/test_agent_job2_loop.py`). All 3 task commit hashes confirmed in
`git log` (`a6636a6`, `f5451e9`, `0ddd814`). Full suite:
653 passed. Vendor-scan and lockfile-scan both clean.
`pyproject.toml` byte-identical to pre-plan state (`git diff --stat
pyproject.toml` — empty). `agent/job2.py`/`agent/settings.py` diffs
against the prior commit contain no leftover mutation-proof artifacts
(confirmed via `git diff --stat` immediately after each revert, before
each corresponding commit).
