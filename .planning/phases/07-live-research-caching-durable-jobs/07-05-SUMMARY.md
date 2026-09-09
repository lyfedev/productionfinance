---
phase: 07-live-research-caching-durable-jobs
plan: 05
subsystem: agent
tags: [pydantic, pyyaml, engine-pipeline, ast-gate, jinja2]

requires:
  - phase: 07-live-research-caching-durable-jobs
    provides: "07-01's agent/job2.py D-90 loop and ResearchRun record shape
      (findings/undetermined_disclosures/ruleset_path/priced already
      declared, None until this plan); 07-02's merge_findings/
      TerminalReason closed taxonomy and JurisdictionIdentity; 07-03's
      durable research_runs.py persistence; 07-04's cache_policy.py
      (unrelated, untouched by this plan)."
provides:
  - "agent/rule_coercion.py — build_rule_document/write_rule_file/
    UNDETERMINED_NEUTRAL_DEFAULTS/apply_neutral_defaults/
    neutral_default_disclosures/serialize_priced_jurisdiction — the D-91
    findings-to-schema coercion layer, importing NOTHING from engine/"
  - "agent/job2.py::_attempt_coercion_and_pricing — wires the sufficient
    path through engine.models.load_ruleset ->
    engine.pipeline.price_jurisdiction, the identical loader and pricing
    call a curated jurisdiction goes through (AGT-07)"
  - "agent/job2.py::TerminalReason gains pricing_refused and
    rule_schema_violation (nine -> eleven members, closed-set addition)"
  - "app/templates/research_result.html — the unvalidated banner above
    the priced figure, the priced-programme table, the 'what was not
    determined' disclosure list, and the pricing_refused refusal message"
affects: [07-06]

actuals:
  tokens: 16515
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "engine-import quarantine: agent/rule_coercion.py imports nothing
      from engine/ at all — it only ever produces a plain dict handed to
      yaml.safe_dump. agent/job2.py is the sole caller of
      engine.models.load_ruleset / engine.pipeline.price_jurisdiction,
      keeping every engine import inside the one file the existing
      two-name AST gate (tests/test_agent_job1_offline.py) already
      covers. Figure/PricedJurisdiction serialization is duck-typed
      (serialize_priced_jurisdiction reads plain attributes) rather than
      importing engine.figure_serialize.figure_to_dict, which is NOT one
      of the two sanctioned names."
    - "Refuse rather than guess, at every classification step: rate
      extraction accepts exactly one percentage figure in a finding's
      text (zero or two-plus is a refusal, never a first-match pick);
      qualifying-base/mechanism classification is keyword-based with no
      default fallback (an unclassifiable finding refuses); a caps
      finding must either name an extractable money figure or say
      explicitly 'uncapped' — anything else refuses rather than silently
      modeling no cap."
    - "UNDETERMINED_NEUTRAL_DEFAULTS as a closed table, not scattered
      inline defaults: each of the four schema-required-but-D-91-uncovered
      fields (taxable, audit.mandatory, per_person_ceiling.applies,
      timing.terms_lock_at) has one entry naming its neutral value and its
      exact disclosure sentence. apply_neutral_defaults(overrides) lets a
      genuinely-determined value (detected from the finding text) skip its
      own disclosure — proven at the unit level that a run needing no
      default returns an empty disclosure list, independent of whether the
      live SufficiencyVerdict schema can realistically supply every
      override in practice."
    - "Optional-spend graceful skip, not a refusal: a sufficient run with
      no qualified_spend_input still writes and loads the ruleset (a
      disclosed, priced-nothing outcome), and only a NON-EMPTY unparseable
      spend string triggers rule_schema_violation — this preserves every
      pre-existing 07-01/07-02 test that calls run_job2(city, None, ...)
      and asserts terminal_reason == 'sufficient'."

key-files:
  created:
    - agent/rule_coercion.py
    - tests/test_agent_job2_coercion.py
  modified:
    - agent/job2.py
    - app/templates/research_result.html
    - tests/test_agent_job2_loop.py
    - tests/test_agent_job2_offline.py

