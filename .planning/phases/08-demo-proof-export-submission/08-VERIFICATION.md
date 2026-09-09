---
phase: 08-demo-proof-export-submission
status: gaps_found
verified_by: orchestrator (main thread, independent of the executing agents)
verified_at: 2026-09-09
plans: 3
summaries: 3
---

# Phase 8 Verification — Demo Proof, Export & Submission (SHIP GATE)

Verified against the codebase and the running app, not the plan summaries.

## Requirements

| ID | Verdict | Evidence |
|---|---|---|
| UI-07 | **PASS** | `GET /proof` → 200. Serves the byte-archived source document from `sources/` (not a redirect) with a sha256 computed from disk **at request time**, cross-checked against both the fixture's recorded hash and `sources/MANIFEST.yaml`. |
| DMO-01 | **PASS** | `ny_anora` reproduces exactly (residue `0`). `nj_joker` renders residue exactly `Decimal("122665")` with its sourced explanation — the 2% diversity bonus — shown verbatim rather than rounded away. |
| PRV-06 | **PASS** | The accuracy figure renders as bucket counts. A live check of the rendered `/proof` page finds **zero** percent-adjacent digits. `AccuracySummary` still carries no percentage field. |
| PRV-07 | **PASS** | `data/source_conflicts.yaml` is committed and legitimately empty — both candidate conflicts this project investigated were closed against primary sources. Tests prove the empty real state AND correct rendering given a real conflict fixture (two sources, equal weight, "unresolved", no winner/average language). No conflict was manufactured to demo the feature. |
| UI-09 | **PASS** | `GET /export` → 200 with **zero `<script>` tags** — genuinely complete without JavaScript. Carries the two-band ranked list, the decomposed gap or its stated refusal, every figure through the existing provenance component, and the full D-60 acknowledged-gaps list. |
| DMO-02 | **PASS** | Computed at request time from the committed `synthetic-uk-style.yaml` fixture: naive £9,540,000 vs net cash £5,382,000 → **43.6% overstatement**. A real measurement, not the brief's quoted 44%. Carries an explicit disclaimer that it is an illustrative arithmetic example, not a model of the UK programme. |
| DMO-03 | **PASS** | Both orderings rendered together across four curated jurisdictions on one shared spend. By headline rate NY is last (25%); by net cash NY is tied-second, because NJ and CT's transferable discount is unsourced and the engine refuses to convert. A genuine computed inversion. |
| DMO-04 | **PASS (renders honestly)** | With credentials absent it renders `integration_status().not_configured_message()` verbatim — "Not configured: PARALLEL_API_KEY, GEMINI_API_KEY (or GOOGLE_API_KEY)…" — the same text `/research` shows, with no spinner or progress markup. Both branches verified by monkeypatch, proving a real conditional rather than a permanent stub. **The live beat itself is unavailable** (see Gaps). |
| SHP-11 | **PASS (script only)** | `docs/DEMO-SCRIPT.md` — a 2:55 shot list with an explicit two-path fallback for the live-research beat depending on whether credentials exist at recording time. The video is a human deliverable. |
| SHP-12 | **PASS** | `docs/SUBMISSION.md` — technology claims checked against `uv.lock`, data-source claims naming manifest artifacts with sha256, findings freshly measured. Lists AGT-03/SHP-05/SHP-06 as **not met**. |
| SHP-13 | **PASS (handoff prepared)** | `.planning/SHIP-CHECKLIST.md` — 8 human-only actions, each stating why no agent can perform it. Verified **0 ticked, 8 unticked**. The cold cross-network check is the final item. |

## Decisions

| | Verdict |
|---|---|
| D-98 archived document, not a citation | **PASS** — served from `sources/` with a request-time sha256 |
| D-99 conflicts surfaced, never resolved | **PASS** — and never manufactured |
| D-100 bucket counts, never a blended percentage | **PASS** — zero percent-adjacent digits on the rendered page |
| D-101 DMO-04 never faked | **PASS** — real conditional, honest unavailable state |
| D-102 SHP-13 is a human handoff | **PASS** — nothing pre-ticked |
| D-103 re-run gates, do not cite them | **PASS** — `scripts/pre_submission_check.sh` re-runs 8 gates live, including SHP-14 non-vacuity by mutating New York's base rate and confirming the suite reddens on the correct test |

## Pre-submission gate, this run

7 of 8 PASS: lockfile-scan, vendor-scan, sdk-call-sites (D-96), pytest (942 passed), CLAUDE.md grep checklist, SHP-14 non-vacuity, SHP-08 licence (`mit`, queried live via `gh repo view`).

**1 FAIL: production log grep — `sdk=google-genai=0, sdk=parallel-web=0`.**

## Gaps

1. **AGT-03, SHP-05, SHP-06** — no live SDK call has ever fired. `PARALLEL_API_KEY` and `GEMINI_API_KEY` are absent locally and in `/opt/prodfin/.env` (verified by SSH this session; that file holds only deploy config). Human action, `SHIP-CHECKLIST.md` items 1/3/4.
2. **SHP-01** — the instance was never resized to 2 GB. It runs at 472 MB with ~309 MB available. CLAUDE.md forbids provisioning without per-resource approval.
3. **Nothing since `9af46b0` is deployed.** The box is **83 commits behind** HEAD; all of Phases 6, 7 and 8 is unshipped. Awaiting approval because the box also hosts vockell.com.
4. **The MapLibre map is visually unverified** — headless browsers lack WebGL2. Needs a human spot-check.

## Corrected during verification

`docs/SUBMISSION.md` described the sensitivity rate-window `ValueError` as an uncaught crash worked around by excluding a quarter from the slider. Both halves were fixed in `55a5fa5` before that document was written. Corrected in `8429558` — overstating a defect is as inaccurate as hiding one.

`docs/sdk-call-sites.md` was one endpoint stale after 08-02 added `/export`. Regenerated; still 4 call sites, 0 failing. Closed WINDOWS #35.
