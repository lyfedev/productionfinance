---
gsd_state_version: 1.0
current_phase: 05
current_phase_name: Curated Breadth & the Validation Loop
status: executing
stopped_at: Completed 06-04-PLAN.md
last_updated: "2026-09-09T15:35:18.773Z"
last_activity: 2026-09-09
last_activity_desc: Phase 05 plan 01 executed — SHP-05/SHP-06 eligibility spine
state_head: 11e5dec7228e136489ff4084709c891f1f13d1b0
progress:
  total_phases: 11
  completed_phases: 3
  total_plans: 49
  completed_plans: 48
  percent: 27
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-24)

**Core value:** Total landed cost of one identical production, priced per city, with every figure sourced, dated, and provably matching what a government actually paid.
**Current focus:** Phase 05 — Curated Breadth & the Validation Loop

## Current Position

Phase: 05 (Curated Breadth & the Validation Loop) — EXECUTING
Plan: 3 of 3
Status: 05-01 complete (SHP-05/SHP-06 eligibility spine, tracer) — ready for 05-02
Last activity: 2026-09-09 — Phase 05 plan 01 executed

Progress: [███░░░░░░░] 27%

**Deadline: 2026-09-09 14:00 PDT — SAME DAY.** Milestone 1 (Accounts, Phases 1-8) is the submission. Milestone 2 (Balances, Phases 9-11) is cuttable as a whole.

**SHP-05 / SHP-06 status:** code is wired and mechanically tested (14 tests,
`tests/test_agent_eligibility.py`), but no live SDK call has been made — no
API key is present in this environment. **UNVERIFIED-IN-PRODUCTION** until a
human sets `PARALLEL_API_KEY` and `GEMINI_API_KEY`/`GOOGLE_API_KEY` per
`deploy/README.md`'s "Phase 5 — agent credentials" section and runs
`python -m agent.job1 --limit 1 --require-live` successfully once.

## Performance Metrics

**Velocity:**