key-decisions:
  - "Money-parse failure and rule-schema-validation failure share the
    SAME TerminalReason member (rule_schema_violation), each with its own
    distinct message. The plan's Task 2 names 'three distinct terminal
    reasons, three distinct sentences' but its own enum-extension
    instruction adds only two new members — reconciled by reading
    'reasons' as three distinct refusal SCENARIOS/sentences over two
    enum values, not three enum values. Both are genuinely 'the priced
    document could not be produced from what we have', which is the
    substance rule_schema_violation names."
  - "A visitor who submits no qualified spend on an otherwise-sufficient
    run is NOT a refusal — the ruleset is still built, written, and
    loaded (ruleset_path set), pricing is simply skipped with its own
    disclosure sentence, and terminal_reason stays 'sufficient'. Treating
    a missing (optional, per the form) input as unparseable would have
    flipped every pre-existing 07-01/07-02 'sufficient' test (all of
    which call run_job2 with qualified_spend_input=None) to
    rule_schema_violation."
  - "'the gross credit the engine did compute, if it got that far' (the
    plan's Task 2 behavior text for the pricing_refused page) could not
    be implemented: engine.pipeline.price_jurisdiction either returns a
    complete PricedJurisdiction or raises before returning anything
    partial, and reaching into price_programme's intermediate qualifying-
    base/gross-credit state would require a THIRD engine import this
    plan's own AST gate forbids. The pricing_refused page instead shows
    every determined D-91 finding plus the engine's own refusal message
    verbatim — informative without a numeric gross-credit figure. Not a
    fabrication risk either way: nothing is invented, something the plan
    conditionally allowed ('if it got that far') is honestly absent."
  - "The rate/base-definition/mechanism classifiers are keyword-based,
    not a second LLM call — deliberately narrow, deterministic, and
    refuse-first. This is a genuine, disclosed scope simplification: a
    tiered rate description (two-or-more percentages in one finding)
    refuses rather than attempts to reconstruct tier boundaries, since
    guessing which percentage applies to which spend band would be
    exactly the fabrication D-94 forbids."

patterns-established:
  - "Coercion module quarantine: any future findings-to-schema mapping
    for a different Job-2-shaped agent should mirror rule_coercion.py's
    zero-engine-import discipline, keeping the engine-touching call sites
    inside the one module the AST gate already audits."

requirements-completed: [AGT-07, AGT-05]

