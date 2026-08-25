---
phase: 02-engine-spine-incentive-interpreter
plan: 03
subsystem: engine
tags: [qualifying-base, decimal, incentive-engine, closed-registry, provenance]

requires:
  - phase: 02-engine-spine-incentive-interpreter
    provides: >
      02-01's complete engine spine (Figure, JurisdictionRuleSet schema,
      closed HANDLER_REGISTRY skeleton, the one-type-implemented
      compute_qualifying_base dispatch) and 02-02's property-tested
      provenance/rounding contracts, which this plan's new handlers must
      keep green (every adjustment step still appends a derivation line
      unconditionally).
provides:
  - "engine/qualifying_base.py — all four base-definition types (total_qualified_spend, labour_only, local_hires_only, lesser_of_pct_core_or_actual_local) plus the custom escape hatch, with excluded_line_items subtraction and the minimum-spend hard cliff applied uniformly across every type"
  - "engine/handlers/__init__.py — HANDLER_REGISTRY's first real entry (labour_plus_quarter_local_hires), proving the closed dict-literal escape hatch is genuinely exercised, not merely declared"
  - "tests/fixtures/jurisdictions/synthetic-basedefs.yaml, synthetic-mincliff.yaml — synthetic_fixture-status fixtures proving the four-types-from-one-budget and minimum-spend-cliff behaviours"
  - "tests/test_engine_qualifying_base.py — 17 tests covering INC-01 and INC-09 as executable boundary/unit assertions, plus the fixture-vs-curated directory-hygiene guard"
affects: [02-04, 02-05, 02-06, 03-new-york-end-to-end]

actuals:
  tokens: 11222
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Single compute_qualifying_base dispatch computes a raw (base_type, derivation) pair via _raw_base, then applies excluded_line_items and the minimum-spend cliff uniformly to every type — no per-type special-casing after the raw-value dispatch"
    - "SpendBreakdown gains an optional line_items: dict[str, Decimal] field (default empty) that excluded_line_items names into; subtraction is applied in declaration order but is order-independent by arithmetic, proven directly rather than assumed"
    - "TYPE_CHECKING-guarded imports in engine/handlers/__init__.py break the qualifying_base <-> handlers circular-import risk: handlers resolves custom_handler_id strings that qualifying_base calls, and qualifying_base's SpendBreakdown type is only needed for handler type hints, never at runtime, so from __future__ import annotations plus a TYPE_CHECKING guard is sufficient"

key-files:
  created:
    - tests/fixtures/jurisdictions/synthetic-basedefs.yaml
    - tests/fixtures/jurisdictions/synthetic-mincliff.yaml
    - tests/test_engine_qualifying_base.py
  modified:
    - engine/qualifying_base.py
    - engine/handlers/__init__.py

key-decisions:
  - "The 'actual local core expenditure' candidate in lesser_of_pct_core_or_actual_local is SpendBreakdown.core_expenditure itself (not local_hires_spend) — per the D-02 interpreter-only boundary, no cost-localisation pipeline exists yet, so every dollar of core expenditure is treated as local at this stage. Verified against the plan's own worked example: 80% of a $10M core ($8M) vs. actual local core ($10M) correctly yields $8M as the smaller candidate."
  - "excluded_line_items subtracts named components from a new SpendBreakdown.line_items: dict[str, Decimal] field (default empty), added to the existing frozen dataclass rather than to engine/models.py — keeps the change inside this plan's declared files_modified. An excluded-item name absent from line_items raises KeyError rather than silently treating it as zero."
  - "The custom escape hatch's first real registry entry (labour_plus_quarter_local_hires = labour_spend + 0.25 * local_hires_spend) was chosen specifically to produce a value ($7,000,000) distinct from all four declarative types' outputs on the shared $10M/$6M/$4M budget ($10M/$6M/$4M/$8M) — proving the escape hatch computes something the four types cannot express, not a disguised duplicate."
  - "The minimum-spend cliff (already correctly implemented as a hard step function in 02-01) needed no functional change for Task 2 — only a comment recording the base-vs-total ordering hazard at its call site, since it already evaluated against the dispatched qualifying base rather than raw spend.total_spend."

