---
phase: 02-engine-spine-incentive-interpreter
verified: 2026-08-25T19:16:29Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 2/5
  gaps_closed:
    - "CR-01 (blended_by_ceiling_split silently discarding minimum-spend cliff, excluded-line-items subtraction and per-person-ceiling reduction while its derivation trail claimed all three were applied) — fixed by plan 02-07, independently reproduced fixed in this verification"
    - "Roadmap SC1 (base under own definition composing through to net cash) — the base-to-credit composition seam CR-01 broke is closed; independently reproduced"
    - "Roadmap SC2 (per-person ceilings, tier/uplift ordering, caps, minimum-spend cliffs each visibly change the result at a boundary) — independently reproduced for all three modelled rate structures, including the previously-broken blended_by_ceiling_split"
    - "Roadmap SC3 (every number carries a readable, truthful derivation reason) — the cliff programme's derivation now states \"qualifying base is $0\" and the returned credit is genuinely Decimal('0'); confirmed by direct execution, not by reading the test"
    - "WR-01 (self-referencing mutually_exclusive_with silently drops an eligible programme) — closed by plan 02-08, independently reproduced raising pydantic.ValidationError"
    - "WR-02 (dangling stacks_with id never validated) — closed by plan 02-08, in the same validator as WR-01"
    - "WR-04 (empty programmes list yields a confident, source-less $0) — closed by plan 02-08 via Field(min_length=1), independently reproduced raising"
    - "WR-03 (loan-out withholding schedule's closed-closed dated-range convention undocumented, no overlap guard) — closed by plan 02-09: convention now commented and named, overlap guard added and tested"
    - "Validation-pairs decoupling from price_jurisdiction — re-coupled by plan 02-09; Anora now reproduces Decimal('991190') through price_jurisdiction end to end (base -> credit -> net cash), independently reproduced"
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
---

# Phase 2: Engine Spine & Incentive Interpreter Verification Report

**Phase Goal:** One generic, data-driven engine turns a production spec plus a
jurisdiction rule file into a net-cash incentive figure whose every component
traces back to its own source.
**Verified:** 2026-08-25T19:16:29Z
**Status:** passed
**Re-verification:** Yes — after gap closure (plans 02-07, 02-08, 02-09)

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Qualifying base under own definition; gross credit converts to net cash by mechanism, net of audit fees, with arrival date | ✓ VERIFIED | CR-01's base→credit composition seam is closed; independently reproduced below. All four net-cash mechanisms remain independently tested and correct (unchanged by this gap-closure run). One honest, non-blocking data limitation is recorded separately (see "Recorded, Non-Blocking Limitation") |
| 2 | Per-person ceilings, tier/uplift ordering + stacking, per-project/annual caps, and minimum-spend cliffs each visibly change the result at a boundary | ✓ VERIFIED | Verified true for `flat` and `tiered_by_spend` (unchanged, previously verified) and now independently reproduced TRUE for `blended_by_ceiling_split`: injected minimum-spend cliff returns exactly `Decimal('0')`; excluded-line-item alone, per-person-ceiling alone, and both together return three pairwise-distinct values (`6904000`, `6768000`, `6496000`) — none byte-identical to the no-adjustment control (`7176000`) |
| 3 | Every figure carries source link, date checked, confidence tier, readable derivation reason | ✓ VERIFIED | PRV-01/PRV-02 mechanics unchanged and sound (previously verified). PRV-03: the cliff programme's derivation trail now states "qualifying base is $0" and the returned credit is genuinely `Decimal('0')` — number and claim agree, confirmed by direct execution walking the full derivation DAG, not by reading the test source |
| 4 | Eligibility answered separately from availability (annual allocation remaining) | ✓ VERIFIED | Unchanged since the previous pass; `Eligibility`/`Availability` remain two distinct dataclasses returned by two distinct functions; regression-checked via the full 162-test suite pass |
| 5 | A new jurisdiction is a rule file alone, zero engine code change | ✓ VERIFIED | Previously confirmed via `git show --name-only` on the additivity commit; regression-checked in this pass — the new gap-closure fixture (`synthetic-blend-adjustments.yaml`) declares jurisdiction id `zz-synthetic-blend-adjustments`, and `tests/test_engine_jurisdiction_additivity.py::test_no_jurisdiction_identifier_appears_in_engine_source` (glob-driven, non-vacuous) still passes with that id in scope |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Recorded, Non-Blocking Limitation (not a gap)