coverage:
  - id: D1
    description: "A live-researched jurisdiction is written in the curated schema and read back through the identical engine.models.load_ruleset a curated file uses (AGT-07)"
    requirement: "AGT-07"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_build_rule_document_round_trips_through_load_ruleset"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_document_matches_the_curated_shape_key_for_key"
        status: pass
      - kind: other
        ref: "manual read of an emitted var/job2/*.ruleset.yaml against jurisdictions/us-ny.yaml (recorded below)"
        status: pass
    human_judgment: false
  - id: D2
    description: "No second pricing path exists — agent/ still imports exactly two names from engine/, and agent/rule_coercion.py imports zero"
    requirement: "AGT-07"
    verification:
      - kind: unit
        ref: "tests/test_agent_job1_offline.py#test_agent_imports_nothing_from_engine_except_the_two_sanctioned_names"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every Figure in a live-researched priced tree is confidence: researched, never validated, and the page carries the unvalidated banner above the figure"
    requirement: "AGT-07"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_every_figure_in_a_sufficient_priced_run_is_researched_never_validated"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_source_confidence_is_never_conflated_with_figure_confidence"
        status: pass
      - kind: integration
        ref: "tests/test_agent_job2_coercion.py#test_disclosure_sentences_and_unvalidated_banner_render_on_the_page"
        status: pass
    human_judgment: false
  - id: D4
    description: "No rate is ever a literal in agent/rule_coercion.py, and UNDETERMINED_NEUTRAL_DEFAULTS carries no rate-bearing entry — the no-fabricated-rate AST gate"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_rule_coercion_has_no_rate_literal_dict_values"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_undetermined_neutral_defaults_has_no_rate_bearing_entry"
        status: pass
    human_judgment: true
    rationale: "The gate itself is a passing automated test, but its non-vacuity was proven by a manual mutate-observe-revert cycle during this session, not by a permanent test — see the transcript below. A human should confirm that written record matches this session's actual terminal output."
  - id: D5
    description: "An engine refusal (transferable with no sourced discount range) becomes the pricing_refused terminal state carrying the engine's own message, never a crash or an invented discount"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_transferable_with_no_discount_range_ends_in_pricing_refused"
        status: pass
      - kind: integration
        ref: "tests/test_agent_job2_coercion.py#test_pricing_refused_page_states_the_refusal_plainly"
        status: pass
    human_judgment: false
  - id: D6
    description: "A schema-invalid coerced document, and an unparseable qualified-spend string, each end in a durable rule_schema_violation record naming the raw string/error text — never coerced to a number, never a crash"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_unparseable_qualified_spend_ends_in_rule_schema_violation_never_coerced_to_a_number"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_a_document_that_fails_schema_validation_reports_the_validation_error_text"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_ambiguous_rate_ends_in_rule_schema_violation_with_no_ruleset_written"
        status: pass
    human_judgment: false
  - id: D7
    description: "The researched city is genuinely priced when a spend figure is supplied (AGT-05), and pricing is gracefully skipped (never refused) when it is not"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_sufficient_run_with_spend_input_is_priced_through_price_jurisdiction"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_sufficient_run_with_no_spend_input_writes_the_ruleset_but_skips_pricing"
        status: pass
    human_judgment: false
  - id: D8
    description: "AGT-06 holds through this plan: a no_programme_found run writes no rule file and prices nothing"
    requirement: "AGT-05"
    verification:
      - kind: unit
        ref: "tests/test_agent_job2_coercion.py#test_no_programme_found_still_writes_no_ruleset_file"
        status: pass
    human_judgment: false
  - id: D9
    description: "Full regression suite green (745 passed), golden totals and Route A basis walk unchanged, vendor/lockfile scans clean, engine/ untouched by this plan"
    requirement: "AGT-07"
    verification:
      - kind: other
        ref: "uv run --frozen pytest -q -> 745 passed"
        status: pass
      - kind: other
        ref: "uv run --frozen pytest tests/test_golden_cost.py tests/test_route_a_basis_walk.py tests/test_agent_job2_loop.py -q -> 43 passed"
        status: pass
      - kind: other
        ref: "bash .github/scripts/vendor-scan.sh; bash .github/scripts/lockfile-scan.sh"
        status: pass
      - kind: other
        ref: "git diff --stat -- engine/ (empty)"
        status: pass
    human_judgment: false

duration: 65min
completed: 2026-09-09
status: complete
---

# Phase 7 Plan 5: Coercing Live Research into the Curated Schema Summary

**A live-researched jurisdiction is written as a plain dict, loaded through the identical `engine.models.load_ruleset` `jurisdictions/us-ny.yaml` goes through, and priced through the identical `engine.pipeline.price_jurisdiction` — with no rate ever hardcoded, every undetermined supporting field named in a disclosure sentence, and the engine's own refusals (a transferable programme with no sourced discount range) rendered as a legible `pricing_refused` page instead of a crash.**

## Performance

- **Duration:** 65 min
- **Started:** 2026-09-09T09:05:00Z (approx.)
- **Completed:** 2026-09-09T10:10:00Z (approx.)
- **Tasks:** 3
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- **`agent/rule_coercion.py`** turns Job 2's merged, sourced D-91 findings
  into a plain `dict` in `engine.models.JurisdictionRuleSet` shape.
  `build_rule_document` maps rate (a single extracted percentage — two or
  more percentages in one finding refuses rather than guessing which
  applies), qualifying-base definition (keyword classification into the
  four schema literals), caps (an extracted money figure or an explicit
  "uncapped" statement — anything else refuses), payout mechanism (keyword
  classification into the four schema mechanisms, plus a `days` extraction
  for the payout lag), and current availability (into
  `caps.cap_consumption_check` and the effective-dates block). This module
  imports **nothing** from `engine/` — not even the two sanctioned names —
  so it structurally cannot reach the engine any way other than through
  the plain dict it produces.
