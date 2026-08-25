---
phase: 02-engine-spine-incentive-interpreter
reviewed: 2026-08-25T16:53:03Z
depth: standard
files_reviewed: 29
files_reviewed_list:
  - engine/__init__.py
  - engine/credit.py
  - engine/figure.py
  - engine/handlers/__init__.py
  - engine/models.py
  - engine/net_cash.py
  - engine/pipeline.py
  - engine/qualifying_base.py
  - engine/rounding.py
  - jurisdictions/SCOPE-FREEZE.md
  - jurisdictions/us-ct.yaml
  - jurisdictions/us-ny.yaml
  - pyproject.toml
  - sources/MANIFEST.yaml
  - tests/fixtures/jurisdictions/synthetic-basedefs.yaml
  - tests/fixtures/jurisdictions/synthetic-ga-style.yaml
  - tests/fixtures/jurisdictions/synthetic-mechanisms.yaml
  - tests/fixtures/jurisdictions/synthetic-mincliff.yaml
  - tests/fixtures/jurisdictions/synthetic-stacking.yaml
  - tests/fixtures/jurisdictions/synthetic-uk-style.yaml
  - tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml
  - tests/fixtures/validation_pairs/ny_succession_s4.yaml
  - tests/test_engine_against_validation_pairs.py
  - tests/test_engine_credit.py
  - tests/test_engine_figure_provenance.py
  - tests/test_engine_jurisdiction_additivity.py
  - tests/test_engine_models.py
  - tests/test_engine_net_cash.py
  - tests/test_engine_qualifying_base.py
  - tests/test_engine_rounding.py
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-08-25T16:53:03Z
**Depth:** standard
**Files Reviewed:** 29
**Status:** issues_found

## Summary

This engine is unusually well-documented and its test suite is disciplined
(half-open boundary sweeps, negative-value assertions, glob-based
fail-loud-on-empty guards, closed-enum security gates). Most of the
domain-critical hazards named in the review brief — cliff-vs-marginal rate
confusion, cap-before-split ordering, confidence-tier laundering, unsafe
YAML loading, dynamic handler resolution — are correctly implemented and
directly tested against their documented failure modes.

However, one Critical defect was found and confirmed by direct execution:
`engine/credit.py`'s `blended_by_ceiling_split` rate-structure branch
computes the credit from the raw, pre-adjustment core-expenditure Figure
instead of the actually-adjusted running base, silently discarding the
minimum-spend cliff, excluded-line-items subtraction, and per-person
ceiling reduction for any programme that uses this rate structure. This is
not exercised by any committed fixture or test, so it currently ships
undetected. Several smaller data-validation gaps (self-referencing
`mutually_exclusive_with`, unchecked `stacks_with` references, an
inconsistent boundary convention on the loan-out withholding schedule
lookup) round out the Warning tier.

## Structural Findings (fallow)

None provided for this review.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `blended_by_ceiling_split` silently bypasses minimum-spend, excluded-line-items, and per-person-ceiling adjustments

**File:** `engine/credit.py:446-467`

**Issue:** For any programme whose `rate_structure.type` is
`blended_by_ceiling_split`, `_apply_rate` computes the credit from
`core_expenditure_figure.value` (the **raw, pre-cap, pre-everything**
`Core expenditure (pre-cap)` Figure reached via
`_find_core_expenditure_figure`), not from `figure.value` (the running
credit figure, which is the actual base after the minimum-spend cliff,
`excluded_line_items` subtraction, and the per-person-ceiling reduction
have all been applied). Because `core_expenditure_figure` is a separate,
immutable `Figure` object attached once at `compute_qualifying_base`
construction time and never touched by any of the subsequent adjustment
steps (`_apply_minimum_spend_check`, `_apply_excluded_line_items`,
`_apply_per_person_ceiling`), every one of those adjustments is silently
discarded for this rate structure, even though their derivation lines are
still emitted claiming the adjustment happened.

Confirmed by direct execution against this reviewed code (not a
hypothetical):

