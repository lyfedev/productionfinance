---
phase: 05-curated-breadth-the-validation-loop
plan: 06
subsystem: validation
tags: [connecticut, us-ct, validation-pairs, pytest, honesty-gate, jur-04]

requires:
  - phase: 01-eligibility-spine-and-source-truth
    provides: "the archived Connecticut open-data CSV (sources/ct/2026-08-24-ct-film-tax-credits-issued.csv) and its sources/MANIFEST.yaml row"
  - phase: 02-engine-core-and-first-jurisdictions
    provides: "jurisdictions/us-ct.yaml's tiered_by_spend rate structure, engine.credit.compute_gross_credit, engine.net_cash.transferable's unsourced-discount refusal, and the ct_christmas_always.yaml top-band fixture"
provides:
  - "tests/fixtures/validation_pairs/ct_colony_video_2015_productions.yaml — the $100,000-$500,000/10% band's first real disclosed-award pair"
  - "tests/fixtures/validation_pairs/ct_mako_games.yaml — the $500,000-$1,000,000/15% band's first real disclosed-award pair"
  - "tests/test_jurisdiction_us_ct.py — literal expected-value assertions per active Connecticut pair, a per-tier band-coverage test, and a uniform per-pair assertion that price_jurisdiction refuses to convert an unsourced transfer discount"
  - "jurisdictions/us-ct.yaml's transfer_discount.source_note restated with the full explanation and this session's source search log"
affects: [phase-5-validation-loop, phase-8-reverification]

actuals:
  tokens: 20500
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Jurisdiction-specific test module (tests/test_jurisdiction_us_ct.py) that re-derives its own active-pair list from the shared fixture glob rather than importing tests/test_engine_against_validation_pairs.py's module-level constants — keeps the two modules independently ownable (05-08 owns the cross-jurisdiction sweep) while both read the same fixtures/*.yaml source of truth"
    - "Structural (never jurisdiction-id-keyed) determination of whether price_jurisdiction can complete: _pipeline_can_complete reads the loaded programme's mechanism and transfer_discount bounds directly, so a future us-ct.yaml update that sources a real discount rate flips this test from pass to a loud, explicit failure demanding a rewrite, not a silent pass"

key-files:
  created:
    - tests/fixtures/validation_pairs/ct_colony_video_2015_productions.yaml
    - tests/fixtures/validation_pairs/ct_mako_games.yaml
    - tests/test_jurisdiction_us_ct.py
  modified:
    - jurisdictions/us-ct.yaml
    - .planning/WINDOWS.md

key-decisions:
  - "Both new fixtures were selected from CSV rows dated on or after jurisdictions/us-ct.yaml's rule_version_effective_from (2010-01-01) — pre-2010 rows in the same statutory-reference filter do NOT follow the current three-tier schedule (e.g. an $81,260 spend, below the $100,000 minimum, still nets a 30% credit in a 2009 row), a genuine earlier statute version rather than noise. Restricting to post-2010 rows before computing band membership avoided anchoring a fixture to data the current rule file does not model."
  - "Both selected productions are exact, zero-rounding-residue single occurrences in the full 658-row CSV (Colony Video 2015 Productions: $187,220 -> $18,722 at exactly 10%; Mako Games LLC: $593,380 -> $89,007 at exactly 15%), matching the D-05 one-off-production preference ct_christmas_always.yaml already established over the many recurring companies in the dataset (e.g. National Media Connection LLC, 14 occurrences)."
  - "The transfer-discount refusal (WINDOWS.md entry #3) is left open by design, not resolved. tests/test_jurisdiction_us_ct.py::test_price_jurisdiction_refuses_unsourced_transfer_discount now asserts it per-pair, structurally, for all three active Connecticut pairs -- making the honesty gate a permanent, named, tested behaviour instead of a footnote proven for one pair. engine/net_cash.py is untouched (empty git diff --stat -- engine/)."
  - "A best-effort primary-source search for a Connecticut government publication of a market transfer-discount rate found none: the codified statute text (cga.ct.gov/current/pub/chap_208.htm) has no 'discount' or 'broker' language near 12-217jj; the DECD film-tax-credit programme page (portal.ct.gov/DECD/.../Film-Digital-Media-Tax-Credit-Program) now 404s -- the state portal has been restructured since this rule file's original 2026-08-25 fetch; DRS's Informational Publications index (200) lists no film/transfer/discount content; and ctfilm.com returned HTTP 403. The search log is recorded in jurisdictions/us-ct.yaml's transfer_discount.source_note so the 'no source exists' claim is an evidenced conclusion, not an assumption."

