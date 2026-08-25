---
phase: 01-foundations-source-truth-deploy-path
plan: 05
subsystem: testing
tags: [source-verification, pytest, pyyaml, hashlib, ny-tax-law, ga-dor, ct-open-data, parallel]

requires:
  - phase: 01-04
    provides: The interpreter-only validation boundary (D-02), sources/MANIFEST.yaml archive-index format, the CT CSV archive and fixture this entry cites rather than re-fetches
provides:
  - "`.planning/SOURCE-TRUTH.md` — the answer record for all four Phase 1 source-verification questions (SRC-01, SRC-02, SRC-04, SRC-05), each with question/answer/URL(s)/date_checked/confidence/what-was-refuted, cited by Phase 2's rule files"
  - "The New York $700M/$800M cap conflict CLOSED against the enacted budget bill (S3009-C/A3009-C, Chapter 59 of the Laws of 2025) rather than left as a press-corroborated guess — the base program stays $700M/yr through 2036, a separate new $100M/yr Empire State Independent Film Production Credit (Tax Law section 24-d) explains the AUP document's $800M figure as a combined total"
  - "tests/test_source_truth.py — entry-shape assertions, bidirectional manifest/disk hash reconciliation, and fixture-to-manifest cross-reference, proven non-vacuous by an observed mutated-file failure"
  - "Nine newly archived and hashed primary documents (3 NY PDFs, 2 NY live-page HTMLs, 3 GA DOR HTMLs) plus manifest completeness rows for two previously-uncited NJEDA screenshot PNGs"
affects: [phase-2-rule-files, phase-3-ci, phase-5-job1-mismatch-taxonomy, phase-7-partner-track, phase-8-proof-panel]

actuals:
  tokens: 765848
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Statute-first source resolution when a live government site is Cloudflare-blocked: fetched the actual enacted bill PDF from the legislature's own PDF-serving subdomain (legislation.nysenate.gov, distinct from the Cloudflare-protected www.nysenate.gov codified-law pages), and used two independent third-party mirrors (Internet Archive Wayback Machine, newyork.public.law) as corroboration only — never as the basis for the answer itself."
    - "Tracked-changes bill text as primary evidence for 'did this figure actually change': a NY budget bill's bracket notation ([old text] new text) directly shows which token changed between two enactments, letting the SRC-01 entry cite 'the dollar figure is not bracketed as changed, only the year' rather than inferring non-change from absence of a contrary statement."
    - "Independent transcription catching a research-document imprecision: re-verifying SRC-02's Municipality-blank artifact directly against the archived CSV bytes found the actual blank rows dated 2009-07-21, not '2007' as 01-RESEARCH.md's prose stated — corrected in the entry rather than silently repeated."
    - "Heading-anchored regex section-splitting (`^## SRC-\\d\\d`) instead of the plan's own fragile literal-substring split, to keep an entry's body free to mention other requirement IDs without corrupting the parser's section boundaries."

key-files:
  created:
    - .planning/SOURCE-TRUTH.md
    - tests/test_source_truth.py
    - sources/ny/2026-08-24-ny-enacted-budget-film-credit-extract.pdf
    - sources/ny/2026-08-24-esd-film-credit-guidelines.pdf
    - sources/ny/2026-08-24-esd-film-prod-cpa-aup.pdf
    - sources/ny/2026-08-24-esd-live-film-production-page.html
    - sources/ny/2026-08-24-esd-independent-film-production-page.html
    - sources/ga/2026-08-24-dor-film-tax-credit-resources.html
    - sources/ga/2026-08-24-dor-film-tax-credit-withholding-instructions.html
    - sources/ga/2026-08-24-dor-instructions-for-production-companies.html
  modified:
    - sources/MANIFEST.yaml

