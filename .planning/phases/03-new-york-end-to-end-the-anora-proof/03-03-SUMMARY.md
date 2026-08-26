---
phase: 03-new-york-end-to-end-the-anora-proof
plan: 03
subsystem: infra
tags: [ci, bash, mutation-testing, compliance-gate, shp-14]

# Dependency graph
requires:
  - phase: 01-foundations-source-truth-deploy-path
    provides: ".github/workflows/ci.yml (five existing blocking jobs) and .github/scripts/lockfile-scan.sh's shell conventions (set -uo pipefail, PASS:/FAIL: prefixes, portable while-read loops)"
  - phase: 02-engine-spine-incentive-interpreter
    provides: "tests/test_engine_against_validation_pairs.py — the suite this plan proves non-vacuous, and its measured fact that Anora is New York's only assertion.mode: exact fixture"
provides:
  - ".github/scripts/mutation-check.sh — a scratch-copy, five-step, non-vacuity proof for the validation suite (SHP-14 second half)"
  - "tests/mutation_targets.yaml — the declared mutation table (D-51); adding a second jurisdiction's anchor is a one-row addition, not a script change"
  - "mutation-check (SHP-14) as a sixth blocking CI job in .github/workflows/ci.yml, running on every push and pull request"
affects: [08-anora-reproof, phase-8-shp-14-reproof]

actuals:
  tokens: 2983
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "mktemp -d scratch copy + immediate EXIT trap, .venv and .git deleted before any step runs — the CI compliance-script scratch-execution pattern, reusable for any future gate that must mutate something without touching the real working tree"
    - "Declared-table-driven bash gate (id/file/find/replace/expected_red_test/requirement/status/why rows), same shape as lockfile-scan.sh's PASS:/FAIL: convention but data-driven instead of hard-coded"

key-files:
  created:
    - tests/mutation_targets.yaml
    - .github/scripts/mutation-check.sh
  modified:
    - .github/workflows/ci.yml

key-decisions:
  - "Restore in step 5 uses cp (not mv) from FILE.orig to FILE, keeping FILE.orig alive through the cmp verification step, then explicitly rm -f'd afterward — this makes the 'verified rather than trusted' restore literal (cmp compares the restored file against a copy that still exists) rather than comparing a file against itself post-move"
  - "sed's substitution delimiter and pattern-escaping follow the plan's literal specification (s/${FIND}/${REPLACE}/, no regex-metacharacter escaping) rather than a more defensive escaped/pipe-delimited form, because D-49 designates this script's shape as inherited by Phase 8's SHP-14 reproof and the current single row's find/replace values contain no delimiter-colliding characters — a future row with a slash-bearing find value would need this delimiter choice revisited, noted here for that future author rather than solved speculatively now"

requirements-completed: [SHP-14]