1. **Minimum-spend cliff bypassed.** A programme with
   `minimum_spend.value = 5,000,000` and `blended_by_ceiling_split`
   priced against `qualified_spend = 3,000,000` (below the threshold):
   `qualifying_base.value` correctly becomes `0` with derivation
   `"spend 3000000 USD is below the declared minimum-spend threshold of
   5000000 USD — qualifying base is $0"`. `compute_gross_credit`'s
   starting Figure correctly starts at `0` too (`"starting base: 0 USD"`).
   But the final gross credit is **`700000`**, not `0` — the rate step
   read `core_expenditure_figure.value = 3000000` and split/rated that
   instead. A production that does not meet the jurisdiction's declared
   minimum-spend floor still gets a six-figure credit.
2. **Per-person ceiling bypassed.** A programme with
   `per_person_ceiling.applies=true`, `w2_cap_amount=500,000`, and
   `blended_by_ceiling_split`, priced with a $2,000,000 W-2 compensation
   line (excess $1,500,000 over the cap): the derivation correctly states
   `"W-2 compensation 2000000 USD exceeds the declared per-person cap of
   500000 USD ... base reduced by 1500000"`, but the computed gross credit
   is **identical** (`700000`) whether or not that compensation line is
   supplied at all — the reduction the derivation describes never reaches
   the number.
3. **`excluded_line_items` bypassed by the same mechanism** (not
   separately re-verified by execution, but the code path is identical:
   `_apply_excluded_line_items` only ever mutates the wrapping "Qualifying
   base" Figure's `.value`, never the `Core expenditure (pre-cap)` input
   Figure the rate step actually reads).

This is worse than a wrong number: the derivation trail — the thing this
codebase's entire provenance model exists to make trustworthy — actively
asserts an adjustment took place that did not affect the reported figure.
A reader trusting `Figure.derivation` (as `PRV-03` promises they can) would
be misled about what the reported credit actually reflects.

Note: `engine/qualifying_base.py`'s own comment ("a ceiling split operates
on core expenditure *before* any percentage cap applies") and
`jurisdictions/SCOPE-FREEZE.md` dimension 3 document that
`blended_by_ceiling_split` is *deliberately* meant to re-derive its own
percentage cap from `base_definition.pct_core_cap` against raw core
expenditure, rather than trusting whatever `base_definition.type` computed
(this is why the UK fixture's `lesser_of_pct_core_or_actual_local` base
type and its `pct_core_cap` are intentionally re-applied per-slice inside
the blend, not reused from the qualifying base). That documented
carve-out covers *the percentage cap only*. Nothing in the design record
extends it to minimum-spend, excluded-line-items, or per-person-ceiling —
this is scope creep in the implementation beyond what was actually
decided, not an intentional design choice.

No committed fixture exercises this combination:
`synthetic-uk-style.yaml` (the only `blended_by_ceiling_split` fixture
with real spend variation) declares no `minimum_spend`, no
`excluded_line_items`, and `per_person_ceiling.applies: false`.
`zz-fixture-throwaway.yaml`'s `primary-throwaway` programme declares
`per_person_ceiling.applies: true`, but its own header comment records
that `price_jurisdiction` never supplies `per_person_compensations`, so
the per-person step is a no-op regardless — it does not exercise the
ceiling-reduction path this bug affects. `minimum_spend` on that same
programme (`1,000,000`) is well below the priced spend (`50,000,000`), so
the cliff never triggers either.

**Fix:** The rate step must operate on the actually-adjusted running base
(`figure.value`), not on the raw core-expenditure input. If the design
intent is genuinely "ceiling-split always re-derives its cap from raw core
expenditure, ignoring `base_definition.type`'s own capping," that intent
must not also discard minimum-spend and per-person-ceiling — those are
separate adjustment steps this function already ran, immediately above,
against `figure.value`. Concretely: track how much the base was already
reduced by the minimum-spend cliff and the per-person ceiling (e.g., by
diffing `figure.value` against `core_expenditure_figure.value` at entry to
`_apply_rate`, or by threading the post-ceiling, pre-rate base value
explicitly) and apply that same reduction to the raw core expenditure
before slicing it, or — more simply and more consistent with every other
branch in this function — slice `figure.value` itself and stop reaching
into `core_expenditure_figure` except to recover `pct_core_cap`'s
percentage-cap re-derivation the design record actually asks for. At
minimum, add a regression test combining `blended_by_ceiling_split` with
each of minimum-spend-not-met, an excluded line item, and a binding
per-person ceiling, asserting the credit reflects all three — this gap
existing uncaught through a full plan/review cycle is itself a signal the
fixture matrix needs that combination before this rate structure ships.

