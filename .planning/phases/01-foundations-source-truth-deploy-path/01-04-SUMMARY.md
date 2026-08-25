---
phase: 01-foundations-source-truth-deploy-path
plan: 04
subsystem: testing
tags: [pyyaml, pytest, decimal, source-verification, validation-fixtures, powerbi]

requires:
  - phase: 01-03
    provides: sources/MANIFEST.yaml format, the fixture path/field convention (D-01, D-03), the interpreter-only validation boundary (D-02), tests/test_validation_pair_fixtures.py base suite
provides:
  - "Twelve committed validation-pair fixtures spanning all four curated jurisdictions (us-ny x3, us-ca x2, us-nj x2, us-ct x1, us-ma x2 blocked, us-pa x2 blocked)"
  - "Connecticut's only validation coverage (JUR-04), closing the zero-CT gap 01-RESEARCH.md's SRC-03 Critical scope finding #2 identified"
  - "The D-05 third exact-mode anchor (ct_christmas_always.yaml, clean 30.0% statutory rate)"
  - "test_curated_jurisdictions_have_coverage, test_committed_pair_count, test_denominator_excludes_blocked_and_separates_stages — the guards that make a jurisdiction gap, a shrinking pair count, or a blended accuracy figure each fail the suite"
  - "accuracy_denominator_by_stage() — importable per-stage active-fixture-count helper for Phase 5's Job 1 mismatch taxonomy"
  - "The D-06 blocked-fixture contract (status blocked, non-null >40-char blocker, null qualified_spend/disclosure_stage permitted) as an explicit test branch"
affects: [phase-3-ci, phase-5-job1-mismatch-taxonomy, phase-6-ui-validated-badges, phase-8-proof-panel]

actuals:
  tokens: 480000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "D-09-style escape hatch for a live, interactive government dashboard (NJEDA's Power BI 'Film Tax Credit Activity Report'): archive the accessibility-tree text extraction (ARIA grid cell content, the same content a screen reader announces) plus a corroborating screenshot, since no single-file export of the full dataset exists — recorded explicitly in MANIFEST.yaml notes rather than silently treated as a normal document archive"
    - "Archive-as-published extension discipline extended beyond PDF/CSV to HTML: CA's disclosure is a server-rendered HTML table (Ninja Tables plugin), archived as .html per D-08's 'archive the original bytes as published' instruction"
    - "Blocked-fixture contract as an explicit per-status test branch, not a loosened blanket assertion: blocked requires MORE of a fixture (a >40-char blocker), not less"
    - "diversity_credit_amount: null (not '0') for jurisdictions whose disclosure has no such column at all — the money-field Decimal-parse check is skipped only for this field, only when null, only for active fixtures"

key-files:
  created:
    - sources/ca/2026-08-24-ca-film-commission-approved-projects.html
    - sources/nj/2026-08-24-njeda-film-tax-credit-activity-report-joker.txt
    - sources/nj/2026-08-24-njeda-film-tax-credit-activity-report-joker.png
    - sources/nj/2026-08-24-njeda-film-tax-credit-activity-report-trial-of-chicago-7.txt
    - sources/nj/2026-08-24-njeda-film-tax-credit-activity-report-trial-of-chicago-7.png
    - sources/ct/2026-08-24-ct-film-tax-credits-issued.csv
    - tests/fixtures/validation_pairs/ca_clueless_s1.yaml
    - tests/fixtures/validation_pairs/ca_disneys_hexed.yaml
    - tests/fixtures/validation_pairs/nj_joker.yaml
    - tests/fixtures/validation_pairs/nj_trial_of_the_chicago_7.yaml
    - tests/fixtures/validation_pairs/ct_christmas_always.yaml
    - tests/fixtures/validation_pairs/ma_dont_look_up.yaml
    - tests/fixtures/validation_pairs/ma_madame_web.yaml
    - tests/fixtures/validation_pairs/pa_creed_ii.yaml
    - tests/fixtures/validation_pairs/pa_knock_at_the_cabin.yaml
  modified:
    - sources/MANIFEST.yaml
    - tests/test_validation_pair_fixtures.py

