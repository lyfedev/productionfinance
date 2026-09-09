---
phase: 05-curated-breadth-the-validation-loop
plan: 07
subsystem: agent
tags: [guardrails, extraction, groundedness, enactment, gemini, parallel, ny-esd]

requires:
  - phase: 05-curated-breadth-the-validation-loop
    provides: "agent/job1.py's D-82 pipeline (05-02), agent/numbers.py and agent/parallel_client.py's primary-domain filter (05-02), the /job1 route and template (05-03)"
provides:
  - "agent/groundedness.py — check_grounded, wired into agent.job1's per-award pricing loop as a mandatory keyword-only precondition"
  - "agent/enactment.py — classify_enactment, EnactmentStatus, EnactmentVerdict, persisted on Job1Run.source_enactment and rendered on /job1"
  - "tests/test_agent_guardrails.py — the standing AGT-08 gate with a registry test asserting all four guardrails have a firing test"
  - ".planning/phases/05-curated-breadth-the-validation-loop/COVERAGE.md's AGT-08 guardrails section"
affects: [phase-07-live-jurisdiction-research, phase-08-reverification-sweep]

actuals:
  tokens: 26000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Guardrail modules as pure functions over strings already in memory (agent/groundedness.py, agent/enactment.py) — no I/O, no SDK, testable without keys, matching agent/numbers.py's existing shape"
    - "Refuse-don't-guess: an unresolvable groundedness/enactment question returns a real 'ungrounded'/'unknown' verdict, never a guessed default"
    - "AGT-08 standing gate: one test module (tests/test_agent_guardrails.py) with a registry test that introspects its own function names so removing a guardrail's coverage fails loudly"

key-files:
  created:
    - agent/groundedness.py
    - agent/enactment.py
    - tests/test_agent_guardrails.py
  modified:
    - agent/job1.py
    - agent/runs.py
    - app/routers/job1.py
    - app/templates/job1_result.html
    - tests/test_agent_job1_offline.py
    - tests/test_app_job1_route.py
    - .planning/phases/05-curated-breadth-the-validation-loop/COVERAGE.md

key-decisions:
  - "Groundedness normalization loosens exact match only across case, NBSP/whitespace, and edge pipe/dash table-framing punctuation — the interior of a quote and every reported money figure must still appear character-for-character, so a fabricated number can never pass regardless of formatting"
  - "Enactment markers key on statute/bill language and URL-path shape, never on host alone, because a state legislature's own host serves both a pending bill and its own signed, chaptered text"
  - "Enactment precedence rule: when a document carries both an enactment marker and a pending-legislation marker, enacted wins (a chaptered statute routinely recites its own bill history) and BOTH marker sets are recorded on the verdict rather than the pending one being discarded"
  - "source_enactment is populated as soon as Extract returns a usable document and is never gated by run_mode — it is a property of the source document, not a priced figure, so T-05-15's live-only gate does not apply to it"
  - "Primary-government-domain and locale-aware-parsing guardrail implementations were verified against the tree and left untouched (agent/parallel_client.py, agent/numbers.py); only their missing/thin test coverage was added, and the COVERAGE.md table records this distinction explicitly rather than claiming new coverage as new implementation"

requirements-completed: [AGT-08]