## Warnings

### WR-01: Self-referencing `mutually_exclusive_with` silently drops a valid programme from the total

**File:** `engine/pipeline.py:140-171`

**Issue:** `_resolve_mutual_exclusivity` does not reject a programme
naming its own `id` in its own `mutually_exclusive_with` list. If it did,
`pair = frozenset({programme.id, other_id})` collapses to a one-element
set, `other_id in programme_by_id` is trivially true (it is the same
programme), `this_value >= other_value` is true (comparing the programme's
contribution to itself), and both `taken_id` and `untaken_id` end up equal
to `programme.id` — so the programme is simultaneously recorded as "taken"
and added to `excluded_ids`, and is silently dropped from
`contributing`/the summed total despite being otherwise fully eligible.
Every other unrecognised-reference case in this same function (an
`other_id` absent from `programme_by_id`) correctly raises `ValueError`;
this one does not, because a self-reference is never "absent."

**Fix:** Reject a self-referencing `mutually_exclusive_with` entry
explicitly, either at Pydantic validation time (a `model_validator` on
`Programme` checking `self.id not in self.mutually_exclusive_with`) or as
an explicit early raise in `_resolve_mutual_exclusivity`:
```python
if other_id == programme.id:
    raise ValueError(
        f"programme {programme.id!r} declares mutually_exclusive_with "
        "itself, which is not a valid mutual-exclusivity edge"
    )
```

### WR-02: `stacks_with` references are never validated against declared programme ids

**File:** `engine/pipeline.py:174-197`

