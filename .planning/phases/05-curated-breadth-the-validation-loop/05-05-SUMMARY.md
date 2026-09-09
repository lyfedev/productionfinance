---
phase: 05-curated-breadth-the-validation-loop
plan: 05
subsystem: jurisdictions
tags: [new-jersey, tax-credit, validation-pairs, source-truth, decimal, pydantic, transferable]

requires:
  - phase: 02-engine-spine-incentive-interpreter
    provides: "engine/models.py schema, engine/pipeline.py::price_jurisdiction, engine/net_cash.py::transferable, jurisdictions/us-ny.yaml and jurisdictions/us-ct.yaml as shape/mechanism references"
provides:
  - "jurisdictions/us-nj.yaml — Garden State Film and Digital Media Jobs Program, the pre-2021-01-07 rate tier (flat 30% base, mechanism transferable), the only tier both committed New Jersey fixtures need"
  - "four newly archived, hash-verified New Jersey primary government sources under sources/nj/, manifested in sources/MANIFEST.yaml"
  - "tests/test_jurisdiction_us_nj.py — literal expected-value reproduction of both committed New Jersey validation pairs, plus an exact Decimal-equality assertion on Joker's diversity-bonus residue"
  - "corrected assertion blocks on both nj_*.yaml fixtures (Trial of the Chicago 7 moved to exact mode; Joker's variance_reason now names the sourced 2% bonus instead of an unexplained gap)"
  - "two new WINDOWS.md entries (#30 lint-warning, #31 unmet-truth — the sourced-floor/unsourced-ceiling transfer_discount gap)"
affects: [05-01, 05-08]

actuals:
  tokens: 11200
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "A rule file's rate applies at the date an APPLICATION was received, not at the current date — New Jersey's rate schedule has four historical tiers (N.J.A.C. 19:31T-1.6(a)(1)-(4)); this file models only the tier both committed 2019/2020-approved fixtures fall under, deliberately not the current (post-2021) schedule, following the same discipline California's plan applied to a stale-vs-current statute citation"
    - "A statutory transfer-price FLOOR ('not less than 75 percent') is a genuine partial source, not a full range — recorded as typical_rate_low sourced / typical_rate_high null rather than either inventing a ceiling or leaving both bounds null, and engine.net_cash.transferable's honesty gate still refuses to convert (it requires both bounds), so the refusal fires exactly as it does for Connecticut's wholly-unsourced case"
    - "mechanism selection is programme-scoped, not jurisdiction-scoped: California's Program 4.0 Non-Indie track correctly declares nonrefundable_credit (sale reserved to an unmodeled track), while New Jersey's structurally near-identical statutory language declares transferable (the sale right applies broadly to the exact modeled programme) — same schema, same closed Literal, two different honest answers"

key-files:
  created:
    - sources/nj/2026-09-09-njeda-nj-a-c-19-31t-garden-state-film-digital-media-jobs-program.pdf
    - sources/nj/2026-09-09-njleg-pl2018-c56-garden-state-film-digital-media-jobs-act.pdf
    - sources/nj/2026-09-09-nj-treasury-division-of-taxation-film-credit-faq.html
    - sources/nj/2026-09-09-njeda-film-tax-credit-transfer-app.pdf
    - jurisdictions/us-nj.yaml
    - tests/test_jurisdiction_us_nj.py
  modified:
    - sources/MANIFEST.yaml
    - tests/fixtures/validation_pairs/nj_joker.yaml
    - tests/fixtures/validation_pairs/nj_trial_of_the_chicago_7.yaml
    - .planning/WINDOWS.md

key-decisions:
  - "Modelled only the pre-2021-01-07 rate tier (N.J.A.C. 19:31T-1.6(a)(2), flat 30%) — the tier both committed fixtures' 2019/2020 application dates fall under — explicitly not the current post-2021 NYC-metro-zone/studio-partner schedule, the South-Jersey-vendor 35% bonus, or the digital-media credit; all disclosed as unmodeled in the file's header."
  - "Declared mechanism: transferable, not nonrefundable_credit — a deliberate departure from jurisdictions/us-ca.yaml's precedent. New Jersey's N.J.A.C. 19:31T-1.10(a) transfer right applies broadly to this exact programme (unlike California's Program 4.0, where sale is reserved to the Independent Films track this repo does not model), and its statutory phrasing closely mirrors jurisdictions/us-ct.yaml's Connecticut statute — declared transferable there for the identical reasoning."
  - "transfer_discount.typical_rate_low sourced at 0.75 (four independent NJ documents agree); typical_rate_high left null since no NJ source states a ceiling — inventing 1.00 (par) would be exactly the plausible-but-unsourced figure D-87 forbids. engine.net_cash.transferable correctly refuses to convert for every New Jersey pair as a result; not worked around."
  - "The 2% diversity-plan bonus (N.J.A.C. 19:31T-1.6(o)(1)) is disclosed in the file's header/source_note but NOT declared as a rate_structure uplift, since it is claimed by some productions and not others and the dashboard discloses it only as a per-row Yes/No flag — declaring it unconditionally would misapply it to every future production priced through this file."
  - "Trial of the Chicago 7's fixture moved from assertion.mode: bounded (tolerance_bps: 50) to mode: exact — the sourced 30% rate reproduces its disclosed Total Award to the exact dollar, with zero residue, so bounded mode was strictly weaker than what the sourced structure actually proves."
  - "Joker's fixture kept bounded mode but its tolerance_bps was raised from 50 to 200 (exactly the sourced bonus rate in basis points) and its variance_reason rewritten to name the bonus, its two independent statutory citations, and the exact residue arithmetic — never a tolerance wide enough to also hide a real modelling bug."