key-decisions:
  - "SRC-01 recorded as CLOSED, not an unresolved conflict (D-13's fallback), because the enacted bill's own tracked-changes text directly shows the $700M dollar figure unbracketed (unchanged) while only the 2034->2036 sunset year is bracketed as amended -- this is direct evidence of non-change, not an argument from silence, and D-13 only requires an unresolved-conflict record when the evidence genuinely does not close the question."
  - "www.nysenate.gov's Cloudflare bot-verification challenge blocked both curl and headless-browser fetches; the enacted bill was instead fetched from legislation.nysenate.gov's PDF-serving endpoint (unblocked, and arguably a stronger source than the codified-law summary page it replaces), with Wayback Machine and newyork.public.law mirrors used only as corroboration -- documented explicitly in the entry's Method note rather than silently presenting the mirror-sourced route as if it were a direct fetch."
  - "Independently re-verified SRC-02's Municipality-blank artifact against the already-archived CT CSV bytes (not re-fetched) and found the blank rows dated 2009-07-21, correcting 01-RESEARCH.md's '2007' attribution -- recorded as a correction in the entry rather than silently repeating an unverified prior claim."
  - "SRC-05's loan-out-specificity confidence raised from 01-RESEARCH.md's MEDIUM caveat to HIGH after fetching the second Georgia DOR page ('Instructions for Production Companies') that explicitly ties loan-out-company payments to 'the current annual rate,' citing O.C.G.A. section 48-7-40.26 and Regulation 560-7-8-45 -- the entry still discloses honestly that the rate table and the explicit loan-out sentence live on two different DOR pages, not one, rather than overstating a single-sentence tie."
  - "Two NJEDA screenshot PNGs from plan 01-04 (archived but never given a manifest row, since the .txt accessibility-tree extracts were the cited digit source) were given manifest rows in this plan, once tests/test_source_truth.py's reverse-direction reconciliation check surfaced them as unindexed archived files -- fixed as an in-scope blocking issue (Rule 3) rather than deferred."

requirements-completed: [SRC-01, SRC-02, SRC-04, SRC-05]

coverage:
  - id: D1
    description: "SRC-01 entry: the New York $700M/$800M cap conflict closed against the enacted budget bill (S3009-C/A3009-C, Chapter 59 of the Laws of 2025) -- base program $700M/yr through 2036, separate new $100M/yr Independent Film Production Credit ($20M/$80M pool split), the AUP document's $800M figure explained as the combined total. Five primary documents archived and hashed (the enacted bill PDF, two ESD PDFs, two live esd.ny.gov page HTMLs)."
    requirement: "SRC-01"
    verification:
      - kind: unit
        ref: "tests/test_source_truth.py::test_every_entry_has_provenance[SRC-01]"
        status: pass
      - kind: unit
        ref: "tests/test_source_truth.py::test_manifest_hashes_match_files_on_disk"
        status: pass
    human_judgment: true
    rationale: "Whether the enacted-bill evidence genuinely closes the conflict (versus still warranting a D-13 unresolved-conflict record) is exactly the kind of judgment 01-VALIDATION.md reserves for document review, not a runtime assertion -- a human should read the SRC-01 entry's reasoning (the tracked-changes bracket argument, the Cloudflare-blocked access-method disclosure) and agree the closure is earned, not asserted."
  - id: D2
    description: "SRC-02 entry: Connecticut's seven CSV column headers recorded verbatim in published order, all six data-quality artifacts independently re-verified against the already-archived bytes (including a correction to 01-RESEARCH.md's Municipality-blank date claim, 2009-07-21 not 2007)."
    requirement: "SRC-02"
    verification:
      - kind: unit
        ref: "tests/test_source_truth.py::test_every_entry_has_provenance[SRC-02]"
        status: pass
    human_judgment: true
    rationale: "The transcription-integrity claim underneath this entry -- that all six artifacts, including the corrected WWE-row date, were actually re-read from the archived CSV this session -- is the same category of honesty claim 01-04-SUMMARY.md flagged for its own fixtures; a human should spot-check at least one artifact against the archived file."
  - id: D3
    description: "SRC-05 entry: the full five-tier Georgia withholding schedule (4.99% down to 5.75%) recorded as exact decimal strings with date bands, plus the second DOR page ('Instructions for Production Companies') fetched and quoted, raising the loan-out-specificity confidence from MEDIUM to HIGH with the residual two-page-tie caveat disclosed rather than smoothed over."
    requirement: "SRC-05"
    verification:
      - kind: unit
        ref: "tests/test_source_truth.py::test_every_entry_has_provenance[SRC-05]"
        status: pass
    human_judgment: true
    rationale: "The confidence-tier promotion from MEDIUM to HIGH is a judgment call about how directly the two-page evidence chain ties the rate table to loan-out withholding specifically -- PRHV-07/D-13's sibling prohibition (SRC-05's own listed prohibition) requires this not be overstated, and a human should confirm the entry's own honest caveat (two pages, not one sentence) reads as calibrated rather than promotional."
  - id: D4
    description: "SRC-04 entry: Parallel recorded as the owner-confirmed partner track, sourced plainly to the owner's direct confirmation rather than an invented URL citation, with a Re-verification log subsection establishing the append-only contract for Phase 8's submission-portal re-check."
    requirement: "SRC-04"
    verification:
      - kind: unit
        ref: "tests/test_source_truth.py::test_every_entry_has_provenance[SRC-04]"
        status: pass
      - kind: unit
        ref: "tests/test_source_truth.py::test_src04_has_reverification_log"
        status: pass
    human_judgment: false
  - id: D5
    description: "tests/test_source_truth.py: three groups of structural assertions (entry shape, bidirectional manifest/disk hash reconciliation, fixture-to-manifest cross-reference), proven non-vacuous by deliberately mutating an archived document, observing the expected hash-mismatch failure, and restoring the file."
    requirement: null
    verification:
      - kind: unit
        ref: "uv run pytest tests/test_source_truth.py -q (10 passed)"
        status: pass
      - kind: other
        ref: "manual: appended one byte to sources/ga/2026-08-24-dor-film-tax-credit-resources.html, ran the suite, observed test_manifest_hashes_match_files_on_disk fail with the exact expected sha256-mismatch message, restored the file from a pre-mutation backup, confirmed byte-identical via git diff --stat (no output) and a re-hash match, re-ran the full suite green"
        status: pass
    human_judgment: false

