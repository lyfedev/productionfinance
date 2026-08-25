---
phase: 02-engine-spine-incentive-interpreter
plan: 05
subsystem: engine
tags: [decimal, incentive-engine, per-person-ceiling, tiered-rate, ceiling-split, connecticut, provenance]

requires:
  - phase: 02-engine-spine-incentive-interpreter
    provides: >
      02-01's complete engine spine (Figure, JurisdictionRuleSet schema,
      the five-step CreditCalculator sequence with per-person-ceiling and
      rate steps stubbed) and 02-03's all-four-base-definition-types
      qualifying_base.py, whose Core expenditure (pre-cap) inputs edge
      this plan's ceiling-split blend reads.
provides:
  - "engine/credit.py — per-person ceiling (W-2 excess-over-cap before the rate, loan-out exemption plus a separate never-netted withholding-obligation Figure on a dated schedule); lookup_flat_rate_by_band and blend_two_rates_by_ceiling wired into _apply_rate's dispatch on rate_structure.type, no shared code path"
  - "jurisdictions/us-ct.yaml — second curated jurisdiction, tiered_by_spend proof, mechanism/minimum-spend/audit sourced from CT General Statutes Sec. 12-217jj"
  - "tests/fixtures/jurisdictions/synthetic-ga-style.yaml, synthetic-uk-style.yaml — the per-person-ceiling and ceiling-split-blend engine-correctness fixtures"
  - "tests/test_engine_credit.py — INC-02/INC-03 as boundary, golden-value and explicit-negative-value assertions"
affects: [02-04, 02-06, 03-new-york-end-to-end]

actuals:
  tokens: 214340
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Production-specific facts (per-person compensation lines, production date) passed to compute_gross_credit as explicit keyword arguments, never threaded through the jurisdiction rule-file schema — a rule file declares the ceiling, not who was paid what"
    - "A separate, never-netted liability Figure (loan-out withholding obligation) attached to the credit figure's inputs tuple via a direct dataclasses.replace, rather than widening compute_gross_credit's return type to a tuple — keeps engine/pipeline.py's existing call site untouched"
    - "Rate-structure functions read the un-capped Core expenditure (pre-cap) Figure through the QualifyingBase Figure's own inputs edge, bypassing the (possibly already-capped) working credit-sequence value entirely — the split-then-cap-each-slice ordering depends on this"

key-files:
  created:
    - jurisdictions/us-ct.yaml
    - sources/ct/2026-08-25-cga-ct-general-statutes-chap208-sec-12-217jj.html
    - tests/fixtures/jurisdictions/synthetic-ga-style.yaml
    - tests/fixtures/jurisdictions/synthetic-uk-style.yaml
    - tests/test_engine_credit.py
  modified:
    - engine/credit.py
    - jurisdictions/SCOPE-FREEZE.md
    - sources/MANIFEST.yaml
    - tests/test_engine_against_validation_pairs.py

key-decisions:
  - "Connecticut's mechanism is transferable, not refundable — sourced directly from CGS 12-217jj(e)(1) ('may be sold, assigned or otherwise transferred... not... more than three times'), fetched this session from cga.ct.gov rather than assumed"
  - "The tiered_by_spend bands stay derivation-sourced (source_note names the CSV, sha256, statute filter, row counts) per the plan's recorded decision, even though the newly-fetched statute text (12-217jj(b)(2)) independently states the identical three-band structure — the statute is recorded as corroboration, not substituted as the primary citation, honoring the plan's explicit instruction not to present a derivation as a statute quotation"
  - "Connecticut's per-individual/aggregate star-talent compensation exclusion (CGS 12-217jj(a)(5)(C)(i): >$15M/individual or >$20M aggregate excluded from qualifying spend entirely) is a genuinely different mechanism from this schema's W-2-cap-with-loan-out-exemption PerPersonCeiling model — recorded as a disclosed, unmodeled simplification in the rule file's header comment rather than mismodeled into the wrong schema shape or silently dropped; per_person_ceiling.applies stays false for Connecticut"
  - "tests/test_engine_against_validation_pairs.py decoupled from engine.pipeline.price_jurisdiction (which always also computes net cash) and now prices base+credit directly via compute_qualifying_base + compute_gross_credit — Connecticut's real mechanism (transferable) is not implemented until plan 02-04 (wave 3, depends on 02-05), so routing the golden-value test through the full pipeline would raise NotImplementedError before ever reaching the gross-credit assertion the test actually needs. This makes RD-03's own stated principle ('assert on gross credit, never net cash') load-bearing rather than accidental"
  - "The loan-out withholding obligation is exposed as an extra entry on the returned gross-credit Figure's inputs tuple (found by label, 'Loan-out withholding obligation — {role}') rather than widening compute_gross_credit's return type to a tuple, which would have required changing engine/pipeline.py's call site — outside this plan's declared files_modified"
  - "Task 1 and Task 2 committed together (one commit, not two) — both add to the same ordered adjustment sequence in engine/credit.py (compute_gross_credit's signature, the __all__ list, the CORE_EXPENDITURE_LABEL import) in ways that are not cleanly separable into non-overlapping git hunks without risking a broken intermediate commit; Task 3 (Connecticut) is a fully independent commit"