key-decisions:
  - "Connecticut's validation pair is 'Christmas Always' ($3,865,005 qualified -> $1,159,502 issued, 30.0%), selected from the data.ct.gov open-data export after confirming a clean three-tier statutory schedule (10%/15%/30% at the $500k/$1M boundaries) across the CGS 12-217jj rows — this is the D-05 third exact-mode anchor deferred from 01-03"
  - "NJ Trial of the Chicago 7's credit_amount corrected to $5,371,984 (read directly from NJEDA's live Power BI dashboard) vs $5,371,983 in 01-RESEARCH.md/feasibility-incentives.md — a $1 discrepancy, archived primary source treated as authoritative per plan instruction, not silently reconciled"
  - "NJEDA's Film Tax Credit Activity Report is a live Power BI dashboard with no downloadable dataset export — archived as an accessibility-tree text extraction (D-09-style escape hatch) rather than a discrete document, documented explicitly as such in MANIFEST.yaml and each fixture's notes"
  - "CA's disclosure is archived as .html (not .csv, per the plan's files_modified list) because the CA Film Commission publishes the approved-projects table as a server-rendered HTML page, not a downloadable spreadsheet — 'archive as published' per D-08/D-09"
  - "diversity_credit_amount is null (not '0') for all CA/NJ/CT/MA/PA fixtures because none of those four jurisdictions' disclosures carry a diversity/equity credit line item at all — required a deviation fix to test_fixture_has_required_fields (see Deviations)"
  - "The four MA/PA pairs are committed status: blocked with qualified_spend and disclosure_stage null and a >40-char blocker naming both reasons (undisclosed spend; no curated rule file for MA/PA) — no sources/ archive exists for them, an explicit absence recorded in each fixture's notes and here"

requirements-completed: [SRC-03]