coverage:
  - id: D1
    description: "bash .github/scripts/mutation-check.sh, invoked from the repo root, proves in one run: the validation suite is green before any mutation, a non-zero count of active New York exact-mode fixtures is on disk AND the declared expected_red_test collects a non-zero item count, the one-basis-point mutation lands exactly once in jurisdictions/us-ny.yaml (comment lines excluded), the mutated suite fails naming test_anora_reproduces_exactly_through_price_jurisdiction (not a collection/import error), and the file is restored byte-identical (cmp-verified) with the suite green again"
    requirement: "SHP-14"
    verification:
      - kind: other
        ref: "bash .github/scripts/mutation-check.sh (manual run, captured output)"
        status: pass
      - kind: other
        ref: "BEFORE=$(git status --porcelain); bash .github/scripts/mutation-check.sh; AFTER=$(git status --porcelain); [ \"$BEFORE\" = \"$AFTER\" ]"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/ -q (219 passed, no regression)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Zero active rows in tests/mutation_targets.yaml (status not 'active') exits non-zero with the empty-table message; an active row whose find pattern no longer matches jurisdictions/us-ny.yaml exactly once exits non-zero naming the unmatched pattern; reverting either edit restores exit 0 — the empty and adjacency SHP-14 edge cases named in the plan's must_haves"
    requirement: "SHP-14"
    verification:
      - kind: other
        ref: "manual run: status field set to 'disabled' -> FAIL: zero active rows -> revert -> exit 0"
        status: pass
      - kind: other
        ref: "manual run: find value set to a non-matching fragment -> FAIL: 0 occurrence(s) -> revert -> exit 0"
        status: pass
      - kind: other
        ref: "manual run: expected_red_test pointed at a non-existent node id -> FAIL: collected zero items -> revert -> exit 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "The script never mutates the invoking working tree, including on an interrupted run — git status --porcelain is byte-identical before and after a run that receives SIGINT mid-copy, and no scratch directory is left behind (D-50)"
    requirement: "SHP-14"
    verification:
      - kind: other
        ref: "manual run: bash .github/scripts/mutation-check.sh backgrounded, kill -INT sent mid-cp; git status --porcelain before/after identical; no leftover mktemp directory found under $TMPDIR"
        status: pass
    human_judgment: false
  - id: D4
    description: "mutation-check (SHP-14) runs as a sixth blocking job in .github/workflows/ci.yml on every push and pull request, and lockfile-scan, vendor-scan, commit-window, secret-scan and tests are byte-for-byte unchanged (D-52)"
    requirement: "SHP-14"
    verification:
      - kind: other
        ref: "uv run python -c \"...jobs==expected...\" (PASS: mutation-check job wired, five existing jobs intact)"
        status: pass
      - kind: other
        ref: "git diff .github/workflows/ci.yml — additions confined to the new job block and its comment"
        status: pass
    human_judgment: false
  - id: D5
    description: "The GitHub Actions run for this branch shows mutation-check (SHP-14) as a sixth job, that it passed, and that its log shows the deliberate red at step 4 for a real hosted CI run (not the local TestClient-equivalent invocation)"
    human_judgment: true
    rationale: "This is a property of the hosted GitHub Actions run, not the local script invocation — cannot be asserted from this machine. Deferred to end-of-phase harvesting per workflow.human_verify_mode=end-of-phase, same pattern as 03-01-SUMMARY.md's D4 and 03-02-SUMMARY.md's D7; consolidated into the phase's UAT.md by the phase-level verifier, not executed by this plan-level executor."

duration: 15min
completed: 2026-08-25
status: complete
---

# Phase 3 Plan 3: New York End-to-End — The Anora Proof — Mutation Non-Vacuity Gate Summary

**A five-step bash script (`mutation-check.sh`) mutates New York's credit rate by one basis point on a `mktemp -d` scratch copy, proves the validation suite goes red naming the exact test SHP-14 depends on, restores the file byte-identical, and now runs as a sixth blocking CI job — the working tree is never touched, even on an interrupted run.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-08-25T19:05:00-07:00 (approx., file reads and design)
- **Completed:** 2026-08-25T19:18:29-07:00 (Task 2 commit)
- **Tasks:** 2 (both `type="auto"`)
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- `tests/mutation_targets.yaml` declares one active row (`ny-base-rate-one-bp`): mutate `jurisdictions/us-ny.yaml`'s `base_rate: "0.25"` to `"0.2501"`, expecting `test_anora_reproduces_exactly_through_price_jurisdiction` to fail — with a header comment recording the measured fact that Anora is New York's only `assertion.mode: exact` fixture and that Connecticut's Christmas Always anchor is a one-row addition once WINDOWS.md #3 clears.
- `.github/scripts/mutation-check.sh` runs the five ordered steps entirely inside a `mktemp -d` scratch copy with an `EXIT` trap: (1) suite green unmutated, (2) a non-zero count of active New York exact-mode fixtures on disk AND a non-zero `--collect-only` count for the declared test — the actual vacuity check, (3) the mutation lands exactly once outside comment lines, (4) the mutated suite fails naming the declared test (not a collection/import/environment error), (5) `cp`-then-`cmp`-verified restore and a re-asserted green suite.
- Every failure path prints a `FAIL:` message on stderr naming the row `id` and the specific reason, matching `lockfile-scan.sh`'s conventions exactly (`set -uo pipefail`, `PASS:`/`FAIL:` prefixes, portable `while IFS= read -r` loops).
- `mutation-check (SHP-14)` is now a sixth job in `.github/workflows/ci.yml`, running `actions/checkout@v4` → `astral-sh/setup-uv@v5` → the script, on every push and pull request — `lockfile-scan`, `vendor-scan`, `commit-window`, `secret-scan` and `tests` are untouched (confirmed via `git diff` showing additions confined to the new job block).
- Manually exercised every named edge case: an empty table (status flipped off `active`) fails loudly with the empty-table message; an unmatched `find` fragment fails loudly naming the zero-occurrence count; a `SIGINT` sent mid-`cp` leaves `git status --porcelain` byte-identical and no scratch directory behind. All reverted to their committed state before commit.

## Task Commits

