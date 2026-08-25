---
phase: 02-engine-spine-incentive-interpreter
plan: 08
subsystem: engine
tags: [pydantic, validation, decimal, jurisdiction-rules, incentive-engine]

requires:
  - phase: 02-engine-spine-incentive-interpreter
    provides: "JurisdictionRuleSet schema (plan 02-01) and multi-programme stacking/exclusivity resolution in engine/pipeline.py (plan 02-06)"
provides:
  - "A load-time model_validator on JurisdictionRuleSet resolving every declared stacks_with and mutually_exclusive_with edge against declared programme ids"
  - "A minimum-length-1 constraint on JurisdictionRuleSet.programmes"
affects: [02-verification, jurisdictions, engine-figure-provenance]

actuals:
  tokens: 3222
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Cross-field model_validator(mode='after') on a Pydantic schema class, resolving related list fields against a computed set of valid ids, mirroring Programme's existing _corporation_tax_rate_required_when_taxable idiom"
    - "Field(min_length=1) as the schema-boundary fix for an unreachable-defect class, leaving the downstream aggregation function (combined_confidence) untouched"

key-files:
  created: []
  modified:
    - engine/models.py
    - engine/pipeline.py
    - tests/test_engine_models.py

key-decisions:
  - "Both edge kinds (stacks_with, mutually_exclusive_with) validated in one model_validator on JurisdictionRuleSet, not two separate validators — WR-02's substance is that the two edge kinds cannot drift apart"
  - "Ids compared with plain Python string equality only — no strip/lower/casefold — a case- or whitespace-differing id is a different id and raises rather than resolving"
  - "engine/pipeline.py's existing runtime ValueError for an unknown mutually_exclusive_with id kept as documented defence-in-depth (unreachable through load_ruleset, still reachable for a bypassing in-memory construction), not deleted"
  - "engine/figure.py left untouched — WR-04 fixed at the JurisdictionRuleSet schema boundary (min_length=1) rather than by changing combined_confidence's documented empty-sequence contract"
  - "Two atomic commits split from what was authored as one coupled edit, to preserve the plan's Task 1 / Task 2 boundary in git history despite both tasks touching the same class"

requirements-completed: [INC-03, JUR-05, PRV-02]

coverage:
  - id: D1
    description: "A rule file with a self-referencing or dangling stacks_with/mutually_exclusive_with edge raises pydantic.ValidationError at load_ruleset time, naming the programme, field, and offending id"
    requirement: INC-03
    verification:
      - kind: unit
        ref: "tests/test_engine_models.py#test_self_referencing_mutual_exclusivity_raises"
        status: pass
      - kind: unit
        ref: "tests/test_engine_models.py#test_self_referencing_stacks_with_raises"
        status: pass
      - kind: unit
        ref: "tests/test_engine_models.py#test_unknown_stacks_with_reference_raises"
        status: pass
      - kind: unit
        ref: "tests/test_engine_models.py#test_unknown_mutually_exclusive_with_reference_raises"
        status: pass
      - kind: unit
        ref: "tests/test_engine_models.py#test_edge_id_differing_only_by_case_is_treated_as_unknown"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every currently-committed rule file (jurisdictions/ and both fixture directories) still loads through load_ruleset after the new validators were added"
    requirement: JUR-05
    verification:
      - kind: unit
        ref: "tests/test_engine_models.py#test_every_committed_rule_file_still_loads"
        status: pass
    human_judgment: false
  - id: D3
    description: "A JurisdictionRuleSet with an empty programmes list raises pydantic.ValidationError, both on direct construction and round-tripped through load_ruleset, rather than reaching combined_confidence's empty-sequence default"
    requirement: PRV-02
    verification:
      - kind: unit
        ref: "tests/test_engine_models.py#test_empty_programmes_list_raises"
        status: pass
      - kind: unit
        ref: "tests/test_engine_models.py#test_empty_programmes_list_raises_through_load_ruleset"
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-08-25
status: complete
---

# Phase 02 Plan 08: Rule-file edge and empty-programme validation Summary

**A `model_validator` on `JurisdictionRuleSet` rejects self-referencing or dangling `stacks_with`/`mutually_exclusive_with` edges at load time, and a `Field(min_length=1)` constraint rejects a zero-programme rule file, closing WR-01, WR-02 and WR-04 from 02-VERIFICATION.md.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-08-25T18:19:00Z
- **Completed:** 2026-08-25T18:41:00Z
- **Tasks:** 2
- **Files modified:** 3 (`engine/models.py`, `engine/pipeline.py`, `tests/test_engine_models.py`)