coverage:
  - id: D1
    description: "ca_clueless_s1.yaml, ca_disneys_hexed.yaml — two California allocation-stage validation pairs re-verified independently against the live CA Film Commission approved-projects table (not feasibility-incentives.md), assertion.mode bounded with a written variance_reason per D-04"
    requirement: "SRC-03"
    verification:
      - kind: unit
        ref: "tests/test_validation_pair_fixtures.py::test_fixture_has_required_fields[tests/fixtures/validation_pairs/ca_clueless_s1.yaml, ca_disneys_hexed.yaml]"
        status: pass
    human_judgment: true
    rationale: "The honesty claim underneath SRC-03 — that these digits were independently re-read from the live government page this session, not carried over from feasibility-incentives.md's secondary compilation — is a transcription-integrity claim a human should spot-check at least once, per the project's own honesty constraint. The bounded-mode variance_reason argument (allocation-vs-issued, unitemized uplift categories) is also a judgment call worth a human's agreement."
  - id: D2
    description: "nj_joker.yaml, nj_trial_of_the_chicago_7.yaml — two New Jersey estimated-stage validation pairs re-verified against NJEDA's live Power BI 'Film Tax Credit Activity Report' dashboard, with a $1 discrepancy found and corrected on the Trial of the Chicago 7 credit_amount (archived primary source treated as authoritative over both prior secondary compilations)"
    requirement: "SRC-03"
    verification:
      - kind: unit
        ref: "tests/test_validation_pair_fixtures.py::test_fixture_has_required_fields[tests/fixtures/validation_pairs/nj_joker.yaml, nj_trial_of_the_chicago_7.yaml]"
        status: pass
    human_judgment: true
    rationale: "Same transcription-integrity concern as D1, plus the $1 discrepancy resolution (favoring the archived dashboard capture over 01-RESEARCH.md and feasibility-incentives.md) is a precedence judgment a human should confirm reads as principled rather than arbitrary."
  - id: D3
    description: "ct_christmas_always.yaml — the twelfth fixture and Connecticut's only validation coverage, selected from the data.ct.gov open-data export using the D-05 small-no-uplift selection principle, closing JUR-04's zero-coverage gap and supplying the D-05 third exact-mode anchor"
    requirement: "SRC-03"
    verification:
      - kind: unit
        ref: "tests/test_validation_pair_fixtures.py::test_fixture_has_required_fields[tests/fixtures/validation_pairs/ct_christmas_always.yaml]"
        status: pass
      - kind: unit
        ref: "tests/test_validation_pair_fixtures.py::test_curated_jurisdictions_have_coverage"
        status: pass
    human_judgment: true
    rationale: "The row-selection reasoning (why this production over the many recurring-company rows in a 658-row dataset, why the 30% tier reads as clean rather than coincidental) is exactly the kind of selection judgment the plan itself calls out for review — a human should agree the selection was reasoned, not convenient."
  - id: D4
    description: "ma_dont_look_up.yaml, ma_madame_web.yaml, pa_creed_ii.yaml, pa_knock_at_the_cabin.yaml — four blocked fixtures, each with a >40-char blocker naming both the undisclosed-spend and no-curated-rule-file reasons, counted toward the 11 named pairs and excluded from the accuracy denominator by construction"
    requirement: "SRC-03"
    verification:
      - kind: unit
        ref: "tests/test_validation_pair_fixtures.py::test_fixture_has_required_fields[tests/fixtures/validation_pairs/ma_dont_look_up.yaml, ma_madame_web.yaml, pa_creed_ii.yaml, pa_knock_at_the_cabin.yaml]"
        status: pass
      - kind: unit
        ref: "tests/test_validation_pair_fixtures.py::test_denominator_excludes_blocked_and_separates_stages"
        status: pass
    human_judgment: false
  - id: D5
    description: "test_curated_jurisdictions_have_coverage, test_committed_pair_count, test_denominator_excludes_blocked_and_separates_stages, and accuracy_denominator_by_stage() — the three guard tests plus the per-stage denominator helper making a jurisdiction gap, a shrinking pair count, and a blended accuracy figure each fail the suite"
    requirement: "SRC-03"
    verification:
      - kind: unit
        ref: "uv run pytest tests/test_validation_pair_fixtures.py -q (17 passed)"
        status: pass
      - kind: other
        ref: "manual: temporarily flipped ct_christmas_always.yaml status to blocked, re-ran test_curated_jurisdictions_have_coverage, observed the expected AssertionError naming us-ct, reverted and confirmed the file diff was identical to the pre-edit backup"
        status: pass
    human_judgment: false

duration: 33min
completed: 2026-08-24
status: complete
---

# Phase 01 Plan 04: CA/NJ/CT Validation Pairs and the Blocked-Pair Guards Summary

**Twelve validation-pair fixtures across all four curated jurisdictions — two California allocation-stage pairs and two New Jersey estimated-stage pairs re-verified live (one $1 discrepancy corrected), a new Connecticut exact-mode pair closing JUR-04's zero-coverage gap, four Massachusetts/Pennsylvania pairs committed honestly as blocked, and three new guard tests plus a per-stage accuracy-denominator helper that make a jurisdiction gap, a shrinking pair count, or a blended accuracy figure each fail the suite.**

## Performance