- **`UNDETERMINED_NEUTRAL_DEFAULTS`** is the closed table for the four
  schema-required fields D-91's five sufficiency fields do not cover
  (`taxable`, `audit.mandatory`, `per_person_ceiling.applies`,
  `timing.terms_lock_at`). Each entry carries its neutral value and its
  exact disclosure sentence naming which direction the true figure would
  move. `apply_neutral_defaults`/`neutral_default_disclosures` let a
  genuinely-determined value (a finding text explicitly stating "subject
  to corporation tax" or "mandatory ... audit") skip its own disclosure —
  proven at the unit level that a fully-overridden call returns zero
  disclosures.
- **`agent/job2.py::_attempt_coercion_and_pricing`** wires the coercion
  onto the `sufficient` terminal path only: `build_rule_document ->
  write_rule_file -> engine.models.load_ruleset ->
  engine.pipeline.price_jurisdiction(spend_confidence="researched")`. A
  visitor who supplied no qualified spend still gets a written, loaded
  ruleset with pricing gracefully skipped (disclosed, not refused). Every
  unexpected exception is caught at the call site and turned into a
  durable `rule_schema_violation` record rather than crashing the
  background thread.
- **`TerminalReason` grows from nine to eleven members**:
  `pricing_refused` (the engine's own `ValueError` — e.g.
  `engine.net_cash.transferable`'s refusal to convert at an unsourced
  discount range) and `rule_schema_violation` (a `pydantic.ValidationError`
  from `load_ruleset`, an internal coercion refusal, or an unparseable
  non-empty qualified-spend string). `no_programme_found` and every other
  non-`sufficient` path is unaffected — still constructs and prices
  nothing (AGT-06).
- **`app/templates/research_result.html`** renders the unvalidated banner
  directly above the priced figure (never a footer), the full
  priced-programme table (qualifying base, gross credit, net cash
  point-or-range, eligibility, availability), the "what was not
  determined by research" disclosure list, and the `pricing_refused`
  refusal message — all read straight off the record dict already on
  disk, no new field invented in `app/routers/research.py`.
- **`tests/test_agent_job2_coercion.py`** (25 tests) is the new standing
  gate: round-trip proof through the curated loader; every refusal
  behaviorally driven through the real `run_job2` loop (not mocked at the
  coercion layer); a recursive Figure-tree walk proving every node in a
  priced live-researched run is `researched`, never `validated`; and an
  AST scan proving no numeric literal is ever assigned to a rate-bearing
  schema key anywhere in `agent/rule_coercion.py`.

## Task Commits

Each task was committed atomically:

1. **Tasks 1+2 (combined — see Deviations): findings coerced into the curated schema, priced through the curated engine, with refusals as terminal states** — `2f5427e` (feat)
2. **Task 3: unvalidated labelling, the no-fabricated-rate gate, and coercion coverage** — `ef124e8` (test)

**Plan metadata:** committed alongside this SUMMARY.

## Files Created/Modified

- `agent/rule_coercion.py` — the findings-to-schema coercion layer, zero `engine/` imports
- `agent/job2.py` — `_attempt_coercion_and_pricing`, the eleven-member `TerminalReason`, `_write_terminal`'s new `ruleset_path`/`priced`/`extra_disclosures` parameters
- `app/templates/research_result.html` — unvalidated banner, priced-programme table, disclosure list, `pricing_refused` message
- `tests/test_agent_job2_coercion.py` — the new standing gate (25 tests)
- `tests/test_agent_job2_loop.py` — realistic coercible `value_text` in `_all_determined_findings`; the closed-set assertion renamed to eleven members (deviation, see below)
- `tests/test_agent_job2_offline.py` — realistic coercible `value_text` in `_scripted_seams`'s "sufficient" branch (deviation, see below)

## Decisions Made

See `key-decisions` in frontmatter. In short: money-parse failure and
schema-validation failure share `rule_schema_violation` (two enum members
serve three named refusal scenarios, reconciling the plan's "three
distinct terminal reasons" prose with its own "extend with two members"
instruction); a missing (not malformed) qualified-spend input is a
graceful skip, never a refusal, to preserve every pre-existing
`qualified_spend_input=None` test; "the gross credit the engine did
compute, if it got that far" could not be surfaced on a `pricing_refused`
page without a third engine import the plan's own AST gate forbids, so
the page shows the determined findings and the engine's verbatim message
instead; and the classifiers are deliberately narrow keyword matchers
that refuse on ambiguity (e.g. a tiered rate description) rather than
guess.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Compatibility] Task 1 and Task 2 landed in a single combined commit rather than two**
- **Found during:** implementing Task 2's refusal handling
- **Issue:** Task 1's happy path and Task 2's three refusals all live
  inside the same `_attempt_coercion_and_pricing` function in
  `agent/job2.py` — the refusal branches read the exact document/ruleset
  state Task 1's happy path builds at each step. Splitting into two
  sequential edits would have meant writing a Task-1-only version that
  never handles a refusal, then immediately rewriting the same function
  body for Task 2 — the identical precedent 07-02-SUMMARY.md documents
  for its own Task 1+2 combination.
