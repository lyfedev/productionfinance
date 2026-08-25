---
gsd_state_version: 1.0
current_phase: 01
current_phase_name: Foundations — Source Truth & Deploy Path
status: executing
stopped_at: Completed 01-04-PLAN.md
last_updated: "2026-08-25T06:13:41.613Z"
last_activity: 2026-08-24
last_activity_desc: Phase 01 execution started
state_head: b9e908ef3f7373fb5c1a6c1acc83e08f3201077d
progress:
  total_phases: 11
  completed_phases: 0
  total_plans: 9
  completed_plans: 5
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-24)

**Core value:** Total landed cost of one identical production, priced per city, with every figure sourced, dated, and provably matching what a government actually paid.
**Current focus:** Phase 01 — Foundations — Source Truth & Deploy Path

## Current Position

Phase: 01 (Foundations — Source Truth & Deploy Path) — EXECUTING
Plan: 6 of 9
Status: Ready to execute
Last activity: 2026-08-24 — Phase 01 execution started

Progress: [░░░░░░░░░░] 0%

**Deadline: 2026-09-09 14:00 PDT — 16 days.** Milestone 1 (Accounts, Phases 1-8) is the submission. Milestone 2 (Balances, Phases 9-11) is cuttable as a whole.

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 21min | 2 tasks | 11 files |
| Phase 01 P06 | 12min | 2 tasks | 2 files |
| Phase 01 P02 | 4min | 3 tasks | 6 files |
| Phase 01 P03 | 8min | 2 tasks | 6 files |
| Phase 01 P04 | 33min | 3 tasks | 17 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Phase 1 merges source verification and the deploy path into one phase with two concurrent tracks — the deploy path has DNS/TLS clocks independent of build progress and must not queue behind research
- [Roadmap]: SHP-14 (CI validation suite) is mapped to Phase 3, not the submission phase — a suite written on the last day cannot have caught anything. It is re-proven non-vacuous in Phase 8.
- [Roadmap]: Cut order is written into ROADMAP.md. Connecticut is the first cuttable item in Accounts; Phase 11 (reverse mode) is the first cuttable item overall.
- [PROJECT]: Curated validated set is exactly NY, CA, NJ, CT — the only four jurisdictions with per-production government disclosure
- [PROJECT]: Co-host on the existing vockell.com Lightsail box, resized to 2 GB via snapshot-and-restore (preserves static IP); Apache reverse-proxies to systemd-supervised uvicorn on a subdomain
- [Phase 01]: uv resolved uvicorn 0.52.4 for the >=0.30 floor; recorded in 01-01-SUMMARY.md
- [Phase 01]: LICENSE copyright holder resolved via gh api user: Dave Vockell
- [Phase 01]: D-14 resolved: public URL is a path mount at https://vockell.com/finance, not a new subdomain (developer's word, not the CONTEXT.md placeholder prodfin.vockell.com) — Developer: "this is not critical path -- just put it at vockell.com/finance and not worry about devops." No new DNS record was needed or created; PRODFIN_HOST records the existing vockell.com apex plus a new PRODFIN_PUBLIC_PATH=/finance.
- [Phase 01]: 01-02 Task 1: publish-now selected — repo created private, CI green, then flipped public — Implements D-25; provenance demonstrable from day one; secret-scanning risk surfaced with time to fix
- [Phase 01]: productionfinance is public at github.com/lyfedev/productionfinance, MIT-licensed (Licensee-confirmed), push protection enabled, 4 CI gates required on main — SHP-07/08/09/10 all closed; plan 01-08 clones from this URL
- [Phase 01]: 01-03 Task 1: D-02 resolved interpreter-only — a validation pair proves the incentive interpreter only, never cost localization. Every NY fixture feeds qualified_spend in as a given and asserts only on credit_amount out; no fixture carries an input-vector field.
- [Phase 01]: 01-03 — three NY issued-stage validation pairs (Anora, Succession S4, The Gilded Age S2) independently transcribed from the archived ESD Q3 2025 PDF (sha256 824e2f32...). Gilded Age's 26.29% rate is assertion.mode: bounded (150bps) — an unlisted uplift the ESD table doesn't itemize; Anora and Succession S4 are the two D-05 exact-mode anchors. Third exact-mode fixture and all CT coverage deferred to plan 01-04.
- [Phase 01]: 01-04 -- CA/NJ pairs re-verified live (no discrepancy); NJ Trial of the Chicago 7 credit_amount corrected to $5,371,984 (archived primary source) vs $5,371,983 in prior secondary docs -- a $1 discrepancy recorded, not silently reconciled. Connecticut's first validation pair, "Christmas Always" ($3,865,005 -> $1,159,502, clean 30.0%), closes JUR-04's zero-coverage gap and supplies the D-05 third exact-mode anchor. Four MA/PA pairs committed status: blocked with a >40-char blocker naming both reasons (undisclosed spend; no curated rule file). Three new guard tests (jurisdiction coverage, pair count, per-stage denominator) make a jurisdiction gap, a shrinking pair count, or a blended accuracy figure each fail the suite.

### Pending Todos

None yet.

### Blockers/Concerns

- ~~**SRC-04 (partner track)**~~ — **RESOLVED 2026-08-24: Parallel.** Owner-confirmed. Parallel Search is a runtime requirement and is load-bearing in Phase 7. SHP-06 is unconditional. Re-verify against the submission portal at filing time.
- **SHP-01 resize takes vockell.com briefly offline.** Discrete, schedulable task inside Phase 1 Track B.
- **Post-resize free memory is unmeasured.** Measure immediately after the Python 3.10+ install; it gates the Milestone 2 data-layer decision (SQLite vs reusing the box's MySQL).
- **AWS Textract is the single most likely accidental Stage One disqualification** — it is the obvious tool for exactly what Job 1 does. All extraction routes through Parallel Extract + Gemini.
- **`google-adk` bare install only** — never `[all]`, `[extensions]` or `[test]`; the extras pull disallowed AI vendor packages into the lockfile.
- 01-01: .env.example could not be created — global Claude Code permission policy denies Read/Write/Bash on any .env* path, including the placeholder-only .env.example template. Needs a human to create the 3-line file (PRODFIN_GIT_SHA=, PRODFIN_LOG_LEVEL=info, PRODFIN_APP_PORT=8000) or grant a scoped permission exception before plan 01-02 flips the repo public.
- 01-06: plan 01-09 (Apache proxy + TLS) was written for a dedicated subdomain vhost + new bncert-tool certificate. Under the D-14 path-mount decision it needs to become a ProxyPass /finance location inside the existing vockell.com vhost, reusing the existing certificate. 01-09 needs a revision pass before it executes. See deploy/README.md "Downstream impact on plan 01-09".

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-08-25T06:13:41.603Z
Stopped at: Completed 01-04-PLAN.md
Resume file: None