- **Duration:** ~33 min
- **Started:** 2026-08-24T22:41:00-07:00 (first source fetch, CT CSV `curl` probe)
- **Completed:** 2026-08-24T23:14:00-07:00
- **Tasks:** 3
- **Files modified:** 17 (5 archived documents/screenshots + 1 manifest + 9 new fixtures + 1 test module, plus 2 screenshots not counted in the SUMMARY's `files_modified` list)

## Accomplishments

- Re-verified California's two allocation-stage pairs (Clueless S1, Disney's Hexed) directly against the live CA Film Commission approved-projects HTML table — figures matched 01-RESEARCH.md and feasibility-incentives.md exactly, no discrepancy.
- Re-verified New Jersey's two estimated-stage pairs (Joker, The Trial of the Chicago 7) directly against NJEDA's live Power BI "Film Tax Credit Activity Report" dashboard — found and corrected a genuine $1 discrepancy on the Trial of the Chicago 7's credit_amount ($5,371,984 archived-primary vs $5,371,983 in both prior secondary documents).
- Selected and committed Connecticut's first-ever validation pair ("Christmas Always", $3,865,005 → $1,159,502, a clean 30.0% statutory rate) from the data.ct.gov open-data export, closing the zero-CT gap 01-RESEARCH.md's SRC-03 Critical scope finding #2 identified and supplying the D-05 third exact-mode anchor deferred from 01-03.
- Committed all four Massachusetts/Pennsylvania pairs honestly as `status: blocked`, each with a >40-character blocker string naming both the undisclosed-qualifying-spend reason and the no-curated-rule-file reason — none silently dropped, none guessed.
- Added `test_curated_jurisdictions_have_coverage`, `test_committed_pair_count`, and `test_denominator_excludes_blocked_and_separates_stages`, plus the importable `accuracy_denominator_by_stage()` helper — the three structural guards this plan exists to add on top of the fixture set itself.
- Full repo suite (`uv run pytest tests/ -q`) is green: 25 passed, including 17 in the validation-pair suite alone (up from 5 at the start of this plan).

## Task Commits

Each task was committed atomically:

1. **Task 1: California and New Jersey pairs, re-verified against primary documents** — `9f4ac6e` (feat)
2. **Task 2: Select and commit a Connecticut validation pair** — `fed887d` (feat)
3. **Task 3: The four blocked pairs, and the guards that make gaps fail loudly** — `2e23f69` (feat)

**Plan metadata:** committed after this SUMMARY (see below)

## Files Created/Modified