patterns-established:
  - "_raw_base(programme, spend) -> (Decimal, str): the single per-type dispatch point: total/labour/local-hires read a spend field directly, lesser-of computes and compares two candidates, custom resolves through HANDLER_REGISTRY — all four converge into the same excluded-line-items -> minimum-spend post-processing pipeline in compute_qualifying_base."

requirements-completed: [INC-01, INC-09]

coverage:
  - id: D1
    description: "One identical $10,000,000 budget yields four different, individually-correct qualifying bases under total_qualified_spend ($10M), labour_only ($6M), local_hires_only ($4M) and lesser_of_pct_core_or_actual_local ($8M) — a dispatch bug routing every type to the same handler would collapse this to fewer than four distinct values"
    requirement: "INC-01"
    verification:
      - kind: unit
        ref: "tests/test_engine_qualifying_base.py::test_base_definition_types"
        status: pass
    human_judgment: false
  - id: D2
    description: "The custom escape hatch prices through HANDLER_REGISTRY's first real entry when custom_handler_id is known, and raises KeyError naming the identifier when it is not — never a silent fallback to a default base (T-02-03 mitigation)"
    verification:
      - kind: unit
        ref: "tests/test_engine_qualifying_base.py::test_custom_handler_prices_through_registry"
        status: pass
      - kind: unit
        ref: "tests/test_engine_qualifying_base.py::test_custom_handler_id_unknown_raises_keyerror"
        status: pass
      - kind: unit
        ref: "manual smoke test: grep -rn --include='*.py' -E '(getattr|importlib)' engine/handlers/ | wc -l returns 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "When the two lesser-of candidates are exactly equal, the result is that value returned once (never doubled), with a derivation line stating the candidates were equal"
    requirement: "INC-01"
    verification:
      - kind: unit
        ref: "tests/test_engine_qualifying_base.py::test_equal_candidates_lesser_of_returns_value_once"
        status: pass
    human_judgment: false
  - id: D4
    description: "A qualified spend of exactly Decimal('0') yields a qualifying base of exactly Decimal('0') under every one of the four types plus custom, each with a non-empty derivation naming its type; the Core expenditure (pre-cap) inputs edge is preserved on all four declarative types"
    requirement: "INC-01"
    verification:
      - kind: unit
        ref: "tests/test_engine_qualifying_base.py::test_zero_budget_yields_zero_base_with_derivation (5 parametrized cases)"
        status: pass
    human_judgment: false
  - id: D5
    description: "excluded_line_items are applied in declaration order and re-ordering the list without changing membership does not change the resulting base; a named item absent from SpendBreakdown.line_items raises KeyError"
    verification:
      - kind: unit
        ref: "tests/test_engine_qualifying_base.py::test_excluded_line_items_are_order_independent"
        status: pass
      - kind: unit
        ref: "tests/test_engine_qualifying_base.py::test_excluded_line_item_unknown_name_raises_keyerror"
        status: pass
    human_judgment: false
  - id: D6
    description: "Every file under tests/fixtures/jurisdictions/ declares jurisdiction.status synthetic_fixture, and no file under jurisdictions/ does — a reviewer can never mistake a test fixture for curated government data (T-02-07 mitigation)"
    verification:
      - kind: unit
        ref: "tests/test_engine_qualifying_base.py::test_directory_hygiene_fixture_status_vs_curated_status"
        status: pass
      - kind: unit
        ref: "manual smoke test: grep -c 'synthetic_fixture' tests/fixtures/jurisdictions/synthetic-basedefs.yaml returns 2; grep -rlc 'synthetic_fixture' jurisdictions/*.yaml | wc -l returns 0"
        status: pass
    human_judgment: false
  - id: D7
    description: "A minimum-spend threshold is a step function proven at threshold-1/threshold/threshold+1: $99,999 yields exactly $0, $100,000 and $100,001 yield the unchanged base — never an interpolated or ramped value"
    requirement: "INC-09"
    verification:
      - kind: unit
        ref: "tests/test_engine_qualifying_base.py::test_minimum_spend_cliff (3 parametrized boundary cases)"
        status: pass
    human_judgment: false
  - id: D8
    description: "The minimum-spend cliff is evaluated against the qualifying base produced by the base-definition dispatch, not against raw total spend; a labour-only programme reducing $110,000 total to $90,000 labour falls below a $100,000 threshold. A programme declaring no minimum spend still emits a derivation line stating none is declared."
    requirement: "INC-09"
    verification:
      - kind: unit
        ref: "tests/test_engine_qualifying_base.py::test_minimum_spend_evaluated_against_base_not_total"
        status: pass
      - kind: unit
        ref: "tests/test_engine_qualifying_base.py::test_minimum_spend_not_declared_still_emits_derivation"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-08-25
