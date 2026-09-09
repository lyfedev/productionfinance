---
phase: 05-curated-breadth-the-validation-loop
plan: 04
subsystem: jurisdictions
tags: [california, tax-credit, validation-pairs, source-truth, decimal, pydantic]

requires:
  - phase: 02-engine-spine-incentive-interpreter
    provides: "engine/models.py schema, engine/pipeline.py::price_jurisdiction, jurisdictions/us-ny.yaml and jurisdictions/us-ct.yaml as shape references"
provides:
  - "jurisdictions/us-ca.yaml — California Film & Television Tax Credit Program 4.0, Non-Indie Feature Film/New TV Series/Mini-Series/Pilots track, mechanism nonrefundable_credit, base_rate 0.35"
  - "three newly archived, hash-verified California primary government sources under sources/ca/, manifested in sources/MANIFEST.yaml"
  - "tests/test_jurisdiction_us_ca.py — literal expected-value reproduction of both committed California validation pairs, direct + pipeline paths"
  - "corrected variance_reason on both ca_*.yaml fixtures (Phase 1's unsourced 20%+uplifts guess replaced with the sourced 0.35 flat rate)"
affects: [05-01, 05-08]

actuals:
  tokens: 8800
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Resolved a stale-vs-current statute conflict (RTC 17053.98 vs 17053.98.1) the same way SOURCE-TRUTH.md SRC-01 resolved NY's $700M/$800M conflict — read further into the text rather than trusting the plan's own named citation at face value"
    - "excluded_line_items is a machine-actionable dollar-value lookup (SpendBreakdown.line_items), not free-text documentation — a categorical (non-dollar) wage exclusion belongs in per_person_ceiling.note instead"

key-files:
  created:
    - sources/ca/2026-09-09-film-ca-gov-tax-credit-the-basics-4-0.html
    - sources/ca/2026-09-09-leginfo-rtc-17053-98-1.html
    - sources/ca/2026-09-09-leginfo-rtc-23698-1.html
    - jurisdictions/us-ca.yaml
    - tests/test_jurisdiction_us_ca.py
  modified:
    - sources/MANIFEST.yaml
    - tests/fixtures/validation_pairs/ca_clueless_s1.yaml
    - tests/fixtures/validation_pairs/ca_disneys_hexed.yaml

key-decisions:
  - "Modelled only the Non-Indie (Feature Film/New TV Series/Mini-Series/Pilots) track — the only track either committed CA fixture needs — and explicitly disclosed the Relocating TV Series and Independent Films tracks as unmodeled, since both need schema extensions (a season-count dispatch dimension; a dual sell-or-refund mechanism) outside this plan's files_modified."
  - "mechanism: nonrefundable_credit, not refundable or transferable — RTC 17053.98.1(a) makes the credit nonrefundable against net tax by default (8-year carryover); the elective partial refund (20%/yr over 5 yrs at a 90% haircut) and the independent-film-only sale right are both real but neither is the default path, and neither maps cleanly onto this schema's refundable/transferable Literals."
  - "No uplifts declared, even though three (out-of-zone filming, VFX, local hire labor) are sourced — engine.credit._apply_uplift_stacking applies every declared uplift unconditionally, and neither disclosure itemizes which uplifts a given production claimed."
  - "Declared zero excluded_line_items and moved the RTC 17053.98.1(a)(22)(B)(iv) above-the-line categorical wage exclusion to per_person_ceiling.note instead — excluded_line_items subtracts a named dollar value from SpendBreakdown.line_items and raises KeyError on a name with no matching line item; neither fixture discloses a per-role wage breakdown."
  - "Both fixtures' variance_reason corrected from a Phase-1 guess (20% base + unconfirmed uplifts) to the now-sourced 35% flat rate, since the primary statute (RTC 17053.98.1) states 35%/40% directly rather than requiring uplift-stacking arithmetic to explain the residue."

patterns-established:
  - "A plan-cited statute section number is a starting point, not ground truth — RTC 17053.98 (named in this plan's own Task 1 text) turned out to be the superseded Program 3.0 statute; RTC 17053.98.1 is the correct current one, discovered only by reading 17053.98's own cross-reference to it."

requirements-completed: []  # JUR-02 is also declared by sibling plans 05-01 and 05-08 — requirements.ready-ids reported 0/1 ready (shared-ID gate, #2388); not marked complete here, will flip once the last declaring plan's SUMMARY lands.