requirements-completed: []  # JUR-03 is also declared by sibling plans 05-01 and 05-08 — requirements.ready-ids reported 0/1 ready (shared-ID gate, #2388); not marked complete here, will flip once the last declaring plan's SUMMARY lands.

coverage:
  - id: D1
    description: "Archive New Jersey's primary rate-structure sources (N.J.A.C. 19:31T administrative code, the original P.L. 2018 c.56 enacting Act, a Division of Taxation FAQ, and NJEDA's own transfer-application form) with sha256 manifest entries"
    requirement: "JUR-03"
    verification:
      - kind: unit
        ref: "tests/test_source_truth.py — 10 passed"
        status: pass
    human_judgment: false
  - id: D2
    description: "jurisdictions/us-nj.yaml loads through engine.models.load_ruleset, encodes only sourced figures for the pre-2021-01-07 tier both fixtures need, engine/ untouched"
    requirement: "JUR-03"
    verification:
      - kind: unit
        ref: "engine.models.load_ruleset('jurisdictions/us-nj.yaml') — returns JurisdictionRuleSet with 1 programme, mechanism transferable, base_rate 0.30, zero uplifts"
        status: pass
      - kind: other
        ref: "git diff --stat -- engine/ — empty"
        status: pass
      - kind: other
        ref: "bash .github/scripts/vendor-scan.sh — exit 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both committed New Jersey validation pairs reproduce their disclosed credit (exactly for Trial of the Chicago 7; via an exact, sourced diversity-bonus residue equality for Joker), asserted against literal expected values via the direct base-then-credit path; price_jurisdiction correctly refuses (unsourced transfer_discount ceiling) for both pairs; both stay disclosure_stage: estimated"
    requirement: "JUR-03"
    verification:
      - kind: unit
        ref: "tests/test_jurisdiction_us_nj.py — 8 passed (test_trial_of_the_chicago_7_reproduces_exactly, test_joker_diversity_bonus_residue_is_exactly_the_sourced_bonus_rate, test_price_jurisdiction_refuses_unsourced_transfer_discount[Joker/Trial], test_every_active_pair_declares_the_nj_programme_and_estimated_stage[Joker/Trial])"
        status: pass
      - kind: unit
        ref: "uv run --frozen pytest -q — 679 passed, 0 deselected, 0 failed"
        status: pass
      - kind: other
        ref: "bash .github/scripts/vendor-scan.sh && bash .github/scripts/lockfile-scan.sh — both exit 0"
        status: pass
      - kind: unit
        ref: "tests/test_golden_cost.py tests/test_route_a_basis_walk.py — 9 passed, pinned golden totals unregressed"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-09-09
status: complete
---

# Phase 5 Plan 05: New Jersey (JUR-03) Summary

**Garden State Film and Digital Media Jobs Program's pre-2021-01-07 rate tier modelled at a directly-sourced 30% flat base rate (N.J.A.C. 19:31T-1.6(a)(2)) with a `transferable` mechanism — reproducing both committed New Jersey validation pairs, one exactly and one via an exact Decimal-equality proof of its sourced 2% diversity bonus, not a widened tolerance.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-09-09T08:43:58Z
- **Completed:** 2026-09-09T08:58:11Z
- **Tasks:** 3
- **Files created:** 6 (4 archived sources, `jurisdictions/us-nj.yaml`, `tests/test_jurisdiction_us_nj.py`)
- **Files modified:** 4 (`sources/MANIFEST.yaml`, two `nj_*.yaml` fixtures, `.planning/WINDOWS.md`)

## Accomplishments