requirements-completed: []
# JUR-04 is declared by three plans in this phase (05-01, 05-06, 05-08) and
# the shared-ID gate (#2388) correctly reports it BLOCKED: 05-08 (the
# cross-jurisdiction sweep this plan's fixtures feed into) has not produced
# a SUMMARY yet. `requirements.mark-complete` was intentionally NOT run for
# JUR-04 here -- it will be marked automatically the next time any plan in
# this phase completes its own update_requirements step, once 05-08's
# SUMMARY exists.

coverage:
  - id: D1
    description: "Every rate band jurisdictions/us-ct.yaml declares (10%, 15%, 30%) is now exercised by a real disclosed Connecticut award drawn from the archived open-data CSV"
    requirement: "JUR-04"
    verification:
      - kind: unit
        ref: "tests/test_jurisdiction_us_ct.py#test_every_declared_tier_has_a_covering_pair"
        status: pass
      - kind: unit
        ref: "tests/test_validation_pair_fixtures.py#test_curated_jurisdictions_have_coverage"
        status: pass
    human_judgment: false
  - id: D2
    description: "Each active Connecticut pair reproduces its disclosed credit exactly through the direct base-then-credit path, asserted against a literal expected Decimal"
    requirement: "JUR-04"
    verification:
      - kind: unit
        ref: "tests/test_jurisdiction_us_ct.py#test_colony_video_2015_productions_reproduces_exactly"
        status: pass
      - kind: unit
        ref: "tests/test_jurisdiction_us_ct.py#test_mako_games_reproduces_exactly"
        status: pass
      - kind: unit
        ref: "tests/test_jurisdiction_us_ct.py#test_christmas_always_reproduces_exactly"
        status: pass
      - kind: unit
        ref: "tests/test_engine_against_validation_pairs.py#test_curated_jurisdiction_reproduces_disclosed_credit"
        status: pass
    human_judgment: false
  - id: D3
    description: "price_jurisdiction's refusal to convert a Connecticut credit to cash without a sourced discount range is asserted, structurally, for every active Connecticut pair; engine/net_cash.py is unchanged"
    requirement: "JUR-04"
    verification:
      - kind: unit
        ref: "tests/test_jurisdiction_us_ct.py#test_price_jurisdiction_refuses_unsourced_transfer_discount"
        status: pass
      - kind: other
        ref: "git diff --stat -- engine/ (empty)"
        status: pass
    human_judgment: false
  - id: D4
    description: "No Connecticut figure anywhere in the repository is invented -- the transfer discount stays an explicit null and the source-search attempt is logged rather than assumed"
    human_judgment: true
    rationale: "Whether a search for a primary Connecticut government publication of a transfer-discount rate was genuinely exhaustive (vs. a rate existing somewhere this session's curl/DDG-lite attempts did not reach) is a judgment call about search completeness, not something a test can assert. The attempted URLs and outcomes are recorded in this SUMMARY and in jurisdictions/us-ct.yaml's transfer_discount.source_note for a human to review."

duration: ~35min
completed: 2026-09-09
status: complete
---

# Phase 5 Plan 06: Connecticut Band Coverage & the Permanent Honesty Gate Summary

**Two real disclosed Connecticut awards fill the last two unexercised rate bands (10% and 15%), and the pipeline's unsourced-transfer-discount refusal is now a uniform, structurally-determined, per-pair assertion instead of a one-off proof.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- **Full statutory band coverage.** `jurisdictions/us-ct.yaml` declares three tiered rate bands ($100,000-$500,000 at 10%, $500,000-$1,000,000 at 15%, $1,000,000+ at 30%). Before this plan only the top band had a validation pair (`ct_christmas_always.yaml`). Two new fixtures — `ct_colony_video_2015_productions.yaml` and `ct_mako_games.yaml` — now cover the other two, both drawn from the already-archived Connecticut open-data CSV (sha256-verified against `sources/MANIFEST.yaml` before parsing), filtered to the film and digital media production statute (`CGS 12-217jj`) only, and further filtered to rows on or after the rule file's 2010-01-01 effective date.
- **Literal, hand-checkable test module.** `tests/test_jurisdiction_us_ct.py` asserts one literal expected Decimal per active Connecticut pair (no snapshot testing), a per-tier band-coverage test that names any declared rate band with no covering pair, and provenance checks (programme id, source document, disclosure stage) for every active pair.
- **The transfer-discount refusal made permanent and uniform.** Connecticut's credit is statutorily transferable (CGS 12-217jj(e)(1)) but the statute states no market discount rate, and no Connecticut government publication does either (search log below). `engine.net_cash.transferable` correctly refuses to convert rather than invent a rate — previously asserted for exactly one pair, now asserted for all three, determined structurally from the loaded programme (never a hard-coded jurisdiction id). `engine/net_cash.py` is byte-identical to its committed state (`git diff --stat -- engine/` is empty).
- **Source note restated.** `jurisdictions/us-ct.yaml`'s `transfer_discount.source_note` now explains the full situation in plain words — including this session's search log — so a reader learns it without cross-referencing a test.

