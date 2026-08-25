---
phase: 01-foundations-source-truth-deploy-path
plan: 03
subsystem: testing
tags: [pyyaml, pytest, decimal, source-verification, validation-fixtures]

requires:
  - phase: 01-01
    provides: pytest/pyyaml dependency resolution, repo skeleton, pyproject.toml test config
provides:
  - "sources/MANIFEST.yaml — the archive index format every future ingested document follows (D-10)"
  - "The fixture path/field convention (D-01, D-03) three NY validation pairs implement, ready for plan 01-04's CA/NJ/CT expansion"
  - "The interpreter-only validation boundary (D-02) confirmed and structurally encoded"
  - "tests/test_validation_pair_fixtures.py — the fixture-shape suite Phase 3's SHP-14 CI job and Phase 5's Job 1 both build on"
affects: [01-04, phase-3-ci, phase-5-job1-mismatch-taxonomy, phase-6-ui-validated-badges, phase-8-proof-panel]

actuals:
  tokens: 2800
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "One YAML validation-pair fixture per file at tests/fixtures/validation_pairs/{jurisdiction}_{slug}.yaml (D-01)"
    - "sources/MANIFEST.yaml as the single source-of-truth index: one document row, sha256, cited_for list naming every figure it backs"
    - "Money fields as YAML strings of bare digits, never floats, parsed to Decimal in tests"
    - "assertion.mode: exact | bounded, with bounded requiring a written variance_reason naming the specific unobservable — no undeclared tier"

key-files:
  created:
    - sources/MANIFEST.yaml
    - sources/ny/2026-08-24-esd-q3-film-report-2025.pdf
    - tests/fixtures/validation_pairs/ny_anora.yaml
    - tests/fixtures/validation_pairs/ny_succession_s4.yaml
    - tests/fixtures/validation_pairs/ny_gilded_age_s2.yaml
    - tests/test_validation_pair_fixtures.py
  modified: []

key-decisions:
  - "D-02 confirmed as interpreter-only (user selected 'interpreter-only' at the Task 1 checkpoint): a validation pair proves the incentive interpreter only, never cost localization. All three fixtures feed qualified_spend IN as a given and assert only on credit_amount OUT; no fixture carries a production_type-adjacent input-vector field (crew, shoot_days, budget_input, etc.), confirmed by grep across all three files."
  - "The Gilded Age S2's assertion.mode set to bounded (tolerance_bps: 150), not exact — its implied rate (26.29%) carries a 129bp residue above the clean 25.0% base rate that Anora and Succession S4 both hit; the ESD table's 7 money/count columns do not itemize which additional credit(s) were stacked, so the unobservable is named explicitly in variance_reason rather than asserted away."
  - "D-05's third required exact-mode fixture is not yet supplied by this plan — Anora and Succession S4 are the two exact-mode anchors; per the plan's own instruction, plan 01-04 (CA/NJ/CT expansion) carries the bar of supplying a third small, uplift-free exact-mode pair, most plausibly from Connecticut per 01-RESEARCH.md's Critical Scope Finding #2 (zero of the 11 named pairs are CT, and CT has no exact-mode candidate yet either)."

patterns-established:
  - "Independent transcription discipline: figures are read with pdftotext -layout over the archived bytes, cross-checked against 01-RESEARCH.md's independently-recorded values, with any discrepancy reported rather than reconciled. No discrepancy occurred this session — all three rows matched exactly."
  - "Diversity Credit Amount tracked as diversity_credit_amount, its own field, never folded into credit_amount — credit_amount equals the ESD table's own Credit Issued Amount column exactly, which is the number the reproduction test exists to match."

requirements-completed: [SRC-03]