duration: 46min
completed: 2026-08-24
status: complete
---

# Phase 01 Plan 05: Source Truth — NY Cap Closure, CT Schema, GA Schedule, Partner Track Summary

**The New York $700M/$800M cap conflict closed against the enacted FY2026 budget bill's own tracked-changes text (not left as a press-corroborated guess), with `.planning/SOURCE-TRUTH.md` recording all four Phase 1 source-verification answers and `tests/test_source_truth.py` proving the archive/manifest/fixture chain agrees — proven non-vacuous by an observed mutated-file failure.**

## Performance

- **Duration:** ~46 min
- **Started:** 2026-08-24T22:57:00-07:00 (first NY PDF fetch)
- **Completed:** 2026-08-24T23:36:39-07:00 (Task 3 commit)
- **Tasks:** 3
- **Files modified:** 11 (9 newly archived documents + 1 manifest + 1 test module; `.planning/SOURCE-TRUTH.md` created)

## Accomplishments

- **Closed the New York cap conflict against the actual enacted budget bill**, not a codified-law summary page. `www.nysenate.gov` returned a Cloudflare bot-verification challenge to every fetch attempt this session (both direct `curl` and a headless browser); the enacted bill text was instead fetched from `legislation.nysenate.gov`'s own PDF-serving endpoint, confirmed via its Actions log as signed into law on 2025-05-09 as Chapter 59 of the Laws of 2025. Its tracked-changes bracket notation shows the base program's $700M dollar figure **unbracketed** (unchanged) — only the 2034-to-2036 sunset year is bracketed as amended — and a brand-new Tax Law section 24-d (also in this same bill) creates the $100M/yr Empire State Independent Film Production Credit ($20M/$80M pool split). $700M + $100M = $800M, which is exactly the May 2026 AUP document's anomalous figure — closing the question as an internal drafting imprecision, not a further legislative change.
- Archived and hashed five NY documents this closure rests on: the enacted bill PDF, both prior ESD PDFs (Guidelines, AUP), and two live esd.ny.gov page HTMLs fetched by direct `curl` (raw bytes, not the LLM-summarized WebFetch 01-RESEARCH.md relied on).
- **SRC-02**: re-verified all seven Connecticut CSV column headers and all six data-quality artifacts directly against the already-archived file (not re-fetched, per plan instruction) — and in doing so, **corrected 01-RESEARCH.md's own prose**: the blank-`Municipality` rows are dated 2009-07-21, not "2007" as previously written (the file's actual earliest row, 2007-08-10, has `Municipality` filled).
- **SRC-05**: recorded the full five-tier Georgia withholding schedule as exact decimal strings, then fetched the second DOR page 01-RESEARCH.md recommended opening ("Instructions for Production Companies") and found the explicit sentence tying loan-out-company payments to "the current annual rate," citing O.C.G.A. § 48-7-40.26 and Regulation 560-7-8-45 — raising the loan-out-specificity confidence from MEDIUM to HIGH, with the entry's own honest caveat that the rate table and the explicit sentence live on two different pages, not one.
- **SRC-04**: recorded Parallel as the owner-confirmed partner track, sourced plainly to the owner's direct confirmation rather than an invented citation, with a `Re-verification log` subsection establishing that Phase 8's submission-portal re-check appends a new dated line rather than replacing the original.
- `tests/test_source_truth.py`: entry-shape assertions (question/answer/date_checked/confidence tier/refutation section per requirement), bidirectional manifest-disk hash reconciliation, and fixture-to-manifest cross-reference — proven non-vacuous by deliberately mutating an archived file, watching the reconciliation test fail with the exact expected message, and restoring it.
- Full repo suite (`uv run pytest tests/ -q`) is green: **35 passed** (up from 25 at the start of this plan).