coverage:
  - id: D1
    description: "Archive California's primary rate-structure sources (CFC program page + RTC 17053.98.1/23698.1 statutes) with sha256 manifest entries"
    requirement: "JUR-02"
    verification:
      - kind: unit
        ref: "tests/test_source_truth.py — 10 passed"
        status: pass
    human_judgment: false
  - id: D2
    description: "jurisdictions/us-ca.yaml loads through engine.models.load_ruleset, encodes only sourced figures, engine/ untouched"
    requirement: "JUR-02"
    verification:
      - kind: unit
        ref: "engine.models.load_ruleset('jurisdictions/us-ca.yaml') — returns JurisdictionRuleSet with 1 programme"
        status: pass
      - kind: other
        ref: "git diff --stat -- engine/ — empty"
        status: pass
      - kind: other
        ref: "bash .github/scripts/vendor-scan.sh — exit 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both committed California validation pairs reproduce their disclosed credit inside declared tolerance, via both direct and price_jurisdiction paths, asserted against literal expected values; both stay disclosure_stage: allocated"
    requirement: "JUR-02"
    verification:
      - kind: unit
        ref: "tests/test_jurisdiction_us_ca.py — 10 passed (includes test_clueless_s1_reproduces_within_tolerance, test_disneys_hexed_reproduces_within_tolerance, test_every_active_california_pair_is_allocation_stage)"
        status: pass
      - kind: unit
        ref: "uv run --frozen pytest -q — 605 passed, 4 deselected (pre-existing, out-of-scope failures in sibling-owned agent/job1.py + agent/job2.py mid-flight WIP, see Deviations)"
        status: pass
      - kind: other
        ref: "bash .github/scripts/vendor-scan.sh && bash .github/scripts/lockfile-scan.sh — both exit 0"
        status: pass
      - kind: unit
        ref: "tests/test_golden_cost.py tests/test_route_a_basis_walk.py — 9 passed, pinned golden totals unregressed"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-09
status: complete
---

# Phase 5 Plan 04: California (JUR-02) Summary

**California Film & Television Tax Credit Program 4.0's Non-Indie track modelled at a directly-sourced 35% base rate (RTC 17053.98.1) — not the 20%-plus-guessed-uplifts figure Phase 1 had assumed — reproducing both committed allocation-stage validation pairs to within 12 bps.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-09T08:20:00Z (approx.)
- **Completed:** 2026-09-09T08:39:09Z
- **Tasks:** 3
- **Files created:** 5 (3 archived sources, jurisdictions/us-ca.yaml, tests/test_jurisdiction_us_ca.py)
- **Files modified:** 3 (sources/MANIFEST.yaml, two ca_*.yaml fixtures)

## Accomplishments