coverage:
  - id: D1
    description: "NY ESD Q3 2025 quarterly report archived byte-for-byte under sources/ny/, indexed in sources/MANIFEST.yaml with a sha256 that matches the file on disk"
    requirement: "SRC-03"
    verification:
      - kind: unit
        ref: "command: python -c sha256 re-hash of sources/MANIFEST.yaml documents[0] against sources/ny/2026-08-24-esd-q3-film-report-2025.pdf"
        status: pass
    human_judgment: false
  - id: D2
    description: "ny_anora.yaml — Anora validation pair (qualified_spend 3964760, credit_amount 991190, diversity_credit_amount 4956) transcribed independently from the archived PDF, interpreter-only boundary (D-02) holding structurally"
    requirement: "SRC-03"
    verification:
      - kind: unit
        ref: "tests/test_validation_pair_fixtures.py::test_fixture_has_required_fields[tests/fixtures/validation_pairs/ny_anora.yaml]"
        status: pass
    human_judgment: true
    rationale: "Automated tests prove the fixture's shape and Decimal-safety, but the honesty claim underneath SRC-03 — that these exact digits were actually read out of the archived government PDF this session, not carried over from a summary or a secondary source — is a transcription-integrity claim a human should spot-check against the archived PDF at least once, per the project's own honesty constraint."
  - id: D3
    description: "ny_succession_s4.yaml and ny_gilded_age_s2.yaml — two more NY issued-stage pairs from the same archived document, with Gilded Age's assertion.mode argued in writing (bounded, 150bps, named unobservable) per D-04"
    requirement: "SRC-03"
    verification:
      - kind: unit
        ref: "tests/test_validation_pair_fixtures.py::test_fixture_has_required_fields[tests/fixtures/validation_pairs/ny_succession_s4.yaml, ny_gilded_age_s2.yaml]"
        status: pass
    human_judgment: true
    rationale: "Same transcription-integrity concern as D2, plus the assertion.mode: bounded choice for Gilded Age is an argued judgment call (which unobservable explains the 129bp residue) that a human should agree reads as an honest argument, not a rationalization."
  - id: D4
    description: "tests/test_validation_pair_fixtures.py — parametrized, deterministic fixture-shape suite that fails collection (not a vacuous green) when the fixture directory is empty"
    requirement: "SRC-03"
    verification:
      - kind: unit
        ref: "uv run pytest tests/test_validation_pair_fixtures.py -q (5 passed)"
        status: pass
      - kind: other
        ref: "manual: moved tests/fixtures/validation_pairs/ aside, re-ran suite, observed RuntimeError at collection time (exit code 2), restored directory"
        status: pass
    human_judgment: false
  - id: D5
    description: "test_disclosure_stages_are_separable — D-07 cohort-separation guarantee, no fixture's disclosure_stage is blended across stages"
    requirement: "SRC-03"
    verification:
      - kind: unit
        ref: "tests/test_validation_pair_fixtures.py::test_disclosure_stages_are_separable"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-08-24
status: complete
---

# Phase 01 Plan 03: NY Validation Pairs — Source-Verification Pipeline Summary

**Three NY issued-stage validation pairs (Anora, Succession S4, The Gilded Age S2) transcribed independently from one archived, sha256-hashed ESD PDF, with the interpreter-only validation boundary (D-02) confirmed by the user and held structurally in every fixture.**

## Performance