## Task Commits

Each task was committed atomically:

1. **Task 1: SRC-01 — run the New York cap conflict down against the enacted budget bill** — `9020a63` (feat)
2. **Task 2: SRC-02 and SRC-05 — Connecticut CSV schema and the Georgia withholding schedule** — `5cebcd1` (feat)
3. **Task 3: SRC-04 entry, the SOURCE-TRUTH shape test, and manifest reconciliation** — `8efdba2` (feat)

**Plan metadata:** committed after this SUMMARY (see below)

## Files Created/Modified

- `.planning/SOURCE-TRUTH.md` - The four-entry answer record (SRC-01, SRC-02, SRC-04, SRC-05), each with question/answer/URL(s)/date_checked/confidence/refutation section
- `tests/test_source_truth.py` - Entry-shape, manifest-reconciliation (both directions), and fixture-cross-reference assertions
- `sources/ny/2026-08-24-ny-enacted-budget-film-credit-extract.pdf` - S3009-C/A3009-C official Senate PDF (511,767 bytes), signed Chapter 59 of the Laws of 2025
- `sources/ny/2026-08-24-esd-film-credit-guidelines.pdf` - 2025-04-18 ESD Guidelines PDF (1,147,218 bytes)
- `sources/ny/2026-08-24-esd-film-prod-cpa-aup.pdf` - May 2026 ESD AUP PDF (907,872 bytes) — the anomalous $800M document
- `sources/ny/2026-08-24-esd-live-film-production-page.html` - Live esd.ny.gov Film Production page, raw `curl` fetch
- `sources/ny/2026-08-24-esd-independent-film-production-page.html` - Live esd.ny.gov Independent Film Production page, raw `curl` fetch
- `sources/ga/2026-08-24-dor-film-tax-credit-resources.html` - Georgia DOR Film Tax Credit Resources page (rate table)
- `sources/ga/2026-08-24-dor-film-tax-credit-withholding-instructions.html` - Georgia DOR withholding-forms hub page
- `sources/ga/2026-08-24-dor-instructions-for-production-companies.html` - Georgia DOR page with the explicit loan-out-withholding sentence
- `sources/MANIFEST.yaml` - Nine new document rows (5 NY, 3 GA, plus `cited_for` addition on the pre-existing CT row) and two new rows for the previously-uncited NJEDA screenshot PNGs from plan 01-04