## Accomplishments
- A `JurisdictionRuleSet.model_validator(mode="after")` resolves every declared `stacks_with` and `mutually_exclusive_with` entry, on every declared programme, against the set of declared programme ids — a self-reference or a dangling reference now raises `pydantic.ValidationError` at `load_ruleset` time, naming the programme id, the field, and (for a dangling reference) the sorted declared ids.
- Ids are compared with exact Python string equality — no whitespace trimming, no case folding — so an id differing only by case or surrounding whitespace from a declared id is treated as unknown and raises, never silently coerced into a match.
- `engine/pipeline.py::_resolve_mutual_exclusivity`'s prior runtime `ValueError` for an unknown id is now unreachable through `load_ruleset` and is kept, with an added comment, as documented defence-in-depth rather than deleted.
- `JurisdictionRuleSet.programmes` now carries a Pydantic `min_length=1` constraint: a rule file declaring zero programmes raises rather than loading and later producing a `validated`, source-less, date-less $0 jurisdiction total through `combined_confidence`'s empty-sequence default. `engine/figure.py` is unmodified — the fix is at the schema boundary, not in the aggregation function.
- Eight new tests added to `tests/test_engine_models.py`, including a non-vacuous glob-driven test proving every currently-committed rule file (both `jurisdictions/` and both `tests/fixtures/jurisdictions/` directories) still loads under the new validators.

## Task Commits

Each task was committed atomically:

1. **Task 1: WR-01 and WR-02 — every declared programme edge resolves, or the rule file raises** - `0497bac` (feat)
2. **Task 2: WR-04 — a jurisdiction with no programmes is an error, not a confident $0** - `e9cded3` (feat)

_Note: both tasks were authored together as one coupled edit to `JurisdictionRuleSet` (the plan itself frames WR-01/WR-02/WR-04 as "one fix in one place"); the edit was manually split back into two commits — first without the `min_length` constraint and its two tests, then with it — to preserve the plan's own Task 1/Task 2 boundary in git history, verifying the full suite green at each split point._

## Files Created/Modified
- `engine/models.py` - Added `_programme_edges_resolve_to_declared_ids` model_validator on `JurisdictionRuleSet`; added `Field(min_length=1)` to `programmes`; imported `Field` from pydantic
- `engine/pipeline.py` - Added a comment on `_resolve_mutual_exclusivity`'s existing runtime `ValueError`, documenting it as now-redundant defence-in-depth given the load-time validator
- `tests/test_engine_models.py` - Added `_make_programme`/`_make_two_programme_ruleset` local helpers and 8 new tests covering self-reference, dangling reference, case-sensitivity, the non-vacuous rule-file-loads check, and the empty-programmes constraint (direct construction + round-tripped through a temp YAML file and `load_ruleset`)