patterns-established:
  - "_w2_excess/_select_loanout_rate/_record_loanout_withholding: the per-person-ceiling step's internal decomposition — a strictly-greater-than boundary comparison, a dated-schedule lookup with a scalar fallback, and a withholding-Figure constructor kept as three separately-testable private functions"
  - "_find_qualifying_base_input/_find_core_expenditure_figure: label-based (never positional) lookup into a Figure's inputs tuple, robust to other steps (the per-person ceiling) also appending entries to the same tuple"

requirements-completed: [INC-02]

coverage:
  - id: D1
    description: "A per-person ceiling reduces the qualifying base before the rate applies (never a post-hoc clip on the credit), distinguishes W-2 compensation (excess-over-cap reduction, strictly-greater-than boundary) from loan-out payments (full qualification plus a separate, never-netted withholding-obligation Figure selected from a dated effective-date schedule, never a scalar), and downgrades confidence to researched for an unconfirmed schedule entry"
    requirement: "INC-02"
    verification:
      - kind: unit
        ref: "tests/test_engine_credit.py::test_per_person_ceiling_w2_vs_loanout"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_per_person_ceiling_w2_boundary (3 parametrized boundary cases)"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_per_person_ceiling_loanout_withholding_selects_earlier_band"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_per_person_ceiling_unconfirmed_schedule_entry_reports_researched"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_per_person_ceiling_no_compensations_supplied_leaves_base_unchanged"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_per_person_ceiling_applies_false_emits_noop_and_leaves_base_unchanged"
        status: pass
    human_judgment: false
  - id: D2
    description: "tiered_by_spend (cliff lookup, lookup_flat_rate_by_band) and blended_by_ceiling_split (split-then-cap-each-slice, blend_two_rates_by_ceiling) are two distinct, separately-named, separately-tested functions with no shared code path; each reproduces its sourced worked figure exactly and each is proven not to produce the plausible wrong figure the other interpretation gives"
    requirement: "INC-03"
    verification:
      - kind: unit
        ref: "tests/test_engine_credit.py::test_lookup_and_blend_are_distinct_callables"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_lookup_flat_rate_by_band_half_open_boundaries (6 parametrized boundary cases)"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_lookup_flat_rate_by_band_reproduces_christmas_always_and_not_the_marginal_misreading"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_lookup_flat_rate_by_band_no_matching_band_raises"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_blend_two_rates_by_ceiling_reproduces_uk_example_and_not_the_cap_before_split_misreading"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_blend_two_rates_by_ceiling_full_pipeline_uk_fixture"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_blend_two_rates_by_ceiling_standard_slice_still_emitted_when_zero"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_blend_two_rates_by_ceiling_missing_core_expenditure_edge_raises"
        status: pass
      - kind: unit
        ref: "tests/test_engine_credit.py::test_tier_dispatch_and_stacking"
        status: pass
    human_judgment: false
  - id: D3
    description: "Connecticut's curated rule file (jurisdictions/us-ct.yaml) reproduces Christmas Always's disclosed $3,865,005 qualified spend as exactly Decimal('1159502') — the second real government-issued figure this project reproduces exactly — and a jurisdiction filter matching zero Connecticut pairs fails loudly rather than silently"
    verification:
      - kind: unit
        ref: "tests/test_engine_against_validation_pairs.py::test_christmas_always_reproduces_exactly"
        status: pass
      - kind: unit
        ref: "tests/test_engine_against_validation_pairs.py::test_at_least_one_connecticut_pair_exercised"
        status: pass
      - kind: unit
        ref: "tests/test_engine_against_validation_pairs.py::test_curated_jurisdiction_reproduces_disclosed_credit[Christmas Always]"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every field jurisdictions/us-ct.yaml encodes (mechanism, minimum spend, audit requirement, and the corroborating tier-band statement) traces to a Connecticut primary source — CGS Sec. 12-217jj, fetched and archived under sources/ct/ this session with a sha256 row in sources/MANIFEST.yaml — rather than being encoded from memory or invented"
    verification:
      - kind: unit
        ref: "tests/test_source_truth.py::test_manifest_hashes_match_files_on_disk"
        status: pass
      - kind: unit
        ref: "tests/test_source_truth.py::test_every_archived_file_has_a_manifest_row"
        status: pass
      - kind: other
        ref: "manual verification this session: CGS 12-217jj(e)(1) (transferable), (b)(2)(i) ($100,000 minimum), (h)(2)(B) (mandatory independent certification) each read directly from the fetched statute text before being encoded"
        status: pass
    human_judgment: true
    rationale: "The automated tests confirm structural reconciliation (sha256 matches, every archived file has a manifest row) but confirming that the statute text genuinely supports each encoded field's specific citation is a judgment call over primary-source legal text that no test can make on its own — flagged for human spot-check rather than silently asserted as machine-verified."

