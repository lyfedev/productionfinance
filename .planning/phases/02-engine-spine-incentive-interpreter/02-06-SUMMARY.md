---
phase: 02-engine-spine-incentive-interpreter
plan: 06
subsystem: engine
tags: [decimal, incentive-engine, stacking, mutual-exclusivity, caps, availability, eligibility, additivity, jur-05]

requires:
  - phase: 02-engine-spine-incentive-interpreter
    provides: >
      02-01's engine spine (Figure, JurisdictionRuleSet schema, the
      five-step CreditCalculator sequence with uplift-stacking, per-project
      cap, and annual-cap steps stubbed as no-ops/NotImplementedError) and
      02-05's per-person-ceiling/tier/blend rate dispatch, which this
      plan's steps run immediately after in the same ordered sequence.
provides:
  - "engine/credit.py — _apply_uplift_stacking (data-ordered, within-programme additive rate), _apply_per_project_cap (strictly-greater-than clip), assess_eligibility and assess_availability (two independent functions, three-state availability)"
  - "engine/pipeline.py — _resolve_mutual_exclusivity and _grinding_clause_lines (multi-programme summation of independent dollar outputs, never rates)"
  - "tests/fixtures/jurisdictions/synthetic-stacking.yaml — national + regional stacking over genuinely different bases, a two-uplift ordering fixture, a mutually-exclusive third programme"
  - "tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml — the JUR-05 additivity proof jurisdiction, zero-line engine diff"
  - "tests/test_engine_jurisdiction_additivity.py — the pricing, no-jurisdiction-specific-code, and concurrency/purity assertions"
  - "jurisdictions/SCOPE-FREEZE.md — RD-06 (checkpoint decision) and dimensions 4-6 marked landed"
affects: [03-new-york-end-to-end]

actuals:
  tokens: 21301
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Within-programme uplift stacking reads order from the rule file's own uplifts list (a stackable uplift always adds; a non-stackable uplift only adds if nothing has applied yet), proven by a fixture test that swaps two declared entries and asserts the resulting credit changes — never a code branch on position"
    - "Cross-programme stacking sums only the final dollar Figures each programme independently produces (_contribution_figure), never their rates — mutual exclusivity is resolved once, before summation, over that same set of dollar figures"
    - "Availability and eligibility are two independently-callable functions (assess_availability, assess_eligibility) returning two independently-read dataclass fields on PricedProgramme — no code path fuses them into one boolean"
    - "The no-jurisdiction-specific-code proof collects jurisdiction identifiers by globbing both rule-file directories at test time (never a hard-coded list), so a jurisdiction added in a later phase is automatically covered without touching this test"

key-files:
  created:
    - tests/fixtures/jurisdictions/synthetic-stacking.yaml
    - tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml
    - tests/test_engine_jurisdiction_additivity.py
  modified:
    - engine/credit.py
    - engine/pipeline.py
    - tests/test_engine_credit.py
    - jurisdictions/SCOPE-FREEZE.md