## Decisions Made

- **SRC-01 recorded as CLOSED, not an unresolved conflict.** D-13 requires an explicit unresolved-conflict record only when the evidence genuinely does not close the question. The enacted bill's tracked-changes bracket notation is direct evidence the $700M dollar figure did not change (only the sunset year did) — not an argument from silence — so the closure is earned by the primary-source text itself, at the top of PITFALLS.md §D2's precedence ordering.
- **Accessed the enacted bill via `legislation.nysenate.gov` (the Senate's PDF-serving subdomain), not `www.nysenate.gov`**, after Cloudflare's bot-verification challenge blocked every attempt at the latter (both direct `curl` and a headless browser, confirmed stuck at "Performing security verification" even after extended waits). Two independent mirrors (Internet Archive Wayback Machine capture of the codified statute page, and `newyork.public.law`'s mirror stating "last accessed Aug. 22, 2026") were fetched as corroboration only — the entry's Method note discloses this access path explicitly rather than presenting it as if `www.nysenate.gov` had been reached directly.
- **Corrected 01-RESEARCH.md's SRC-02 date attribution.** Independently re-verifying the Municipality-blank artifact against the archived CSV bytes (not the research prose) found the blank rows dated 2009-07-21, not "2007." Recorded as a correction in the entry, following the project's own independent-transcription-discipline pattern established in 01-03/01-04.
- **Raised SRC-05's loan-out-specificity confidence from MEDIUM to HIGH** after finding an explicit primary-source sentence naming loan-out-company payments on the second Georgia DOR page 01-RESEARCH.md recommended opening — while still disclosing, rather than smoothing over, that the rate table and the explicit sentence sit on two different DOR pages.
- **Added manifest rows for two NJEDA screenshot PNGs (plan 01-04 artifacts)** once `tests/test_source_truth.py`'s reverse-direction reconciliation check (every archived file must have a manifest row) surfaced them as unindexed — a genuine pre-existing gap, fixed here under deviation Rule 3 (blocking) since it directly prevented the new test from passing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 1's own `<verify>` command was fragile against the file's necessary intro paragraph**
- **Found during:** Task 1, first `<verify>` run
- **Issue:** The plan's Task 1 `<verify>` command splits `SOURCE-TRUTH.md` on the literal substring `"SRC-01"` and then on `"SRC-0"` to isolate the entry body. The file's own introductory paragraph (explaining what the file contains) needed to mention the requirement IDs for readability, which broke the split — the first `"SRC-01"` match landed in the intro sentence, and the very next `"SRC-0"` match (from `"SRC-02"` in the same sentence) truncated the captured "entry" to a few characters, failing every assertion in the verify script.
- **Fix:** Rewrote the intro paragraph to describe the file's contents without repeating the literal requirement-ID codes, so the first `"SRC-01"` occurrence in the file is the actual `## SRC-01` heading.
- **Files modified:** `.planning/SOURCE-TRUTH.md`
- **Verification:** Re-ran the Task 1 `<verify>` command; it printed `SRC-01 entry shape ok`.
- **Committed in:** `9020a63`

**2. [Rule 3 - Blocking] Two NJEDA screenshot PNGs (plan 01-04) had no manifest row**
- **Found during:** Task 3, writing `test_every_archived_file_has_a_manifest_row`
- **Issue:** Plan 01-04 archived two corroborating screenshots (`.png`) alongside its accessibility-tree text extracts (`.txt`), explicitly noting in the manifest that the screenshots were "not separately sha256'd; the .txt is the cited source of the digits." That is correct for citation purposes, but it left two files under `sources/` with no manifest row at all — which the plan's own required reverse-direction reconciliation test ("every file under `sources/` other than `MANIFEST.yaml` has a manifest row") would fail against.
- **Fix:** Added manifest rows for both PNGs, hashed and dated to match their original archival session, with notes clarifying they remain corroborating evidence rather than the cited digit source (the `.txt` files retain that role).
- **Files modified:** `sources/MANIFEST.yaml`
- **Verification:** `test_every_archived_file_has_a_manifest_row` and the full `tests/test_source_truth.py` suite pass; the mutated-file non-vacuity proof (see below) confirms the reconciliation check is genuinely exercised, not vacuously green.
- **Committed in:** `8efdba2`

---

**Total deviations:** 2 (both auto-fixed — 1 verify-script fragility bug, 1 blocking manifest-completeness gap)
**Impact on plan:** Neither deviation touched a money value, a hash, or the substance of any entry's answer. Both were necessary for the plan's own literal `<verify>`/acceptance criteria to be satisfiable as written.

## Issues Encountered

- **`www.nysenate.gov` was Cloudflare-blocked for the entire session** (bot-verification challenge, confirmed stuck even after extended waits via both `curl` and a headless browser). Resolved by fetching the enacted bill directly from `legislation.nysenate.gov`'s PDF-serving subdomain instead — not a workaround of lower evidentiary value, since the bill text itself is more directly primary than the codified-law summary page that was originally targeted. Documented explicitly in the SRC-01 entry's Method note so a later reader understands exactly what was and wasn't directly accessed.

## Observed Non-Vacuity Proof (mutated-document hash check)

Appended one byte (`X`) to `sources/ga/2026-08-24-dor-film-tax-credit-resources.html` after backing it up:

```
$ echo -n "X" >> sources/ga/2026-08-24-dor-film-tax-credit-resources.html
$ uv run pytest tests/test_source_truth.py -q
...
FAILED tests/test_source_truth.py::test_manifest_hashes_match_files_on_disk
AssertionError: Manifest/disk hash mismatch(es):
sources/ga/2026-08-24-dor-film-tax-credit-resources.html: recorded sha256
fddc5cc771fffe854a0d4dec5cb1ba2b08c717b2b66e3b0090500d16d8d8a002 does not
match computed sha256
afd4a2326916bd53828a8be9a0b0d7a5f8fd4122f9868d176c0ed9c6f6d67f49
1 failed, 9 passed in 0.08s
```

Restored the file from the pre-mutation backup; `git diff --stat` on the file showed no output (byte-identical), and the re-computed sha256 matched the manifest's recorded value exactly (`fddc5cc7...`). Re-ran the full suite: `35 passed`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All four Phase 1 source-verification questions (SRC-01, SRC-02, SRC-04, SRC-05) now have written, sourced, dated, confidence-tiered answers in `.planning/SOURCE-TRUTH.md`. Phase 2's rule files can cite this record directly instead of re-deriving the reasoning.
- The New York cap figures Phase 2's `JurisdictionRuleSet` for NY needs are now unambiguous: $700,000,000/yr base program (2024-2036, $45,000,000/yr post-production earmark) and, separately, $100,000,000/yr Independent Film Production Credit ($20,000,000/yr sub-$10M pool + $80,000,000/yr pool) — never summed into a single reported cap.
- `tests/test_source_truth.py` is a standing structural guard: any future document substitution, missing manifest row, or unarchived fixture citation will fail the suite, not go unnoticed — and this has now been directly observed to work, not merely asserted to.
- SRC-04's `Re-verification log` establishes the append-only contract Phase 8 needs for its submission-portal re-check; no further Phase 1 work is implied.
- `sources/MANIFEST.yaml` is now fully self-consistent: every file under `sources/` (23 documents/screenshots) has exactly one manifest row, and every row's recorded sha256 matches the file on disk.
- No blockers for Phase 2.

---
*Phase: 01-foundations-source-truth-deploy-path*
*Completed: 2026-08-24*

## Self-Check: PASSED

All 10 key files (`.planning/SOURCE-TRUTH.md`, the test module, 9 archived documents) confirmed present on disk with `[ -f ]`. All three task commit hashes (`9020a63`, `5cebcd1`, `8efdba2`) confirmed present in `git log --oneline --all`. Full repo suite (`uv run pytest tests/ -q`) confirmed green: 35 passed. `sources/MANIFEST.yaml` reconciliation independently re-run and confirmed passing after the SUMMARY was drafted.