- **Duration:** ~8 min (this continuation; Task 1's checkpoint decision was resolved by the user in a prior session)
- **Started:** 2026-08-24T22:41:10-07:00 (first fetch)
- **Completed:** 2026-08-24T22:45:40-07:00
- **Tasks:** 2 (Task 1 was a decision checkpoint, resolved by the user before this continuation — recorded below, no file changes)
- **Files modified:** 6 created (1 manifest, 1 PDF, 3 fixtures, 1 test module)

## Accomplishments

- Task 1 (checkpoint:decision) resolved: user selected **interpreter-only** for D-02 — a validation pair proves the incentive interpreter only, never cost localization. Applied structurally: every fixture feeds `qualified_spend` in as a given and asserts only on `credit_amount` out; no fixture carries any input-vector field.
- Fetched the NY ESD Q3 2025 quarterly report (`https://esd.ny.gov/sites/default/files/media/document/Q3-Film-Report-2025.pdf`, 410,471 bytes) and archived it byte-for-byte at `sources/ny/2026-08-24-esd-q3-film-report-2025.pdf`. Well under the D-09 25MB escape-hatch threshold.
- `sources/MANIFEST.yaml` records the archive's `url`, `retrieved_at`, `sha256`, `jurisdiction: us-ny`, `document_title`, and `cited_for` (all three productions). Re-hashing the archived file reproduces the recorded sha256 exactly.
- Independently transcribed all three NY rows with `pdftotext -layout` (not an LLM summary, not carried over from `feasibility-incentives.md`) and cross-checked against 01-RESEARCH.md's independently-recorded values — **zero discrepancies** across Anora, Succession S4, and The Gilded Age S2.
- `ny_anora.yaml`: `qualified_spend 3964760` → `credit_amount 991190` (clean 25.0%), `diversity_credit_amount 4956` tracked separately, `assertion.mode: exact` — the D-05 anchor.
- `ny_succession_s4.yaml`: `qualified_spend 102920384` → `credit_amount 25747913` (25.02%, effectively clean), `assertion.mode: exact` — the second D-05 anchor.
- `ny_gilded_age_s2.yaml`: `qualified_spend 134340015` → `credit_amount 35318864` (26.29%), `assertion.mode: bounded`, `tolerance_bps: 150`, with `variance_reason` naming the specific unobservable — the ESD table does not itemize which stackable NY credit uplift (if any) was claimed on top of the base rate.
- `tests/test_validation_pair_fixtures.py`: sorted-glob parametrization (deterministic case order across runs), hard `RuntimeError` at collection time on an empty fixture directory (verified by moving the directory aside and observing the failure), `test_fixture_filenames_are_unique`, and `test_disclosure_stages_are_separable` (D-07).
- Full repo test suite (`uv run pytest tests/ -q`) is green: 13 passed, including the pre-existing health-check suite from plan 01-01.

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix the validation boundary (D-02)** — no commit; a decision checkpoint resolved by the user (interpreter-only), applied structurally starting in Task 2. See Decisions Made.
2. **Task 2: End-to-end "Anora reproduces from a government document"** — `ff0f48c` (feat)
3. **Task 3: The two remaining New York pairs, from the same archived document** — `9661043` (feat)
4. **Deviation fix: date consistency** — `27e7a28` (fix)

**Plan metadata:** committed after this SUMMARY (see below)

## Files Created/Modified

- `sources/MANIFEST.yaml` - Archive index: one document row (NY ESD Q3 2025 report), sha256, `cited_for` naming all three productions
- `sources/ny/2026-08-24-esd-q3-film-report-2025.pdf` - Byte-for-byte archived copy, 410,471 bytes
- `tests/fixtures/validation_pairs/ny_anora.yaml` - Anora validation pair, `assertion.mode: exact`
- `tests/fixtures/validation_pairs/ny_succession_s4.yaml` - Succession S4 validation pair, `assertion.mode: exact`
- `tests/fixtures/validation_pairs/ny_gilded_age_s2.yaml` - Gilded Age S2 validation pair, `assertion.mode: bounded` with an argued `variance_reason`
- `tests/test_validation_pair_fixtures.py` - Parametrized fixture-shape suite: required-field/type checks, empty-set hard failure, filename uniqueness, disclosure-stage cohort separation

## Decisions Made

- **D-02 resolved: interpreter-only.** The user selected `interpreter-only` at the Task 1 checkpoint, confirming CONTEXT.md's own recommendation. A validation pair proves the incentive interpreter only — fixtures feed `qualified_spend` in as a given and assert only on `credit_amount` (net cash) out. The cost-localization half of the pipeline (inputs → qualified_spend) has no government ground truth and is never labelled validated anywhere in this fixture set. Verified structurally: grepping all three fixtures for `crew|shoot_days|cast|budget_input|input_vector` returns nothing.
- **Gilded Age S2 assertion tier: `bounded`, not `exact`.** Its implied rate (26.29%) is 129bp above the clean 25.0% base rate both Anora and Succession S4 hit exactly. `feasibility-incentives.md:266` names this exact residue as an unlisted uplift. The ESD "Credits Issued" table's 7 money/count columns (Qualified Costs, NYS Spend, Total Hires, Credit Eligible Hours, Credit Eligible Wages, Credit Issued Amount, Diversity Credit Amount) do not name which additional credit was stacked — NY's program has at least one documented stackable bonus in this period (the "Production Plus" 5-10% bonus, `feasibility-incentives.md:162`) but the disclosure does not say whether this production claimed it or something else. `tolerance_bps: 150` is sized to cover the observed 129bp residue plus a small margin, not to reverse-engineer the exact mechanism.
- **D-05's third exact-mode fixture is deferred to plan 01-04.** This plan supplies two (Anora, Succession S4); Gilded Age is deliberately `bounded`. Per the plan's own instruction, 01-04 (CA/NJ/CT expansion) should supply the third small, uplift-free exact-mode pair — Connecticut is the most plausible source, since 01-RESEARCH.md's Critical Scope Finding #2 already flags zero of the 11 named pairs as CT and recommends selecting a small, single-programme CT production from the open-data CSV for exactly this reason.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] retrieved_at/date_checked recorded in UTC, rolling to the wrong calendar day**
- **Found during:** Post-Task-3 review, before writing this SUMMARY
- **Issue:** `date -u` was used to timestamp `retrieved_at` in `sources/MANIFEST.yaml`, which returned `2026-08-25T05:41:10Z` — one calendar day ahead of the local session date (`2026-08-24`, MST/UTC-7) and, more importantly, one day ahead of the archive filename itself (`sources/ny/2026-08-24-esd-q3-film-report-2025.pdf`, D-08's own date-stamped filename convention). `date_checked` in all three fixtures inherited the same UTC-rolled date.
- **Fix:** Re-expressed `retrieved_at` as local time with an explicit `-07:00` offset (`2026-08-24T22:41:10-07:00`), still fully ISO-8601 per D-10, and set `date_checked` to `2026-08-24` across all three fixtures — consistent with the filename and the local session date.
- **Files modified:** `sources/MANIFEST.yaml`, `tests/fixtures/validation_pairs/ny_anora.yaml`, `tests/fixtures/validation_pairs/ny_succession_s4.yaml`, `tests/fixtures/validation_pairs/ny_gilded_age_s2.yaml`
- **Verification:** Re-ran `uv run pytest tests/ -q` (13 passed) and the sha256 re-hash check (still matches — the fix touched only timestamp fields, not the archived bytes or any money value) after the edit.
- **Committed in:** `27e7a28`

**2. [Rule 2 - Missing critical, self-corrected before commit] Front-loaded `test_disclosure_stages_are_separable` and all three `cited_for` entries into the Task 2 commit**
- **Found during:** Writing Task 2's test file and manifest
- **Issue:** The plan sequences `test_disclosure_stages_are_separable` and the second/third `cited_for` entries as Task 3 work. Writing the test suite once with all its assertions, and the manifest's `cited_for` list with all three productions already known from 01-RESEARCH.md, was simpler than staging the file in two passes for no functional benefit.
- **Fix:** No behavioral fix needed — both are additive and harmless with only one fixture present at Task 2's commit point (the D-07 test still passes trivially on a single-fixture set). Documented here rather than hidden, since it is a real deviation from the plan's literal task boundary even though the artifact-level acceptance criteria for both tasks are unaffected.
- **Files modified:** `tests/test_validation_pair_fixtures.py`, `sources/MANIFEST.yaml` (both already reflected in the Task 2 commit `ff0f48c`)
- **Verification:** Task 2's own acceptance criteria (exactly one manifest document entry) and Task 3's acceptance criteria (manifest `cited_for` names three productions, `test_disclosure_stages_are_separable` defined) both independently pass.
- **Committed in:** `ff0f48c` (originally), unaffected by later commits

---

**Total deviations:** 2 (1 auto-fixed bug, 1 self-noted sequencing deviation with no functional impact)
**Impact on plan:** The date-consistency bug was real and is fixed; it never touched a money value or the archived document's bytes. The sequencing deviation changed nothing observable at either task's acceptance-criteria checkpoint.

## Issues Encountered

None. The NY ESD PDF fetched cleanly on the first attempt (HTTP 200, no redirect — effective URL matched the requested URL), and all three independently-transcribed rows matched 01-RESEARCH.md's recorded values exactly with no discrepancy to report.

## Observed Empty-Fixture-Directory Failure (plan-level verification step 3)

```
$ mv tests/fixtures/validation_pairs /tmp/... && mkdir -p tests/fixtures/validation_pairs
$ uv run pytest tests/test_validation_pair_fixtures.py -q
==================================== ERRORS ====================================
___________ ERROR collecting tests/test_validation_pair_fixtures.py ____________
tests/test_validation_pair_fixtures.py:28: in <module>
    raise RuntimeError(
E   RuntimeError: No fixture files found under tests/fixtures/validation_pairs/*.yaml — an empty validation-pair set must fail loudly, not report a vacuous green.
=========================== short test summary info ============================
ERROR tests/test_validation_pair_fixtures.py - RuntimeError: No fixture files...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.45s
$ exit code: 2
```
Directory restored immediately after (`ny_anora.yaml` intact); re-ran the full suite to confirm 13 passed afterward.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `sources/MANIFEST.yaml` and the `tests/fixtures/validation_pairs/{jurisdiction}_{slug}.yaml` convention are proven end-to-end and ready for plan 01-04 to extend into CA, NJ, and CT.
- **Carried bar for 01-04:** D-05 needs a third `mode: exact` fixture on a small, uplift-free production. Anora and Succession S4 supply two; The Gilded Age S2 is deliberately `bounded`. 01-RESEARCH.md's Critical Scope Finding #2 (zero of the 11 named pairs are Connecticut) makes CT the natural source for both the third exact-mode pair and JUR-04's only validation coverage — recommend selecting a small, single-programme (`§12-217jj` only) CT production from the open-data CSV.
- **Carried bar for 01-04 (blocked pairs):** 01-RESEARCH.md's Critical Scope Finding #1 recommends committing the 4 MA/PA pairs as `status: blocked` fixtures with an explicit `blocker` string (no disclosed qualifying spend, no curated JurisdictionRuleSet for MA/PA in Milestone 1 scope) rather than silently omitting them.
- `tests/test_validation_pair_fixtures.py` is ready for Phase 3's SHP-14 CI suite and Phase 5's Job 1 mismatch taxonomy to build on directly — no schema changes anticipated, only more fixtures.

---
*Phase: 01-foundations-source-truth-deploy-path*
*Completed: 2026-08-24*

## Self-Check: PASSED

All key files (`sources/MANIFEST.yaml`, the archived PDF, all three fixtures, the test module, this SUMMARY) confirmed present on disk with `[ -f ]`. All three commit hashes (`ff0f48c`, `9661043`, `27e7a28`) confirmed present in `git log --oneline --all`.
