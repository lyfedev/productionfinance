---
phase: 02-engine-spine-incentive-interpreter
verified: 2026-08-25T17:02:08Z
status: gaps_found
score: 2/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Per-person ceilings, tier/uplift ordering, per-project and annual caps, and minimum-spend cliffs each visibly change the result when their inputs cross a boundary (Roadmap SC2; requirements INC-02, INC-09)"
    status: failed
    reason: >
      CR-01 (engine/credit.py, _apply_rate's `blended_by_ceiling_split` branch,
      lines ~446-467): for this one rate structure, the credit is computed from
      `core_expenditure_figure.value` — the raw, pre-adjustment "Core expenditure
      (pre-cap)" Figure captured once at compute_qualifying_base construction time
      — instead of `figure.value`, the running Figure that minimum-spend,
      excluded-line-items, and per-person-ceiling have already adjusted.
      Independently reproduced in this verification (not just re-stated from the
      review or the orchestrator): loading tests/fixtures/jurisdictions/synthetic-uk-style.yaml,
      pricing £18,000,000 with an injected minimum_spend of £50,000,000 (above
      the priced spend) yields qualifying_base.value == 0 with a derivation line
      reading "qualifying base is $0 (step function, never interpolated)" — yet
      compute_gross_credit on that same base still returns 7,176,000, byte-identical
      to the no-cliff control run. Separately, injecting a per_person_ceiling with
      a £500,000 W-2 cap and a £2,000,000 compensation line (a declared £1,500,000
      excess) produces a derivation line stating "base reduced by 1500000" while
      the returned credit is again 7,176,000, identical with or without that
      compensation line. The derivation trail asserts adjustments took place that
      the reported number does not reflect.
    artifacts:
      - path: "engine/credit.py"
        issue: "Lines ~446-467 (blended_by_ceiling_split branch of _apply_rate) read core_expenditure_figure.value (immutable, captured pre-adjustment) instead of figure.value (the running, already-adjusted base) when slicing/rating. minimum-spend, excluded_line_items and per-person-ceiling reductions are silently discarded for this rate structure only."
    missing:
      - "Rewrite the blended_by_ceiling_split branch to slice the actually-adjusted running base (figure.value), preserving only the documented, narrower carve-out (SCOPE-FREEZE.md dimension 3) that this rate structure re-derives its own percentage cap from core expenditure rather than trusting base_definition.type's cap — that carve-out covers the percentage cap only, not minimum-spend, excluded-line-items, or per-person-ceiling."
      - "Add a regression test combining blended_by_ceiling_split with (a) a binding minimum-spend cliff, (b) a non-empty excluded_line_items list, and (c) a binding per-person ceiling — asserting the credit reflects all three. No committed fixture currently exercises this combination: synthetic-uk-style.yaml declares no minimum_spend and per_person_ceiling.applies: false; zz-fixture-throwaway.yaml's primary-throwaway declares both but with values chosen so neither actually binds (minimum_spend well below priced spend; per_person_ceiling.applies true but price_jurisdiction never supplies per_person_compensations, so the step is a no-op regardless)."
  - truth: "A jurisdiction's qualifying base is computed under its own definition and its gross credit converts to net cash by mechanism, net of audit fees, with cash arrival reported (Roadmap SC1)"
    status: failed
    reason: >
      compute_qualifying_base itself and engine/net_cash.py's four mechanism
      conversions are both independently correct and unaffected by CR-01 — the
      defect sits exactly at the seam between the two, inside compute_gross_credit.
      For the blended_by_ceiling_split rate structure, the "gross credit" figure
      handed to net-cash conversion does not actually reflect "the qualifying base
      under its own definition" once that base has been reduced by a cliff,
      exclusion, or ceiling — see the same CR-01 reproduction above. SC1 is an
      end-to-end claim (base -> credit -> net cash); the composition is broken for
      one of the three modelled rate structures.
    artifacts:
      - path: "engine/credit.py"
        issue: "Same root cause as above — blended_by_ceiling_split branch of _apply_rate."
    missing:
      - "Same fix as the SC2 gap above; this is one underlying defect surfaced against two roadmap success criteria."
  - truth: "Every number the engine returns carries a source link, date checked, confidence tier, and a readable derivation reason (Roadmap SC3; requirement PRV-03)"
    status: failed
    reason: >
      Source/date/confidence-tier provenance (PRV-01, PRV-02) is structurally
      sound and independently verified — Figure enforces non-null-or-explicit-None
      source_url/date_checked, a closed two-value confidence enum with no default,
      and never-upgrade-on-aggregation semantics, per the passing 02-02 property
      tests. PRV-03's "readable derivation reason" promise is what CR-01 actually
      breaks: for blended_by_ceiling_split, the derivation trail states a $0 base
      or a reduced base and then the reported credit does not reflect that
      statement — worse than silence, this is a derivation that reads as true and
      is not. This is not a general defect in the derivation mechanism (which is
      disciplined everywhere else: two adjacent no-op steps stay distinct, a
      zero-adjustment Figure still carries a base-definition line, order is stable
      across runs) — it is scoped to this one rate structure's rate step.
    artifacts:
      - path: "engine/credit.py"
        issue: "Same root cause — the misleading derivation is a symptom of CR-01, not a separate defect."
    missing:
      - "Same fix as above closes this gap as a byproduct — once the rate step reads the adjusted base, the existing derivation lines become truthful again without any wording change."