coverage:
  - id: D1
    description: "Groundedness guardrail: an extracted quote and its reported money figures are checked against the source document; an ungrounded award becomes an ExtractionFailure and is never priced"
    requirement: "AGT-08"
    verification:
      - kind: unit
        ref: "tests/test_agent_guardrails.py#test_groundedness_quote_present_verbatim_is_grounded"
        status: pass
      - kind: unit
        ref: "tests/test_agent_guardrails.py#test_groundedness_quote_not_in_document_is_ungrounded"
        status: pass
      - kind: unit
        ref: "tests/test_agent_guardrails.py#test_groundedness_figure_missing_from_present_quote_is_ungrounded"
        status: pass
      - kind: integration
        ref: "tests/test_agent_guardrails.py#test_run_job1_rejects_ungrounded_award_as_extraction_failure"
        status: pass
      - kind: integration
        ref: "tests/test_agent_job1_offline.py#test_offline_loop_rejects_an_ungrounded_award_alongside_the_grounded_rows"
        status: pass
    human_judgment: false
  - id: D2
    description: "Primary-government-domain preference: run_job1 uses only a search result that passes is_primary_government_url, and terminates with no fallback when none qualify"
    requirement: "AGT-08"
    verification:
      - kind: integration
        ref: "tests/test_agent_guardrails.py#test_primary_domain_run_job1_prefers_a_government_result_over_a_higher_ranked_one"
        status: pass
      - kind: integration
        ref: "tests/test_agent_guardrails.py#test_primary_domain_run_job1_terminates_with_no_primary_source_when_none_qualify"
        status: pass
      - kind: unit
        ref: "tests/test_agent_guardrails.py#test_primary_domain_rejects_government_looking_string_in_path_not_host"
        status: pass
    human_judgment: false
  - id: D3
    description: "Locale-aware number parsing guardrail entry point: an ambiguous figure raises, both grouping conventions parse to the same Decimal"
    requirement: "AGT-08"
    verification:
      - kind: unit
        ref: "tests/test_agent_guardrails.py#test_locale_aware_parsing_ambiguous_figure_raises_rather_than_guessing"
        status: pass
      - kind: unit
        ref: "tests/test_agent_guardrails.py#test_locale_aware_parsing_both_grouping_conventions_parse_to_the_same_decimal"
        status: pass
    human_judgment: false
  - id: D4
    description: "Enactment classification: enacted, proposed, and unknown are each real reachable verdicts; both-markers-present resolves to enacted with both marker sets recorded; the verdict persists through agent/runs.py and renders on /job1"
    requirement: "AGT-08"
    verification:
      - kind: unit
        ref: "tests/test_agent_guardrails.py#test_enactment_document_with_enactment_marker_classifies_as_enacted"
        status: pass
      - kind: unit
        ref: "tests/test_agent_guardrails.py#test_enactment_document_with_pending_marker_only_classifies_as_proposed"
        status: pass
      - kind: unit
        ref: "tests/test_agent_guardrails.py#test_enactment_document_with_neither_marker_classifies_as_unknown"
        status: pass
      - kind: unit
        ref: "tests/test_agent_guardrails.py#test_enactment_document_with_both_markers_prefers_enacted_and_records_both"
        status: pass
      - kind: e2e
        ref: "tests/test_app_job1_route.py#test_get_job1_with_persisted_proposed_verdict_renders_proposed_not_enacted"
        status: pass
    human_judgment: false
  - id: D5
    description: "AGT-08 registry test: every declared guardrail identifier has at least one firing test in tests/test_agent_guardrails.py, verified by introspection"
    requirement: "AGT-08"
    verification:
      - kind: unit
        ref: "tests/test_agent_guardrails.py#test_every_guardrail_has_a_firing_test"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-09
status: complete
---

# Phase 5 Plan 07: AGT-08's Complete Guardrail Set Summary

**Two new guardrail modules (groundedness, enactment) wired onto the real Job 1 path, plus the previously-missing test coverage for two pre-existing guardrails (primary-domain preference, locale-aware parsing) — all four proven by a single standing test module that fails loudly if any coverage is ever removed.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-09T07:48Z (approx.)
- **Completed:** 2026-09-09T08:43Z
- **Tasks:** 3
- **Files modified:** 10 (3 created, 7 modified)

## Accomplishments