- `sources/MANIFEST.yaml` - Five document entries: NY (pre-existing), CA (.html), NJ x2 (.txt dashboard extracts), CT (.csv)
- `sources/ca/2026-08-24-ca-film-commission-approved-projects.html` - Byte-for-byte curl of the CA Film Commission approved-projects page (1,741,901 bytes; archived as .html, not .csv, per D-08/D-09's "archive as published" instruction)
- `sources/nj/2026-08-24-njeda-film-tax-credit-activity-report-joker.txt` / `.png` - Accessibility-tree text extraction plus corroborating screenshot of the Joker row from NJEDA's live Power BI dashboard (D-09-style escape hatch — no downloadable export exists)
- `sources/nj/2026-08-24-njeda-film-tax-credit-activity-report-trial-of-chicago-7.txt` / `.png` - Same, for the Trial of the Chicago 7 row; the .txt records the $1 discrepancy finding explicitly
- `sources/ct/2026-08-24-ct-film-tax-credits-issued.csv` - Byte-for-byte curl of the data.ct.gov open-data export (101,709 bytes, 658 rows, 2007-08-10 through 2024-10-25)
- `tests/fixtures/validation_pairs/ca_clueless_s1.yaml`, `ca_disneys_hexed.yaml` - CA allocation-stage pairs, `assertion.mode: bounded`
- `tests/fixtures/validation_pairs/nj_joker.yaml`, `nj_trial_of_the_chicago_7.yaml` - NJ estimated-stage pairs, `assertion.mode: bounded`
- `tests/fixtures/validation_pairs/ct_christmas_always.yaml` - CT issued-stage pair, `assertion.mode: exact` (D-05 third anchor)
- `tests/fixtures/validation_pairs/ma_dont_look_up.yaml`, `ma_madame_web.yaml`, `pa_creed_ii.yaml`, `pa_knock_at_the_cabin.yaml` - Blocked fixtures, no sources/ archive (explicit absence)
- `tests/test_validation_pair_fixtures.py` - Explicit blocked/active branch in `test_fixture_has_required_fields`, `diversity_credit_amount: null` allowance, stage-separability test scoped to active fixtures, three new guard tests, `accuracy_denominator_by_stage()` helper

## Decisions Made

- **Connecticut pair selection: "Christmas Always"** — chosen over dozens of alternatives after computing the implied rate for every CGS 12-217jj row in the 658-row dataset and confirming a clean, undocumented-anywhere-in-project three-tier statutory schedule (10% at $100k-$500k, 15% at $500k-$1M, 30% above $1M) with essentially zero residue across every tier boundary checked. Preferred over recurring production companies (e.g. "National Media Connection LLC", 8+ occurrences) for the same D-05 reasoning 01-03 applied to Anora: a single, one-off production is the best test case.
- **NJ Trial of the Chicago 7 credit_amount corrected to $5,371,984**, overriding both 01-RESEARCH.md and feasibility-incentives.md's $5,371,983, per the plan's own instruction to treat the archived primary document as authoritative when a discrepancy is found. Recorded in the fixture's `notes` rather than silently reconciled.
- **NJEDA's Power BI dashboard archived via accessibility-tree text extraction, not a raw HTML/CSV file.** The report is a live, interactive Azure Government-cloud-backed visualization with a virtualized data grid and no single-file export; `$B html` on the rendered DOM does not contain the visible cell text (it lives only in the accessibility tree), so the archived artifact is the same content a screen reader announces, captured after sorting and scrolling the target row into the virtualized viewport. This is a genuine escape-hatch pattern beyond what D-08/D-09 anticipated (a live dashboard, not a discrete document) and is documented as such in `sources/MANIFEST.yaml`.
- **CA's disclosure archived as `.html`, not `.csv`** — the plan's `files_modified` list named a `.csv` path, but the CA Film Commission's approved-projects list is published as a server-rendered HTML table (a WordPress Ninja Tables plugin embed), not a downloadable spreadsheet. Archived "as published" per D-08/D-09's own instruction for exactly this case; filename deviation documented here.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `diversity_credit_amount` required-field check blocked every CA/NJ/CT/MA/PA fixture from passing the pre-existing test**
- **Found during:** Task 1 (writing `ca_clueless_s1.yaml`)
- **Issue:** The plan instructs (Task 1 action text): "Omit `diversity_credit_amount` where the jurisdiction publishes no such column rather than writing a zero, because a zero asserts the column exists and was empty." But the pre-existing `test_fixture_has_required_fields` (written in plan 01-03, not modified by this plan's `<files>` list for Task 1) requires every `MONEY_FIELDS` entry — including `diversity_credit_amount` — to be a Decimal-parseable string for any `status: active` fixture. Neither omitting the key (fails the `REQUIRED_FIELDS` presence check) nor setting it to `null` (fails the `isinstance(raw, str)` check) nor `""` (fails the `Decimal()` parse) could satisfy the existing test as written, directly blocking every one of this plan's active fixtures from passing.
- **Fix:** Modified `test_fixture_has_required_fields`'s money-field loop to skip the Decimal-string check specifically for `diversity_credit_amount` when its value is `null`, with an inline comment explaining the distinction from "0" (column absent vs. column present-and-empty). `qualified_spend` and `credit_amount` remain mandatory non-null strings for every active fixture — only this one field may be `null`. Applied to all nine new active/blocked fixtures.
- **Files modified:** `tests/test_validation_pair_fixtures.py` (not in Task 1's `<files>` list, but necessary to complete the task as literally instructed)
- **Verification:** `uv run pytest tests/test_validation_pair_fixtures.py -q` — all 9 fixtures (5 pre-existing NY + 4 new) passed after the fix.
- **Committed in:** `9f4ac6e` (Task 1 commit)

**2. [Rule 1 - Sequencing, self-noted, no functional impact] MANIFEST.yaml's Connecticut entry committed one commit before the CT source file and fixture**
- **Found during:** Reviewing the staged diff before Task 1's commit
- **Issue:** All five `sources/MANIFEST.yaml` document entries (NY pre-existing, CA, NJ x2, CT) were written in a single edit before Task 1's commit, for efficiency. `git add sources/MANIFEST.yaml` in Task 1 staged the whole file — including the CT entry — one commit before `sources/ct/2026-08-24-ct-film-tax-credits-issued.csv` itself was committed in Task 2. Between `9f4ac6e` and `fed887d`, the committed MANIFEST briefly referenced an uncommitted file.
- **Fix:** No behavioral fix needed — by the end of the plan (after `fed887d`), the CT source file and its MANIFEST entry are both committed and the sha256 re-hash check passes. Documented here rather than hidden, following the precedent 01-03-SUMMARY.md set for harmless sequencing deviations.
- **Files modified:** `sources/MANIFEST.yaml` (already reflected in the Task 1 commit `9f4ac6e`)
- **Verification:** After `fed887d`, `git log` shows both the MANIFEST entry and the archived file present; the re-hash check in Task 2's automated verify passed.
- **Committed in:** `9f4ac6e` (MANIFEST entry), `fed887d` (the file itself, closing the gap)

---

**Total deviations:** 2 (1 auto-fixed blocking issue, 1 self-noted sequencing deviation with no functional impact)
**Impact on plan:** The `diversity_credit_amount` fix was necessary for the plan's own explicit instruction ("omit... rather than writing a zero") to be satisfiable at all against the pre-existing test — without it, Task 1 could not have completed. The MANIFEST sequencing gap never touched a committed inconsistency (the gap closed within the same plan, before the next task read it) and never affected a money value or a hash.

## Issues Encountered

- **Search engines (Google, Bing, DuckDuckGo) all returned bot-detection challenges or irrelevant results** when attempting to locate the NJEDA activity report via web search. Resolved by navigating njeda.gov's own site search directly, which surfaced the `njeda.gov/film/` program page and, from its outbound links, the "Film Incentive Transparency Map" — a live Power BI dashboard that turned out to be the primary disclosure itself (better than a static PDF would have been, since it's the government's own current data, not a point-in-time report).
- **The Power BI dashboard's virtualized table does not expose row text in its raw DOM (`innerHTML`)** — only in the browser's accessibility tree. Resolved by using JS `eval` to read and set the internal `.mid-viewport` scroll container's `scrollTop` directly (dispatching a `scroll` event to trigger PowerBI's virtualization re-render), then extracting the accessibility-tree text at each scroll position. This was a genuine technical obstacle not anticipated by the plan's PDF/CSV-oriented archival instructions; see "NJEDA's Power BI dashboard archived via accessibility-tree text extraction" under Decisions Made for the resulting pattern.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All four curated jurisdictions (NY, CA, NJ, CT — JUR-01 through JUR-04) now have active validation coverage; `test_curated_jurisdictions_have_coverage` guards against any of them silently losing it.
- `accuracy_denominator_by_stage()` is importable from `tests.test_validation_pair_fixtures` and ready for Phase 5's Job 1 mismatch taxonomy to consume directly — current per-stage counts are `{'issued': 4, 'allocated': 2, 'estimated': 2}` (8 active fixtures total; 4 blocked, excluded).
- D-05's three-exact-mode-anchor bar is now met: Anora, Succession S4 (both 01-03), and ct_christmas_always.yaml (this plan) are all `assertion.mode: exact` with no unexplained residue.
- The "Flagged planner assumption" in 01-04-PLAN.md (a 12th, additive Connecticut pair rather than a swap for one of the 11) was accepted as written — the developer did not request the alternative (holding the set at exactly 11 by replacing a blocked MA/PA pair). If that preference changes, the swap remains a one-file change per the plan's own note.
- Phase 3's SHP-14 CI suite and Phase 5's Job 1 mismatch taxonomy can both build on this fixture set and the new guard tests directly — no further schema changes anticipated for Milestone 1's four curated jurisdictions.

---
*Phase: 01-foundations-source-truth-deploy-path*
*Completed: 2026-08-24*

## Self-Check: PASSED

All 15 key files (`sources/MANIFEST.yaml`, 5 archived documents, 2 screenshots, 9 fixtures, the test module) confirmed present on disk with `[ -f ]`. All three task commit hashes (`9f4ac6e`, `fed887d`, `2e23f69`) confirmed present in `git log --oneline --all`. Full repo suite (`uv run pytest tests/ -q`) confirmed green: 25 passed.