deferred: []
---

# Phase 2: Engine Spine & Incentive Interpreter Verification Report

**Phase Goal:** One generic, data-driven engine turns a production spec plus a
jurisdiction rule file into a net-cash incentive figure whose every component
traces back to its own source.
**Verified:** 2026-08-25T17:02:08Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Qualifying base under own definition; gross credit converts to net cash by mechanism, net of audit fees, with arrival date | ✗ FAILED (scoped) | compute_qualifying_base and net_cash.py are each correct in isolation and independently reproduced (see below); the base→credit composition is broken for `blended_by_ceiling_split` — CR-01, reproduced live in this verification |
| 2 | Per-person ceilings, tier/uplift ordering + stacking, per-project/annual caps, and minimum-spend cliffs each visibly change the result at a boundary | ✗ FAILED (scoped) | Verified true for `flat` (GA-style fixture) and `tiered_by_spend` (Connecticut, CT boundary tests) rate structures. Independently reproduced FALSE for `blended_by_ceiling_split`: injected minimum-spend cliff and injected per-person-ceiling excess both leave the reported credit byte-identical to the no-adjustment control (7,176,000 in both cases) |
| 3 | Every figure carries source link, date checked, confidence tier, readable derivation reason | ✗ FAILED (scoped) | PRV-01/PRV-02 mechanics verified sound (closed enum, no default, never-upgrade-on-aggregation, distinct figure_id per distinct source). PRV-03 "readable" (truthful) derivation is violated for `blended_by_ceiling_split`: derivation asserts an adjustment (e.g. "qualifying base is $0") that the reported credit does not reflect |
| 4 | Eligibility answered separately from availability (annual allocation remaining) | ✓ VERIFIED | `Eligibility`/`Availability` are two distinct dataclasses returned by two distinct functions (`assess_eligibility`, `assess_availability`), `engine/credit.py:622-727`; three-state availability (`None`/`True`/`False`) confirmed by reading `assess_availability`'s no-consumption-supplied branch, which returns `available=None` with a stated reason rather than defaulting to available |
| 5 | A new jurisdiction is a rule file alone, zero engine code change | ✓ VERIFIED | Independently confirmed via `git show --name-only commit 7ad2e83` (the commit `02-06-SUMMARY.md` cites): touches only `tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml` and `tests/test_engine_jurisdiction_additivity.py` — zero files under `engine/` |

**Score:** 2/5 truths verified (0 present-but-behavior-unverified)

**Blast radius of CR-01, precisely:**
- **NOT affected:** `jurisdictions/us-ny.yaml` (`rate_structure.type: flat`) and `jurisdictions/us-ct.yaml` (`rate_structure.type: tiered_by_spend`) — the two curated, government-sourced jurisdictions. Confirmed by direct grep of both files; neither declares `blended_by_ceiling_split`. Anora ($991,190) and Christmas Always ($1,159,502) reproduce correctly and are unaffected by this defect.
- **Affected:** the `blended_by_ceiling_split` rate structure only, currently exercised solely by two synthetic fixtures — `tests/fixtures/jurisdictions/synthetic-uk-style.yaml` (declares no minimum_spend, no excluded_line_items, `per_person_ceiling.applies: false`, so the bug is latent/unexercised as committed) and `tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml`'s `primary-throwaway` programme (declares a minimum_spend and a per-person ceiling, but with values chosen so neither actually binds against the fixture's priced spend — the bug is latent there too). No committed fixture or test combines this rate structure with a *binding* minimum-spend cliff, excluded-line-item, or per-person-ceiling reduction, which is why the 142-test green suite (independently re-run in this verification: 142 passed, 2.43s) does not catch it.
- **Practical consequence:** any future jurisdiction curated with a `blended_by_ceiling_split` rate structure (a genuinely plausible future case — this is a documented real-world pattern, e.g. two-rate uplift schemes) combined with a minimum-spend threshold, excluded line items, or a per-person cap will silently over-report its credit today, with a derivation trail that reads as if the adjustment was applied.
- **Root cause is singular:** all three FAILED roadmap truths above trace to the same code location (`engine/credit.py` lines ~446-467) and the same fix closes all three.

