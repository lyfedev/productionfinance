---
phase: 02-engine-spine-incentive-interpreter
reviewed: 2026-08-25T20:00:00Z
depth: standard
scope: gap-closure-delta (plans 02-07, 02-08, 02-09 only; diff range 6ce2d9d^..HEAD)
supersedes: previous 02-REVIEW.md (pre-gap-closure pass, covering plans 02-01..02-06)
files_reviewed: 8
files_reviewed_list:
  - engine/credit.py
  - engine/models.py
  - engine/pipeline.py
  - engine/qualifying_base.py
  - tests/fixtures/jurisdictions/synthetic-blend-adjustments.yaml
  - tests/test_engine_against_validation_pairs.py
  - tests/test_engine_credit.py
  - tests/test_engine_models.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 2 Gap-Closure Review Report (plans 02-07, 02-08, 02-09)

**Reviewed:** 2026-08-25T20:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found (1 Warning, 2 Info — no Critical/Blocker findings)

## Summary

This pass reviews only the delta introduced by the three gap-closure plans (02-07
CR-01 fix, 02-08 WR-01/WR-02/WR-04, 02-09 WR-03 + validation-pairs re-coupling),
per `git diff 6ce2d9d^..HEAD`. The previous phase review and verification
(`02-VERIFICATION.md`) identified CR-01 as a blocking defect — the
`blended_by_ceiling_split` rate branch silently discarded minimum-spend,
excluded-line-item, and per-person-ceiling reductions while its derivation
trail claimed they were applied.

I traced the new "effective core expenditure" arithmetic in
`engine/credit.py` line by line against the hand-worked derivation in the new
`synthetic-blend-adjustments.yaml` fixture and independently reproduced all
three programmes' expected values by re-running the arithmetic by hand. The
fix is **correct** for the one base-definition/rate-structure combination it
is exercised against (`lesser_of_pct_core_or_actual_local` +
`blended_by_ceiling_split`) — I initially suspected a percentage-cap
scale/domain mismatch (subtracting a "post-cap-selection" dollar reduction
from a "pre-cap" core-expenditure figure), traced it through by hand and by
direct execution, and confirmed the arithmetic is self-consistent given the
current D-02 interpreter-only boundary (`actual_local == core_expenditure`
always, at this phase). All 162 tests pass; the CR-01 regression fixture's
five new tests are non-vacuous, assert on exact values with named
wrong-answer guards, and independently verify the derivation trail states
what actually happened.

The WR-01/WR-02 (`engine/models.py`) and WR-04 edge/empty-programme
validators are sound: exact-string comparison (no case/whitespace
normalization, correctly tested), self-reference and dangling-reference
both raise, `Field(min_length=1)` closes the empty-programmes gap at the
schema boundary rather than patching the aggregation function. WR-03's
loan-out withholding schedule overlap guard (`engine/credit.py`) implements
a correct standard closed-interval overlap test and is proven not to
false-positive on the committed Georgia-style schedule's abutting bands.