status: complete
---

# Phase 2 Plan 03: Qualifying-Base Dispatch — All Four Types Plus the Closed Escape Hatch Summary

**All four `base_definition.type` values (total/labour/local-hires/lesser-of) plus the `custom` escape hatch now compute distinct, individually-correct qualifying bases from one shared budget, with excluded-line-item subtraction and a hard minimum-spend cliff applied uniformly across every type.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-08-25T11:36:09Z (approx., from prior plan's completion)
- **Completed:** 2026-08-25T11:47:13Z
- **Tasks:** 2
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- `engine/qualifying_base.py` widens `compute_qualifying_base` from the
  one type 02-01's tracer proved (`total_qualified_spend`) to all four
  declared types plus the `custom` escape hatch: `labour_only` and
  `local_hires_only` read directly off the corresponding `SpendBreakdown`
  field; `lesser_of_pct_core_or_actual_local` computes both candidates
  (a declared percentage of core expenditure, and actual local core
  expenditure — the latter equal to `core_expenditure` itself under the
  D-02 boundary, since no localisation split exists yet) and returns the
  smaller, with an explicit equal-candidates branch that returns the tied
  value once rather than doubling it. Every one of the five dispatch paths
  (four types + custom) now records the `Core expenditure (pre-cap)`
  `inputs` edge, not just the original tracer's `total_qualified_spend`
  branch — preserving the edge Plan 02-05's ceiling split depends on.
- `engine/handlers/__init__.py`'s `HANDLER_REGISTRY` gains its first real
  entry, `labour_plus_quarter_local_hires`, proving the closed dict-literal
  escape hatch is genuinely exercised end-to-end rather than merely
  declared empty. Resolving an identifier absent from the registry still
  raises `KeyError` naming it — no `getattr`/`importlib` anywhere in the
  package (verified by grep, part of both this plan's and 02-02's source-
  level security gates).
- `excluded_line_items` is now real: `SpendBreakdown` gains an optional
  `line_items: dict[str, Decimal]` field, and a new
  `_apply_excluded_line_items` step subtracts every named component in
  declaration order, uniformly across all five dispatch paths, before the
  minimum-spend check. Order-independence (re-ordering the list without
  changing membership never changes the result) is asserted directly, not
  assumed from arithmetic.
- The minimum-spend cliff — already a correct hard step function from
  02-01 — is proven at exactly `$99,999` / `$100,000` / `$100,001` against
  a `$100,000` threshold, proven to evaluate against the *qualifying base*
  the dispatch produces rather than raw total spend (a labour-only
  programme reducing $110,000 total to $90,000 labour correctly falls
  below the threshold), and proven to still emit a derivation line when no
  threshold is declared at all.
- Two new `synthetic_fixture`-status YAML fixtures
  (`tests/fixtures/jurisdictions/synthetic-basedefs.yaml`,
  `synthetic-mincliff.yaml`) and a directory-hygiene test close the loop
  on T-02-07: every file under `tests/fixtures/jurisdictions/` is
  structurally guaranteed to declare `synthetic_fixture`, and no file
  under `jurisdictions/` (the curated set) does.

## Task Commits

Each task was committed atomically:

1. **Task 1: All four base-definition types plus the closed-registry
   escape hatch** - `13b9838` (feat)
2. **Task 2: Minimum-spend thresholds as tested cliffs, never ramps** -
   `3c0ff54` (test)

_Both tasks are `type="auto" tdd="true"` without a preceding RED-phase
failing-test commit — the widening work and its tests were written and
verified together per task, matching 02-02's precedent of no dedicated
RED/GREEN split when there is no pre-existing broken behaviour to prove
first._

## Files Created/Modified

- `engine/qualifying_base.py` - `_raw_base` dispatch covering all four
  declarative types plus `custom`; `_apply_excluded_line_items`;
  `_lesser_of_pct_core_or_actual_local`; `_custom`; `SpendBreakdown` gains
  `line_items: dict[str, Decimal]`; minimum-spend call site gains an
  ordering-hazard comment
- `engine/handlers/__init__.py` - `HANDLER_REGISTRY`'s first real entry,
  `labour_plus_quarter_local_hires`; `TYPE_CHECKING`-guarded imports break
  the `qualifying_base` <-> `handlers` circular-import risk
- `tests/fixtures/jurisdictions/synthetic-basedefs.yaml` - one synthetic
  jurisdiction, five programmes (one per base-definition type plus
  `custom`) over a shared $10,000,000 budget
- `tests/fixtures/jurisdictions/synthetic-mincliff.yaml` - one synthetic
  jurisdiction, two programmes ($100,000 minimum spend; no minimum spend),
  mirroring Connecticut's real lower band in magnitude only
- `tests/test_engine_qualifying_base.py` - 17 tests: four-distinct-values
  proof, custom-handler proof (known + unknown identifier), equal-
  candidates tie, zero-budget across all five paths, excluded-line-item
  order-independence and unknown-name failure, directory hygiene, and the
  three minimum-spend cliff behaviours

## Decisions Made

See `key-decisions` in frontmatter for the full rationale on: (1) "actual
local core expenditure" = `core_expenditure` under the D-02 boundary; (2)
`line_items` added to `SpendBreakdown` rather than `engine/models.py`, to
stay inside this plan's declared `files_modified`; (3) the custom
handler's formula chosen specifically to produce a value distinct from all
four declarative outputs on the shared budget; (4) no functional change
needed to the minimum-spend step itself, only a documenting comment.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/cleanup] Minor ruff findings cleaned up in
`engine/qualifying_base.py` and `engine/handlers/__init__.py`**
- **Found during:** Task 2, running `uv run ruff check` against the files
  this plan touches before finalizing