- `agent/groundedness.py` (new): `check_grounded` normalizes an extracted quote and the document text identically (case-fold, NBSP/whitespace collapse, edge pipe/dash stripping) and requires the quote to be a substring of the document *and* every reported money figure to be a substring of the quote. Wired into `agent/job1.py::_price_and_classify_award` as a required keyword-only `document_text` parameter — no caller can skip it. An ungrounded award becomes an `ExtractionFailure` naming the guardrail; `AccuracySummary` gains no new field (D-86 held).
- `agent/enactment.py` (new): `classify_enactment` returns a closed three-member `EnactmentStatus` (`enacted`/`proposed`/`unknown`) from named regex marker sets over statute/bill language and URL-path shape — never the host alone. Absence of both signal kinds is a real `unknown`, never a default. When both fire, `enacted` wins per a documented precedence rule and both marker sets are recorded on the verdict. Persisted on `Job1Run.source_enactment`, round-trips through `agent/runs.py` (a pre-existing run file with no `source_enactment` key loads with `None`, never raises), and renders on `/job1` beside the source document URL.
- `tests/test_agent_guardrails.py` (new): the single standing AGT-08 gate — a module docstring mapping all four clauses to implementation and test, and `test_every_guardrail_has_a_firing_test` which introspects the module's own function names to assert coverage exists for each declared guardrail identifier.
- Closed the primary-government-domain test gap: `agent.parallel_client.is_primary_government_url` and `search_for_disclosure`'s ranked-result loop had zero test references anywhere in the suite before this plan (verified by grep, not assumed). Three new tests prove the preference, the no-fallback termination, and the host-vs-path/query rejection — `agent/parallel_client.py` itself was not touched.
- `.planning/phases/05-curated-breadth-the-validation-loop/COVERAGE.md` gained an `## AGT-08 guardrails` section distinguishing the two newly-built guardrails from the two pre-existing ones, and new test coverage from inherited test coverage.

## Task Commits

Each task was committed atomically:

1. **Task 1: agent/groundedness.py — reject an extracted quote the document does not contain** - `c6ca7ad` (feat)
2. **Task 2: agent/enactment.py — classify a source as enacted law, a proposed bill, or unknown** - `24a690c` (feat)
3. **Task 3: tests/test_agent_guardrails.py — the standing AGT-08 gate, and the honest coverage record** - `0e3729a` (test)

## Files Created/Modified

- `agent/groundedness.py` - `check_grounded`/`GroundednessVerdict`; pure, dependency-free, no SDK, no I/O
- `agent/enactment.py` - `classify_enactment`/`EnactmentStatus`/`EnactmentVerdict`; pure, dependency-free, no SDK, no I/O
- `agent/job1.py` - threads `document_text` into `_price_and_classify_award`; adds `Job1Run.source_enactment` (defaulted); populates it after Extract returns a usable document; CLI `--json` output includes it
- `agent/runs.py` - serializes/deserializes `source_enactment`; a pre-existing run file with no such key loads with `None`
- `app/routers/job1.py` - `_run_render_context`/`_EMPTY_RUN_CONTEXT` carry `source_enactment` for any run that reached Extract, live or replay
- `app/templates/job1_result.html` - renders the enactment verdict beside the search-result document URL
- `tests/test_agent_guardrails.py` - the new standing AGT-08 gate (16 tests)
- `tests/test_agent_job1_offline.py` - new ungrounded-award test case proving both groundedness branches through the real offline loop
- `tests/test_app_job1_route.py` - `_fake_extract_factory` rebuilt to generate document text containing each award's `source_row_text` (see Deviations), plus a new route-level proposed-verdict test
- `.planning/phases/05-curated-breadth-the-validation-loop/COVERAGE.md` - new `## AGT-08 guardrails` section

## Decisions Made

See `key-decisions` in frontmatter. The two decisions worth calling out for a future reader:

1. **Groundedness normalization is a deliberate, narrow loosening** — it never lets a fabricated figure through. Only formatting differences (case, NBSP, whitespace runs, edge table-framing punctuation) are tolerated; the money figures themselves must still appear character-for-character inside the quote.
2. **Enactment's precedence rule favors `enacted` when both signal kinds are present, and records both marker sets** — an enacted statute's own text routinely recites its bill history, so a stray "as amended" or "introduced" phrase inside a signed, chaptered law's text must not demote it back to "proposed". The verdict makes the conflict visible rather than silently picking a side.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `tests/test_app_job1_route.py`'s fixed `_fake_extract` broke under the new groundedness guardrail**
- **Found during:** Task 2 verification (running the full guardrails + route + offline test set)
- **Issue:** The route-test module's `_fake_extract` always returned the literal string `"test-double-markdown, not a real government document"` regardless of which awards were being priced. Once `_price_and_classify_award` started checking `source_row_text` and money figures against the document text (Task 1), every route-test award became ungrounded, and `test_get_job1_with_persisted_live_run_shows_bucket_counts_and_every_award` started failing (`exact_match` dropped from 1 to 0 because the award was rejected before pricing).
- **Fix:** Replaced the fixed `_fake_extract` with `_fake_extract_factory(awards)`, which builds document text from the `source_row_text` of whatever award list is being tested — the same pattern `tests/test_agent_job1_offline.py` already used for its committed fixture file. `_build_run` now calls the factory per award list instead of a single shared fake.
- **Files modified:** tests/test_app_job1_route.py
- **Verification:** Full `tests/test_agent_guardrails.py tests/test_app_job1_route.py tests/test_agent_job1_offline.py` run green (33 passed) after the fix; full suite green afterward.
- **Committed in:** 24a690c (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — a pre-existing test fixture broken by the new, correctly-firing groundedness check).
**Impact on plan:** Necessary correctness fix, not scope creep — the guardrail was doing exactly what it should; the test double needed to catch up.

### Note on the plan's verified-state table

The plan's pre-execution state table was re-verified against the tree before writing any code (grep for `is_primary_government_url`/`search_for_disclosure` and `groundedness`/`enactment` across `tests/` and `agent/`) and found accurate: groundedness absent, primary-domain preference implemented with zero test references, locale-aware parsing implemented and fully tested, enactment absent. No correction to the plan's own claims was needed.

The plan anticipated the committed offline fixture (`tests/fixtures/agent/esd_excerpt_double.md`) might need correction once groundedness landed. It did not — all five of its rows were already grounded verbatim against the real fake awards once checked. The fixture that actually needed correction was the *other* test module's fixed, unrelated document string in `tests/test_app_job1_route.py`, discovered only by running the full verification set (documented above).

## Issues Encountered

None beyond the one deviation documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- AGT-08 is fully satisfied: all four guardrails enforced on the real Job 1 path, each proven by a firing test, and the registry test (`test_every_guardrail_has_a_firing_test`) prevents silent regression.
- `agent/groundedness.py` and `agent/enactment.py` are pure, dependency-free modules — reusable as-is by Phase 7's live-research path (Job 2) without modification, should that path also want to check groundedness or enactment status on its own extracted documents.
- No blockers. Full suite green (well past the pre-plan baseline of 578, now including this plan's 20 net new tests plus concurrent work from sibling plans), both CI scan scripts exit 0, pinned golden totals (NY $758,427 / LA $693,521 / London £548,595 / gap $64,906) and the route-A honesty gate unchanged.

---
*Phase: 05-curated-breadth-the-validation-loop*
*Completed: 2026-09-09*

## Self-Check: PASSED

- `agent/groundedness.py` — FOUND
- `agent/enactment.py` — FOUND
- `tests/test_agent_guardrails.py` — FOUND
- `.planning/phases/05-curated-breadth-the-validation-loop/05-07-SUMMARY.md` — FOUND
- Commit `c6ca7ad` (Task 1) — FOUND in `git log`
- Commit `24a690c` (Task 2) — FOUND in `git log`
- Commit `0e3729a` (Task 3) — FOUND in `git log`
- Full suite: 653 passed, 0 failed
- `bash .github/scripts/vendor-scan.sh` — PASS
- `bash .github/scripts/lockfile-scan.sh` — PASS
- `git diff --stat -- engine/` — empty
- `tests/test_golden_cost.py tests/test_route_a_basis_walk.py` — 9 passed
- `uv run python -m agent.job1 --limit 1` with no keys — prints not-configured message naming both variables, exits 0