## CSV rows selected — verbatim and arithmetic

| Fixture | Verbatim CSV row | Band | Implied rate |
|---|---|---|---|
| `ct_colony_video_2015_productions.yaml` | `"Colony Video 2015 Productions","$187,220.00","2016-11-10T00:00:00.000","$18,722","Film and Digital Media Production Tax Credit","CGS 12-217jj","Stonington"` | $100,000-$500,000 (10%) | 18,722 / 187,220 = exactly 10.00000% — zero rounding residue |
| `ct_mako_games.yaml` | `"Mako Games LLC","$593,380.00","2011-08-15T00:00:00.000","$89,007","Film and Digital Media Production Tax Credit","CGS 12-217jj","Stamford"` | $500,000-$1,000,000 (15%) | 89,007 / 593,380 = exactly 15.00000% — zero rounding residue |

Both are single occurrences across the entire 658-row CSV (confirmed by full-dataset grep), preferred over recurring production companies (e.g. `National Media Connection LLC` appears 14 times) for the same D-05 one-off-production principle `ct_christmas_always.yaml` already applies.

Selection method: parsed with `csv.reader` (never `float`), skipped the blank row after the header, stripped `$` and thousands commas before `Decimal` conversion, filtered to `Statutory Reference == "CGS 12-217jj"` (611 of 658 rows matched, confirmed non-empty), then further filtered to `Date Issued >= 2010-01-01` (519 of 611 rows) — pre-2010 rows follow a genuinely different, non-tiered schedule (e.g. an $81,260 spend below the $100,000 minimum still nets a 30% credit in a 2009 row), so including them would have anchored a fixture to data the current rule file does not model. Within the post-2010 set the implied-rate distribution is clean: 24 rows at exactly 10%, 22 at exactly 15%, 472 at exactly 30%, one at a sub-dollar-rounding-adjacent 29.9% — no unexplained residue anywhere.

## Transfer-discount source search — URLs attempted and outcomes

Per Task 3's instruction to make the "no source exists" claim evidenced rather than assumed:

