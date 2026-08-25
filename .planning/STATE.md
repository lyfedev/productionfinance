---
gsd_state_version: 1.0
current_phase: 02
current_phase_name: Engine Spine & Incentive Interpreter
status: executing
stopped_at: Completed 02-09-PLAN.md
last_updated: "2026-08-25T19:02:03.943Z"
last_activity: 2026-08-25
last_activity_desc: Phase 02 execution started
state_head: 8b343e02d0ae99ecd895f4328d84c6a202a04958
progress:
  total_phases: 11
  completed_phases: 1
  total_plans: 18
  completed_plans: 17
  percent: 9
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-24)

**Core value:** Total landed cost of one identical production, priced per city, with every figure sourced, dated, and provably matching what a government actually paid.
**Current focus:** Phase 02 — Engine Spine & Incentive Interpreter

## Current Position

Phase: 02 (Engine Spine & Incentive Interpreter) — EXECUTING
Plan: 4 of 9
Status: Ready to execute
Last activity: 2026-08-25 — Phase 02 execution started

Progress: [█░░░░░░░░░] 9%

**Deadline: 2026-09-09 14:00 PDT — 15 days.** Milestone 1 (Accounts, Phases 1-8) is the submission. Milestone 2 (Balances, Phases 9-11) is cuttable as a whole.

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
| Phase 01 P05 | 46min | 3 tasks | 11 files |
| Phase 01 P08 | 19min | 3 tasks | 5 files |
| Phase 01 P09 | 16min | 1 tasks | 3 files |
| Phase 02 P01 | 44min | 2 tasks | 15 files |
| Phase 02 P02 | 12min | 2 tasks | 3 files |
| Phase 02 P03 | 11min | 2 tasks | 5 files |
| Phase 02 P05 | 55min | 3 tasks | 9 files |
| Phase 02 P04 | 18min | 2 tasks | 3 files |
| Phase 02 P06 | 50min | 3 tasks | 7 files |
| Phase 02 P07 | 51min | 2 tasks | 4 files |
| Phase 02 P08 | 22min | 2 tasks | 3 files |
| Phase 02 P09 | 32min | 2 tasks | 3 files |

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
- [Phase 01]: SRC-01 closed against the enacted budget bill (S3009-C, Chapter 59 of Laws of 2025): NY base film credit stays $700M/yr through 2036; new $100M/yr Independent Film Production Credit (Tax Law 24-d) explains the AUP document's $800M as a combined total, not a base-cap change.
- [Phase 01]: www.nysenate.gov was Cloudflare-blocked all session; enacted bill text was fetched via legislation.nysenate.gov's PDF endpoint instead, with Wayback Machine and newyork.public.law used only as corroboration (documented explicitly in SOURCE-TRUTH.md).
- [Phase 01]: SRC-05 loan-out-withholding confidence raised from MEDIUM to HIGH after finding an explicit primary-source sentence tying loan-out payments to Georgia's current withholding rate, citing O.C.G.A. 48-7-40.26.
- [Phase 01]: [Phase 01] 01-08: 01-07 resize deferral holds -- Task 1/3 ran entirely on the original un-resized nano_2_0 (472MB) box. Measured 353MB available immediately after uv python install 3.12, 284MB available with prodfin.service running post-reboot (buff/cache still cold). Comfortable headroom for the bare FastAPI skeleton; not yet evidence either way for Milestone 2's data-layer decision since no AI-SDK or DB has been imported yet.
- [Phase 01]: [Phase 01] 01-08: pushed 17 previously-unpushed local commits (plans 01-03 through 01-07) to origin/main for the first time, a Rule-3 blocking-issue fix -- D-19's git-pull deploy path is meaningless against a stale remote. Push tripped secret-scan (SHP-10) on a genuine gitleaks grafana-api-key false positive against a public NJEDA Power BI Government citation URL (shared base64 {"k":...} envelope by coincidence, not a credential); fixed with a single scoped .gitleaks.toml literal-string allowlist entry, re-verified green on every subsequent push.
- [Phase 01]: [Phase 01] 01-08: prodfin.service (systemd) deployed on 127.0.0.1:8000 as the dedicated non-login prodfin user, deploy/deploy.sh proven idempotent (two consecutive runs), and a real sudo reboot executed and recovered unaided -- prodfin.service's own boot_time (06:59:44Z) later than the host's post-reboot uptime -s (06:59:38Z), the evidence distinguishing survived-a-reboot from restarted-after-one per D-23/SHP-04. vockell.com's pre-existing 301-to-www redirect (unrelated to this plan) is documented in deploy/README.md so it isn't mistaken for a regression.
- [Phase 01]: 01-09 executed a revised plan: ProxyPass /finance added inline to the EXISTING vockell.com Apache vhost, reusing its existing Let's Encrypt certificate -- not the dedicated subdomain vhost + new bncert-tool certificate 01-09-PLAN.md was originally written for (superseded by D-14's path-mount decision, 01-06). No AWS resource (snapshot/resize) was touched; a file-level backup + configtest + graceful reload substituted. Two live Apache bugs found and fixed during verification (a www-redirect swallowing /finance; a doubled-slash ProxyPass target) plus one app-code bug (an absolute-path link breaking under the /finance mount, fixed via PRODFIN_PUBLIC_PATH). https://vockell.com/finance is now confirmed reachable by an anonymous off-box visitor over valid TLS; vockell.com's pre-existing behaviour on every other path is unchanged.
- [Phase 02]: Phase 02 plan 01: engine spine tracer reproduces New York's Anora credit exactly ($991,190); RD-01..RD-05 schema deviations recorded in jurisdictions/SCOPE-FREEZE.md; Succession S4 fixture corrected exact->bounded (10bps) after measuring a 1.73bps residue, not silently reconciled.
- [Phase 02]: Phase 02 plan 02: property-tested PRV-01/02/03 and the pinned-rounding/Decimal-precision/fail-loud-schema contracts against a real Anora-priced Figure tree -- zero engine/ production code changes needed, both plan-anticipated escape hatches went unused, both non-vacuity checks (deleted rounding= arg, removed no-op derivation line) performed and reverted.
- [Phase 02]: Phase 02 plan 03: all four base-definition types plus the closed HANDLER_REGISTRY escape hatch widened from 02-01's tracer; excluded_line_items and the minimum-spend cliff apply uniformly across every type; lesser-of's 'actual local' candidate is core_expenditure itself under the D-02 no-localisation boundary. — Widens engine/qualifying_base.py per plan 02-03 without restructuring the schema plan 02-01 landed
- [Phase 02]: Phase 02 plan 05: per-person ceiling reduces the qualifying base before the rate (W-2 excess over cap; loan-out exempt qualifies in full plus a separate, never-netted withholding-obligation Figure selected from a dated schedule); tiered_by_spend (cliff lookup) and blended_by_ceiling_split (split-then-cap-each-slice) landed as two distinct engine/credit.py functions, reproducing Christmas Always ($1,159,502) and the UK worked example ($7,176,000) exactly, each proven not to produce the plausible wrong figure (984502 / 7632000). Connecticut's mechanism (transferable), minimum spend ($100,000) and mandatory audit are sourced from CT General Statutes Sec. 12-217jj, fetched and archived this session -- also independently corroborating the CSV-derived tier bands.
- [Phase 02]: Phase 02 plan 04: all four net-cash mechanisms (refundable, transferable, rebate_grant, nonrefundable_credit) landed in engine/net_cash.py, sharing a half-open cliff-tiered audit fee lookup that mirrors engine/credit.py's rate-band shape; the UK worked example closes on Decimal('5382000') net cash from Decimal('7176000') gross at 25% corporation tax, putting DMO-02's 44% naive-arithmetic-overstatement claim under test rather than only in a slide. transferable reports a low/high bound with point=None, never a fabricated midpoint. ArrivalTiming now computes an estimated date from a declared payout_lag.typical_days; an unsourced lag still reports a null date with a stated reason.
- [Phase 02]: Phase 02 plan 06: national+regional stacking sums independent dollar Figures across N declared programmes (never rates); mutual exclusivity resolved before summation, taken and untaken figures both recorded; per-project cap clips at a strictly-greater-than boundary while the annual cap never touches the credit (RD-04); eligibility and availability land as two genuinely independent answers, availability three-state and never defaulted to available. zz-fixture-throwaway.yaml prices correctly with a zero-line diff to engine/, proving JUR-05. Checkpoint decision: regional programmes live as additional entries in the parent jurisdiction's own file (programmes-in-one-file), recorded as RD-06 in SCOPE-FREEZE.md.
- [Phase 02]: Phase 02 plan 07: closed CR-01 by carrying the minimum-spend, excluded-line-items and per-person-ceiling reductions onto core expenditure before slicing in blended_by_ceiling_split, via an always-attached EXCLUDED_LINE_ITEMS_TOTAL_LABEL marker Figure; a zero-or-below running base now short-circuits to Decimal('0') before any slice is rated. Anora, Christmas Always, the UK worked example and zz-fixture-throwaway all still reproduce byte-identically.
- [Phase 02]: engine/models.py: both stacks_with and mutually_exclusive_with edges validated in ONE model_validator on JurisdictionRuleSet (WR-02 substance: cannot drift apart), comparing ids via plain string equality with no normalization
- [Phase 02]: WR-04 fixed at the JurisdictionRuleSet schema boundary (Field min_length=1 on programmes); engine/figure.py::combined_confidence left untouched since its empty-sequence contract is correct for its primary use
- [Phase 02]: Phase 02 plan 09: WR-03 closed-closed dated-range convention recorded and guarded against overlapping withholding bands (both dated-dated and open-ended-dated). Validation-pairs golden test re-coupled to price_jurisdiction: New York's Anora reproduces Decimal('991190') end-to-end. Genuine discovered finding, documented not routed around: jurisdictions/us-ct.yaml's real transfer_discount has no sourced typical_rate_low/typical_rate_high, so price_jurisdiction raises for every active Connecticut pair; Christmas Always's direct-path exact reproduction (Decimal('1159502')) is unaffected. Recorded to WINDOWS.md as an unmet-truth entry.