- **Fix:** Wrote both tasks' code as one coherent change, verified against
  both tasks' `<verify>` filters before committing.
- **Files modified:** `agent/rule_coercion.py`, `agent/job2.py`
- **Verification:** `uv run --frozen pytest tests/test_agent_job2_coercion.py -q -k "document or load or defaults"` and `-k "refus or violation or spend"` both pass in isolation; full suite green at commit time.
- **Commit:** `2f5427e`

**2. [Rule 1 - Bug] Updated `tests/test_agent_job2_loop.py` and `tests/test_agent_job2_offline.py`'s "sufficient" fixtures to realistic, coercible text**
- **Found during:** first full-suite run after wiring coercion into the `sufficient` path
- **Issue:** Both pre-existing fixtures used generic placeholder
  `value_text` (`f"value-{f.value}"`) for all five D-91 fields. Since a
  `sufficient` run now also runs through `agent.rule_coercion
  .build_rule_document`, this placeholder text failed every classifier
  (no percentage, no keyword match), flipping `terminal_reason` away
  from `"sufficient"` in tests that predate and do not concern this
  plan.
- **Fix:** Replaced the placeholder text with realistic, coercible
  sentences per field (a 25% rebate, total qualified production spend, a
  $10M annual cap, a refundable credit paid within 90 days, currently
  active) in both fixtures; renamed and updated the closed-set
  `TerminalReason` assertion from nine to eleven members. Mirrors
  07-02-SUMMARY.md's own documented precedent of updating 07-01's
  fixture when its new checks required it.
- **Files modified:** `tests/test_agent_job2_loop.py`, `tests/test_agent_job2_offline.py`
- **Verification:** `uv run --frozen pytest tests/test_agent_job2_loop.py tests/test_agent_job2_offline.py tests/test_agent_job2_durability.py tests/test_agent_job1_offline.py -q` — 84 passed.
- **Commit:** `ef124e8`

**3. [Rule 1 - Lint] 8 new FURB157 (verbose `Decimal("N")` constructor) findings in `_SCALE_MULTIPLIERS`**
- **Found during:** final `ruff check` pass
- **Issue:** `agent/rule_coercion.py`'s money-scale multiplier table
  (`"million": Decimal("1000000")`, etc.) triggers ruff's
  verbose-Decimal-constructor rule — the same established RD-01
  quoted-Decimal convention already present hundreds of times across
  `engine/`/`tests/` (WINDOWS entries 2, 4, 5, 11, 14, 17, 23, 24, 25,
  27, 29, 30 document the identical accepted pattern in every prior
  phase).
- **Fix:** Not fixed — out of scope per the executor's scope-boundary
  rule and this repo's own established precedent (using a bare int
  literal for a `Decimal` constructor argument is exactly the pattern
  RD-01's quoted-string convention exists to avoid elsewhere in the
  codebase; ruff's rule and this project's own documented convention
  disagree, and every prior phase has resolved that disagreement the
  same way). Recorded on the ledger instead.
- **Files modified:** none (recorded, not fixed)
- **Verification:** `uv run --frozen ruff check agent/rule_coercion.py --statistics` → `8 FURB157`
- **Ledger:** `.planning/WINDOWS.md` entry 33 (`gsd-tools windows append --kind lint-warning`)

---