key-decisions:
  - "Checkpoint decision (programmes-in-one-file vs. separate-files-parent-id), answered by the human 2026-08-25: programmes-in-one-file. A regional programme that stacks on a national one lives as an additional entry in the SAME jurisdiction file's programmes list, never as a separate file linked by jurisdiction.parent_id. Stacking edges resolve WITHIN one file; the engine performs no cross-file resolution step. Recorded as RD-06 in jurisdictions/SCOPE-FREEZE.md with the rejected alternative and its undo cost."
  - "Resumed from an uncommitted, session-interrupted state: a prior executor had written engine/credit.py and engine/pipeline.py's full Task 1+2 implementation but no tests, before being killed by a transient stream error. That implementation was read in full and judged on its merits before being kept — verified line-by-line that stacking sums dollar Figures (never rates), that eligibility and availability are genuinely two separate functions/fields, and that the per-project/annual-cap distinction (RD-04) holds. No corrections were needed; the implementation was sound as found."
  - "Tasks 1 and 2 committed together (9a5bde8), not as two separate commits — both extend the same ordered adjustment sequence in engine/credit.py (compute_gross_credit's steps) and the same engine/pipeline.py call sites in ways that are not cleanly separable into non-overlapping git hunks without risking a broken intermediate commit. This mirrors 02-05's own precedent for the identical reason. Task 3 (7ad2e83) is a fully independent commit, touching zero engine/ files."
  - "The stacking fixture's mutual-exclusivity pair was deliberately designed so the SMALLER-contributing programme (third-exclusive) is the one excluded and the two genuinely-stacking programmes (national-base, regional-topup) both remain contributing — an earlier draft had third-exclusive's rate larger than regional-topup's, which would have excluded the very programme the stacking test needed to exercise the grinding-clause and dollar-summation checks against. Caught before committing by hand-verifying the fixture's own numbers against price_jurisdiction's actual output."
  - "TDD gate note: both Task 1 and Task 2 carry tdd=\"true\" in the plan, but the implementation predated the tests in this session (inherited from the interrupted prior executor, not written by this one). A strict RED phase — a failing test committed before the implementation exists — could not be reconstructed without stashing ~460 lines of already-reviewed, sound work, which the continuation instructions explicitly prohibited. See '## TDD Gate Compliance' below for the full accounting: every test was verified to assert real, discriminating behavior (explicit wrong-value negative assertions per the plan's own acceptance criteria) even though the formal RED commit is absent."

patterns-established:
  - "_resolve_mutual_exclusivity/_grinding_clause_lines (engine/pipeline.py): frozenset-deduplicated pairwise resolution over declared edges, run once before summation, each emitting a derivation line naming both the taken and untaken/considered programme — never a silent drop"
  - "_qualifying_base_figure / _make_jurisdiction_ruleset (tests/test_engine_credit.py): in-memory Figure and JurisdictionRuleSet constructors for tests that need an exact, hand-picked base value or a varying programme count, without maintaining N separate committed YAML fixtures"

requirements-completed: [INC-03, INC-04, INC-05, JUR-05]

coverage:
  - id: D1
    description: "Within-programme uplift stacking applies uplifts in declared order (data, not a code branch) — a stackable uplift always adds, a non-stackable uplift only if nothing has applied yet — proven by swapping two declared entries and asserting the credit changes"
    requirement: "INC-03"
    verification:
      - kind: unit
        ref: "tests/test_engine_credit.py::test_tier_dispatch_and_stacking (uplift-ordering section)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Cross-programme stacking sums independent dollar outputs computed against each programme's own (possibly different) base, never rates — the wrong summed-rates figure is computed explicitly and asserted not equal to the engine's result"
    requirement: "INC-03"
    verification:
      - kind: unit
        ref: "tests/test_engine_credit.py::test_stacking_sums_dollars_not_rates_and_resolves_mutual_exclusivity"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_stacking_prices_every_declared_programme (N=1,2,3 parametrized)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Two mutually-exclusive programmes contribute exactly one figure to the jurisdiction total; the derivation names both the taken and the untaken programme and its figure — never a silent drop"
    requirement: "INC-03"
    verification:
      - kind: unit
        ref: "tests/test_engine_credit.py::test_stacking_sums_dollars_not_rates_and_resolves_mutual_exclusivity"
        status: pass
    human_judgment: false
  - id: D4
    description: "A per-project cap clips the credit at min(credit, cap), strictly-greater-than at the boundary (a credit exactly at the cap is not clipped); where a per-project and an annual programme cap are both declared, only the per-project cap clips and both emit their own derivation line"
    requirement: "INC-04"
    verification:
      - kind: unit
        ref: "tests/test_engine_credit.py::test_cap_boundaries (3 parametrized boundary cases)"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_cap_boundaries_no_cap_declared_emits_noop"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_per_project_and_annual_cap_both_declared_only_per_project_clips"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_annual_cap_remaining_parameter_never_changes_credit"
        status: pass
    human_judgment: false
  - id: D5
    description: "Eligibility and availability are two independently-computed answers, never fused: an eligible-but-exhausted production reports eligible=True and available=False as two separate field reads; an unfetched consumption figure yields available=None with a stated reason, never defaulted to True; an ineligible production still gets a fully-computed availability answer"
    requirement: "INC-05"
    verification:
      - kind: unit
        ref: "tests/test_engine_credit.py::test_availability_three_state"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_availability_separate_from_eligibility"
        status: pass
    human_judgment: false
  - id: D6
    description: "A jurisdiction the engine has never seen (tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml — sharing no base_definition.type, rate_structure.type, mechanism, or currency with either curated file) prices correctly on the first try against hand-computed literal values, with a commit that touches zero files under engine/"
    requirement: "JUR-05"
    verification:
      - kind: unit
        ref: "tests/test_engine_jurisdiction_additivity.py::test_zz_fixture_throwaway_prices_correctly_against_hand_computed_values"
        status: pass
      - kind: unit
        ref: "tests/test_engine_jurisdiction_additivity.py::test_no_jurisdiction_identifier_appears_in_engine_source"
        status: pass
      - kind: unit
        ref: "tests/test_engine_jurisdiction_additivity.py::test_pricing_two_jurisdictions_in_one_process_does_not_cross_contaminate"
        status: pass
      - kind: other
        ref: "git diff --name-only HEAD~1 HEAD | grep -c '^engine/' against commit 7ad2e83 -> 0 (recorded verbatim below)"
        status: pass
    human_judgment: false