1. **Task 1: The declared mutation table and the five-step non-vacuity gate** — `1e11503` (feat)
2. **Task 2: Wire mutation-check into CI as a sixth blocking job** — `5446912` (feat)

**Plan metadata:** committed alongside this SUMMARY.

_Both tasks are `type="auto"`, not TDD — this plan adds no application code, only a compliance script and its CI wiring, so no RED/GREEN cycle applies._

## Files Created/Modified

- `tests/mutation_targets.yaml` — the declared mutation table (D-51); one active row, quoted-string fields throughout
- `.github/scripts/mutation-check.sh` — the five-step scratch-copy non-vacuity gate (SHP-14), matching `lockfile-scan.sh`'s shell conventions
- `.github/workflows/ci.yml` — adds the `mutation-check` job after `tests`, no other job touched

## Decisions Made

- Restore in step 5 uses `cp` (not the plan's literal `mv`) from `$FILE.orig` back to `$FILE`, so `$FILE.orig` still exists for the `cmp` verification that follows — a `mv`-then-`cmp` would have nothing left to compare against unless a second reference copy were kept. `$FILE.orig` is `rm -f`'d immediately after the verified restore, keeping the same net effect (no residue) the plan's literal wording intended.
- `sed`'s substitution follows the plan's literal, unescaped `s/${FIND}/${REPLACE}/` form. The current row's find/replace values contain no `/` or regex-metacharacter collision risk; a future row whose `find` value contains a slash would need the delimiter revisited — flagged here rather than solved speculatively for a case that doesn't exist yet.

## Deviations from Plan

None - plan executed exactly as written. The `cp`-vs-`mv` restore choice above is an implementation-level fidelity decision to make the plan's own "verified rather than trusted" restore requirement literally true, not a deviation from what the plan asked for.

## Issues Encountered

None. All acceptance criteria for both tasks verified directly:
- `bash .github/scripts/mutation-check.sh` — exits 0, `PASS:` lines for steps 1, 2, 4, 5 present, reports 1 active New York exact-mode fixture and 1 collected item
- `git status --porcelain` byte-identical before/after a full run, before/after an unmatched-`find` run, before/after an empty-table run, and before/after a `SIGINT`-interrupted run
- `tests/mutation_targets.yaml` parses under `yaml.safe_load`, one active row carries all eight required keys (verified both by the plan's own inline Python assertion and by the script's own `MALFORMED` row check)
- `uv run python -c "...jobs==expected..."` — PASS, exactly six job keys, `mutation-check`'s `runs-on`/`uses`/`run` fields all present
- `git diff .github/workflows/ci.yml` — additions confined to the new job block and its comment
- `uv run pytest tests/ -q` — 219 passed, unchanged from the 03-02 baseline
- `bash .github/scripts/lockfile-scan.sh`, `bash .github/scripts/vendor-scan.sh`, `bash .github/scripts/commit-window.sh` — all PASS, Phase 1 gates unaffected

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SHP-14 is now fully closed: the `tests` job (Phase 1) asserts exact equality against disclosed government figures on every commit, and `mutation-check` (this plan) proves that assertion is non-vacuous on every commit — Phase 8's SHP-14 reproof reruns this exact job rather than re-enacting a manual mutation ritual (D-49).
- Adding Connecticut's Christmas Always anchor once `WINDOWS.md` #3 (`jurisdictions/us-ct.yaml`'s unsourced `transfer_discount` rate) clears is a one-row addition to `tests/mutation_targets.yaml` with zero script changes — the table-driven design is proven, not aspirational.
- The hosted GitHub Actions confirmation (sixth job visible, deliberate red in its log) is deferred to end-of-phase per `workflow.human_verify_mode=end-of-phase`, matching 03-01's and 03-02's identical deferral pattern; will be harvested into the phase's UAT.md by the phase-level verifier.
- This is the last plan in Phase 3 (03-01, 03-02, 03-03 all complete) — Phase 3's remaining open item is the batch of deferred end-of-phase human-verify checks (D4/D7 from 03-01/03-02, D5 from this plan) that the phase-level verifier consolidates.
- No blockers for Phase 4.

---
*Phase: 03-new-york-end-to-end-the-anora-proof*
*Completed: 2026-08-25*

## Self-Check: PASSED

Both created files verified present on disk (`[ -f ]`): `tests/mutation_targets.yaml`, `.github/scripts/mutation-check.sh`. Both task commits (`1e11503`, `5446912`) verified present in `git log --oneline --all`. `.github/workflows/ci.yml` re-parsed under `yaml.safe_load` with exactly six job keys after the edit.