### Deferred Items

None. No later phase in ROADMAP.md (checked Phase 3 through Phase 8, specifically Phase 5 "Curated Breadth & the Validation Loop") names fixing this rate-structure/adjustment interaction as a goal or success criterion. This is a real, unresolved gap in Phase 2's own scope, not scheduled work.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/figure.py` | Immutable Figure value object with derivation DAG | ✓ VERIFIED | `verify.artifacts` (gsd-tools) 8/8 for plan 02-01 |
| `engine/rounding.py` | Pinned ROUND_HALF_UP quantisation | ✓ VERIFIED | proven distinct from ROUND_HALF_EVEN in tests/test_engine_rounding.py |
| `engine/models.py` | Closed-enum schema, Decimal-typed fields, safe YAML load | ✓ VERIFIED | 3/3 plan 02-02 artifacts pass |
| `engine/qualifying_base.py` | Four base-definition handlers + minimum-spend cliff | ✓ VERIFIED | 4/4 plan 02-03 artifacts pass; cliff independently reproduced correct at the qualifying-base layer |
| `engine/net_cash.py` | Four mechanisms, audit-fee cliffs, corp tax, arrival timing | ✓ VERIFIED | 3/3 plan 02-04 artifacts pass; UK worked example net Decimal('5382000') from gross Decimal('7176000') confirmed in test suite |
| `engine/credit.py` | Per-person ceiling, tiered/blended rate, uplift stacking, caps, availability | ⚠️ VERIFIED with defect | 5/5 + 4/4 plan 02-05/02-06 artifact checks pass (presence/substance), but contains CR-01 (see gaps) |
| `engine/pipeline.py` | price_jurisdiction, mutual-exclusivity resolution, additivity | ✓ VERIFIED | 4/4 plan 02-06 artifacts pass; additivity independently confirmed via git |
| `jurisdictions/us-ny.yaml`, `jurisdictions/us-ct.yaml` | Curated rule files tracing to primary sources | ✓ VERIFIED | Present, sourced, unaffected by CR-01 (flat / tiered_by_spend) |
| `jurisdictions/SCOPE-FREEZE.md` | Dated scope-freeze note | ✓ VERIFIED | Present, referenced by name in review and by the blended_by_ceiling_split carve-out comment in engine/credit.py |

### Key Link Verification

All `gsd-tools query verify.key-links` checks passed for plans 02-02 through 02-06 (2/2 each, all_verified=true) — figure-provenance tests actually walk `price_jurisdiction`'s output tree, `test_engine_models.py` actually reads `engine/handlers/` source text for dynamic-resolution absence, `test_engine_qualifying_base.py` actually globs `tests/fixtures/jurisdictions/`, etc. No orphaned or stub-wired artifacts found.

### Independent Reproduction (this verification, not carried over from SUMMARY/REVIEW claims)