The one substantive finding (WR-05, below) is a **latent, currently
unreachable analogue of CR-01's own root cause**, introduced by this
gap-closure's own new code: the effective-core-expenditure carry-forward
logic assumes the qualifying-base value it reads adjustment deltas from is
scaled consistently with `core_expenditure`. That assumption is only true
for `base_definition.type: lesser_of_pct_core_or_actual_local` (the only
type any committed `blended_by_ceiling_split` fixture uses) — it silently
produces a plausible-looking but arithmetically meaningless "effective core
expenditure" derivation line for any other `base_definition.type`
(`total_qualified_spend`, `labour_only`, `local_hires_only`, `custom`)
combined with `blended_by_ceiling_split` and a binding exclusion or
per-person ceiling. No currently curated or committed rule file triggers
this, which is why it is scored Warning rather than Critical — but it is
exactly the same shape of defect (a derivation trail that reads as true and
isn't) that this entire gap-closure phase exists to eliminate, and it lives
in the code this phase just rewrote.

## Warnings

### WR-05: `blended_by_ceiling_split`'s effective-core-expenditure carry-forward silently mixes domains for any `base_definition.type` other than `lesser_of_pct_core_or_actual_local`

**File:** `engine/credit.py:565-576`

**Issue:** The new CR-01 fix computes `total_reduction` (excluded-line-items
total plus the per-person-ceiling's dollar reduction) as a delta against
`qualifying_base_input.value` — the *base-definition-typed* qualifying base
(which may read `spend.total_spend`, `spend.labour_spend`,
`spend.local_hires_spend`, or a `custom` handler's output) — and then
subtracts that delta directly from `core_expenditure_figure.value`
(`spend.core_expenditure`, a *different* `SpendBreakdown` field in general).
This is arithmetically sound only when the two figures are provably the same
scale, which today happens to hold for `lesser_of_pct_core_or_actual_local`
because of the D-02 interpreter-only boundary (`actual_local ==
core_expenditure`, so `min(pct_cap * core_expenditure, core_expenditure)` is
always scaled to `core_expenditure`). For any other `base_definition.type`,
`qualifying_base_input.value` is computed from a field of `SpendBreakdown`
that is independent of `core_expenditure` — subtracting a reduction measured
in that other field's domain from `core_expenditure` produces a number with
no defined meaning, while the derivation line states it plainly as if it
were a real, connected figure (violating the same PRV-03 "readable
derivation reason" promise CR-01 was fixed to restore).

Reproduced directly (not hypothetical) with a synthetic programme:
`base_definition.type: total_qualified_spend`, `spend.total_spend =
30,000,000`, `spend.core_expenditure = 18,000,000`, one excluded line item
of `1,000,000` (subtracted from the `total_spend`-domain qualifying base).
The engine emits:

```
blended_by_ceiling_split effective core expenditure: raw core
expenditure 18000000 USD, minus total reduction 1000000 USD (excluded line
items 1000000 + per-person ceiling 0, ...) = effective core expenditure
17000000 USD
```

— a derivation line that reads as a coherent, traceable computation, but the
`1,000,000` reduction was never part of the `18,000,000` core-expenditure
figure it is subtracted from; it came out of an unrelated `30,000,000`
total. This is not reachable through any currently committed jurisdiction
file (the only two committed `blended_by_ceiling_split` fixtures —
`synthetic-uk-style.yaml` and the new `synthetic-blend-adjustments.yaml` —
both declare `base_definition.type: lesser_of_pct_core_or_actual_local`),
which is why it is not a Critical/blocker today. It is, however, a defect in
code this gap-closure plan wrote to fix exactly this class of bug, and it
will silently mis-price the first future jurisdiction that pairs
`blended_by_ceiling_split` with any other base-definition type and a binding
exclusion or per-person ceiling — with no test anywhere to catch it, since
no fixture exercises the combination.

**Fix:** Either (a) add an explicit guard in the `blended_by_ceiling_split`
branch raising `ValueError` when `programme.base_definition.type !=
"lesser_of_pct_core_or_actual_local"` and an exclusion or per-person-ceiling
reduction is non-zero, naming the unsupported combination explicitly
(cheapest, matches this codebase's existing "no requirement or curated
jurisdiction in this phase combines X with Y — extending it speculatively
would be an unverified guess" pattern already used two paragraphs above this
exact branch for uplift stacking); or (b) generalize the carry-forward to
read the reduction against whichever `SpendBreakdown` field
`base_definition.type` actually draws from, so the subtraction is always
domain-consistent. Given the 17-day hackathon window and that this
combination is not required by any curated jurisdiction in this phase,
option (a) — a loud, named raise — is the appropriate fix, not a silent
scope-restriction.

## Info

### IN-03: Zero-or-below short-circuit's derivation line omits excluded line items as a possible cause

**File:** `engine/credit.py:547-554`

**Issue:** The new short-circuit's derivation line attributes a zero-or-below
running base to "the declared adjustments (minimum-spend cliff and/or
per-person ceiling)" — but a sufficiently large `excluded_line_items`
reduction can, in principle (no `minimum_spend` declared, no per-person
ceiling), also drive `figure.value` at or below zero on its own (if
`base_definition.excluded_line_items` sums to more than the raw base). The
derivation line would then name causes that did not actually apply, which is
a minor instance of the same "derivation states something not quite true"
category this phase is otherwise disciplined about.

**Fix:** Add "and/or excluded line items" to the short-circuit's derivation
line, e.g. `"zero or below after the declared adjustments (minimum-spend
cliff, excluded line items, and/or per-person ceiling)"`.

### IN-04: Short-circuit skips the "always emit a line, even when zero" convention it sits beside

**File:** `engine/credit.py:541-554` vs. `602-611`

**Issue:** Two paragraphs below the short-circuit, the code comments
explicitly that "Both slices ALWAYS emit a derivation line, even when one is
zero" (PRV-03 discipline). The short-circuit branch itself does not follow
this: when it fires, neither the "effective core expenditure" line nor
either slice's line is ever emitted — only the one summary line. This is a
defensible, deliberate design choice (slicing is meaningless once the base
is non-positive) and is not incorrect, but it is a slight inconsistency with
the "no-op steps still get their own line" convention this same function
otherwise enforces strictly. Purely stylistic; no behavior change needed.

**Fix:** None required. Noted for consistency awareness only — could
optionally add a one-line note inside the short-circuit's derivation
explicitly stating "no slice lines follow" if a future reader finds the
asymmetry confusing.

## Verification Performed

- `uv run pytest tests/ -q` — 162 passed, 0 failed (matches all three
  plans' SUMMARY claims).
- `uv run ruff check` on all 8 in-scope files — all findings are the
  pre-existing, disclosed `FURB157`/`ISC004`/`RUF022` backlog (tracked in
  `.planning/WINDOWS.md` entries 2 and 4); no new rule categories.
- Hand-traced and independently re-derived (by hand and by direct script
  execution against `engine.credit`/`engine.qualifying_base`) all three
  `synthetic-blend-adjustments.yaml` programmes' expected gross-credit
  values (`6,496,000`; `6,904,000`/`6,768,000` split-adjustment values;
  `0` for the minimum-spend-cliff case) — all confirmed arithmetically
  correct for the `lesser_of_pct_core_or_actual_local` base type.
- Independently reproduced the WR-05 domain-mismatch finding via direct
  script execution (see Warning above) rather than by inspection alone.
- Confirmed `jurisdictions/us-ct.yaml`'s `transfer_discount.typical_rate_low`
  /`typical_rate_high` are genuinely `null` in the committed file (not
  altered by 02-09), corroborating the `unmet-truth` entry in
  `.planning/WINDOWS.md` (id 3) and the corresponding test's honesty.
- Confirmed `PerPersonCeilingTier.effective_from` is a required, non-null
  `date` field — the new overlap-check comparison logic cannot hit a
  null-comparison bug.
- Confirmed `stacks_with`/`mutually_exclusive_with` default to `[]` (never
  `None`) on `Programme`, so the new `model_validator`'s iteration is safe.
- Confirmed NY/CT curated rule files declare `excluded_line_items: []`, so
  the validation-pairs pipeline re-coupling (02-09) cannot hit
  `_apply_excluded_line_items`'s `KeyError` path via `price_jurisdiction`'s
  `SpendBreakdown.from_total` (empty `line_items`).

## Known, Already-Recorded Items (not re-litigated)

- Repo-wide pre-existing `ruff` backlog (~297 findings, `FURB157`/`RUF022`
  mostly) — accepted project convention, tracked in `.planning/WINDOWS.md`.
- `jurisdictions/us-ct.yaml`'s unsourced `transfer_discount` blocking
  Connecticut's pipeline-routed reproduction (WINDOWS.md entry 3,
  `unmet-truth`) — deliberate honesty, not a bug. The dedicated test
  (`test_christmas_always_reproduces_exactly_through_price_jurisdiction`)
  is well-constructed: it asserts the *raise* directly with a
  self-invalidating leading assertion (`assert not
  _pipeline_can_complete(...)`) that will fail loudly the moment
  `us-ct.yaml` is ever sourced with a real rate, so the test cannot go
  silently stale. No changes recommended to this test.

---

_Reviewed: 2026-08-25T20:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