### Pending Todos

None yet.

### Blockers/Concerns

- ~~**SRC-04 (partner track)**~~ — **RESOLVED 2026-08-24: Parallel.** Owner-confirmed. Parallel Search is a runtime requirement and is load-bearing in Phase 7. SHP-06 is unconditional. Re-verify against the submission portal at filing time.
- **SHP-01 resize takes vockell.com briefly offline.** Discrete, schedulable task inside Phase 1 Track B.
- **Free memory measured 2026-08-25, on the un-resized `nano_2_0` box (01-07 was deferred, not completed — see `01-07-DEFERRED.md`).** Immediately after `uv python install 3.12` + `uv venv` completed, before anything else was installed into the venv: `free -m` → total 472MB, used 106MB, free 18MB, buff/cache 347MB, **available 353MB**; swap 634MB total, 96MB used, 538MB free. `df -h /` → 14GB available of 20GB. Read: 353MB available is comfortable headroom for a SQLite file with no server process (near-zero RAM cost beyond page cache) and for the bare FastAPI skeleton (Task 2 will measure uvicorn's actual RSS once it's running). It is not comfortable headroom for a second server process (a dedicated Postgres/MySQL daemon) alongside the existing MariaDB — reusing the box's existing MySQL, if Milestone 2 needs a server-backed store, costs no new resident daemon. This reading favors SQLite-or-reuse-existing-MySQL over provisioning a new database server on this box; ROADMAP Phase 9 owns the actual decision. This measurement predates any AI-SDK import footprint (`google-genai`, `parallel-web`) — those loads happen in a later phase and are not yet reflected here.
- **AWS Textract is the single most likely accidental Stage One disqualification** — it is the obvious tool for exactly what Job 1 does. All extraction routes through Parallel Extract + Gemini.
- **`google-adk` bare install only** — never `[all]`, `[extensions]` or `[test]`; the extras pull disallowed AI vendor packages into the lockfile.
- 01-01: .env.example could not be created — global Claude Code permission policy denies Read/Write/Bash on any .env* path, including the placeholder-only .env.example template. Needs a human to create the 3-line file (PRODFIN_GIT_SHA=, PRODFIN_LOG_LEVEL=info, PRODFIN_APP_PORT=8000) or grant a scoped permission exception before plan 01-02 flips the repo public.
- ~~01-06: plan 01-09 (Apache proxy + TLS) was written for a dedicated subdomain vhost + new bncert-tool certificate. Under the D-14 path-mount decision it needs to become a ProxyPass /finance location inside the existing vockell.com vhost, reusing the existing certificate. 01-09 needs a revision pass before it executes.~~ — **RESOLVED 2026-08-25.** 01-09 executed under that revised scope: ProxyPass `/finance` inline in the existing vhost, existing certificate reused, no new DNS record, no certificate issued. See deploy/README.md "Apache path mount (plan 01-09, D-14 revision)".

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-08-25T19:02:03.883Z
Stopped at: Completed 02-09-PLAN.md
Resume file: None
