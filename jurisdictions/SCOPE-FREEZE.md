# Scope Freeze — Phase 2 Engine Spine & Incentive Interpreter

**Date:** 2026-08-25

This is the fixed set of rule dimensions Phase 2's generic engine
(`engine/`) models, checked against what `engine/models.py` and
`jurisdictions/us-ny.yaml` actually contain after plan 02-01's Task 1 —
not transcribed unchecked from `02-RESEARCH.md`'s draft. Anything not on
this list is out of scope for Phase 2 and must be named here as a
disclosed simplification, never left as a silent gap. This note sits
beside the rule files it bounds so a reviewer opening the curated data
finds the boundary in the same directory.

## In scope — the eleven modelled rule dimensions

1. **Base definition types** (INC-01). `engine/models.py`'s
   `BaseDefinition.type` is a closed `Literal` over
   `total_qualified_spend`, `labour_only`,
   `lesser_of_pct_core_or_actual_local`, `local_hires_only`, and the
   `custom` escape hatch (`custom_handler_id`, resolved only through
   `engine/handlers/__init__.py`'s closed `HANDLER_REGISTRY`). Plan 02-01
   implements `total_qualified_spend`; the other three raise
   `NotImplementedError` naming plan 02-03, which lands them.
2. **Per-person ceilings as a schedule, not a scalar** (INC-02).
   `engine/models.py`'s `PerPersonCeiling` carries both a scalar
   `loanout_withholding_rate` fallback and a `loanout_withholding_schedule`
   of `PerPersonCeilingTier` entries keyed by effective date — Georgia's
   confirmed five-tier declining withholding schedule
   (`SOURCE-TRUTH.md` SRC-05) is the concrete proof this must be a
   lookup-by-effective-date table. New York's rule file declares
   `per_person_ceiling.applies: false` with a note (the FY2026 budget
   removed New York's $500,000 above-the-line cap). **Plan 02-05** landed
   ceiling application: `engine/credit.py::_apply_per_person_ceiling`
   reduces the qualifying base by each W-2 compensation's excess over the
   declared cap (before the rate step, never a post-hoc clip on the
   credit — the ordering `02-RESEARCH.md` Pitfall 4 verified by
   execution), and treats a loan-out payment as fully qualifying when
   `loanout_exempt` is true, instead producing a **separate**
   withholding-obligation `Figure` (`compute_gross_credit`'s
   `per_person_compensations` parameter — production-specific data, not
   rule-file data). That withholding-obligation figure is attached to the
   credit figure's `inputs` for provenance but is **never subtracted from
   the credit or from net cash** — it is a liability on the loan-out
   entity, a different party, and netting it off would misstate both
   figures (T-02-05). An unconfirmed schedule entry
   (`loanout_withholding_confirmed: false`) is still used to compute the
   obligation, but downgrades the resulting figure's confidence to
   `researched`.
3. **Rate structures** (INC-03). `RateStructure.type` is closed to `flat`,
   `tiered_by_spend` (cliff lookup —
   `engine/credit.py::lookup_flat_rate_by_band`), `blended_by_ceiling_split`
   (two-rate blend — `engine/credit.py::blend_two_rates_by_ceiling`), and
   `headcount_scaled` (dispatch shape only). New York exercises `flat`
   (`base_rate: "0.25"`); Connecticut (plan 02-05) exercises
   `tiered_by_spend` — the whole qualifying base takes the ONE rate of the
   band it falls in, never a marginal/blended calculation across bands
   (conflating the two produced a ~$175,000 error against Connecticut's
   disclosed Christmas Always figure when verified by execution,
   `02-RESEARCH.md` Finding 3). `blend_two_rates_by_ceiling` (plan 02-05)
   splits core expenditure at the declared enhanced threshold FIRST, then
   caps EACH slice to the declared percentage cap, then applies each
   slice's own rate — capping the whole base before splitting instead
   gives a different, wrong number (verified against the UK worked
   example: £7,176,000 correct vs. £7,632,000 for the wrong ordering).
   `headcount_scaled` still raises `NotImplementedError` naming plan
   02-05 — no curated jurisdiction needs it yet. `Uplift` entries
   (additive to base rate, stackable/non-stackable, separate-application
   flag) are modelled in the schema; their application is implemented in
   plan 02-06.
4. **Stacking across national/regional programmes** (INC-03). The schema
   supports multiple `programmes` per jurisdiction with `stacks_with` /
   `mutually_exclusive_with` fields; `engine/pipeline.py::price_jurisdiction`
   loops over every declared programme and sums independent dollar outputs
   from independently-computed bases — never percentages. New York declares
   one programme, so the loop was exercised for N=1 through plan 02-05;
   **plan 02-06** lands the genuine multi-programme case:
   `engine/credit.py::_apply_uplift_stacking` applies a programme's own
   `uplifts` additively to its own base rate, in the order the rule file
   declares them (data, not a code branch — proven by a fixture test that
   swaps two declared uplifts and asserts the credit changes);
   `engine/pipeline.py::_resolve_mutual_exclusivity` resolves every declared
   `mutually_exclusive_with` edge before summation, taking the larger
   contribution and recording both the taken and untaken programme's figure
   (never silently dropping one); `_grinding_clause_lines` checks for a
   declared grinding/assistance-reduction clause between two stacked,
   contributing programmes and records the absence when the schema has no
   field to express one (RD-06 below records the layout decision this
   depends on). `tests/fixtures/jurisdictions/synthetic-stacking.yaml`
   proves the whole chain: independent dollar summation across a national
   and a regional programme with genuinely different bases, computed by
   hand and asserted to differ from the wrong summed-rates figure.
5. **Caps** (INC-04). `Caps.per_project_cap` and
   `Caps.annual_programme_cap` (amount, period, optional escalator
   schedule) are both present in the schema. New York declares
   `per_project_cap: null` and an annual cap of $700,000,000 per calendar
   year (cited to the enacted budget bill). **Plan 02-06** lands per-project
   clipping (`engine/credit.py::_apply_per_project_cap`, `min(credit, cap)`,
   strictly-greater-than at the boundary — a credit exactly at the cap is
   not clipped, proven at cap-minus-one/cap/cap-plus-one). The annual cap
   step (`_apply_annual_programme_cap`) still NEVER reduces gross credit
   (RD-04) — cap existence is rule data (modelled here); cap consumption is
   live data, out of Phase 2's scope entirely (dimension 11 below). Where
   both caps are declared, only the per-project cap clips the credit value;
   the annual cap's derivation line is recorded independently.
6. **Availability versus eligibility** (INC-05). `Caps.cap_consumption_check`
   declares the *method* by which live consumption would be checked
   (`live_research` for New York) without Phase 2 ever performing that
   check itself. **Plan 02-06** lands the two-independent-field answer:
   `engine/credit.py::assess_eligibility` (does this production qualify —
   minimum spend, programme open, mutual exclusivity considered) and
   `assess_availability` (does the programme's annual allocation still have
   money left) are two separate functions returning two separate results,
   both attached to `PricedProgramme` (`engine/pipeline.py`). `available` is
   three-state: `True`/`False` only when a remaining-allocation figure was
   actually supplied; an absent figure yields `None` with a reason stating
   consumption state was not fetched — never defaulted to available. An
   eligible-but-exhausted production reports `eligible=True,
   available=False`; an ineligible production still gets a fully-computed,
   non-null availability answer. **Partial allocation is deliberately not
   modelled**: where the remaining allocation is smaller than the computed
   credit, this phase reports the programme unavailable rather than
   splitting the award across periods — a disclosed simplification owned by
   whichever later phase adds a partial-award model, never a silent gap.
7. **Net-cash mechanisms** (INC-06). `Programme.mechanism` is closed to
   `refundable`, `transferable`, `rebate_grant`, `nonrefundable_credit`.
   `engine/net_cash.py` implements `refundable` (New York's mechanism);
   the other three raise `NotImplementedError` naming plan 02-04, which
   also lands audit-fee cliff tiering (`Audit.fee_schedule` — New York's
   is empty, so $0 is deducted with a derivation line saying so).
8. **Cash-arrival timing** (INC-08). `Timing.terms_lock_at` and
   `PayoutLag` (description, `typical_days`, `interest_paid`) are present
   on every programme and `engine/net_cash.py::convert_to_net_cash`
   returns an `ArrivalTiming` for every mechanism. **Explicit scope cut:**
   timing is displayed, never discounted to present value, in this phase.
   No later phase's UI copy may claim otherwise. New York's `typical_days`
   is `null` — the exact multi-year payout schedule has no
   `SOURCE-TRUTH.md` entry yet (see "Unsourced facts" below), and
   `ArrivalTiming.estimated_date` is never synthesised from an unsourced
   lag.
9. **Minimum-spend cliffs** (INC-09). `Programme.minimum_spend` is a
   `Money | None` field; `engine/qualifying_base.py`'s minimum-spend check
   is a hard step function — a spend one dollar below a declared threshold
   yields a `Decimal("0")` base, never an interpolated or rounded-down
   small number. When no threshold is declared (New York's case) the step
   still emits a line saying so, so silence is never mistaken for "not
   considered."
10. **Provenance** (PRV-01, PRV-02, PRV-03). Every `engine.figure.Figure`
    carries `source_url`, `date_checked`, a closed
    `confidence: {"validated", "researched"}` with no default, and a
    non-empty `derivation` tuple that only ever grows via `with_step` —
    never replaced, never collapsed. Every adjustment step in
    `engine/credit.py` appends a derivation line unconditionally, including
    a no-op line, so PRV-03 holds even where a rule declares nothing.
11. **Additivity proof** (JUR-05). The schema and every function in
    `engine/` are written generically, dispatching only on declared field
    values (`base_definition.type`, `rate_structure.type`, `mechanism`,
    etc.) — `grep -rn -E 'us-ny|NewYork|new_york' engine/` returns zero
    matches, confirmed by plan 02-01's own acceptance criteria. A
    throwaway fixture jurisdiction, structurally separate from
    `jurisdictions/` under `tests/fixtures/jurisdictions/`, proves this
    additivity with zero diffs to any `engine/*.py` file — implemented in
    plan 02-06.

## Explicitly out of scope for Phase 2 (disclosed simplifications)

- **Sales tax / hotel occupancy tax exemptions (INC-10).** Phase 4's
  requirement, not Phase 2's. `engine/` has no sales-tax or
  hotel-occupancy modelling of any kind; do not let engine scope drift
  into it.
- **Time-value-of-money discounting on delayed cash.** Cash-arrival
  timing (dimension 8, INC-08) is displayed only, per the stated scope
  cut above. No later phase may present a discounted-to-present-value
  figure as if Phase 2 computed it.
- **New York's diversity and equity bonus credit.** Disclosed in the
  source data (`diversity_credit_amount` in every New York validation-pair
  fixture) but not itemised by the ESD "Credits Issued" table — which
  additional credit, if any, a given production claimed is not derivable
  from the archived disclosure. `jurisdictions/us-ny.yaml` does not model
  it, and `tests/test_engine_against_validation_pairs.py` asserts against
  `credit_amount` alone, never `credit_amount + diversity_credit_amount`.
- **Cost localization (COST-01..08).** Phase 4's requirement.
  `engine/qualifying_base.py::SpendBreakdown.from_total` feeds the engine a
  disclosed qualified-spend `Decimal` directly (the D-02 interpreter-only
  boundary) — no `LocalizedBudget`-shaped pipeline exists yet or is built
  in this phase.
- **Cap-consumption fetching, programme open/closed live status, and FX
  rates.** Phase 7's `DataFreshnessGate`. Phase 2 accepts these as
  passed-in parameters/interfaces (`annual_cap_remaining`,
  `annual_cap_remaining_by_programme` in `engine/credit.py` and
  `engine/pipeline.py`) and never fetches them itself.
- **California and New Jersey curated rule files (JUR-02/03).** Phase 5's
  requirement per `REQUIREMENTS.md`'s traceability table. Phase 2 builds
  New York in plan 02-01 and Connecticut in plan 02-05 only — the two
  jurisdictions whose exact-mode D-05 anchor fixtures already existed at
  planning time and directly exercise `flat` and `tiered_by_spend`
  respectively.
- **Georgia, New Mexico, the United Kingdom, and Canada as curated
  jurisdictions.** Never curated in this project — no per-production
  disclosure exists for any of them. Reachable only via Job 2 live
  research in a later phase. The UK worked example (used elsewhere in this
  phase purely as an engine-correctness regression fixture for
  `blended_by_ceiling_split` and the taxable mechanism) is a golden-value
  test, not a curated jurisdiction file, and must never be represented as
  one.

## Recorded deviations and extensions (RD-01 through RD-05)

From `02-01-PLAN.md`'s "Recorded decisions" section, restated here so a
reader of the curated data finds the reasoning beside the rules it
governs, not only inside a plan file:

- **RD-01 — `Decimal`, never `float`, on every rule-file numeric.**
  `.planning/research/ARCHITECTURE.md` Q2's schema listing types several
  rate/threshold fields `float` as shorthand for "this is a fractional
  number." `02-RESEARCH.md` Finding 1 verified by direct execution
  (against this repo's own locked `pydantic==2.13.4` and `pyyaml==6.0.3`)
  that an unquoted YAML value like `0.263` parses as a native Python
  `float`, and that naive `Decimal()` conversion of that float corrupts it
  past the fifteenth significant digit. Every money, rate, percentage and
  threshold field in `engine/models.py` is therefore `Decimal`, and every
  matching value in every rule file is a quoted YAML string.
- **RD-02 — two confidence vocabularies, never conflated.**
  `Jurisdiction.sources[].confidence` (`engine/models.py`) uses the
  four-tier source-document-reliability vocabulary already established by
  `tests/test_source_truth.py`'s `LEGAL_CONFIDENCE_TIERS`
  (`LOW`/`MEDIUM`/`MEDIUM-HIGH`/`HIGH`). `engine.figure.Figure.confidence`
  is a different, closed two-value scale (`validated`/`researched`)
  measuring whether a *computed figure* has been checked against a real
  government disclosure. A test in plan 02-02 asserts the two-value enum
  specifically, never against the four-tier set.
- **RD-03 — the golden assertion is on gross credit, not net cash.**
  Government disclosures report the credit issued or allocated — a
  pre-audit-fee, pre-transfer-discount figure.
  `tests/test_engine_against_validation_pairs.py` asserts against the
  `GrossCredit` Figure for exactly this reason.
- **RD-04 — the annual programme cap never reduces gross credit.** A
  per-project cap is a rule about this project's entitlement and does clip
  the credit (plan 02-06); an annual programme cap is a fact about the
  programme's remaining allocation and produces the separate availability
  answer instead (INC-05).
- **RD-05 — five deliberate schema extensions beyond
  `ARCHITECTURE.md` Q2**, each because a Phase 2 requirement needs a field
  Q2 does not provide: (1) the Decimal-typing and quoted-string YAML
  convention above (RD-01); (2) `jurisdiction.status` gains a fourth value,
  `synthetic_fixture`, so real curated data and test fixtures are
  machine-separable rather than a directory convention a reader has to
  notice; (3) `programme.corporation_tax_rate: Decimal | None`, required
  when `taxable` is true (INC-07 needs a rate; Q2 supplies only the
  boolean); (4) `rate_structure.source_note: str | None`, mirroring
  `transfer_discount.source_note`, for a rate schedule derived empirically
  from a government dataset; (5)
  `validation.validation_pair_fixture_glob: str | None`, replacing an
  inline copy of the validation pairs — Phase 1's already-committed
  fixtures under `tests/fixtures/validation_pairs/` stay the single source
  of truth instead of being duplicated into the rule file where the two
  copies could diverge.
- **RD-06 — regional programmes live in the parent jurisdiction's own file,
  as additional `programmes` entries, never in a separate file linked by
  `parent_id`.** `02-06-PLAN.md`'s opening task was a
  `checkpoint:decision` (`programmes-in-one-file` vs.
  `separate-files-parent-id`) precisely because `ARCHITECTURE.md` Q2
  supplies both mechanisms and picks neither, and this decision fixes the
  shape of every rule file committed from this point forward AND Phase 7's
  Job 2 structured-extraction contract. **Decision: `programmes-in-one-file`
  — answered by a human checkpoint on 2026-08-25.** Rationale: one file per
  jurisdiction is the property that makes a public repository inspectable
  (a reviewer opens one file and sees everything a place offers); stacking
  edges (`stacks_with`, `mutually_exclusive_with`) resolve WITHIN that one
  file, so the engine performs NO cross-file resolution step; it matches
  how this phase's two curated files are already written; and Job 2
  extracts one document per city rather than orchestrating two. Rejected
  alternative, `separate-files-parent-id` (one file per programme-issuing
  body, linked upward by `jurisdiction.parent_id`): cleaner per-body
  provenance separation, but makes stacking a cross-file resolution step
  the engine would have to perform, requires a reviewer to open two files
  to see what one city actually offers, and would force Job 2 to judge when
  a discovered regional scheme warrants a new file versus an entry — a
  judgement an extraction step is poorly placed to make. Undo cost if this
  is reversed later: rewriting every affected rule file, re-deriving the
  Gemini response schema, and migrating any permalink that encodes a
  jurisdiction identifier — a migration, not a refactor, which is why the
  decision was gated rather than assumed.
  `tests/fixtures/jurisdictions/synthetic-stacking.yaml` is written in this
  layout: one file, three `programmes` entries, stacking and
  mutual-exclusivity edges resolved locally by
  `engine/pipeline.py::price_jurisdiction`.

## Unsourced facts deliberately not encoded

Every place a rule file carries an explicit `null` because no primary
source confirms the value, rather than a plausible-looking invented
figure — at minimum, in `jurisdictions/us-ny.yaml`:

- **New York's payout lag.** `programmes[0].timing.payout_lag.typical_days`
  is `null`. New York pays refundable film credits across multiple tax
  years above statutory amount thresholds, but the exact schedule has no
  `SOURCE-TRUTH.md` entry yet. Closing this requires locating and
  transcribing the ESD's payout-schedule documentation (if one is
  published) and recording it as a new `SOURCE-TRUTH.md` entry before any
  rule file encodes a number.
- **New York's audit fee schedule.** `programmes[0].audit.fee_schedule` is
  an empty list, so `engine/net_cash.py` deducts exactly `$0` with a
  derivation line saying no fee schedule is declared. New York requires a
  CPA agreed-upon-procedures engagement, but no fee figure is confirmed
  against a primary source. Closing this requires locating the AUP
  engagement's fee schedule (if publicly disclosed) as a primary source.
- **New York's Empire State Independent Film Production Credit rate (Tax
  Law 24-d).** Not modelled in `jurisdictions/us-ny.yaml` at all.
  `SOURCE-TRUTH.md` SRC-01 confirms the $100M/year cap and its $20M/$80M
  pool split, but not the credit's rate against a primary source.
  Encoding an unsourced rate is the one thing this project may never do;
  closing this requires a primary-source rate before this programme can be
  added as a second entry in `jurisdictions/us-ny.yaml`'s `programmes`
  list.

## Verification

- `test -f jurisdictions/SCOPE-FREEZE.md` — this file exists.
- `uv run pytest tests/ -q` — the full suite, including this plan's five
  new golden-value tests and Phase 1's 35 pre-existing tests, is green.
