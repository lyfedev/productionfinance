---
phase: 08-demo-proof-export-submission
plan: 01
subsystem: ui
tags: [fastapi, jinja2, proof-panel, provenance, taxonomy, sha256]

requires:
  - phase: 03-validation-route
    provides: "app/services/validate.py::selectable_pairs, VALIDATION_PAIRS_DIR, RD-03's gross-credit-only comparison discipline"
  - phase: 05-agent-taxonomy
    provides: "agent/taxonomy.py::AccuracySummary/MatchClass/classify(), agent/variance_rules.yaml's closed predicate set"
provides:
  - "GET /proof, GET /proof/{pair_id}, GET /proof/{pair_id}/document — the proof panel (UI-07/DMO-01)"
  - "app.services.proof.accuracy_over_validation_pairs() — a real, always-available AccuracySummary computed over every selectable validation pair (PRV-06)"
  - "app.services.proof.load_source_conflicts() + app/templates/_conflict.html::render_conflict — the unresolved-conflict surface (PRV-07)"
  - "data/source_conflicts.yaml — the committed (currently empty) conflict data source"
affects: ["08-02", "08-03", "any future phase that adds a genuinely unresolved source conflict"]

actuals:
  tokens: 14700
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Gross-credit-only reproduction for a proof surface (bypassing engine.net_cash.convert_to_net_cash) — the correct like-for-like comparison against a disclosed CREDIT figure, reusing engine.qualifying_base.compute_qualifying_base + engine.credit.compute_gross_credit directly rather than engine.pipeline.price_jurisdiction's full (net-cash-inclusive) pipeline."
    - "Live sha256 computed from the file on disk at request time, cross-checked against both the fixture's recorded value and sources/MANIFEST.yaml — never trusting a recorded hash blindly."
    - "A committed, currently-empty YAML data file (data/source_conflicts.yaml) as the single source of truth for an honesty surface that must never be populated to demonstrate itself."

key-files:
  created:
    - app/services/proof.py
    - app/routers/proof.py
    - app/templates/proof.html
    - app/templates/_conflict.html
    - app/static/proof.css
    - data/source_conflicts.yaml
    - tests/test_app_proof_panel.py
    - tests/test_source_conflict.py
  modified:
    - app/main.py
    - app/templates/index.html

key-decisions:
  - "The proof panel compares the disclosed figure against a GROSS credit computed directly via compute_qualifying_base + compute_gross_credit, not through price_jurisdiction (which also unconditionally converts to net cash and therefore refuses on New Jersey/Connecticut's undeclared transfer_discount range). This reaches a real computed number for every selectable pair, including the two jurisdictions /validate reports as 'cannot be computed' — a different, unrelated question (net cash after a broker's discount) that the proof panel never asks."
  - "PRV-06's accuracy figure is computed by actually running agent.taxonomy.classify() over every selectable validation pair against the real agent/variance_rules.yaml rule set — not by replaying a live agent.job1.run_job1() extraction (no runs/job1/ evidence is committed; Parallel/Gemini credentials are not installed on this host per D-101). This is a distinct, always-available, 100% real measurement, honestly labelled as such on the page."
  - "Under this measurement the real bucket counts are 5 exact_match / 0 explained_variance / 5 unexplained (out of 10 selectable pairs) — including nj_joker, whose $122,665 residue IS fully explained in prose (the fixture's own assertion.variance_reason) but is NOT covered by either of the two named predicates in agent/variance_rules.yaml (both are NY-specific: a diversity-credit dollar column, an alternate-programme-label check). The page states this honestly rather than silently upgrading it to a match."
  - "data/source_conflicts.yaml is a new, committed, currently-empty data file — necessary because no schema existed to record a real conflict; both candidate conflicts this project has investigated (NY $700M/$800M, GA loan-out withholding) were already closed against a primary source, so the file stays empty rather than being seeded with a manufactured entry."

requirements-completed: [UI-07, PRV-06, PRV-07, DMO-01]