duration: 55min
completed: 2026-08-25
status: complete
---

# Phase 2 Plan 05: Per-Person Ceilings and Cliff/Blend Rate Dispatch Summary

**Per-person ceilings reduce the qualifying base before the rate (W-2 excess-over-cap vs. loan-out exemption plus a separate never-netted withholding obligation on a dated schedule); tiered_by_spend and blended_by_ceiling_split land as two genuinely distinct rate functions, reproducing Connecticut's Christmas Always ($1,159,502) and the UK's £18M worked example ($7,176,000) exactly while explicitly proving neither produces the other's plausible wrong figure ($984,502 / £7,632,000).**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3
- **Files modified:** 9 (5 created, 4 modified)

## Accomplishments

- `engine/credit.py`'s per-person-ceiling step (`_apply_per_person_ceiling`)
  now reduces the qualifying base by each W-2 compensation's excess over
  the declared cap — strictly-greater-than at the boundary, before the
  rate step ever runs (02-RESEARCH.md Pitfall 4's verified ordering) — and
  treats a loan-out payment under `loanout_exempt` as fully qualifying
  while producing a *separate* withholding-obligation `Figure`, selected
  from a dated effective-date schedule (never a single scalar,
  SOURCE-TRUTH.md SRC-05's Georgia proof), attached to the credit figure's
  `inputs` for provenance but never subtracted from the credit or net
  cash. `compute_gross_credit` gained two new keyword-only parameters,
  `per_person_compensations` and `production_date`, for this
  production-specific data — never threaded through the jurisdiction
  schema, so `engine/pipeline.py`'s existing call site (and every
  jurisdiction with `per_person_ceiling.applies: false`, e.g. New York)
  is unaffected.
- `lookup_flat_rate_by_band` (cliff lookup) and `blend_two_rates_by_ceiling`
  (now taking an explicit `pct_cap`, implementing "split first, cap each
  slice, then apply each slice's own rate") are wired into `_apply_rate`'s
  dispatch strictly on `rate_structure.type`, with no shared code path.
  The blend reads the un-capped `Core expenditure (pre-cap)` Figure
  through the `QualifyingBase` Figure's own `inputs` edge — bypassing the
  credit sequence's working value, which may already be capped by the
  base-stage's own `lesser_of_pct_core_or_actual_local` computation — and
  raises, naming the missing label, if that edge is absent rather than
  silently falling back to the already-capped value.
- Two new engine-correctness fixtures land under
  `tests/fixtures/jurisdictions/`: `synthetic-ga-style.yaml` (two
  programmes — a confirmed and an unconfirmed withholding schedule,
  transcribing SOURCE-TRUTH.md SRC-05's real five-tier Georgia schedule
  verbatim) and `synthetic-uk-style.yaml` (the £18M UK IFTC worked
  example). Both declare `jurisdiction.status: synthetic_fixture` and
  state plainly, in their header comments, that neither Georgia nor the
  UK is ever a curated jurisdiction for this project.
- `jurisdictions/us-ct.yaml`, the second curated rule file, reproduces
  Christmas Always's disclosed $3,865,005 qualified spend as exactly
  `Decimal('1159502')`. Phase 1 verified Connecticut's CSV schema but not
  the programme's mechanism, minimum spend or audit requirement — this
  plan closes that gap by fetching Connecticut General Statutes Chapter
  208, Sec. 12-217jj directly from `cga.ct.gov` this session (archived
  under `sources/ct/`, sha256 recorded in `sources/MANIFEST.yaml`) and
  encoding `mechanism: transferable` (12-217jj(e)(1): sold, assigned or
  transferred up to three times — never refundable), `minimum_spend:
  "100000"` (12-217jj(b)(2)(i)), and `audit.mandatory: true`
  (12-217jj(h)(2)(B): mandatory independent CPA certification) directly
  from the statute text. The tiered_by_spend bands stay
  derivation-sourced from the open-data CSV per the plan's own recorded
  decision, and are additionally — not substitutively — corroborated by
  the statute's own identical three-band text.
- `tests/test_engine_against_validation_pairs.py` generalized from a
  hard-coded New York-only filter to a `jurisdiction_id -> ruleset_path`
  mapping, and (Rule 1 deviation, below) decoupled from
  `engine.pipeline.price_jurisdiction` to price base+credit directly.

## Task Commits

Task 1 and Task 2 both extend the same ordered adjustment sequence in
`engine/credit.py` in ways that are not cleanly separable into
non-overlapping git hunks (shared imports, `__all__`, and
`compute_gross_credit`'s signature) — committed together rather than
split to avoid a broken intermediate state. Task 3 is fully independent.

1. **Tasks 1+2: Per-person ceilings and cliff/blend rate dispatch** -
   `8ae57b2` (feat)
2. **Task 3: Connecticut — a second real government figure, every field
   sourced** - `8a573a4` (feat)

## Files Created/Modified

- `jurisdictions/us-ct.yaml` - Second curated rule file: `tiered_by_spend`
  proof, mechanism/minimum-spend/audit sourced from CGS 12-217jj
- `sources/ct/2026-08-25-cga-ct-general-statutes-chap208-sec-12-217jj.html` -
  Connecticut General Statutes Chapter 208, fetched from cga.ct.gov this
  session
- `tests/fixtures/jurisdictions/synthetic-ga-style.yaml` - Per-person
  ceiling fixture: W-2 cap, loan-out exemption, five-tier dated
  withholding schedule (confirmed + unconfirmed variants)
- `tests/fixtures/jurisdictions/synthetic-uk-style.yaml` - Ceiling-split
  blend fixture: the £18M IFTC worked example
- `tests/test_engine_credit.py` - INC-02/INC-03 as boundary, golden-value
  and explicit-negative-value assertions (23 tests)
- `engine/credit.py` - `_apply_per_person_ceiling` fully implemented;
  `PerPersonCompensation`, `_w2_excess`, `_select_loanout_rate`,
  `_record_loanout_withholding`; `blend_two_rates_by_ceiling` gains
  `pct_cap`; `_apply_rate` dispatches `tiered_by_spend` and
  `blended_by_ceiling_split`; `_find_qualifying_base_input`/
  `_find_core_expenditure_figure`; `compute_gross_credit` gains
  `per_person_compensations`/`production_date`
- `jurisdictions/SCOPE-FREEZE.md` - Dimensions 2/3 updated to record both
  landed mechanisms and the withholding-obligation netting exclusion
- `sources/MANIFEST.yaml` - New row for the archived Connecticut statute
- `tests/test_engine_against_validation_pairs.py` - Generalized to a
  jurisdiction mapping; decoupled from `price_jurisdiction`'s net-cash
  step (Rule 1 deviation, below)

## Decisions Made

See `key-decisions` in frontmatter for the full rationale on: (1)
Connecticut's mechanism is `transferable`, sourced directly from statute,
never assumed `refundable`; (2) the tiered_by_spend bands stay
derivation-sourced per the plan's recorded decision, with the statute
recorded as corroboration rather than substituted as the primary
citation; (3) Connecticut's star-talent compensation exclusion is a
disclosed, unmodeled simplification rather than mismodeled into
`PerPersonCeiling`'s W-2-cap shape; (4) the golden-value test decoupled
from `price_jurisdiction` (net-cash-independent by design, matching
RD-03); (5) the withholding obligation is exposed via `Figure.inputs`
rather than widening `compute_gross_credit`'s return type; (6) Tasks 1
and 2 committed together.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Decoupled the golden-value test from
`engine.pipeline.price_jurisdiction`**
- **Found during:** Task 3, writing the Connecticut extension to
  `tests/test_engine_against_validation_pairs.py`
- **Issue:** The existing test priced New York via
  `price_jurisdiction`, which always also computes net cash through
  `engine.net_cash.convert_to_net_cash` — this happened to work for New
  York only because its mechanism (`refundable`) is the one mechanism
  `net_cash.py` implements so far. Connecticut's real, statute-sourced
  mechanism is `transferable`, which `net_cash.py` does not implement
  until plan 02-04 (wave 3, depends on 02-05 — not yet run). Routing the
  Connecticut golden-value test through the full pipeline would raise
  `NotImplementedError` before ever reaching the gross-credit assertion
  the test actually needs, even though the test never inspects net cash
  at all.
- **Fix:** `_gross_credit_for` now calls
  `engine.qualifying_base.compute_qualifying_base` and
  `engine.credit.compute_gross_credit` directly, bypassing
  `price_jurisdiction` (and therefore net cash) entirely. This makes
  RD-03's own stated principle ("assert on gross credit, never net
  cash") structurally true of the test rather than accidentally true of
  it for one jurisdiction.
- **Files modified:** `tests/test_engine_against_validation_pairs.py`
- **Verification:** `uv run pytest tests/test_engine_against_validation_pairs.py -x -q`
  passes (8 tests, both New York and Connecticut pairs).
- **Committed in:** `8a573a4` (Task 3's commit)

---

**Total deviations:** 1 auto-fixed (1 bug — an accidental coupling
between a golden-value test and an unrelated, not-yet-implemented
mechanism).
**Impact on plan:** No scope creep — the fix is scoped entirely to the
one test file this plan already declared as `files_modified`, and
strengthens rather than weakens the RD-03 principle the plan itself
documents.

## Issues Encountered

None beyond the deviation above. The Connecticut Department of Economic
and Community Development's own film-credit web pages returned HTTP 404
for every URL pattern tried this session; the codified statute text
(`cga.ct.gov`, the Connecticut General Assembly's own domain — a
primary-source alternative the plan's own instruction explicitly
permits: "the state's own statute text ... or the state
economic-development department's own film tax credit page") was used
instead, and proved to be a stronger source than the department page
would have been (it is the enacted law itself, not a paraphrase of it).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Two of Phase 2's D-05 exact-mode anchors now reproduce exactly: Anora
  (New York, $991,190) and Christmas Always (Connecticut, $1,159,502).
- `engine/credit.py`'s per-person-ceiling and rate steps are fully
  implemented; only `headcount_scaled` (no curated jurisdiction needs it
  yet), uplift stacking, per-project-cap clipping and availability
  assessment remain — all explicitly assigned to plan 02-06 per
  `jurisdictions/SCOPE-FREEZE.md` dimensions 3-6, unaffected by this
  plan.
- Plan 02-04 (wave 3, depends on 02-01 and 02-05) can now proceed: it
  reads `tests/fixtures/jurisdictions/synthetic-uk-style.yaml`
  (committed, unmodified per this plan's instruction) for the taxable
  UK-mechanism golden-value test, and will implement the `transferable`
  mechanism that `jurisdictions/us-ct.yaml` now declares — until 02-04
  lands, pricing Connecticut through the full `price_jurisdiction`
  pipeline (rather than `compute_gross_credit` directly) will still raise
  `NotImplementedError`; this is expected, not a regression.
- `INC-03` is a shared requirement ID with sibling plan 02-06 (uplift
  stacking/caps/availability) and was NOT marked complete by this plan
  per the phase's shared-ID gate — it becomes ready once 02-06 also
  produces a `SUMMARY.md`. `INC-02` was marked complete.
- No blockers.

---

*Phase: 02-engine-spine-incentive-interpreter*
*Completed: 2026-08-25*

## Self-Check: PASSED

All 5 created files verified present on disk (`[ -f ]`). Both task commit
hashes (`8ae57b2`, `8a573a4`) verified present in `git log --oneline
--all`. Full suite (`uv run pytest tests/ -q`) verified green at 108
passed and `bash .github/scripts/vendor-scan.sh` verified exit 0
immediately before writing this summary.