| Check | Command/method | Result | Status |
|-------|------|--------|--------|
| CR-01, minimum-spend path | Loaded `synthetic-uk-style.yaml`, injected `minimum_spend=£50,000,000` against £18M priced spend, ran `compute_qualifying_base` then `compute_gross_credit` directly via `uv run python` | `qualifying_base.value == 0`, derivation states cliff applied; `gross_credit.value == 7176000` (identical to no-cliff control) | ✗ FAIL — reproduces CR-01 exactly |
| CR-01, per-person-ceiling path | Same fixture, injected `per_person_ceiling` with £500,000 W-2 cap and a £2,000,000 compensation line | Derivation states "base reduced by 1500000"; `gross_credit.value == 7176000` with or without the compensation line | ✗ FAIL — reproduces CR-01 exactly |
| JUR-05 zero-engine-diff claim | `git show --name-only 7ad2e8385e664238fc070ab3704a51d4ebf0cdca` | Touches only `tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml` and `tests/test_engine_jurisdiction_additivity.py` | ✓ PASS |
| Full test suite | `uv run pytest -q` (run once, per verifier constraints) | `142 passed, 1 warning in 2.43s` | ✓ PASS (matches SUMMARY claim; suite does not exercise CR-01's combination) |
| Debt-marker scan | `grep -rn -E "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER" engine/ jurisdictions/*.yaml sources/MANIFEST.yaml` | No matches | ✓ PASS |
| Curated-jurisdiction rate-structure check | `grep -n "type:" jurisdictions/us-ny.yaml jurisdictions/us-ct.yaml` | us-ny: `flat`; us-ct: `tiered_by_spend` | Confirms CR-01 blast radius excludes both curated jurisdictions |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| INC-01 | Qualifying base under own definition (4 base types) | ✓ SATISFIED | `compute_qualifying_base` unaffected by CR-01 (which is downstream, inside `compute_gross_credit`); four base types independently tested (02-03) |
| INC-02 | Per-person ceilings, loan-out vs W-2 | ⚠️ PARTIALLY SATISFIED | Verified correct for `flat` rate structure (GA-style fixture, 02-05 tests). FAILS for `blended_by_ceiling_split` — CR-01, independently reproduced above |
| INC-03 | Tier/uplift order incl. national/regional stacking | ✓ SATISFIED | Connecticut `tiered_by_spend` cliff lookup exact; blended split's own internal enhanced/standard slicing math verified exact (£7,176,000, not the cap-before-split £7,632,000 wrong answer); uplift-order-swap test passes. CR-01 is a discard of *upstream* adjustments, not a defect in the tier/uplift ordering logic itself |
| INC-04 | Per-project + annual caps | ✓ SATISFIED | Boundary tests pass (02-06); caps apply correctly to whatever value reaches them — not independently broken by CR-01, though a capped `blended_by_ceiling_split` credit inherits CR-01's wrong starting value when the combination occurs |
| INC-05 | Availability separate from eligibility | ✓ SATISFIED | `Eligibility`/`Availability` confirmed as two independent dataclasses/functions; three-state availability confirmed by code read |
| INC-06 | Net cash by mechanism, audit fees deducted | ✓ SATISFIED | Four mechanisms independently tested; unaffected by CR-01 |
| INC-07 | Taxable net of corporation tax | ✓ SATISFIED | UK worked example net Decimal('5382000') tested and passing |
| INC-08 | Cash arrival timing reported | ✓ SATISFIED | `ArrivalTiming` tested per mechanism, including the null-with-reason path |
| INC-09 | Minimum-spend cliffs modelled | ⚠️ PARTIALLY SATISFIED | Cliff correctly zeroes the qualifying base at the base layer (02-03, independently reproduced true) but the effect does not propagate into the reported credit for `blended_by_ceiling_split` — CR-01 |
| JUR-05 | Additive jurisdiction, no engine change | ✓ SATISFIED | Independently confirmed via git |
| PRV-01 | Source link + date checked | ✓ SATISFIED | Property-tested over a real computed tree (02-02) |
| PRV-02 | Confidence tier, validated/researched only | ✓ SATISFIED | Closed two-value enum, no default, never-upgrade-on-aggregation, all property-tested |
| PRV-03 | Readable derivation reason | ⚠️ PARTIALLY SATISFIED | Derivation mechanics (ordering, non-collapsing no-ops, always-non-empty) are sound everywhere. Truthfulness is violated specifically for `blended_by_ceiling_split` — the derivation states an adjustment happened that the reported number doesn't reflect (CR-01) |

No orphaned requirements: all 13 requirement IDs listed against Phase 2 in REQUIREMENTS.md (INC-01 through INC-09, JUR-05, PRV-01 through PRV-03) appear in at least one plan's frontmatter `requirements` field.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `engine/credit.py` | 446-467 | Silent adjustment discard (CR-01) | 🛑 Blocker | Breaks Roadmap SC1, SC2, SC3 for one of three modelled rate structures — see gaps |
| `engine/pipeline.py` | 140-171 | WR-01: self-referencing `mutually_exclusive_with` silently drops an otherwise-eligible programme | ⚠️ Warning (from 02-REVIEW.md, not independently re-reproduced in this pass) | Not tied to a specific must-have truth in this phase's must_haves; recommend addressing alongside CR-01 fix |
| `engine/pipeline.py` | 174-197 | WR-02: `stacks_with` references never validated against declared programme ids | ⚠️ Warning (from 02-REVIEW.md) | Typo'd reference produces a plausible-looking but wrong derivation line rather than raising |
| `engine/credit.py` | 125-128 | WR-03: loan-out withholding schedule lookup uses closed-closed boundaries, inconsistent with every other tier lookup in this codebase | ⚠️ Warning (from 02-REVIEW.md) | Convention inconsistency; no overlap-detection guard |
| `engine/pipeline.py` / `engine/figure.py` | 251-261 / 98-109 | WR-04: empty `programmes` list yields a spuriously `validated`, unsourced $0 total | ⚠️ Warning (from 02-REVIEW.md) | Minor confidence-laundering edge case, not exercised by any curated or committed fixture |
| `engine/models.py` | 230-233 | IN-01: `escalator_schedule` accepted but never referenced in derivation | ℹ️ Info | Schema field with no runtime effect, undocumented as such |
| `engine/models.py` | 100-102 | IN-02: `Money.currency` unconstrained free text | ℹ️ Info | Out of scope for two single-currency curated jurisdictions per review; worth a schema cross-check before a multi-currency jurisdiction is curated |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in `engine/`, `jurisdictions/*.yaml`, or `sources/MANIFEST.yaml`.

### Known, Already-Recorded Items (not new findings — factored into this verdict, not re-litigated)

1. `tests/test_engine_against_validation_pairs.py` is deliberately decoupled from `engine.pipeline.price_jurisdiction`, with the reason documented in the file itself (avoiding a `NotImplementedError` for CT's `transferable` mechanism before plan 02-04 landed). 02-04 has since implemented `transferable`; re-coupling is now unblocked and is recorded as a recommendation in `02-04-SUMMARY.md`. This slightly weakens the end-to-end evidence for Roadmap SC1 (the golden-value proof for NY/CT currently bypasses `price_jurisdiction`, hence bypasses `convert_to_net_cash`), though `price_jurisdiction` itself is separately, adequately exercised end-to-end for NY via `test_engine_figure_provenance.py` and for the UK/throwaway fixtures via `test_engine_net_cash.py` and `test_engine_jurisdiction_additivity.py`. Not treated as a blocking gap in this verification, but flagged as a real (if minor) evidence gap the fix for CR-01 should close alongside — a re-coupled validation-pairs test would have caught neither CR-01 (NY/CT don't use the affected rate structure) nor prevented it, but re-coupling is still the more rigorous state and is already a recorded recommendation.
2. `tests/fixtures/validation_pairs/ny_succession_s4.yaml` reclassified exact → bounded (10bps), 1.73bps residue documented in the fixture. Not re-litigated.
3. Plan 02-06's tests were written after implementation (executor recovering from a stream error); `tdd_mode` is false project-wide. Not re-litigated.

## Human Verification Required

None. All must-have truths in this phase are either directly verifiable by code reading, direct execution, or existing test evidence — no visual, real-time, or external-service-dependent behavior in scope for this phase.

## Gaps Summary

One root-cause defect (CR-01, already identified by code review and independently reproduced twice in this verification via direct execution against the actual fixture and engine code — not merely re-stated) invalidates three of the five roadmap success criteria for one of the three modelled rate structures (`blended_by_ceiling_split`). The two currently-curated, government-sourced jurisdictions (New York, Connecticut) are unaffected — they use `flat` and `tiered_by_spend` respectively, and their golden-value reproductions (Anora $991,190; Christmas Always $1,159,502) hold. The defect is latent in the two committed fixtures that do exercise `blended_by_ceiling_split` (`synthetic-uk-style.yaml`, `zz-fixture-throwaway.yaml`) only because neither happens to combine that rate structure with a *binding* minimum-spend cliff, excluded line item, or per-person ceiling — a combination that is entirely plausible for a future real jurisdiction and that this engine, as shipped, would silently mis-price while presenting a derivation trail that claims otherwise. Per this phase's own PRV-03 discipline and the roadmap's explicit requirement that adjustments "visibly change the result," this is a goal-blocking gap, not a cosmetic one. Recommended fix is scoped and already spelled out in `02-REVIEW.md`'s CR-01 finding: make the `blended_by_ceiling_split` rate step operate on the actually-adjusted running base rather than the raw core-expenditure input, preserving only the narrower, documented percentage-cap re-derivation carve-out, and add the missing combination regression test before this phase is re-verified.

---

_Verified: 2026-08-25T17:02:08Z_
_Verifier: Claude (gsd-verifier)_