coverage:
  - id: D1
    description: "The proof panel shows a reproduced government award figure alongside the byte-archived government document itself (not a citation), with a live-computed sha256 (UI-07, DMO-01)."
    requirement: "UI-07"
    verification:
      - kind: integration
        ref: "tests/test_app_proof_panel.py#test_proof_document_route_serves_exact_bytes_matching_recorded_sha256"
        status: pass
      - kind: integration
        ref: "tests/test_app_proof_panel.py#test_proof_page_shows_the_recorded_and_live_sha256_and_they_match"
        status: pass
      - kind: integration
        ref: "tests/test_app_proof_panel.py#test_proof_page_shows_the_archived_document_path_not_only_a_live_link"
        status: pass
    human_judgment: false
  - id: D2
    description: "The exact Decimal residue renders — zero for an exact-match pair (ny_anora), and the exact $122,665 sourced residue for nj_joker, with its explanation."
    requirement: "DMO-01"
    verification:
      - kind: integration
        ref: "tests/test_app_proof_panel.py#test_proof_detail_exact_match_pair_renders_zero_residue"
        status: pass
      - kind: integration
        ref: "tests/test_app_proof_panel.py#test_proof_detail_nj_joker_renders_the_exact_sourced_residue"
        status: pass
    human_judgment: false
  - id: D3
    description: "The accuracy figure is rendered as three bucket counts (exact match / explained variance / unexplained), never a blended percentage; AccuracySummary itself carries no percentage field."
    requirement: "PRV-06"
    verification:
      - kind: integration
        ref: "tests/test_app_proof_panel.py#test_proof_index_renders_the_three_bucket_counts_and_no_percent_sign"
        status: pass
      - kind: unit
        ref: "tests/test_app_proof_panel.py#test_accuracy_summary_never_carries_a_percentage_field"
        status: pass
      - kind: unit
        ref: "tests/test_agent_taxonomy.py#test_accuracy_summary_exposes_no_percentage_mean_or_blended_field"
        status: pass
    human_judgment: false
  - id: D4
    description: "A disagreement between two authoritative sources is surfaced as unresolved (both sources, both citations, no winner); the surface renders empty for the real committed data because no genuine unresolved conflict currently exists, and is proven correct via a real conflict fixture (PRV-07)."
    requirement: "PRV-07"
    verification:
      - kind: unit
        ref: "tests/test_source_conflict.py#test_the_real_committed_source_conflicts_file_is_empty"
        status: pass
      - kind: unit
        ref: "tests/test_source_conflict.py#test_render_conflict_never_declares_a_winner_or_an_average"
        status: pass
      - kind: integration
        ref: "tests/test_app_proof_panel.py#test_no_conflict_is_manufactured_for_the_real_committed_data"
        status: pass
      - kind: integration
        ref: "tests/test_app_proof_panel.py#test_conflict_renders_correctly_when_given_a_real_conflict_fixture"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-09
status: complete
---

# Phase 8 Plan 1: The Proof Panel, the Accuracy Figure, and Unresolved Conflicts Summary

**A proof panel that serves the byte-archived government document (with a live-computed sha256) beside the exact Decimal residue, a real bucket-count accuracy figure computed by running `agent.taxonomy.classify()` over every validation pair, and an unresolved-conflict surface that is empty because no fabricated conflict was ever added to it.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-09-09T07:28:00-07:00
- **Completed:** 2026-09-09T07:44:17-07:00
- **Tasks:** 3
- **Files modified:** 10 (8 created, 2 modified)

## Accomplishments