| URL | Outcome |
|---|---|
| `https://www.cga.ct.gov/current/pub/chap_208.htm` (CGS Chapter 208, the codified statute text) | HTTP 200. Full-text search for "discount" surfaces only unrelated open-space/educational-land and factoring-transaction definitions elsewhere in the chapter — nothing near §12-217jj, and no "broker" or "market rate" language anywhere in the section. |
| `https://portal.ct.gov/DECD/Content/Film-Division/Tax-Credits-and-Incentives/Film-Digital-Media-Tax-Credit-Program` (DECD's film tax credit programme page — the same page category `jurisdictions/us-ct.yaml`'s sources cite) | HTTP 302 -> the state portal's own 404 page. The `portal.ct.gov` site has been restructured since this rule file's original 2026-08-25 fetch; the specific programme guidance page could not be located at its prior path. |
| `https://portal.ct.gov/DRS/Publications/Informational-Publications` (Dept. of Revenue Services publications index) | HTTP 200. No "film", "transfer" or "discount" content anywhere on the listing page. |
| `https://www.ctfilm.com` (the state's former film-office marketing site) | HTTP 403 (blocked). |
| DuckDuckGo (lite/html) web search, several query variants | Returned no usable result links — the endpoint appears to require JS or block automated `curl` requests from this environment. |

No Connecticut government source publishing a market transfer-discount rate was located. This is recorded as a search log, not a proof of non-existence — see coverage entry D4 above.

## Task Commits

1. **Task 1: Add one Connecticut pair per unexercised statutory band** — `558ab35` (feat)
2. **Task 2: Connecticut test module — literal expected values and full band coverage** — `edcf63e` (test)
3. **Task 3: Make the unsourced-transfer-discount refusal a permanent asserted behaviour** — `79f2fa7` (test)

## Files Created/Modified

- `tests/fixtures/validation_pairs/ct_colony_video_2015_productions.yaml` — new active Connecticut pair, 10% band
- `tests/fixtures/validation_pairs/ct_mako_games.yaml` — new active Connecticut pair, 15% band
- `tests/test_jurisdiction_us_ct.py` — new Connecticut-specific test module (literal values, band coverage, uniform transfer-discount refusal)
- `jurisdictions/us-ct.yaml` — `transfer_discount.source_note` restated; `validation.last_checked_against_disclosure` updated to 2026-09-09
- `.planning/WINDOWS.md` — entry #29 added (FURB157 lint findings in the new test module, established RD-01 pattern)

## Decisions Made

See `key-decisions` in frontmatter above.

## Deviations from Plan

None — plan executed exactly as written. All three tasks completed, all `<verify>` commands pass, `engine/` and `sources/MANIFEST.yaml` are both untouched.

### Auto-fixed Issues

None.

### Out-of-scope observations (not fixed, not this plan's files)

**tests/test_jurisdiction_us_ct.py adds 3 new FURB157 findings** (verbose `Decimal("N")` constructor) — the same established RD-01 quoted-Decimal convention already present hundreds of times across `engine/`/`tests/` (WINDOWS entries 2, 4, 5, 11, 14, 17, 23, 24, 25, 27 record the identical accepted pattern in every prior phase). No new rule category introduced. Logged as WINDOWS.md entry #29 rather than fixed, per the established repo-wide convention.

---

**Total deviations:** 0 auto-fixed. **Impact:** None — plan executed as written.

## Issues Encountered

**Concurrent-agent interference during full-suite verification (not caused by this plan).** During this plan's final `uv run --frozen pytest -q` run, another GSD executor was actively mid-edit on `agent/job1.py` and `agent/groundedness.py` in the same shared checkout (`isolation="none"`, concurrent commits expected per this plan's dispatch instructions) — both files are on this plan's explicit forbidden-touch list and neither is in `files_modified`. This produced a transient full-suite failure (`tests/test_app_job1_route.py::test_get_job1_with_persisted_live_run_shows_bucket_counts_and_every_award`) and, moments later, a collection error in a new untracked file (`tests/test_agent_guardrails.py`, referencing a not-yet-created `agent.enactment` module) — both artifacts of another plan's in-progress, uncommitted work, not of this plan's changes. Confirmed by: (1) `git status --short` showing `agent/job1.py` and `agent/groundedness.py` modified/untracked while this plan never touched either; (2) `git diff --stat -- engine/` empty; (3) this plan's own scoped test run (`tests/test_jurisdiction_us_ct.py tests/test_engine_against_validation_pairs.py tests/test_engine_net_cash.py tests/test_validation_pair_fixtures.py tests/test_source_truth.py tests/test_golden_cost.py tests/test_route_a_basis_walk.py`, 88 tests) green; (4) the full suite excluding the two files the concurrent agent was actively editing, 578 tests, green. This plan's own commits and verification are unaffected; the transient state will resolve when the concurrent plan commits its own work.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All three of `jurisdictions/us-ct.yaml`'s declared rate bands are now backed by a real disclosed government award, closing the gap 01-RESEARCH.md's SRC-03 finding originally flagged and D-97 restored to this phase.
- The transfer-discount honesty gate (WINDOWS.md entry #3) is now uniformly tested rather than proven for one pair only — it remains genuinely open (no discount rate has been sourced) and should stay that way until a real Connecticut government publication states one.
- JUR-04 is not yet marked complete in REQUIREMENTS.md — it is shared with plan 05-08 (the cross-jurisdiction sweep), which has not finished. It will auto-complete the next time any plan in this phase finishes its `update_requirements` step after 05-08's SUMMARY exists.
- No blockers for downstream work in this phase.

---
*Phase: 05-curated-breadth-the-validation-loop*
*Completed: 2026-09-09*

## Self-Check: PASSED

- All 5 key files (2 new fixtures, 1 new test module, 2 modified files) confirmed present on disk with `[ -f ]`.
- All 3 task commits (`558ab35`, `edcf63e`, `79f2fa7`) confirmed present in `git log --oneline --all`.
- All plan-level `<acceptance_criteria>`/`<done>` criteria re-verified: `tests/test_jurisdiction_us_ct.py` (10 tests) green; `tests/test_engine_against_validation_pairs.py`, `tests/test_engine_net_cash.py`, `tests/test_validation_pair_fixtures.py`, `tests/test_source_truth.py` green; `tests/test_golden_cost.py` and `tests/test_route_a_basis_walk.py` (pinned golden totals + live honesty gate) green; `git diff --stat -- engine/` empty; `git diff --stat -- sources/MANIFEST.yaml` empty; `git diff --stat -- tests/test_engine_against_validation_pairs.py` empty (unmodified, as required).
- `bash .github/scripts/vendor-scan.sh` and `bash .github/scripts/lockfile-scan.sh` both exit 0.