**Issue:** `_resolve_mutual_exclusivity` validates that every
`mutually_exclusive_with` id resolves to a real declared programme,
raising `ValueError` naming the unknown id otherwise. `_grinding_clause_lines`
performs no equivalent check on `stacks_with`: `other_id` is used directly
to build a derivation line ("no grinding or assistance-reduction clause is
declared between stacked programmes X and Y") without ever confirming `Y`
is a real programme in this ruleset. A typo'd or stale `stacks_with`
reference is never caught — it produces a plausible-looking derivation
line about a programme that does not exist, rather than raising.

**Fix:** Validate `stacks_with` ids against `programme_by_id` the same way
`_resolve_mutual_exclusivity` already does for `mutually_exclusive_with`,
raising `ValueError` naming the unknown id — or add the check to the
`Programme`/`JurisdictionRuleSet` schema itself (a cross-field
`model_validator` on `JurisdictionRuleSet` checking every `stacks_with`
and `mutually_exclusive_with` entry resolves to a declared programme id)
so both edges are validated in one place at load time.

### WR-03: Loan-out withholding schedule lookup uses closed-interval boundaries, inconsistent with every other tier lookup in this codebase

**File:** `engine/credit.py:125-128`

**Issue:** `_select_loanout_rate`'s schedule lookup matches
`tier.effective_from <= production_date and (tier.effective_to is None or
production_date <= tier.effective_to)` — a closed-closed interval. Every
other tiered lookup in this codebase (`lookup_flat_rate_by_band` in
`engine/credit.py`, `_select_audit_fee_tier` in `engine/net_cash.py`) is
explicitly documented and tested as half-open (`low <= x < high`), with
dedicated boundary tests proving a value exactly at a band's upper edge
falls into the *next* band. This lookup has no such test and uses the
opposite convention. Nothing currently validates that a
`loanout_withholding_schedule`'s entries don't overlap at a boundary (e.g.
one tier's `effective_to` equal to the next tier's `effective_from`); if
that ever happens, the first matching entry in declared list order wins
silently, rather than raising — a rule-file authoring mistake that would
otherwise surface loudly (as every other closed-enum/tier dispatch in this
codebase does per the domain's "silent fallthrough" requirement) instead
picks a rate with no diagnostic.

**Fix:** Either document explicitly why this one lookup is intentionally
closed-closed (dated "through" ranges read naturally as inclusive, unlike
a spend-threshold band) and add a boundary test proving the convention is
deliberate at an adjacency point, or add an overlap-detection check when
the schedule is loaded/consulted so two schedule entries covering the same
date raise instead of silently resolving by list order.

### WR-04: An empty `programmes` list yields a spuriously `validated`, unsourced `$0` jurisdiction total

**File:** `engine/pipeline.py:251-261`, `engine/figure.py:98-109`

**Issue:** `JurisdictionRuleSet.programmes` has no minimum-length
constraint, so a rule file could declare `programmes: []` and still pass
schema validation. `price_jurisdiction` would then compute
`total_inputs = []` and call `combined_confidence([])`, which — per its
own documented contract ("an empty sequence defaults to `validated` —
there is nothing weaker to inherit from") — returns `"validated"`. The
resulting `total_net_cash` Figure reports `value=0`, `confidence=
"validated"`, `source_url=None`, `date_checked=None` for a jurisdiction
that priced nothing at all. A `"validated"` confidence tag on a figure
with no actual source and no actual computation is a small instance of
the confidence-laundering failure mode this review is weighted against,
even though `combined_confidence`'s empty-sequence behaviour is
reasonable for its primary (non-empty) use case.

**Fix:** Either require `programmes` to be non-empty at the
`JurisdictionRuleSet` schema level (a jurisdiction with zero programmes is
arguably not a meaningful rule file), or have `price_jurisdiction` special-case
the empty-programmes case to report a Figure whose confidence and
derivation make the "nothing was priced" state explicit rather than
routing it through `combined_confidence`'s "nothing to combine" default.

## Info

### IN-01: `AnnualProgrammeCap.escalator_schedule` is accepted by the schema but never referenced by any derivation line

**File:** `engine/models.py:230-233`, `engine/credit.py:527-560`

**Issue:** `AnnualProgrammeCap.escalator_schedule` is a declared,
validated schema field, but `_apply_annual_programme_cap` never reads it
or emits any derivation line acknowledging it exists or was considered.
Every other schema field this engine doesn't yet act on (per-project caps
alongside annual caps, cap-consumption-check methods, uplift stacking
edge cases) gets an explicit "considered, here's why nothing happened"
derivation line per this codebase's own PRV-03 discipline; this field is
the one exception that is silently invisible to a reader of the
derivation trail.

**Fix:** Add a derivation line in `_apply_annual_programme_cap` naming
whether `escalator_schedule` is declared, mirroring the treatment every
other unconsumed-but-schema-present field already gets, or document in
`jurisdictions/SCOPE-FREEZE.md` that escalator schedules are accepted for
future use but not yet surfaced anywhere.

### IN-02: `Money.currency` and cross-currency fields are unconstrained free-text strings

**File:** `engine/models.py:100-102`

**Issue:** `Money.currency: str` accepts any string, with no validation
against `Jurisdiction.currency` or an ISO-4217 allow-list. A rule file
could declare a `w2_cap_amount` or `per_project_cap` in a different
currency than the jurisdiction's own declared `currency` field, and
nothing in the schema or the engine would catch the mismatch — the
engine would silently compare/subtract values across currencies without
converting, since none of the arithmetic in `engine/credit.py` or
`engine/net_cash.py` checks that a `Money.currency` it reads matches the
`Figure.unit` it's about to operate against.

**Fix:** Out of scope for Phase 2's two curated jurisdictions (both
single-currency, USD/GBP, and hand-verified), but worth a schema-level
cross-check (`Money.currency == jurisdiction.currency` at
`JurisdictionRuleSet` validation time, or an explicit currency-conversion
step where a cross-currency `Money` is intentional) before a future
multi-currency jurisdiction is curated.

---

_Reviewed: 2026-08-25T16:53:03Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