## Decisions Made
- Both edge kinds validated in one `model_validator`, per WR-02's explicit "cannot drift apart" requirement.
- Plain string equality for id comparison, no normalization, per the plan's adjacency-edge truth and to avoid silently coercing a near-miss id into a match.
- `engine/pipeline.py`'s existing runtime guard kept as documented dead-but-safe defence-in-depth rather than removed, since `price_jurisdiction` also accepts an in-memory-constructed `JurisdictionRuleSet` that goes through the same Pydantic validation path.
- `engine/figure.py::combined_confidence` left untouched; WR-04's fix lives entirely at the `JurisdictionRuleSet` schema boundary.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reworded validator docstring to avoid tripping the plan's own no-normalization grep gate**
- **Found during:** Task 1 (after initial implementation, running the plan's own acceptance-criteria grep)
- **Issue:** The validator's docstring explained the "no `.strip()`, no `.lower()`/`.casefold()`" comparison rule using the literal function-call syntax, which is itself matched by the plan's acceptance-criteria grep (`grep -vE "^\s*#" engine/models.py | grep -cE "strip\(\)|lower\(\)|casefold"`, expected 0) — the same "docstring literally contains the banned token" pitfall `tests/test_engine_models.py`'s own module docstring flags as a known trap from `02-01-SUMMARY.md`.
- **Fix:** Reworded the docstring to describe the behavior in prose ("no whitespace trimming, no case folding, no fuzzy matching") without using the literal `.strip()`/`.lower()`/`.casefold()` call syntax.
- **Files modified:** engine/models.py
- **Verification:** `grep -vE "^\s*#" engine/models.py | grep -cE "strip\(\)|lower\(\)|casefold"` now returns 0
- **Committed in:** 0497bac (Task 1 commit)

**2. [Rule 1 - Bug] Removed quotes from the new validator's return type annotation**
- **Found during:** Task 1, running `uv run ruff check engine/models.py`
- **Issue:** The plan's `read_first` instructed mirroring `Programme._corporation_tax_rate_required_when_taxable`'s exact idiom, which returns a quoted forward-reference type (`-> "Programme"`) — that pattern trips ruff's UP037 (quotes unnecessary given `from __future__ import annotations`). Mirroring it verbatim on the new validator would have added a second instance of a rule already-latent in the file.
- **Fix:** Wrote the new validator's return annotation unquoted (`-> JurisdictionRuleSet`), which is equivalent under `from __future__ import annotations` and ruff-clean. The pre-existing instance on `Programme`'s validator was left as-is (out of scope, unrelated to this plan's task).
- **Files modified:** engine/models.py
- **Verification:** `uv run ruff check engine/models.py` reports zero UP037 findings on the new code (one pre-existing UP037 remains on the unrelated, unmodified `Programme` validator)
- **Committed in:** 0497bac (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — corrections to satisfy the plan's own stated acceptance criteria / lint gate, discovered and fixed within Task 1 before its commit)
**Impact on plan:** Neither changed the validator's behavior or test coverage; both are wording/style corrections caught by the plan's own verification commands. No scope creep.

## Issues Encountered

**`uv run ruff check engine/ tests/` does not exit 0 — this predates this plan and is unrelated to its changes.** Task 1 and Task 2 both list this command as an acceptance criterion assuming a clean baseline. Verified via `git stash` before making any change: the full `engine/ tests/` tree already reported 294 ruff findings (mostly `FURB157` verbose `Decimal("N")` constructors, `RUF022` unsorted `__all__` lists, and `ISC004` implicit string concatenation, spread across files this plan does not touch) before this plan's first edit. This plan's own three files (`engine/models.py`, `engine/pipeline.py`, `tests/test_engine_models.py`) were left at 5 pre-existing findings — the identical 5 present on the same three files before this plan started, confirmed via the same stash comparison — and this plan's new code introduces zero new findings (one new `UP037` was introduced by mirroring the plan's own instructed idiom and was immediately fixed, see Deviations #2, dropping the file's total by one from baseline). Per the executor's scope-boundary rule ("do not auto-fix pre-existing issues unrelated to current task... in unrelated files"), the 293 remaining pre-existing findings across `engine/`/`tests/` were left untouched rather than bulk-fixed as an unplanned, unbounded change. Recorded to `.planning/WINDOWS.md` as a `lint-warning` entry (kind, phase 02, `engine/pipeline.py`) so it stays visible at ship time.

All five plan-level `<verification>` checks that do not depend on this pre-existing condition are green: `uv run pytest tests/ -q` (155 passed, up from the 147-test baseline this session started with — Task 1 added 6 tests, Task 2 added 2), every committed rule file still loads through `load_ruleset`, the self-referencing/dangling/empty-programmes cases each raise (proven by their own tests), and `engine/figure.py` / `jurisdictions/SCOPE-FREEZE.md` are both unmodified (absent from `git diff --name-only` across both commits). `bash .github/scripts/vendor-scan.sh` exits 0.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- WR-01, WR-02 and WR-04 from `02-VERIFICATION.md` are closed: a malformed rule file (self-referencing edge, dangling edge, or zero programmes) now fails loudly at `load_ruleset` time rather than pricing a jurisdiction with a silently-dropped programme, a false derivation-trail reference, or a confident $0.
- The pre-existing repo-wide ruff backlog (293 findings across `engine/`/`tests/`, none introduced by this plan) remains open and tracked in `.planning/WINDOWS.md` — a future phase or a dedicated lint-cleanup plan should address it before it accumulates further, since it currently makes the `ruff check` acceptance-criteria gate ineffective for any plan touching these directories.
- No blockers for the next plan in this phase.

---
*Phase: 02-engine-spine-incentive-interpreter*
*Completed: 2026-08-25*