- Total plans completed: 12
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 9 | - | - |
| 03 | 3 | - | - |

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
| Phase 03 P01 | 20min | 3 tasks | 13 files |
| Phase 03 P02 | 15min | 4 tasks | 11 files |
| Phase 03 P03 | 15min | 2 tasks | 3 files |
| Phase 04 P01 | 95min | 3 tasks | 23 files |
| Phase 04 P02 | 48min | 3 tasks | 22 files |
| Phase 04 P03 | 95min | 3 tasks | 18 files |
| Phase 04 P04 | 24min | 3 tasks | 15 files |
| Phase 04 P05 | 80min | 3 tasks | 20 files |
| Phase 04 P06 | 220min | 3 tasks | 14 files |
| Phase 04 P07 | 33min | 3 tasks | 8 files |
| Phase 05 P01 | 55min | 3 tasks | 12 files |
| Phase 05 P02 | 55min | 3 tasks | 10 files |
| Phase 05 P03 | 30 min | 3 tasks | 12 files |
| Phase 07 P01 | 55min | 3 tasks | 11 files |
| Phase 05 P06 | ~35min | 3 tasks | 5 files |
| Phase 05 P04 | 25min | 3 tasks | 8 files |
| Phase 07 P02 | 55min | 3 tasks | 6 files |
| Phase 07 P03 | 55min | 3 tasks | 6 files |
| Phase 05 P05 | 15min | 3 tasks | 10 files |
| Phase 05 P08 | 20min | 3 tasks | 7 files |
| Phase 07 P05 | 65min | 3 tasks | 6 files |
| Phase 06 P03 | 70min | 3 tasks | 9 files |
| Phase 06 P02 | 70 min | 3 tasks | 7 files |
| Phase 08 P01 | 45min | 3 tasks | 10 files |
| Phase 06 P04 | 95min | 3 tasks | 11 files |
| Phase 08 P03 | 40min | 3 tasks | 5 files |

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
- [Phase 03]: 03-01: Route B (Reproduce a disclosure) reproduces Anora exactly end-to-end through HTTP; pair selector shows every fixture with a plain-words reason when unselectable
- [Phase 03]: [Phase 03] 03-02: engine/spec.py::ProductionSpec lands the INP-01..INP-07 input contract (decision Task 1 resolved autonomously to option A: production_type enum alone, no scale field); handle_spec_submission enforces the D-35 two-layer budget refusal, resolves crew tier to a headcount range labelled modelling_assumption (never validated), and returns New York's cited rule terms with zero dollar figures derived from the visitor's spec. Two Rule-1 bugs caught and fixed before commit: an order-dependent sys.modules test isolation bug, and a comma-splitting bug that tore 'Albany, NY'-style city names in two.
- [Phase 04]: [Phase 04] 04-01: basis provenance axis (D-58/D-59) lands on Figure; Route A closes D-36, returning a real basis-tagged dollar total_landed_cost (Decimal("253125") for the fixed test spec) built from one canonical budget localized against New York's committed cost profile — Closes the D-36 seam with three non-vacuous CI honesty gates (D-59, D-63, D-72); cost-profile naming settled at {jurisdiction}-{city} to match every later wave in this phase
- [Phase 04]: [Phase 04] 04-02: labour widened from a single flat estimated day rate to real per-craft union rate rows (IATSE Local 600 camera scale sourced for both regions) plus fringe as a separate visible Figure; Los Angeles gets its first full cost profile with jurisdiction_id null (D-53 proven). Fixed-test-spec total_landed_cost moves from $253,125 (04-01) to $447,532. DGA/WGA fringe percentages resolved sourced from primary documents (Assumptions A1/A2); SAG-AFTRA and 9 of 10 crew departments remain estimated pending further sourcing, recorded in WINDOWS.md.
- [Phase 04]: [Phase 04] 04-03: GSA FY2026 per-diem bulk file re-confirmed byte-for-byte against 04-RESEARCH.md's CITED figures for both floor cities (zero discrepancy, raised to basis: sourced); housing/per_diem/flights now price against imported crew and cast only via a new travel: profile block, and New York's start quarter genuinely moves the number through the housing line alone (per diem's M&IE is flat) while Los Angeles has zero quarter-variant lines. Fixed-test-spec total_landed_cost moves from $447,532 (04-02) to $515,867.
- [Phase 04]: [Phase 04] 04-04: facilities (COST-06) and INC-10 exemptions land; not_priced empties for New York and Los Angeles, and both cities' total_landed_cost now reports basis: modelling_assumption (the weakest tier, from the five facilities lines). Low-bound pricing treatment chosen uniformly over the midpoint for all facilities categories, both cities (research row A5). No live document-fetch tool was available this session, so every facilities/exemption entry stayed at basis: estimated or modelling_assumption rather than a named-anchor sourced/estimated tier -- recorded honestly to WINDOWS.md (entries 15-17) rather than fabricated. D-76's four guarantees (exemption Figure ids disjoint from the incentive DAG; gross credit never greater with exemptions; cost-total delta equals the summed reduction; absent-category raise) are proven as tests against real committed New York data.
- [Phase 04]: 04-05: dated GBP->USD FX snapshot (1.363, 2026-08-26) with refuse-rather-than-derive convert/rate_figure; London lands as the third floor city and first non-USD one with BECTU rows genuinely basis: sourced (live network access this session), zero engine changes to union_rates/per_diem/facilities/exemptions; per-component conversion added to aggregate() via reporting_currency, converted total exactly equals the sum of converted components, FX rate visible as its own named component (D-75). London's fixed-test-spec total: £548,595 GBP / $747,735 USD.
- [Phase 04]: 04-06: Two-band ranked list (engine.ranker) and component-by-component gap decomposition (engine.gap) land; rank() requires reporting_currency after catching a Rule-1 bug where a GBP city would have sorted against a raw USD total; decompose_gap folds a city-specific INC-10 exemption reduction into its target cost line before by-label matching (another real discovery against NY/LA's genuinely different exemption types). Golden Decimal totals pinned in CI (D-78): NY $758,427, LA $693,521, London £548,595/$747,735, NY-vs-LA gap $64,906 -- every value independently hand-derived and confirmed exact against the pipeline, non-vacuity proven via an in-memory rate perturbation. Route A's JSON contract splits the two bands into separate top-level keys (net_ranked_cities/incentive_not_modelled_cities), resolving a contradiction between the plan's own action prose and its acceptance criteria in favor of the criteria.
- [Phase 04]: [Phase 04] 04-07: seven-row declared sensitivity step table drives a real-pipeline perturbation engine (D-67/D-68); regime-signature diffing reads chain-produced derivation text to detect crew-tier and incentive tiered-band cliff crossings (D-69); a non-vacuous D-70 gate (proven to fail on an inserted word, twice) covers both engine strings and rendered HTML. Fixed golden NY-vs-LA gap $64,906; quarter-forward is the only cliff-crossing row (per-diem month band shifts April->July); full 8-run perturbation set measured ~539ms. Fixed a real bug: the new four-quarter quarter-invariance re-run must exclude a quarter a dated union rate row does not cover, rather than crashing the visitor's own request.
- [Phase 05]: 05-01 (tracer): agent/ package wires Parallel Search -> primary-government-domain filter -> Parallel Extract -> google-genai structured extraction -> engine.pipeline.price_jurisdiction, in that fixed order (D-82), with both SDKs imported lazily and a D-84 PRODFIN_SDK_CALL log line unconditional at both call sites. Parallel/Gemini SDK call signatures resolved by introspecting the installed parallel-web==1.3.3 / google-genai==2.19.0 packages, not from memory (recorded in 05-01-SUMMARY.md's Decisions Made). tests/test_agent_eligibility.py (14 tests) is the standing CI gate. No API key is present in this environment — SHP-05/SHP-06 are code-verified but UNVERIFIED-IN-PRODUCTION until a human installs both keys per deploy/README.md and runs `python -m agent.job1 --limit 1 --require-live` successfully once.
- [Phase 05]: 05-02: D-88 locale-aware money parsing (parse_money) and D-86 three-value mismatch taxonomy (MatchClass/classify/AccuracySummary) land together; explained_variance is reachable only through agent/variance_rules.yaml's closed predicate registry (T-05-07), with an unknown predicate raising at load.
- [Phase 05]: 05-02: AGT-03 (three exact live reproductions) is honestly gated open via .planning/WINDOWS.md entry #26, not a live artifact -- PARALLEL_API_KEY/GEMINI_API_KEY remain unset in this environment; tests/test_agent_job1_offline.py enforces exactly one of {live artifact, WINDOWS.md entry}, never a skip.
- [Phase 05]: Job 1's SDK-call evidence block reuses agent.telemetry.sdk_call via an ambient contextvars collector (agent.telemetry.collecting), not a signature change at the existing parallel_client.py/gemini_client.py call sites -- the D-84 log line and the on-page evidence are provably the same record.
- [Phase 05]: The non-live rendering guard (T-05-15) is enforced in app/routers/job1.py itself, not only in the template: for a non-live run, awards/accuracy are never placed in the Jinja2 context at all, so a template rewrite cannot leak an accuracy figure for data it was never handed.
- [Phase 05]: Deployed to vockell.com/finance (git_sha 9af46b0) with no API keys on the box (Path B). SHP-05 and SHP-06 were left Pending in REQUIREMENTS.md despite the mechanical shared-ID gate reporting them ready, because both are live-outcome claims that remain false; only AGT-02 (a mechanism claim, already proven) was marked complete. WINDOWS.md entry 28 records the exact human action needed.
- [Phase 07]: 07-01 (tracer): agent/job2.py lands the D-90 self-terminating research loop — while True: driven only by SufficiencyVerdict.decision, no round counter, proven by an AST gate plus scripted 1/2/5-round tests. One session_id threads every round's Search call; app/services/cache_policy.py is the single AGT-10 choke point, asserted before the first Search (mutation-tested). var/job2/{job_id}.json persists each round atomically before the next round starts (D-92). No API key is present in this environment — every claim is proven offline (24 new tests); the live Parallel/Gemini call pair remains unverified pending keys, same as 05-01's SHP-05/SHP-06 gap.
- [Phase 05]: Plan 05-06: two new Connecticut validation pairs (Colony Video 2015 Productions at 10%, Mako Games at 15%) fill the last two unexercised rate bands; the transfer-discount refusal is now asserted uniformly per-pair rather than for one pair only.
- [Phase 05]: 05-04: California (JUR-02) modelled as one nonrefundable_credit programme at a directly-sourced 35% base rate (RTC 17053.98.1), not the 20%+uplifts guess Phase 1 assumed — RTC 17053.98 (the statute this plan's own Task 1 text names) is the superseded Program 3.0 statute; RTC 17053.98.1 is the current one, confirming 35%/40% directly and matching both fixtures within 12 bps on the bare base rate
- [Phase 07]: 07-02 finishes the D-90 loop's shape: merge_findings/unmet_fields/build_refined_objective/normalize_queries/normalize_mode are pure functions driving refinement (a determined field is never flipped back False, an unsourced later value never overwrites a sourced one); TerminalReason is now a closed nine-value taxonomy (not a pass-through of the model's decision literal) with a "sufficient" claim cross-checked against the driver's own merged findings and a new JurisdictionIdentity block before being believed; the wall-clock guard is now enforced (time.monotonic(), checked only between rounds, never mid-call) producing budget_exhausted distinct from agent_gave_up; both SDK call sites are wrapped so an exception becomes a durable sdk_error record. tests/test_agent_job2_loop.py is the new standing AST-based gate (34 tests); both non-vacuity mutations were performed by hand, observed failing, and reverted this session. No API keys are present in this environment; every claim is proven offline, same gap 07-01 already named.
- [Phase 07]: AGT-11 restart recovery is a boot_id comparison centralized in save_run/append_round, never a timeout — A heuristic staleness timer would either declare a slow live job dead or leave a genuinely dead job spinning — proven with a real two-process SIGKILL test plus a live uvicorn kill/restart
- [Phase 05]: us-nj.yaml declares mechanism: transferable (not nonrefundable_credit) — NJ's transfer right applies broadly to the modeled programme, unlike CA's track-restricted sale right — N.J.A.C. 19:31T-1.10(a) mirrors CT's statutory phrasing more closely than CA's track-restricted sale right; produces the correct engine.net_cash.transferable honesty-gate refusal
- [Phase 05]: Widened RULESET_PATH_BY_JURISDICTION to all four curated jurisdictions (NY, CA, NJ, CT) in app/services/_paths.py, the single dict app.services.spec and app.services.validate both import. — JUR-02/JUR-03/JUR-04 require a validated model reachable from the hosted /validate surface, not just a rule file in the repo; the honest-refusal path (WINDOWS.md #3) proved to fire for real committed NJ/CT pairs rather than staying hypothetical.
- [Phase 06]: SLIDER_QUARTERS scoped to 3 real, sourced quarters (Q4 2025/Q1 2026/Q2 2026), excluding Q3 2026 after discovering it triggers a pre-existing, uncaught ValueError in engine.sensitivity.sensitivity_rows (WINDOWS #34) rather than routing around it silently. — The bug is out of this plan's files_modified (engine/sensitivity.py); recorded to WINDOWS instead of fixed.
- [Phase 06]: UI-05's band-honesty refusal is a new policy layer in app/services/compare.py (resolve_gap_selection), not a change to engine.gap.decompose_gap, which stays band-agnostic to preserve app/services/spec.py's existing golden NY-vs-LA gap. — The new two-city picker is a different UX (visitor-selectable pair) than /spec's fixed first-two-cities gap, so it gets its own gate rather than widening decompose_gap's contract.
- [Phase 08]: Phase 08-01 proof panel compares disclosed vs. GROSS credit (compute_qualifying_base + compute_gross_credit directly), never through price_jurisdiction's net-cash-inclusive pipeline — price_jurisdiction unconditionally converts to net cash, which refuses on NJ/CT's undeclared transfer_discount range — an unrelated question to what a disclosure actually reports (the gross credit).
- [Phase 08]: PRV-06's accuracy figure is computed by running agent.taxonomy.classify() over every selectable validation pair against agent/variance_rules.yaml, not by replaying a live Job 1 extraction run — No runs/job1/ evidence is committed (Parallel/Gemini credentials absent, D-101); this measurement is a distinct, always-available, 100% real computation, honestly labelled as such.
- [Phase 08]: Real bucket counts today: 5 exact_match / 0 explained_variance / 5 unexplained of 10 selectable pairs — nj_joker's fully-prose-explained $122,665 residue is not covered by either named predicate in agent/variance_rules.yaml (both NY-specific) and is shown honestly as unexplained rather than silently upgraded
- [Phase 08]: Added data/source_conflicts.yaml as the committed (currently empty) data source for PRV-07's conflict surface — No schema existed to ever record a real conflict; both candidate conflicts this project investigated (NY $700M/$800M, GA loan-out withholding) were already closed against a primary source, so the file stays empty rather than seeded with a manufactured entry.
- [Phase 06]: UI-11's original-currency figure is reconstructed via a one-level, non-deduplicating walk over cost_only_total.inputs (never collect_rate_figures' deduplicated walk, which silently undercounts a genuine sum) — Cross-checked against the documented golden London figure (£548,595) — the deduplicating approach reconstructed only £491,419
- [Phase 06]: CompareInputs.display_currency added to app/services/compare.py, outside plan 06-04's declared files_modified — Needed for POST/GET contract parity so the settled-slider JS path preserves a visitor's chosen display currency with zero changes to compare.js
- [Phase 05]: Pre-submission gate exit code reflects genuine ship-readiness (currently 1), not code well-formedness — production SDK-call logs and the sdk-call-sites table both honestly fail today — Matches SHIP-CHECKLIST.md's 8 unticked human actions; a script that reported 0 today would be lying about credential/deploy state

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
- **SHP-05/SHP-06 UNVERIFIED-IN-PRODUCTION (05-01, 2026-09-09).** `PARALLEL_API_KEY` and `GEMINI_API_KEY`/`GOOGLE_API_KEY` are not set anywhere in this environment or on the Lightsail box's `/opt/prodfin/.env`. The full pipeline is code-complete and mechanically tested with no keys present, but no live Search/Extract/Gemini call has ever actually fired. A human must obtain both keys and install them per `deploy/README.md`'s "Phase 5 — agent credentials" section, then run `python -m agent.job1 --limit 1 --require-live` once, successfully, before this eligibility gate can be considered proven rather than merely plumbed. This is a hard Stage One submission blocker.

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-09-09T15:02:55.890Z
Stopped at: Completed 06-04-PLAN.md
Resume file: None