**Total deviations:** 3 (1 Rule 1 commit-structure compatibility, 1 Rule 1 fixture-compatibility fix, 1 Rule 1 lint-warning recorded on the ledger).
**Impact on plan:** No scope creep. Deviations 1-2 were required for the plan's own `<verification>` block ("full suite green") to hold; deviation 3 is cosmetic and matches this repo's own established precedent for the identical rule-vs-convention disagreement.

## Non-vacuity mutation performed (Task 3, recorded per plan instruction)

Performed by hand against the real `agent/rule_coercion.py`, observed to
fail the gate, then reverted — never committed (confirmed via `git diff
--stat agent/rule_coercion.py` showing empty immediately before the Task
3 commit).

**Mutation — literal rate assignment inside a dict.** Inserted
`_MUTATION_NON_VACUITY_PROOF = {"base_rate": 25.0}  # temporary, reverted immediately`
immediately above `build_rule_document` and ran
`uv run --frozen pytest tests/test_agent_job2_coercion.py -q -k rate_literal`:

```
FAILED tests/test_agent_job2_coercion.py::test_rule_coercion_has_no_rate_literal_dict_values
AssertionError: rate-bearing literal found in agent/rule_coercion.py:
  rule_coercion.py:350: 'base_rate' = 25.0
```

Reverted (removed the inserted line); re-ran the same filter:
`1 passed, 24 deselected`.

## Manual read: an emitted `var/job2/*.ruleset.yaml` against `jurisdictions/us-ny.yaml`

Generated one real document from scripted findings (`agent/rule_coercion.build_rule_document` -> `write_rule_file`) and read it back. Same top-level keys (`jurisdiction`, `programmes`), same nested shape, every numeric value a quoted YAML string (`base_rate: '0.2'`, `caps.annual_programme_cap.amount.value: '50000000'`), `jurisdiction.status: live_researched` where `us-ny.yaml` declares `curated_validated`. File removed after inspection (it lives under gitignored `var/job2/`, never committed).

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no new environment variable or external service configuration is
introduced. `PARALLEL_API_KEY` and `GEMINI_API_KEY`/`GOOGLE_API_KEY`
remain unset in this environment (re-verified at the start and end of
this session via `env | grep` and a check for `/opt/prodfin/.env`) — this
plan's own tests never exercise a live SDK call, exactly as required;
they run entirely through `run_job2`'s injectable `search_fn`/`judge_fn`
seams.

## Next Phase Readiness

**D-96 call-site audit:** unchanged by this plan. No new
`parallel-web`/`google-genai` call site was added — `agent/rule_coercion
.py` and this plan's changes to `agent/job2.py` touch only the pure
findings-to-schema-to-pricing path (`yaml.safe_dump`, `engine.models
.load_ruleset`, `engine.pipeline.price_jurisdiction`), none of which are
SDK calls. 07-02's audit table (`agent/job2.py:391`, reachable only from
`POST /research`'s background thread) remains the complete and current
record.

**Ready for 07-06:** the researched jurisdiction now flows all the way to
a rendered, labelled, priced (or honestly refused/skipped) page. Nothing
in this plan's record shape needs to change for any subsequent plan to
consume `record["priced"]`/`record["ruleset_path"]`/
`record["undetermined_disclosures"]` — all three are already the final
shape 07-01/07-02 declared.

---
*Phase: 07-live-research-caching-durable-jobs*
*Completed: 2026-09-09*

## Self-Check: PASSED

Both created files confirmed present on disk (`agent/rule_coercion.py`,
`tests/test_agent_job2_coercion.py`). Both task commit hashes confirmed
in `git log` (`2f5427e`, `ef124e8`). Full suite: 745 passed (up from the
720-passing baseline; 25 net new tests, matching
`tests/test_agent_job2_coercion.py`'s own count). Golden totals
(`tests/test_golden_cost.py`, 6 tests) and the Route A basis walk
(`tests/test_route_a_basis_walk.py`, 3 tests) unchanged and passing.
`vendor-scan.sh` and `lockfile-scan.sh` both clean. `git diff --stat --
engine/` empty. The non-vacuity mutation was performed, observed failing,
and confirmed reverted before the Task 3 commit.