- Archived four newly fetched New Jersey primary government documents: N.J.A.C. Title 19, Chapter 31T (the current administrative code, hosted by NJEDA itself), the original enacting P.L. 2018, c. 56 (fetched directly from the NJ Legislature's own bill host), a Division of Taxation FAQ (state.nj.us), and NJEDA's own tax-credit-transfer application form — all sha256-verified in `sources/MANIFEST.yaml`.
- Discovered New Jersey's rate schedule is tiered by APPLICATION-RECEIVED date, not by today's date (N.J.A.C. 19:31T-1.6(a)(1)-(4)) — both committed fixtures (Joker, approved 08/13/2019; Trial of the Chicago 7, approved 07/14/2020) fall under the pre-2021-01-07 tier (flat 30%, `jurisdictions/us-nj.yaml` models this one), NOT the current post-2021 NYC-metro-zone/studio-partner schedule (30-40%, several sub-tiers) a naive "use the current statute" approach would have wrongly applied.
- Wrote `jurisdictions/us-nj.yaml`: one programme (`nj-garden-state-film-digital-media-jobs-program`), `flat` rate structure at `base_rate: "0.30"`, `mechanism: transferable`, minimum spend $1,000,000, annual programme cap $100,000,000/fiscal_year, no per-project cap — every field traced to the archived sources. `mechanism: transferable` is a deliberate departure from `jurisdictions/us-ca.yaml`'s `nonrefundable_credit` precedent (see key-decisions), producing the same deliberate `engine.net_cash.transferable` refusal Connecticut's file already exercises.
- Sourced the transfer-discount floor at 0.75 from four independent New Jersey documents; the ceiling stays an explicit null since no document states one, so `price_jurisdiction` correctly refuses to convert for both pairs — not worked around.
- Wrote `tests/test_jurisdiction_us_nj.py` (8 tests): literal expected-value assertions for both pairs (`Decimal('5371984')` for Trial of the Chicago 7, exact match; `Decimal('1839977')` base-rate-only for Joker), an exact Decimal-equality proof that Joker's residue against its disclosed credit equals precisely `Decimal('122665')` — the sourced 2% diversity bonus applied to Joker's own disclosed qualified spend — and per-pair proof that `price_jurisdiction` refuses (unsourced transfer_discount ceiling).
- Corrected both fixtures' `assertion` blocks: Trial of the Chicago 7 moved to `mode: exact` (true zero-residue reproduction); Joker's `variance_reason` rewritten to name the sourced bonus and its two independent statutory citations, with `tolerance_bps` raised from an arbitrary 50 to exactly 200 (the sourced bonus rate in basis points) rather than a number wide enough to also mask a real bug.

## Task Commits

1. **Task 1: Archive New Jersey's primary rate-structure sources and manifest them** — `52349c8` (feat)
2. **Task 2: Write jurisdictions/us-nj.yaml from the archived sources only** — `921db16` (feat)
3. **Task 2 correction: declare mechanism transferable, not nonrefundable_credit** — `08a1589` (fix) — a Rule 4-adjacent judgment call surfaced and corrected before Task 3, not a deviation discovered mid-task (see Deviations)
4. **Task 3: Reconcile both New Jersey fixtures and assert the uplift residue exactly** — `0df1196` (test)

## Files Created/Modified

- `sources/nj/2026-09-09-njeda-nj-a-c-19-31t-garden-state-film-digital-media-jobs-program.pdf` — N.J.A.C. Title 19, Chapter 31T, current administrative code (rates, caps, minimum spend, diversity bonus, transfer floor, audit requirement)
- `sources/nj/2026-09-09-njleg-pl2018-c56-garden-state-film-digital-media-jobs-act.pdf` — the original enacting Act, independently confirming the same figures at time of enactment
- `sources/nj/2026-09-09-nj-treasury-division-of-taxation-film-credit-faq.html` — third independent government source, corroborating the annual cap, absence of a per-project cap, and carryforward
- `sources/nj/2026-09-09-njeda-film-tax-credit-transfer-app.pdf` — fourth independent confirmation of the 75-cent transfer floor
- `sources/MANIFEST.yaml` — four new rows, each with sha256, retrieved_at, and `cited_for` naming the exact figures each document backs
- `jurisdictions/us-nj.yaml` — the New Jersey rule file (pre-2021-01-07 tier only, header comment discloses every unmodeled tier/track/uplift and the mechanism-choice reasoning)
- `tests/test_jurisdiction_us_nj.py` — New Jersey-specific validation-pair reproduction tests
- `tests/fixtures/validation_pairs/nj_joker.yaml` — `assertion` block corrected to name and quantify the sourced diversity bonus
- `tests/fixtures/validation_pairs/nj_trial_of_the_chicago_7.yaml` — `assertion.mode` corrected to `exact`; notes extended with the disclosure_stage rationale
- `.planning/WINDOWS.md` — two new entries (#30 lint-warning, #31 unmet-truth)

## Decisions Made

See `key-decisions` in frontmatter. Summarized: modelled only the pre-2021-01-07 tier (the only one either fixture needs); declared `mechanism: transferable` (not `nonrefundable_credit`, departing from California's precedent for a structurally different reason); sourced a genuine partial transfer-discount range (floor only) rather than inventing a ceiling or leaving both bounds null; kept the 2% diversity bonus disclosed-but-undeclared as an uplift; moved Trial of the Chicago 7 to exact mode and rewrote Joker's bounded-mode tolerance to reflect the now fully-explained residue.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `jurisdictions/us-nj.yaml`'s Task 2 draft declared `mechanism: nonrefundable_credit`, mirroring California's precedent without re-examining whether that precedent actually applies to New Jersey's statute**
- **Found during:** Between Task 2 and Task 3, re-reading N.J.A.C. 19:31T-1.10(a) against `jurisdictions/us-ca.yaml`'s and `jurisdictions/us-ct.yaml`'s own mechanism-choice reasoning before writing the Task 3 test's transfer-discount-refusal assertions.
- **Issue:** California's Program 4.0 correctly declares `nonrefundable_credit` because its transfer/sale right is statutorily reserved to the Independent Films track (a track `jurisdictions/us-ca.yaml` deliberately does not model). New Jersey's transfer right (N.J.A.C. 19:31T-1.10(a)) applies broadly to the SAME programme this file models — a materially different statutory shape closer to Connecticut's (declared `transferable`) than to California's. Declaring `nonrefundable_credit` for New Jersey would have been the less honest single-value characterization, and would have caused `price_jurisdiction` to SUCCEED via the `nonrefundable_credit` net-cash path instead of correctly refusing at the unsourced-ceiling gate — silently skipping the exact honesty-gate proof the plan's `<known_landmine>` section explicitly expects.
- **Fix:** Changed `mechanism` to `transferable`, added a header paragraph explaining the CA-vs-NJ distinction, and updated the `payout_lag.description` to describe both the default carryforward path and the elective transfer path.
- **Files modified:** `jurisdictions/us-nj.yaml`
- **Verification:** `price_jurisdiction(NJ_RULESET, Decimal('6133257'))` raises `ValueError` naming `transfer_discount`, confirmed by direct interactive check and by `tests/test_jurisdiction_us_nj.py::test_price_jurisdiction_refuses_unsourced_transfer_discount`
- **Committed in:** `08a1589` (separate commit, between Task 2 and Task 3)

---

**Total deviations:** 1 auto-fixed (1 bug). **Impact:** contained to `jurisdictions/us-nj.yaml`'s `mechanism` field and its two adjacent prose fields; caught and corrected before Task 3 began, never landed in a state where a subsequent test would have silently passed against the wrong dispatch path.

## Issues Encountered

None beyond the deviation above. `uv run --frozen pytest -q` reports a clean **679 passed, 0 deselected, 0 failed** — unlike 05-04's concurrency noise from a sibling agent's in-flight `agent/job2.py` WIP, no other in-flight file collided with this plan's scope at any point this session. `git status --short` before each commit confirmed only this plan's own `files_modified` were staged; `pyproject.toml` and `uv.lock` showed a small concurrent-agent diff (untouched, unstaged, left for whichever plan owns that change).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- New Jersey (JUR-03) is fully sourced, modelled, and validated for the tier both committed fixtures need. The current post-2021 rate schedule, the South-Jersey-vendor bonus, the digital-media credit, the post-2025 promotional bonuses, and studio-partner/film-lease-production-company designations all remain explicitly unmodeled (see `jurisdictions/us-nj.yaml`'s header comment) — a future plan adding any of these would need either a new applicant-category dispatch dimension or a genuinely separate programme entry.
- `JUR-03` is NOT marked complete in `REQUIREMENTS.md` — `gsd-tools requirements.ready-ids` reports 0/1 ready because sibling plans `05-01` and `05-08` also declare `JUR-03` and have not yet produced their own `SUMMARY.md` (shared-ID gate, #2388). It will flip to complete automatically once the last of the three declaring plans finishes.
- No blockers for any other sibling plan in this phase — this plan touched only its own `files_modified` scope and left `sources/MANIFEST.yaml` in a clean, committed state promptly (per this plan's file-ownership grant).
- WINDOWS.md entries #30 and #31 are both open by design (lint-warning tracked centrally in entry #2; the transfer_discount ceiling gap resolves automatically if a future session sources a real NJ market-discount ceiling).

## Self-Check: PASSED

- All 6 created files verified present on disk (4 archived sources, `jurisdictions/us-nj.yaml`, `tests/test_jurisdiction_us_nj.py`).
- All 4 task commits (`52349c8`, `921db16`, `08a1589`, `0df1196`) verified present in `git log`.

---
*Phase: 05-curated-breadth-the-validation-loop*
*Completed: 2026-09-09*