- **Issue:** `__all__` not isort-sorted in `engine/qualifying_base.py`;
  redundant quoted forward-reference type annotations
  (`-> "SpendBreakdown"`, `programme: "Programme"`) now that
  `from __future__ import annotations` already defers every annotation to
  a lazily-evaluated string; `Callable` imported from `typing` instead of
  `collections.abc` in `engine/handlers/__init__.py`
- **Fix:** Sorted `__all__`; removed the now-redundant quotes; moved the
  `Callable` import
- **Files modified:** `engine/qualifying_base.py`,
  `engine/handlers/__init__.py`
- **Verification:** `uv run ruff check` on both files reports only the
  pre-existing `FURB157` (`Decimal("...")` vs `Decimal(...)`) style —
  already the established convention throughout the committed codebase
  (e.g. `tests/test_engine_against_validation_pairs.py`), not introduced
  by this plan and not fixed here to stay consistent with that convention.
  Full suite green throughout (82 passed).
- **Committed in:** `3c0ff54` (part of Task 2's commit)

---

**Total deviations:** 1 auto-fixed (1 lint cleanup, zero behaviour change).
**Impact on plan:** No scope creep — the cleanup touched only the two
files this plan already declared as `files_modified`, and no test
assertion or computed value changed as a result.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All four base-definition types and the closed escape hatch are proven
  correct and provenance-complete; plan 02-05 (this wave's other engine
  file, `engine/credit.py`) reads the `Core expenditure (pre-cap)` edge
  this plan preserved on every one of the five dispatch paths.
- The full test suite is green at 82 tests (up from 65 before this plan:
  Phase 1's 35, plus 02-01's 5, plus 02-02's 25, plus this plan's 17).
- No blockers. This plan's `files_modified` were followed exactly —
  `engine/qualifying_base.py`, `engine/handlers/__init__.py`, one test
  module, and two fixtures — no sibling plan's files were touched.

---

*Phase: 02-engine-spine-incentive-interpreter*
*Completed: 2026-08-25*

## Self-Check: PASSED

All 5 created/modified files verified present on disk (`[ -f ]`). Both
task commit hashes (`13b9838`, `3c0ff54`) verified present in
`git log --oneline --all`. Full suite (`uv run pytest tests/ -q`) verified
green at 82 passed immediately before writing this summary.