- Archived three newly fetched California primary government documents (CFC's own Program 4.0 page, and RTC 17053.98.1 + 23698.1 — the correct, current statute), all sha256-verified in `sources/MANIFEST.yaml`.
- Discovered and resolved a stale-source trap: the plan's own Task 1 text names RTC 17053.98, which is actually the superseded Program 3.0 statute (20%/25% base rates). RTC 17053.98.1 — reachable only by reading 17053.98's own cross-reference in its subdivision (k) — is the correct current statute (35%/40%), matching what film.ca.gov's live page displays and what both fixtures' disclosed figures imply.
- Wrote `jurisdictions/us-ca.yaml`: one programme (`ca-film-television-tax-credit-program`), `flat` rate structure at `base_rate: "0.35"`, `mechanism: nonrefundable_credit`, per-project cap $120,000,000, annual programme cap $750,000,000/fiscal_year, minimum spend $1,000,000 — every field traced to the archived sources.
- Wrote `tests/test_jurisdiction_us_ca.py` (10 tests): literal expected-value assertions for both pairs (`Decimal('16282700.00')` for Clueless S1, `Decimal('16638300.00')` for Disney's Hexed), direct-path/pipeline-path agreement, `disclosure_stage: allocated` guard, non-empty us-ca active-pair guard.
- Corrected both fixtures' `variance_reason`: Phase 1 had guessed a 20% base rate plus unconfirmed uplifts; the sourced 35% flat rate alone reproduces Clueless S1 within 11.24 bps and Disney's Hexed within 0.06 bps — no uplift-stacking arithmetic is needed to explain the residue.

## Task Commits

1. **Task 1: Archive California's primary rate-structure sources and manifest them** — `7875a83` (feat)
2. **Task 2: Write jurisdictions/us-ca.yaml from the archived sources only** — `79d2194` (feat)
3. **Task 3: Reconcile both California fixtures and assert explicit expected values** — `a4d2ee9` (test) — includes a Rule 1 bug fix for `excluded_line_items` misuse discovered while running this task's tests (see Deviations)

_No plan-metadata commit gap: the plan's `files_modified` list does not include a separate docs step; this SUMMARY's own commit closes the plan._

## Files Created/Modified

- `sources/ca/2026-09-09-film-ca-gov-tax-credit-the-basics-4-0.html` — CFC's own Program 4.0 basics page (rates, caps, minimum budget, uplift categories)
- `sources/ca/2026-09-09-leginfo-rtc-17053-98-1.html` — RTC 17053.98.1, the current Program 4.0 statute (Personal Income Tax Law mirror)
- `sources/ca/2026-09-09-leginfo-rtc-23698-1.html` — RTC 23698.1, the Corporation Tax Law mirror, second independent confirmation
- `sources/MANIFEST.yaml` — three new rows, each with sha256, retrieved_at, and `cited_for` naming the exact figures each document backs
- `jurisdictions/us-ca.yaml` — the California rule file (Non-Indie track only, header comment discloses the two unmodeled tracks and three unmodeled uplifts)
- `tests/test_jurisdiction_us_ca.py` — California-specific validation-pair reproduction tests
- `tests/fixtures/validation_pairs/ca_clueless_s1.yaml` — `assertion.variance_reason` corrected to cite the sourced 35% rate
- `tests/fixtures/validation_pairs/ca_disneys_hexed.yaml` — `assertion.variance_reason` corrected to cite the sourced 35% rate

## Decisions Made

See `key-decisions` in frontmatter. Summarized: modelled only the Non-Indie track (the only one either fixture needs); used `mechanism: nonrefundable_credit` as the closest honest single-value characterization of California's actual nonrefundable-with-elective-partial-refund structure; declared zero uplifts since neither disclosure itemizes which (if any) a production claimed; corrected `excluded_line_items` misuse to `per_person_ceiling.note` (that field is a dollar-lookup against `SpendBreakdown.line_items`, not free text).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `excluded_line_items` misused as free-text documentation, raising `KeyError` at load time**
- **Found during:** Task 3, first run of `tests/test_jurisdiction_us_ca.py`
- **Issue:** Task 2's `jurisdictions/us-ca.yaml` put the RTC 17053.98.1(a)(22)(B)(iv) categorical above-the-line wage exclusion prose directly into `base_definition.excluded_line_items` as a single long string. `engine.qualifying_base._apply_excluded_line_items` treats every entry in that list as a *name to look up in `SpendBreakdown.line_items`* and subtract a real dollar value — it is not a documentation field. Since neither committed fixture discloses a per-role wage breakdown (only a single `qualified_spend` total), the lookup raised `KeyError` for both pairs.
- **Fix:** Set `excluded_line_items: []` and moved the full exclusion explanation into `per_person_ceiling.note`, mirroring `jurisdictions/us-ct.yaml`'s established pattern for its own categorical star-talent exclusion (which also lives in `per_person_ceiling.note`, not `excluded_line_items`).
- **Files modified:** `jurisdictions/us-ca.yaml`
- **Verification:** `uv run --frozen pytest tests/test_jurisdiction_us_ca.py -q` — 10 passed (was 8 failed / 2 passed before the fix)
- **Committed in:** `a4d2ee9` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug). **Impact:** contained to `jurisdictions/us-ca.yaml`; caught by this plan's own Task 3 tests before commit, never landed in a green state.

## Issues Encountered

**Concurrent sibling agent WIP causes 4 unrelated full-suite failures — out of scope, not caused by this plan.** `uv run --frozen pytest -q` reports 4 failures (`tests/test_agent_job2_offline.py::test_scripted_*` x3, `tests/test_app_job1_route.py::test_get_job1_with_persisted_live_run_shows_bucket_counts_and_every_award`). These are in files this plan's `<file_ownership>` explicitly forbids touching (`agent/job1.py`, `agent/job2.py`) and were confirmed, via `git status`/`git diff --stat`, to be a **different, concurrently-running agent's uncommitted mid-flight work** (a 416-line uncommitted diff to `agent/job2.py` rewriting its terminal-reason taxonomy — the failing tests expect the old enum values `"sufficient"`/`"give_up"`, the uncommitted code returns `"insufficient_identity"`/`"agent_gave_up"`). Re-running the full suite with those 4 tests deselected: **605 passed, 4 deselected** — confirms no other test in the suite is affected by this plan's changes. Not fixed here (would violate `<file_ownership>` and would edit code mid-flight under another agent). Not filed to `WINDOWS.md` as this plan's own defect — it belongs to whichever plan lands `agent/job2.py`'s taxonomy rewrite, which will presumably fix its own tests when it commits.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- California (JUR-02) is fully sourced, modelled, and validated for the track both committed fixtures need. The Relocating TV Series and Independent Films tracks remain explicitly unmodeled (see `jurisdictions/us-ca.yaml`'s header comment) — a future plan adding either would need a season-count dispatch dimension (Relocating TV's first-vs-subsequent-season rate) and/or a dual sell-or-refund mechanism representation (Independent Films) that this schema does not yet support.
- `JUR-02` is NOT marked complete in `REQUIREMENTS.md` — `gsd-tools requirements.ready-ids` reports 0/1 ready because sibling plans `05-01` and `05-08` also declare `JUR-02` and have not yet produced their own `SUMMARY.md` (shared-ID gate, #2388). It will flip to complete automatically once the last of the three declaring plans finishes.
- No blockers for `05-06` (Connecticut) or any other sibling plan in this phase — this plan touched only its own `files_modified` scope and left `sources/MANIFEST.yaml` in a clean, committed state promptly (per this plan's file-ownership grant).

## Self-Check: PASSED

- All 5 created files verified present on disk (3 archived sources, `jurisdictions/us-ca.yaml`, `tests/test_jurisdiction_us_ca.py`).
- All 3 task commits (`7875a83`, `79d2194`, `a4d2ee9`) verified present in `git log`.

---
*Phase: 05-curated-breadth-the-validation-loop*
*Completed: 2026-09-09*