duration: 50min
completed: 2026-08-25
status: complete
---

# Phase 2 Plan 06: Stacking, Caps, Availability, and the Additivity Proof Summary

**National-plus-regional stacking sums independent dollar Figures (never rates) across N declared programmes, per-project caps clip at a strictly-greater-than boundary while annual caps never touch the credit, eligibility and availability land as two genuinely separate answers, and a jurisdiction the engine has never seen prices correctly with a zero-line diff to any engine/*.py file.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3 (Task 1 stacking, Task 2 caps/availability — committed
  together per necessity; Task 3 additivity — independent commit)
- **Files modified:** 7 (3 created, 4 modified)

## Accomplishments

- `engine/credit.py::_apply_uplift_stacking` applies a programme's own
  `uplifts` additively to its own base rate, strictly in the order the rule
  file's `uplifts` list declares them — a stackable uplift always adds; a
  non-stackable uplift only adds if nothing has applied yet. Swapping two
  declared, non-stackable uplifts changes which one survives to
  contribute, proven directly in `test_tier_dispatch_and_stacking`
  ((0.20+0.05)×10,000,000 = 2,500,000 vs. (0.20+0.03)×10,000,000 =
  2,300,000).
- `engine/pipeline.py::_resolve_mutual_exclusivity` resolves every declared
  `mutually_exclusive_with` edge before summation — the larger contribution
  is taken, and BOTH the taken and untaken programme's figure are recorded
  in the total's derivation, never a silent drop. `_grinding_clause_lines`
  checks for a declared grinding/assistance-reduction clause between two
  stacked, contributing programmes and records the absence when the schema
  has no field for one (`jurisdictions/SCOPE-FREEZE.md` dimension 4).
- `tests/fixtures/jurisdictions/synthetic-stacking.yaml` (per the checkpoint
  decision, `programmes-in-one-file`) declares a national programme (flat
  0.20 + a 0.05 uplift, full $10M base → $2,500,000), a regional top-up
  stacking with it over a genuinely different, smaller base (30% of core
  expenditure = $3M, flat 0.10 → $300,000), and a third programme mutually
  exclusive with the regional one (flat 0.02, full base → $200,000 —
  deliberately the smaller contribution, so it is the one excluded and the
  actual stacking pair keeps contributing). The wrong summed-rates figure
  ((0.25+0.10)×$10,000,000 = $3,500,000) is computed explicitly in the test
  and asserted not equal to the correct $2,800,000.
- `engine/credit.py::_apply_per_project_cap` clips at `min(credit, cap)`
  with a strictly-greater-than boundary comparison — a credit exactly at
  the cap is unclipped, proven at $1,999,999 / $2,000,000 / $2,000,001. The
  annual programme cap step (`_apply_annual_programme_cap`) still never
  changes the credit value (RD-04): a test asserts the gross credit is
  byte-identical whether `annual_cap_remaining` is supplied or omitted, and
  another proves that where both caps are declared, only the per-project
  cap clips.
- `engine/credit.py::assess_eligibility` and `assess_availability` are two
  independent functions returning two independently-read fields on
  `PricedProgramme`. `available` is three-state: `True`/`False` only when a
  remaining-allocation figure was actually supplied; an absent figure
  yields `None` with a stated reason — never defaulted to available. An
  eligible-but-exhausted production reports `eligible=True,
  available=False`; an ineligible production still gets a fully-computed,
  non-null availability answer.
- `tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml`: a jurisdiction
  the engine has never seen, sharing no `base_definition.type`
  (`labour_only`), `rate_structure.type` (`blended_by_ceiling_split`),
  `mechanism` (`rebate_grant`), or currency (`CZK`) with either curated
  file. Also declares a per-person ceiling, a minimum spend, a genuinely
  binding per-project cap, an audit fee schedule, a payout lag, and two
  stacking programmes. Priced against CZK 50,000,000 total qualified spend,
  it prices to CZK 12,475,000 total net cash — hand-computed in the
  fixture's own header comment and asserted as literals in the test, never
  obtained by calling the engine on itself.
- `tests/test_engine_jurisdiction_additivity.py` adds the no-
  jurisdiction-specific-code assertion (every declared `jurisdiction.id`,
  collected by globbing both rule-file directories, is absent from every
  `engine/**/*.py` file with comment-only lines removed) and the
  concurrency/purity assertion (pricing the throwaway fixture and
  `jurisdictions/us-ny.yaml` together, in both orderings, gives each the
  same figure values AND derivation tuples as pricing it alone — proving no
  module-level mutable state).
- `jurisdictions/SCOPE-FREEZE.md` dimensions 4-6 updated to record what
  landed; RD-06 records the checkpoint decision, its rejected alternative
  (`separate-files-parent-id`), and the undo cost that justified gating it;
  "partial allocation" is recorded as a disclosed simplification.

## Task Commits

Tasks 1 and 2 committed together (both extend the same ordered adjustment
sequence in `engine/credit.py` and the same `engine/pipeline.py` call
sites, not cleanly separable into non-overlapping hunks — mirrors 02-05's
own precedent). Task 3 is fully independent.

1. **Tasks 1+2: Stacking, caps, eligibility/availability** - `9a5bde8`
   (feat)
2. **Task 3: Additivity proof, zero-line engine diff** - `7ad2e83` (feat)

_This plan's checkpoint (`checkpoint:decision`, "how does a regional
programme live on disk") was already answered by the human before this
executor was spawned (`programmes-in-one-file`, 2026-08-25) — recorded
above and in `jurisdictions/SCOPE-FREEZE.md` RD-06, not re-presented._

## Files Created/Modified

- `engine/credit.py` - `_apply_uplift_stacking`,
  `_find_uplift_additional_rate`, `_apply_per_project_cap` (now clips),
  `Eligibility`/`assess_eligibility`, `Availability`/`assess_availability`
- `engine/pipeline.py` - `_resolve_mutual_exclusivity`,
  `_grinding_clause_lines`, `_contribution_figure`; `price_jurisdiction`
  now genuinely sums N programmes and resolves mutual exclusivity;
  `PricedProgramme` gains `eligibility`/`availability` fields
- `tests/fixtures/jurisdictions/synthetic-stacking.yaml` - National +
  regional stacking over different bases, a two-uplift ordering fixture, a
  mutually-exclusive third programme
- `tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml` - The JUR-05
  additivity proof jurisdiction: `labour_only` /
  `blended_by_ceiling_split` / `rebate_grant` / `CZK`, none shared with
  either curated file
- `tests/test_engine_jurisdiction_additivity.py` - Pricing,
  no-jurisdiction-specific-code, and concurrency/purity assertions
- `tests/test_engine_credit.py` - Stacking-order, dollar-not-rate-
  summation, mutual-exclusivity, N=1/2/3 programme-count, cap-boundary, and
  eligibility/availability-separation tests (12 new tests)
- `jurisdictions/SCOPE-FREEZE.md` - RD-06 (checkpoint decision); dimensions
  4-6 marked landed; "partial allocation" disclosed simplification recorded

## Decisions Made

See `key-decisions` in frontmatter for the full rationale on: (1) the
checkpoint decision (`programmes-in-one-file`); (2) how the inherited,
uncommitted implementation was reviewed and kept; (3) Tasks 1+2 committed
together; (4) the stacking fixture's mutual-exclusivity design (smaller
programme excluded, so the actual stacking pair stays exercised); (5) the
TDD gate accounting below.

## Manual-Only Verification: Zero Engine-Code Diff (02-VALIDATION.md)

Per `02-VALIDATION.md` § "Manual-Only Verifications", run against the
commit that adds the throwaway fixture and its test (`7ad2e83`), exactly
as prescribed:

```
$ git diff --name-only HEAD~1 HEAD
tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml
tests/test_engine_jurisdiction_additivity.py