`jurisdictions/us-ct.yaml`'s real `transfer_discount.typical_rate_low`/`typical_rate_high`
are both `null` — CGS 12-217jj(e)(1) states Connecticut's credit is transferable but names
no market discount rate. `engine.net_cash.transferable` correctly refuses to fabricate a
conversion rate, so `price_jurisdiction` raises `ValueError` for every active Connecticut
pair. This is a genuine, disclosed **data** limitation, not an engine defect:

- Confirmed directly: `jurisdictions/us-ct.yaml`'s `transfer_discount` block genuinely
  declares both rates `null` (read the committed file directly in this verification).
- Christmas Always still reproduces `Decimal('1159502')` exactly through the direct
  base-then-credit path (`test_christmas_always_reproduces_exactly`, independently re-run).
- The pipeline-routed test (`test_christmas_always_reproduces_exactly_through_price_jurisdiction`)
  asserts the raise directly, with a self-invalidating leading assertion
  (`assert not _pipeline_can_complete(...)`) that will fail loudly — not silently pass — the
  moment `us-ct.yaml` is ever sourced with a real discount rate.
- `PIPELINE_ROUTABLE_PAIRS` excludes Connecticut structurally (by reading the declared
  `mechanism`/`transfer_discount` fields), not by a hardcoded jurisdiction id — a future
  sourced rate is picked up automatically.
- Inventing a discount rate to make this pass would violate the project's explicit honesty
  mandate ("never present a researched figure as validated"). Recorded in `.planning/WINDOWS.md`
  entry 3 (`unmet-truth`, open).

**Judgment:** this does not block the phase goal. The engine's `transferable` mechanism
itself is correct and independently tested (02-04); the gap is that one real jurisdiction's
own source document doesn't disclose a discount rate. New York, the other curated
jurisdiction, reproduces `Decimal('991190')` exactly through `price_jurisdiction` end to
end, proving the composition genuinely works when the underlying data is complete. Treating
an engine that correctly refuses to fabricate a missing figure as a phase failure would
invert the project's own honesty constraint.

### Independent Reproduction (this verification, not carried over from SUMMARY/REVIEW claims)