- `GET /proof`, `GET /proof/{pair_id}`, `GET /proof/{pair_id}/document` — the disclosed government figure and this engine's gross-credit reproduction shown side by side, the exact Decimal residue (zero for `ny_anora`, exactly `122665` for `nj_joker`), and the archived `sources/` document served directly with a live-recomputed sha256 cross-checked against both the fixture's recorded value and `sources/MANIFEST.yaml`.
- `accuracy_over_validation_pairs()` — a real `AccuracySummary` (5 exact match / 0 explained variance / 5 unexplained / 0 could-not-be-computed, out of 10 selectable pairs today) computed by running every selectable validation pair through `agent.taxonomy.classify()` against the committed `agent/variance_rules.yaml` rule set. Rendered on `/proof` as three labeled counts — no percentage anywhere on the page.
- `load_source_conflicts()` + `_conflict.html::render_conflict` — the unresolved-conflict surface. `data/source_conflicts.yaml` is committed empty (both candidate conflicts this project investigated were closed against a primary source), so the real page renders nothing; a test-supplied fixture proves the render path shows both sources with equal weight and states the disagreement is unresolved.

## Task Commits

1. **Task 1: the proof panel (UI-07, DMO-01)** — `cd56019` (feat) — `app/services/proof.py`, `app/routers/proof.py`, `app/templates/proof.html`, `app/static/proof.css`, `app/main.py`, `app/templates/index.html`
2. **Task 3: unresolved source conflicts (PRV-07)** — `696859b` (feat) — `app/templates/_conflict.html`, `data/source_conflicts.yaml`
3. **Tests (Tasks 1–3, PRV-06 included via `app/services/proof.py`'s already-committed `accuracy_over_validation_pairs`)** — `8fd4ebd` (test) — `tests/test_app_proof_panel.py`, `tests/test_source_conflict.py`

_Note: Task 2 (the accuracy figure, PRV-06) added no new files of its own — `accuracy_over_validation_pairs()` lives inside `app/services/proof.py` (committed in Task 1's commit) and its rendering lives inside the already-committed `app/templates/proof.html`; the third commit above is where its test coverage lands. This reflects the plan's own `files_modified` list, which assigns Task 2 no exclusive files._

**Plan metadata:** (this commit)

## Files Created/Modified

- `app/services/proof.py` — `build_proof()` (Task 1), `accuracy_over_validation_pairs()` (Task 2), `load_source_conflicts()` (Task 3), and the `ArchivedDocument`/`ProofResult`/`ConflictSource`/`SourceConflict` dataclasses.
- `app/routers/proof.py` — `GET /proof`, `GET /proof/{pair_id}`, `GET /proof/{pair_id}/document`.
- `app/templates/proof.html` — the single template serving the pair list, the accuracy summary, the conflict surface, and the per-pair detail (D-43's one-view-shared-across-routes pattern).
- `app/templates/_conflict.html` — the `render_conflict()` macro.
- `app/static/proof.css` — own stylesheet (a sibling plan owns `prodfin.css` this wave).
- `data/source_conflicts.yaml` — the committed conflict data source, empty, with a fully documented schema and the reasoning for why it stays empty.
- `app/main.py` — registered the proof router (2-line diff).
- `app/templates/index.html` — added a "Proof panel" link.
- `tests/test_app_proof_panel.py`, `tests/test_source_conflict.py` — 28 tests total.

## Decisions Made

See `key-decisions` in the frontmatter above — all four are substantive interpretation calls made where the plan's own worked example (`nj_joker`'s `$122,665` residue) turned out to be unreachable through `app/services/validate.py::reproduce_disclosure`'s existing `price_jurisdiction` pipeline (New Jersey's `transferable` mechanism refuses on an undeclared `transfer_discount` range — a NET CASH question, orthogonal to the GROSS credit a disclosure actually reports). Verified directly against the real ruleset before writing any code: `compute_qualifying_base` + `compute_gross_credit` alone reproduce New Jersey's Joker row to `$1,839,977`, exactly matching the plan's own stated residue of `$122,665`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `data/source_conflicts.yaml` as the committed data source for PRV-07**
- **Found during:** Task 3
- **Issue:** The plan names `app/templates/_conflict.html` as the render surface but does not name a data source. Without one, there is no way for a future session to ever record a real conflict — the capability would exist but have nowhere to persist real data.
- **Fix:** Added `data/source_conflicts.yaml`, committed empty, with a documented schema (`app/services/proof.py::ConflictSource`/`SourceConflict`) and an explanation of why it is empty today (both candidate conflicts already closed against a primary source).
- **Files modified:** `data/source_conflicts.yaml`, `app/services/proof.py`
- **Verification:** `tests/test_source_conflict.py::test_the_real_committed_source_conflicts_file_is_empty` and the loader/render tests in the same module.
- **Committed in:** `696859b`

**2. [Rule 2 - Missing Critical] Added a "Proof panel" link to `app/templates/index.html`**
- **Found during:** Task 1
- **Issue:** Without a link from the landing page, the proof panel would be unreachable by a cold anonymous visitor navigating the site — undermining DMO-01's "open on validation" demo beat and the SHIP GATE's discoverability requirement.
- **Fix:** Added a two-paragraph section linking to `/proof`, in the same style as the existing route links on that page.
- **Files modified:** `app/templates/index.html`
- **Verification:** `tests/test_app_proof_panel.py::test_landing_page_links_to_the_proof_panel`
- **Committed in:** `cd56019`

**3. [Rule 1 - Bug, caught before landing] Reverted an unrelated `ruff --fix` change to `app/main.py`'s pre-existing `datetime.now(timezone.utc)` call**
- **Found during:** Task 1 (registering the proof router)
- **Issue:** Running `ruff check --fix` across the touched files auto-applied an unrelated `UP017` fix (`timezone.utc` → `datetime.UTC`) to `_resolve_git_sha`'s neighboring code — code this plan does not own and a sibling plan may also be touching concurrently (isolation is `none`, same working tree).
- **Fix:** Manually reverted that hunk before committing, keeping the diff scoped to the router registration only (2 lines).
- **Files modified:** `app/main.py` (reverted, not applied)
- **Verification:** `git diff app/main.py` shows only the intended 2-line addition; confirmed the pre-existing `S110`/`BLE001` findings in the same function predate this plan (`git stash` + `ruff check` against the base tree shows the identical findings).
- **Committed in:** `cd56019`

---

**Total deviations:** 3 (2 auto-added missing functionality, 1 scope-boundary correction). **Impact:** All three were necessary for correctness/discoverability or for staying strictly within this plan's file ownership; no unrelated code was changed.

## Known Stubs

None — every figure, hash, and count on the proof panel is computed live from committed data; nothing is hardcoded or simulated.

## Threat Flags

None — `GET /proof/{pair_id}/document` resolves `pair_id` through the same closed-selectable-set membership check `reproduce_disclosure` already uses (T-03-01/T-05-12) before any filesystem path is built, and the served path is always derived from a fixture's own already-validated `source_document` field, never from request input directly.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Ready for 08-02 and 08-03.
- `agent/variance_rules.yaml` currently names only two NY-specific predicates; a future session adding a New Jersey diversity-bonus predicate (matching `nj_joker`'s already-proven residue) would move that pair from `unexplained` to `explained_variance` in the honest accuracy count — noted here as a real, well-understood opportunity, not a blocker.
- `data/source_conflicts.yaml` is ready to receive a real entry the moment a genuinely unresolved conflict is found in a future research session; the schema and render path are already proven correct.

---
*Phase: 08-demo-proof-export-submission*
*Completed: 2026-09-09*

## Self-Check: PASSED

All created files confirmed present on disk (`app/services/proof.py`, `app/routers/proof.py`, `app/templates/proof.html`, `app/templates/_conflict.html`, `app/static/proof.css`, `data/source_conflicts.yaml`, `tests/test_app_proof_panel.py`, `tests/test_source_conflict.py`). All three task commits confirmed present in `git log` (`cd56019`, `696859b`, `8fd4ebd`). Full suite: 857/857 passing. Golden regression (`tests/test_golden_cost.py`, `tests/test_route_a_basis_walk.py`): 9/9 passing, unedited. `vendor-scan.sh`, `lockfile-scan.sh`, `scripts/audit_sdk_call_sites.py --check`: all PASS.