$ git diff --name-only HEAD~1 HEAD | grep -c '^engine/'
0
```

Zero files under `engine/` appear in that commit's diff. The additivity
claim (JUR-05) holds: a jurisdiction the engine has never seen, exercising
a base type, rate structure, mechanism, and currency none of the curated or
prior synthetic fixtures use, prices correctly with no engine code change.

`jurisdictions/SCOPE-FREEZE.md` is dated 2026-08-25 (unchanged from plan
02-01), enumerates all eleven modelled rule dimensions plus RD-01 through
RD-06, and every disclosed simplification in it (payout lag, audit fee
schedule, star-talent exclusion, partial allocation, timing-display-only)
matches what the code actually does — re-confirmed this session while
editing dimensions 4-6 and adding RD-06.

## Deviations from Plan

### Auto-fixed Issues

None — the inherited implementation (see below) required no fixes on
review; every subsequent line of code and every fixture/test written this
session matched the plan's `<action>` and `<behavior>` blocks on the first
pass, verified against a real run of `price_jurisdiction` before being
committed.

### Continuation from an interrupted prior session

This plan was executed as a continuation. A prior executor had written the
full implementation for Task 1 (uplift stacking, multi-programme
summation, mutual-exclusivity resolution) and Task 2 (per-project cap
clipping, the annual-cap no-op, `assess_eligibility`/`assess_availability`)
directly in `engine/credit.py` and `engine/pipeline.py`, entirely
uncommitted, before being killed by a transient API stream error. No tests
for that implementation existed yet.

This executor reviewed that implementation on its merits — not on trust —
before keeping any of it:

- Confirmed `_resolve_mutual_exclusivity` sums `_contribution_figure`
  (a Figure's `.value`, in currency units) across programmes, never a rate,
  and that the summation loop in `price_jurisdiction` sums
  `_contribution_figure(...).value` per contributing programme — dollars,
  never percentages, matching the prohibition against summing stacked
  rates.
- Confirmed `Eligibility` and `Availability` are two separate frozen
  dataclasses with two separate constructor functions, both attached as
  two separate fields on `PricedProgramme` — no code path merges them into
  one boolean.
- Confirmed `_apply_annual_programme_cap` never assigns to `figure.value`
  (only calls `.with_step(line)` with no `value=` argument) — RD-04
  structurally enforced, not just documented.
- Confirmed `assess_availability`'s `None` branch is reached only when
  `annual_cap_remaining is None`, with no code path that substitutes a
  default — the "unfetched" state cannot silently become `True`.

Having verified the design was sound, this executor wrote the tests the
implementation lacked (fixture YAML, `test_engine_credit.py` additions),
ran them against the untouched implementation, and confirmed every one
passed on the first run with no implementation changes required. This is
recorded as a deviation from the plan's literal RED-GREEN-TDD sequence, not
as a correctness gap — see "TDD Gate Compliance" immediately below for the
full accounting.

## TDD Gate Compliance

Both Task 1 and Task 2 carry `tdd="true"` in `02-06-PLAN.md`. The formal
RED-GREEN gate sequence (a `test(...)` commit whose tests fail, followed by
a `feat(...)` commit that makes them pass) is **not** present in this
plan's git history: `9a5bde8` is a single `feat(...)` commit carrying both
the implementation (inherited, already sound) and its tests (written this
session, passing on the first run against that implementation).

**Why:** the implementation predated the tests in this working tree,
inherited uncommitted from a prior executor killed mid-session by a
transient stream error. The continuation instructions this executor was
given were explicit and took precedence over the plan's own `tdd="true"`
marker for this recovery scenario: judge the inherited work on its merits,
keep it if sound, and — critically — do NOT `git stash`/`checkout`/
`restore` it away, which is the only mechanism available to reconstruct a
clean pre-implementation state and observe a genuine RED failure. Stashing
carries real risk of losing already-reviewed, verified-sound work for a
process formality; the instructions judged that risk not worth taking.

**What was actually verified, in lieu of a formal RED commit:** every new
test written this session includes an explicit, hand-computed
discriminating assertion — the plan's own acceptance criteria required this
independent of TDD sequencing (e.g. "the stacking test computes the
summed-rates figure explicitly and asserts the engine's total is not equal
to it"; "assert the credit is identical whether annual_cap_remaining is
supplied or omitted"; boundary tests at cap−1/cap/cap+1). These negative
and boundary assertions are themselves evidence the tests discriminate
correct from incorrect behavior — a test that could not fail against a
plausible wrong implementation would not have survived being written this
way. Every acceptance criterion in the plan's Task 1 and Task 2 sections
was independently re-run and confirmed passing (see coverage block above).

**Impact:** none on correctness — the full suite (142 tests, up from 127
pre-existing + 12 new) is green, every plan acceptance criterion passes,
and the implementation was read line-by-line before being trusted (see
"Continuation from an interrupted prior session" above). The impact is
narrowly on process auditability: a future reader of `git log` will not
find a literal failing-test commit preceding the passing one for this
plan's two TDD-marked tasks. Task 3 carries no `tdd` marker and is
unaffected.

---

**Total deviations:** 0 auto-fixed corrections to the inherited code (it
was sound as found); 1 documented process deviation (TDD gate sequencing,
above), with no impact on correctness.
**Impact on plan:** No scope creep. No incorrect code was kept or shipped.

## Issues Encountered

None beyond the session-interruption recovery documented above. The
recovered implementation (~460 uncommitted lines) was verified sound and
required zero corrections.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 2 (Engine Spine & Incentive Interpreter) is complete: all six plans
  (02-01 through 02-06) have landed. `jurisdictions/SCOPE-FREEZE.md`
  enumerates all eleven modelled rule dimensions plus RD-01 through RD-06,
  every one confirmed against what the code actually does as of this plan.
- `INC-03` is a shared requirement ID with sibling plan 02-05 (tier/blend
  rate dispatch half). 02-05 did not mark it complete per the phase's
  shared-ID gate; this plan (the last plan declaring it) marks it complete
  now.
- **Known open item, not this plan's to fix** (per this plan's own
  wave-context instruction): plan 02-05 decoupled the golden-value test in
  `tests/test_engine_against_validation_pairs.py` from
  `engine.pipeline.price_jurisdiction` because Connecticut's `transferable`
  mechanism did not exist yet at that point in the wave; plan 02-04 has
  since implemented it. Re-coupling that test to the full pipeline is a
  recommendation for the phase verifier, not performed here (outside this
  plan's declared `files_modified`).
- No blockers. Phase 3 (New York end-to-end) can proceed against a complete
  engine spine: all four base-definition types, all four rate-structure
  behaviors (flat/tiered/blended/stacking), all four net-cash mechanisms,
  per-project and annual caps, and the eligibility/availability split are
  landed and tested.

---

*Phase: 02-engine-spine-incentive-interpreter*
*Completed: 2026-08-25*

## Self-Check: PASSED

All 3 created files verified present on disk (`[ -f ]`):
`tests/fixtures/jurisdictions/synthetic-stacking.yaml`,
`tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml`,
`tests/test_engine_jurisdiction_additivity.py`. Both task commit hashes
(`9a5bde8`, `7ad2e83`) verified present in `git log --oneline --all`. Full
suite (`uv run pytest tests/ -q`) verified green at 142 passed immediately
before writing this summary; `bash .github/scripts/vendor-scan.sh` and
`bash .github/scripts/lockfile-scan.sh` both verified exit 0.