| Check | Command/method | Result | Status |
|-------|------|--------|--------|
| CR-01 fix, both adjustments | Loaded `synthetic-blend-adjustments.yaml` directly, built `SpendBreakdown` with `completion_bond` line item, ran `compute_qualifying_base` then `compute_gross_credit` with a W-2 compensation via `uv run python` (not via the test suite) | `blend-adjustments-both` = `Decimal('6496000')`; none of the four documented wrong values (`7176000`/`6307000`/`5045600`/`7632000`) | ✓ PASS — CR-01 genuinely fixed |
| CR-01 fix, cliff programme | Same method, `blend-adjustments-cliff` | `qualifying_base.value == 0`; `gross_credit.value == 0`; walked full derivation DAG, found "qualifying base is $0" line present | ✓ PASS — number and derivation claim agree |
| CR-01 fix, independence of adjustments | Same method, ceiling-only and excluded-only variants | `6768000` (ceiling alone), `6904000` (excluded alone), `6496000` (both) — three pairwise-distinct values | ✓ PASS |
| WR-01/WR-02, self-reference and dangling edges | Ran the 8 targeted `test_engine_models.py` tests directly (`-k "self_referencing or unknown or empty_programmes or every_committed or case_is_treated"`) | 8/8 passed | ✓ PASS |
| WR-04, empty programmes | Direct `pydantic.ValidationError` construction with `programmes=[]` via `uv run python` | Raised as expected | ✓ PASS |
| Curated files still load | `load_ruleset("jurisdictions/us-ny.yaml")`, `load_ruleset("jurisdictions/us-ct.yaml")` via direct execution | Both load without error | ✓ PASS |
| WR-03, dated-range adjacency + overlap guard | Ran the 2 targeted `test_engine_credit.py` tests (`-k "loanout_withholding_schedule_dated or overlapping_loanout"`) | 2/2 passed | ✓ PASS |
| Validation-pairs re-coupling | Ran full `tests/test_engine_against_validation_pairs.py` (13 tests) directly | 13/13 passed, including `test_anora_reproduces_exactly_through_price_jurisdiction` and the honest CT-raise test | ✓ PASS |
| WR-05 (new Warning) blast radius | `grep` for `blended_by_ceiling_split` + `base_definition.type` across every committed and fixture jurisdiction file | Only `lesser_of_pct_core_or_actual_local` base types pair with `blended_by_ceiling_split` in any committed file; `zz-fixture-throwaway.yaml`'s `labour_only`+`blended_by_ceiling_split` combination declares empty `excluded_line_items` and supplies no `per_person_compensations` to `price_jurisdiction` (confirmed by reading the file directly) — WR-05 is confirmed unreachable today | ✓ CONFIRMED non-blocking |
| Full test suite | `uv run pytest -q` (run once, per verifier constraints) | `162 passed, 1 warning in 2.45s` | ✓ PASS (matches all three plans' SUMMARY claims) |
| Vendor/eligibility scan | `bash .github/scripts/vendor-scan.sh` | `PASS: vendor-scan clean over '.' — no forbidden AWS AI service call-site tokens found`, exit 0 | ✓ PASS |
| Debt-marker scan | `grep -rn -E "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER" engine/ jurisdictions/*.yaml tests/fixtures/jurisdictions/*.yaml sources/MANIFEST.yaml` | No matches | ✓ PASS |
| Float-arithmetic scan | `grep -rniE "float\(|: *float" engine/credit.py engine/qualifying_base.py engine/models.py` | No matches | ✓ PASS |
| SCOPE-FREEZE.md integrity | `git log --oneline -5` and `git diff --stat 6ce2d9d^..HEAD -- jurisdictions/SCOPE-FREEZE.md` | No diff — file untouched by the gap-closure commits | ✓ PASS |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/credit.py` | `blended_by_ceiling_split` slices the actually-adjusted base | ✓ VERIFIED | Rewritten branch independently exercised; effective-core-expenditure carry-forward confirmed correct by direct execution |
| `engine/qualifying_base.py` | `EXCLUDED_LINE_ITEMS_TOTAL_LABEL` marker Figure, always attached | ✓ VERIFIED | Present in `__all__`; confirmed feeding `_find_excluded_line_items_total` in `engine/credit.py` |
| `tests/fixtures/jurisdictions/synthetic-blend-adjustments.yaml` | First fixture combining `blended_by_ceiling_split` with a binding cliff, exclusion, and ceiling | ✓ VERIFIED | Present, loads, drives the independent reproduction above; `jurisdiction.status: synthetic_fixture` correctly declared |
| `engine/models.py` | Cross-field validator on `JurisdictionRuleSet` resolving `stacks_with`/`mutually_exclusive_with` edges; `programmes` min_length=1 | ✓ VERIFIED | Independently exercised via direct construction; 8/8 targeted tests pass |
| `engine/credit.py` (WR-03) | Documented closed-closed convention, overlap-detection guard | ✓ VERIFIED | Comment present naming WR-03; overlap guard independently exercised via targeted tests |
| `tests/test_engine_against_validation_pairs.py` | Re-coupled to `price_jurisdiction`, direct path kept alongside | ✓ VERIFIED | 13/13 tests pass; both paths present and both required to agree per the module's own assertions |
| `jurisdictions/us-ny.yaml`, `jurisdictions/us-ct.yaml` | Curated rule files, unmodified by gap closure | ✓ VERIFIED | `git diff --stat` confirms unmodified; both still load |
| `jurisdictions/SCOPE-FREEZE.md` | Unmodified | ✓ VERIFIED | `git diff` confirms byte-identical across the gap-closure commit range |

### Key Link Verification

All links independently exercised by direct script execution (not just reading test source):
`engine/qualifying_base.py`'s `EXCLUDED_LINE_ITEMS_TOTAL_LABEL` marker Figure genuinely
reaches `engine/credit.py`'s `_find_excluded_line_items_total` and is read back correctly
(proven by the `6904000` excluded-only reproduction, which only makes sense if the marker's
value round-trips exactly). `tests/test_engine_against_validation_pairs.py` genuinely calls
`engine.pipeline.price_jurisdiction` (confirmed by the Anora pipeline reproduction and by the
CT test's `ValueError` originating from inside `price_jurisdiction`, not from a mock). No
orphaned or stub-wired artifacts found.

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| INC-01 | Qualifying base under own definition (4 base types) | ✓ SATISFIED | Unaffected by this run; independently confirmed still correct |
| INC-02 | Per-person ceilings, loan-out vs W-2 | ✓ SATISFIED | Now correct for all three rate structures including `blended_by_ceiling_split` — CR-01 closed, independently reproduced |
| INC-03 | Tier/uplift order incl. stacking, and rule-file edge integrity | ✓ SATISFIED | Blended-split arithmetic correct; WR-01/WR-02 close the edge-validation gap, independently reproduced |
| INC-04 | Per-project + annual caps | ✓ SATISFIED | Unaffected; regression-checked via full suite |
| INC-05 | Availability separate from eligibility | ✓ SATISFIED | Unaffected; regression-checked |
| INC-06 | Net cash by mechanism, audit fees deducted | ✓ SATISFIED | Four mechanisms unaffected and correct; `transferable` now proven to run end-to-end for New York via the pipeline re-coupling (Connecticut blocked by a data gap, not an engine defect — see limitation above) |
| INC-07 | Taxable net of corporation tax | ✓ SATISFIED | Unaffected; UK worked example still `Decimal('5382000')` net, independently confirmed via full suite pass |
| INC-08 | Cash arrival timing reported | ✓ SATISFIED | Unaffected |
| INC-09 | Minimum-spend cliffs modelled | ✓ SATISFIED | Now correctly reaches the credit for `blended_by_ceiling_split` — independently reproduced `Decimal('0')` with derivation agreement |
| JUR-05 | Additive jurisdiction, no engine change | ✓ SATISFIED | Regression-confirmed; new fixture's jurisdiction id absent from `engine/` source per the glob-driven test |
| PRV-01 | Source link + date checked | ✓ SATISFIED | Unaffected |
| PRV-02 | Confidence tier, validated/researched only | ✓ SATISFIED | WR-04 closes the empty-programmes confidence-laundering hole, independently reproduced raising |
| PRV-03 | Readable derivation reason | ✓ SATISFIED | CR-01's derivation-contradicts-number defect closed; independently confirmed the cliff programme's derivation and its returned number now agree |

No orphaned requirements: all 13 requirement IDs listed against Phase 2 in REQUIREMENTS.md
(INC-01 through INC-09, JUR-05, PRV-01 through PRV-03) are marked Complete in
REQUIREMENTS.md and appear in at least one plan's frontmatter `requirements` field across
the full phase (02-01 through 02-09).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `engine/credit.py` | 565-576 | WR-05 (new, from fresh 02-REVIEW.md): effective-core-expenditure carry-forward assumes `qualifying_base_input.value` is scale-consistent with `core_expenditure_figure.value`, which holds only for `base_definition.type: lesser_of_pct_core_or_actual_local` | ⚠️ Warning | Confirmed unreachable by any committed jurisdiction or fixture in this verification (see Independent Reproduction table). Recommend a guard or scope note before any future jurisdiction pairs `blended_by_ceiling_split` with a different base-definition type and a binding exclusion/ceiling |
| `engine/credit.py` | 547-554 | IN-03 (from 02-REVIEW.md): zero-or-below short-circuit's derivation line omits excluded line items as a possible cause | ℹ️ Info | Cosmetic wording gap only; does not affect correctness |
| `engine/credit.py` | 541-611 | IN-04 (from 02-REVIEW.md): short-circuit skips the "always emit a line, even when zero" convention nearby | ℹ️ Info | Deliberate, documented design choice; no behavior change needed |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in `engine/`, `jurisdictions/*.yaml`,
`tests/fixtures/jurisdictions/*.yaml`, or `sources/MANIFEST.yaml`. No Blocker-severity
anti-patterns found in the gap-closure delta.

### Known, Already-Recorded Items (not new findings — factored into this verdict, not re-litigated)

1. `.planning/WINDOWS.md` entry 1 (`.env.example` not created in repo; documented alternative used) — Phase 1 item, out of scope for this verification.
2. `.planning/WINDOWS.md` entries 2 and 4 — pre-existing repo-wide `ruff` backlog (~297 findings, `FURB157`/`RUF022`/`ISC004`), confirmed via `git stash` comparison in `02-REVIEW.md` to predate this phase's gap-closure delta and to add no new rule categories. Per this project's own instructions, this is an accepted, tracked convention, not a phase-blocking finding.
3. `.planning/WINDOWS.md` entry 3 — Connecticut's `price_jurisdiction` pipeline routing blocked by an unsourced `transfer_discount` rate in the real `jurisdictions/us-ct.yaml`. Discussed in detail above under "Recorded, Non-Blocking Limitation." Judged not to block the phase goal.
4. `ny_succession_s4.yaml` reclassified exact → bounded (10bps) — Phase 2, plan 02-05 era, not re-litigated (unaffected by gap closure).
5. Plan 02-06's tests written after implementation (`tdd_mode` false project-wide) — not re-litigated.

## Human Verification Required

None. All must-have truths in this phase are directly verifiable by code reading, direct
execution against the actual engine and fixtures, or existing test evidence — no visual,
real-time, or external-service-dependent behavior in scope for this phase. The one open
item (Connecticut's unsourced discount rate) is a recorded data limitation, not a judgment
call requiring human testing — it is already proven and named by a self-invalidating test.

## Gaps Summary

None. The gap-closure run (plans 02-07, 02-08, 02-09) closed all three roadmap-blocking
gaps from the previous verification pass (CR-01, surfaced as failures of SC1/SC2/SC3) and
all four recommended-scope warnings (WR-01, WR-02, WR-03, WR-04). Every closure claim was
independently re-derived in this verification by direct script execution against the actual
engine and fixture files — not accepted from SUMMARY.md or 02-REVIEW.md text — and every
previously-reproducing figure (Anora `Decimal('991190')`, Christmas Always `Decimal('1159502')`
via the direct path, the UK worked example gross `Decimal('7176000')`/net `Decimal('5382000')`,
`zz-fixture-throwaway.yaml`'s totals) still reproduces byte-identically. The fresh code
review's one new Warning (WR-05) is confirmed unreachable by any currently committed
jurisdiction or fixture and does not block the phase goal; it is recorded here for future
attention rather than fixed speculatively, consistent with this project's own scope-freeze
discipline. Connecticut's inability to route through `price_jurisdiction` is a genuine,
disclosed government-data gap that the engine correctly refuses to paper over — judged a
recorded limitation, not a phase-blocking defect, per the project's explicit honesty mandate.

---

_Verified: 2026-08-25T19:16:29Z_
_Verifier: Claude (gsd-verifier)_
