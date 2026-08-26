# Roadmap: ProductionFinance

## Overview

ProductionFinance prices one identical film production across every city a producer is considering and reports the true landed cost of each, with every figure sourced, dated, and provably matching a government disclosure. The build starts by confirming the facts the engine will encode and standing up a reachable HTTPS URL — both on day one, because DNS and TLS have their own clock. It then lands the generic incentive engine, which is the hard gate everything else plugs into, and immediately proves it end-to-end on New York by reproducing the Anora figure ($3,964,760 qualified spend → $991,190 credit issued) on the hosted URL with its citation. From there the work broadens in parallel: cost localization and landed-cost outputs, then three more curated jurisdictions with the validation-loop agent on one track and the real map/slider/ranked-list interface on another. Live research for uncurated cities lands after the validation loop, so ADK and Parallel integration problems surface on the known-answer case first. Accounts closes with the four demo beats, the proof panel, and a cold-network submission check — that is the ship gate and the actual hackathon submission. Balances, the scheduled public index, follows and is cuttable as a whole.

**Deadline: 2026-09-09 14:00 PDT.** Milestone 1 (Accounts) alone satisfies the hosted-URL Definition of Done. Milestone 2 (Balances) is explicitly cuttable.

## Milestones

- 🚧 **Milestone 1 — Accounts** — Phases 1-8. The hosted private calculator. **This is the hackathon submission.** All 88 v1 requirements.
- 📋 **Milestone 2 — Balances** — Phases 9-11. The scheduled public index. 11 v2 requirements. **CUTTABLE AS A WHOLE** if Accounts slips.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

### Milestone 1 — Accounts (the submission)

- [ ] **Phase 1: Foundations — Source Truth & Deploy Path** - Confirm every fact the engine will encode and get a public HTTPS URL live, in parallel
- [x] **Phase 2: Engine Spine & Incentive Interpreter** - One generic data-driven engine turning a spec plus a rule file into cited net cash (completed 2026-08-25)
- [ ] **Phase 3: New York End-to-End — The Anora Proof** - The thinnest vertical slice: a real cited government figure reproduced on the hosted URL
- [ ] **Phase 4: Cost Localization & Landed-Cost Outputs** - The same production priced against each city's real local costs, ranked and gap-decomposed
- [ ] **Phase 5: Curated Breadth & the Validation Loop** - CA, NJ, CT modelled and Job 1 proving them against government disclosures
- [ ] **Phase 6: The Interface** - Map, slider, ranked list, and every number on screen clickable through to its source
- [ ] **Phase 7: Live Research, Caching & Durable Jobs** - Job 2 prices an uncurated city live, labelled unvalidated, and survives a restart
- [ ] **Phase 8: Demo Proof, Export & Submission** - The four demo beats, the proof panel, and a cold-network verification — **SHIP GATE**

### Milestone 2 — Balances (cuttable)

- [ ] **Phase 9: Reference Production & Scheduled Index Runs** - A fixed reference production priced on a schedule, every run stored
- [ ] **Phase 10: The Published Index** - Public index with movement, change log, permanent URLs and a downloadable dataset
- [ ] **Phase 11: Reverse Mode & Chart-of-Accounts Depth** - What change closes a city's gap, plus full per-department breakdown

## Phase Details

### Phase 1: Foundations — Source Truth & Deploy Path

**Milestone**: 1 — Accounts
**Goal**: Every fact the engine will encode is confirmed against a primary source, and a public HTTPS URL serves the app on the host while vockell.com stays live.

> **Status 2026-08-25 — goal substantively met, one plan deliberately outstanding.**
> Verified 5/5 must-haves (`01-VERIFICATION.md`). `https://vockell.com/finance` serves
> anonymous visitors over valid TLS and vockell.com is unaffected.
> The word "resized" was dropped from the goal above because the resize did **not**
> happen: plan 01-07 is **deferred, not superseded** (`01-07-DEFERRED.md`) by user
> decision — the app instead runs on the un-resized 0.5 GB box, which measured 283 MB
> available with swap untouched. **SHP-01 remains open** and this phase stays unchecked
> until it is resolved or consciously retired. Re-test the memory premise as soon as
> `google-genai` or a datastore lands; the hosted URL is a Stage One submission
> requirement with a hard 2026-09-09 deadline.
**Depends on**: Nothing (first phase)
**Requirements**: SRC-01, SRC-02, SRC-03, SRC-04, SRC-05, SHP-01, SHP-02, SHP-03, SHP-04, SHP-07, SHP-08, SHP-09, SHP-10
**Success Criteria** (what must be TRUE):

  1. The New York cap, the Connecticut CSV column headers, the Georgia loan-out withholding rate and the partner track each have a written answer carrying a primary-source URL and the date it was checked
  2. All 11 production/award pairs exist as committed test fixtures, each recording its source document URL and its disclosure stage (issued, allocated or estimated)
  3. An anonymous visitor loads the project's subdomain over valid TLS and receives a response from the app, while vockell.com continues serving normally
  4. The app runs under systemd on Python 3.10 or newer, isolated from the system Python that Bitnami and Apache depend on, survives a host reboot, and is reached through Apache's reverse proxy
  5. CI fails the build if the resolved lockfile contains a forbidden package, if a secret is committed, or if a commit falls outside the contest window — and GitHub's About section displays an OSI-approved licence

**Plans**: 8/9 plans executed in 4 waves

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Python 3.12 project + FastAPI `/health` skeleton proven end-to-end locally, MIT licence, repo hygiene (wave 1)
- [x] 01-06-PLAN.md — Confirm the subdomain, record host facts, create the DNS A record (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Four blocking compliance CI gates proven fail-first, then publish the repository (wave 2)
- [x] 01-03-PLAN.md — Source-truth pipeline tracer on Anora, plus the three New York validation pairs (wave 2)
- [ ] 01-07-PLAN.md — Snapshot-and-restore resize to 2 GB, preserving the static IP (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-04-PLAN.md — CA, NJ and CT validation pairs, the four blocked MA/PA pairs, and the coverage guards (wave 3)
- [x] 01-08-PLAN.md — Isolated Python 3.12 on the host, systemd service, executed reboot test (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-05-PLAN.md — SOURCE-TRUTH.md: NY cap run down against the statute, CT schema, GA rate, partner track (wave 4)
- [x] 01-09-PLAN.md — Apache reverse proxy and Let's Encrypt TLS on the subdomain (wave 4)

**Parallel tracks**: Track A (source verification, SRC-*) and Track B (host and deploy path, SHP-*) share no state and run concurrently. Track B is day 2-3 work and must not wait on Track A — the subdomain DNS record and Let's Encrypt issuance have propagation clocks independent of build progress, and a working app with no reachable URL fails the submission.
**Gate notes**: SRC-04 (partner track) is **RESOLVED — Parallel**, owner-confirmed 2026-08-24 before planning began. Parallel Search is therefore a runtime requirement and is load-bearing in Phase 7; SHP-06 is no longer conditional. Re-verify against the submission portal when the entry is filed. SHP-01 (snapshot-and-restore resize to 2 GB) takes the live vockell.com site briefly offline and is a discrete, schedulable task. Measure free memory immediately after the Python install — it gates the Milestone 2 data-layer decision.
**Compliance notes**: SHP-07..10 are armed here and then verified continuously on every commit, not re-checked at the end. `google-adk` is installed bare — never `[all]`, `[extensions]` or `[test]`.

### Phase 2: Engine Spine & Incentive Interpreter

**Milestone**: 1 — Accounts
**Goal**: One generic, data-driven engine turns a production spec plus a jurisdiction rule file into a net-cash incentive figure whose every component traces back to its own source.
**Depends on**: Phase 1 (verified facts; a wrong constant here propagates into every downstream number)
**Requirements**: INC-01, INC-02, INC-03, INC-04, INC-05, INC-06, INC-07, INC-08, INC-09, JUR-05, PRV-01, PRV-02, PRV-03
**Success Criteria** (what must be TRUE):

  1. A jurisdiction's qualifying base is computed under its own definition — total local spend, labour only, lesser-of, or local-hires-only — and its gross credit converts to net cash by mechanism (refundable, transferable sold at broker discount, taxable net of corporation tax, or direct rebate) net of audit fees, with an estimated cash arrival date reported alongside the value
  2. Per-person ceilings with distinct loan-out and W-2 treatment, tier and uplift ordering including national/regional stacking, per-project and annual caps, and minimum-spend cliffs each visibly change the result when their inputs cross a boundary
  3. Every number the engine returns carries a source link, the date it was checked, a confidence tier of validated or researched, and a readable derivation reason
  4. Whether the production qualifies is answered separately from whether the programme's annual allocation still has money left in it
  5. A new jurisdiction can be added as a rule file alone with no change to engine code — demonstrated by adding a throwaway fixture jurisdiction

**Plans**: 9/9 plans executed in 3 waves; 3 gap-closure plans added in 2 waves after verification found gaps (02-VERIFICATION.md, status gaps_found, 2/5 must-haves)

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Tracer: New York priced end-to-end from rule file to the cited $991,190, plus the full schema and the dated scope-freeze note (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Pinned rounding, Decimal-typing regression, and PRV-01/02/03 as property assertions over a real computed tree (wave 2)
- [x] 02-03-PLAN.md — All four base-definition types, the closed-registry escape hatch, and minimum-spend cliffs (wave 2)
- [x] 02-05-PLAN.md — Per-person ceilings, cliff-tier versus ceiling-split rates, and Connecticut reproducing $1,159,502 (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-04-PLAN.md — Four net-cash mechanisms, audit-fee cliffs, corporation tax, arrival timing, and the UK £5.382M net (wave 3)
- [x] 02-06-PLAN.md — Stacking across programmes, caps, availability separate from eligibility, and the JUR-05 additivity proof (wave 3)

**Gap closure** *(added after 02-VERIFICATION.md returned gaps_found; run with `/gsd-execute-phase 2 --gaps-only`)*

- [x] 02-07-PLAN.md — CR-01: a failing regression fixture for `blended_by_ceiling_split` combined with a binding cliff, excluded line items and a per-person ceiling, then the fix that makes the rate step slice the actually-adjusted base (gap-closure wave 1)
- [x] 02-08-PLAN.md — WR-01/WR-02/WR-04: one load-time validator resolving every `stacks_with` and `mutually_exclusive_with` edge against declared programme ids, plus a non-empty `programmes` constraint (gap-closure wave 1)
- [x] 02-09-PLAN.md — WR-03: the loan-out withholding schedule's closed-closed dated-range convention documented, boundary-tested and guarded against overlapping bands; plus the validation-pairs golden test re-coupled to `price_jurisdiction` (gap-closure wave 2)

**Critical path**: This is the hard gate. Nothing in Phases 3-8 starts meaningfully before it lands. Scope is fixed by ARCHITECTURE.md's already-specified schemas — the `JurisdictionRuleSet` YAML schema, the immutable `Figure` value object carrying its own derivation DAG, and the generic rule interpreter with a small named Python handler registry as the escape hatch. No fresh research needed; implement against the specified design.
**Scope discipline**: Write a dated scope-freeze note listing the fixed set of modelled rule dimensions before moving on. Unbounded normalization scope is the #3 project-sinking risk.

### Phase 3: New York End-to-End — The Anora Proof

**Milestone**: 1 — Accounts
**Goal**: A visitor at the hosted URL describes a production and the system reproduces a published New York government award figure exactly, with its citation beside it.
**Depends on**: Phase 2 (engine spine), Phase 1 (deploy path)
**Requirements**: INP-01, INP-02, INP-03, INP-04, INP-05, INP-06, INP-07, INP-08, JUR-01, SHP-14
**Success Criteria** (what must be TRUE):

  1. A visitor can describe a production by type and scale, shoot days split stage versus location, crew size or a tier from which department ratios are inferred, principal cast count and how many are imported, crew imported versus hired locally, and a start window by quarter
  2. Entering a budget figure is refused with an explanation — cost is only ever an output, never an input
  3. The visitor names New York and the hosted page returns $991,190 against $3,964,760 of qualified spend, linked through to the NY ESD source document
  4. A validation test suite runs in CI on every commit asserting exact Decimal equality against the disclosed New York figures, and deliberately corrupting a rule value makes that suite fail

**Plans**: 2/3 plans executed in 2 waves

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — Tracer: Anora reproduces $991,190 end-to-end on the hosted page, with both provenance chains and a closed pair allowlist (wave 1)

**Wave 2** *(blocked on Wave 1 completion — the tracer must be green before either expansion plan lands)*

- [x] 03-02-PLAN.md — Route A: the `ProductionSpec` input contract, the crew-tier table, the never-suggest city resolver, and the visible budget refusal (wave 2)
- [ ] 03-03-PLAN.md — SHP-14: the declared mutation table, the five-step non-vacuity gate, and the sixth blocking CI job (wave 2)

**Frontend note**: a minimal form is sufficient here — deliberately no UI hint, because the real interface treatment is Phase 6 and must not be started early at the cost of the Anora proof.
**Why New York first**: Richest-documented curated jurisdiction, the demo's opening beat, and the first real cited number on a hosted URL. Unmissable — do not broaden before this lands. SHP-14's CI suite is born here rather than at submission time because a suite written on the last day cannot have caught anything; it is re-proven non-vacuous in Phase 8.

### Phase 4: Cost Localization & Landed-Cost Outputs

**Milestone**: 1 — Accounts
**Goal**: The same identical production is priced against each city's real local costs, producing a ranked total landed cost and a gap between any two cities decomposed by component.
**Depends on**: Phase 2 (engine spine), Phase 3 (input contract)
**Requirements**: COST-01, COST-02, COST-03, COST-04, COST-05, COST-06, COST-07, COST-08, INC-10, OUT-01, OUT-02, OUT-03, OUT-04
**Success Criteria** (what must be TRUE):

  1. One identical budget model is localized per city against published union rate cards (IATSE locals, SAG-AFTRA, DGA, WGA, BECTU, ACTRA) with fringe and payroll burden included — the comparison is never made against published rates
  2. Housing, meals, flights, stages, equipment, permits, locations and trucking are all priced per city, with GSA and State Department per diem labelled explicitly as reimbursement ceilings rather than market hotel rates, estimated lines labelled as estimates, and sales-tax or hotel-occupancy exemptions shown as separate stackable cost reductions where they exist
  3. Total landed cost is reported per candidate city, ranked; the gap between any two cities is decomposed by component; and the breakdown can be viewed aligned to the standard ATL/BTL/Post chart of accounts *(chart-of-accounts view is a stretch here — full treatment is Phase 11)*
  4. Changing the start quarter changes the cost figures through seasonal variation, not only through incentive availability, and a non-USD city converts at a dated FX rate carried as its own cited figure
  5. The output shows which single input most moves the gap, displayed as a delta and never as a prescriptive recommendation

**Plans**: TBD
**Cut line**: OUT-04 (chart-of-accounts breakdown) is the cuttable item within this phase — it is marked stretch in REQUIREMENTS.md and gets its full treatment in Milestone 2.

### Phase 5: Curated Breadth & the Validation Loop

**Milestone**: 1 — Accounts
**Goal**: Four jurisdictions are modelled and an agent proves the models against published government disclosures, reporting a real, honest accuracy figure.
**Depends on**: Phase 2 (engine spine), Phase 1 (locked validation pairs, confirmed CT CSV schema). Runs in parallel with Phase 6.
**Requirements**: JUR-02, JUR-03, JUR-04, AGT-01, AGT-02, AGT-03, AGT-04, AGT-08, AGT-09, SHP-05
**Success Criteria** (what must be TRUE):

  1. California, New Jersey and Connecticut each price correctly against their own government disclosure, with allocation-stage (CA) and estimated (NJ) figures labelled as such rather than presented with the same weight as issued figures
  2. Job 1 ingests a published government disclosure document and extracts every production/award pair from it
  3. Job 1 re-runs the model against each extracted pair and reports an accuracy figure, with at least three published government award figures reproduced exactly
  4. Every Job 1 result is classified as exact match, explained variance, or unexplained — no blended mean-error number that can silently absorb a real bug
  5. Every document and PDF extraction runs through a permitted Google SDK, proven by a timestamped log line at the call site in production logs, with groundedness checks on extracted quotes, preference for primary `.gov` domains, locale-aware number parsing, and proposed-bill versus enacted-law classification all enforced

**Plans**: TBD
**Cut line**: **Connecticut (JUR-04) is the first cuttable item in all of Accounts.** Its CSV schema is the least-verified of the four and the three-award Definition of Done is already met by NY/CA/NJ. Demote CT to live-researched-only if the deadline tightens.
**Absolute constraint**: AWS Textract is the single most likely accidental Stage One disqualification on this project — it is the obvious tool for exactly what Job 1 does. All extraction routes through Parallel Extract plus Gemini. Never Textract, Bedrock, Comprehend or any other AWS AI service.
**Track note**: This is Track A + Track C of the parallelizable breadth tier. Job 1 can start against New York alone while the CA/NJ/CT rule files finish. Build the mismatch taxonomy in from the start — retrofitting it is what makes an accuracy figure decorative instead of trustworthy.

### Phase 6: The Interface

**Milestone**: 1 — Accounts
**Goal**: An anonymous visitor gets a real map, slider and ranked-list product where every number on screen opens its own rule, source and date.
**Depends on**: Phase 4 (landed-cost outputs). Runs in parallel with Phase 5, built against the API contract fixed in Phases 2-3 using New York plus mocked cities until Phase 5 lands.
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-08, UI-11, UI-12, PRV-04, PRV-05
**Success Criteria** (what must be TRUE):

  1. An anonymous, unauthenticated visitor prices a described production across named cities from the hosted URL, and a map displays those cities coloured by total landed cost
  2. Dragging the start-date slider reorders the ranking live as it moves, and the ranked list shows net cost, incentive value, and when the cash actually arrives
  3. Selecting any two cities shows the decomposed gap between them, and clicking any number on screen opens its rule, its source link, and the date it was checked
  4. A comparison is shareable as a permalink URL encoding its inputs, and reopening that link shows what has changed since it was created
  5. A consolidated printable assumptions panel lists every rate used with its own source and date, a persistent linkable methodology page explains how figures are computed, and costs display in a chosen currency with dual display where a government figure is in another currency

**Plans**: TBD
**UI hint**: yes
**Why this is not incidental**: Design is one of four equally weighted judging criteria, and the hackathon scorecard ranks "build a real interface" as the single biggest needle-mover because it scores Design and Potential Impact simultaneously. This is the real map/slider/ranked-list treatment, not a form. It must not drift into Milestone 2.

### Phase 7: Live Research, Caching & Durable Jobs

**Milestone**: 1 — Accounts
**Goal**: A city with no curated model is researched live, priced, and clearly labelled unvalidated — and the job survives a process restart without hanging.
**Depends on**: Phase 5 (Job 1's extraction machinery and guardrails), Phase 6 (progress surface)
**Requirements**: AGT-05, AGT-06, AGT-07, AGT-10, AGT-11, UI-10, SHP-06
**Success Criteria** (what must be TRUE):

  1. Naming an uncurated city triggers live research that builds a model on the fly, prices it, and displays the result visibly labelled unvalidated and visually distinguishable from validated figures — with production logs showing a timestamped Parallel Search call at its call site fired by that session
  2. A city with no programme returns "no programme found" as a legitimate result rather than inventing one
  3. A live-researched jurisdiction lands in the same rule schema as a curated one, so it flows through the identical engine with no separate code path
  4. The visitor sees informative progress and reaches a legible terminal state within the documented ceiling — never a silent spinner that can time out
  5. Curated rules are served from cache while cap consumption, programme open/closed status, FX and uncurated-city research go live, enforced at a single point; a restarted process resumes or reclassifies in-flight research jobs instead of hanging

**Plans**: TBD
**UI hint**: yes
**Sequencing rationale**: Job 2 is deliberately after Job 1 so that ADK and Parallel integration problems surface on the cheaper, known-answer case first. Job 2 carries materially higher risk — unknown jurisdiction, unknown correct answer — and the live-research demo hanging in front of judges is the #5 project-sinking risk. Verify by triggering Job 2 against a deliberately obscure or nonexistent city and confirming a legible terminal state.
**Partner requirement**: SHP-06 is unconditional — the track is confirmed as Parallel. Job 2 must genuinely call Parallel's Search API at runtime via `parallel-web`, with a timestamped log line at the call site as the evidence.

### Phase 8: Demo Proof, Export & Submission — SHIP GATE

**Milestone**: 1 — Accounts
**Goal**: The four demo beats are showable on the hosted URL, the proof is visible in-product, and the submission is verified working for a cold anonymous visitor.
**Depends on**: Phase 7
**Requirements**: DMO-01, DMO-02, DMO-03, DMO-04, PRV-06, PRV-07, UI-07, UI-09, SHP-11, SHP-12, SHP-13
**Success Criteria** (what must be TRUE):

  1. A proof panel shows a reproduced government figure alongside the government document itself, and the running validation-loop accuracy figure is visible inside Accounts on the hosted page — not only in Balances
  2. The product can show a case where naive percentage arithmetic is badly wrong (the £18M UK example overstating by 44%), and a ranking that inverts once net cash and timing replace headline rate
  3. An uncurated city is researched live and priced on the hosted URL, labelled unvalidated, as a repeatable demo beat
  4. A comparison exports as a document a producer can hand upward, and conflicting authoritative sources appear as an unresolved conflict rather than being silently resolved to one value
  5. A demo video of 3 minutes or under lands the pain in its first 15 seconds, a written description covers features, technologies, data sources and findings, and the hosted URL is verified working from a fully logged-out browser on a different network than the development machine as the literal final pre-submission step

**Plans**: TBD
**UI hint**: yes
**Re-verification sweep** (not new requirements — re-running gates armed earlier): re-prove SHP-14's validation suite non-vacuous by breaking a rule value; grep production logs for at least one real Gemini call (SHP-05) and one real Parallel call (SHP-06) fired by a live logged-out session within 24 hours of submission; re-confirm the lockfile is clean (SHP-07) and the About-section licence is detectable (SHP-08).

---

## 🚩 SHIP GATE — Milestone 1 (Accounts) complete

**Everything above this line is the hackathon submission.** Accounts alone satisfies the hosted-URL Definition of Done: an anonymous visitor prices a production across named cities, at least three published government award figures are reproduced exactly, and an uncurated city is researched live and labelled unvalidated.

**Do not start Milestone 2 until Phase 8 is complete and submitted.** Everything below is cuttable as a whole.

---

### Phase 9: Reference Production & Scheduled Index Runs

**Milestone**: 2 — Balances **(CUTTABLE)**
**Goal**: A fixed reference production is defined as a methodology and priced across a fixed city set on a schedule, with every run stored so movement is computable over time.
**Depends on**: Phase 8 (ship gate — Accounts complete and submitted)
**Requirements**: IDX-01, IDX-02, IDX-06
**Success Criteria** (what must be TRUE):

  1. A written, published methodology defines the fixed reference production — its type, scale, shoot days, crew and cast composition — as a stated methodology rather than a shortcut constant
  2. A scheduled run prices the reference production across the fixed city set without manual intervention
  3. Every run is stored, so the difference between any two runs is computable after the fact

**Plans**: TBD
**Infrastructure note**: systemd timer, not EventBridge. Data layer decision (SQLite versus reusing the box's existing MySQL) is deferred to this phase's planning and depends on the free-memory measurement taken in Phase 1.
**Minimum publishable version if time is short**: a manually-triggered reference-production run rather than a scheduled one.

### Phase 10: The Published Index

**Milestone**: 2 — Balances **(CUTTABLE)**
**Goal**: The index is public, with movement between runs, a dated change log attributing each movement to its cause, permanent data-point URLs and a downloadable dataset.
**Depends on**: Phase 9
**Requirements**: IDX-03, IDX-04, IDX-05, IDX-07, IDX-08, IDX-09
**Success Criteria** (what must be TRUE):

  1. A public page shows the index with movement between runs, and the validation-loop accuracy figure republished alongside it
  2. A dated change log attributes each movement to its cause
  3. Individual data points have permanent URLs that resolve, and a versioned dataset is downloadable
  4. A standing public methodology page documents both the reference production and the model

**Plans**: TBD
**UI hint**: yes
**Minimum publishable version if time is short**: the index page with one real change-log entry and the republished accuracy figure. Permanent URLs (IDX-08) and the downloadable dataset (IDX-07) are the cuttable items within this phase.

### Phase 11: Reverse Mode & Chart-of-Accounts Depth

**Milestone**: 2 — Balances **(CUTTABLE — first thing to drop entirely)**
**Goal**: For a chosen city, the system reports what change would close its gap against the leader, and the cost breakdown reaches full per-department depth.
**Depends on**: Phase 10
**Requirements**: REV-01, DEP-01
**Success Criteria** (what must be TRUE):

  1. Choosing a city reports what change would close its gap against the leader, expressed as a named lever with its magnitude
  2. The cost breakdown resolves to full per-department detail aligned to the standard chart of accounts

**Plans**: TBD
**Cut line**: **This is the correct first thing to drop entirely.** Reverse mode is explicitly deferred in PROJECT.md's own Key Decisions and is the most computationally novel remaining piece. Dropping it costs nothing that the submission depends on.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → **SHIP GATE** → 9 → 10 → 11

**Parallel opportunities** (parallelization is enabled in config):

- Within Phase 1: Track A (SRC-*) and Track B (SHP-*) run concurrently
- Phase 5 and Phase 6 both depend only on Phases 2-4 and run concurrently

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundations — Source Truth & Deploy Path | 1 — Accounts | 8/9 | In Progress|  |
| 2. Engine Spine & Incentive Interpreter | 1 — Accounts | 9/9 | Complete    | 2026-08-25 |
| 3. New York End-to-End — The Anora Proof | 1 — Accounts | 2/3 | In Progress|  |
| 4. Cost Localization & Landed-Cost Outputs | 1 — Accounts | 0/TBD | Not started | - |
| 5. Curated Breadth & the Validation Loop | 1 — Accounts | 0/TBD | Not started | - |
| 6. The Interface | 1 — Accounts | 0/TBD | Not started | - |
| 7. Live Research, Caching & Durable Jobs | 1 — Accounts | 0/TBD | Not started | - |
| 8. Demo Proof, Export & Submission | 1 — Accounts | 0/TBD | Not started | - |
| 9. Reference Production & Scheduled Index Runs | 2 — Balances | 0/TBD | Not started | - |
| 10. The Published Index | 2 — Balances | 0/TBD | Not started | - |
| 11. Reverse Mode & Chart-of-Accounts Depth | 2 — Balances | 0/TBD | Not started | - |

## Cut Order Under Deadline Pressure

Ordered list of what to drop first if 2026-09-09 14:00 PDT tightens. Drop from the top.

1. **Phase 11 entirely** — reverse mode and per-department depth
2. **Phase 10 partial** — permanent data-point URLs (IDX-08) and the downloadable dataset (IDX-07)
3. **Phase 9-10 entirely** — all of Milestone 2. Accounts alone is the submission.
4. **Connecticut (JUR-04)** in Phase 5 — demote to live-researched-only; NY/CA/NJ already clear the three-award bar
5. **OUT-04** in Phase 4 — the chart-of-accounts view, already marked stretch
6. **UI-12** in Phase 6 — the "what changed since this link was created" diff

**Never cuttable:** Phase 1 (both tracks), Phase 2, Phase 3, and Phase 8's SHP-11/12/13. These are the Definition of Done.

## Requirement Coverage

**v1 (Accounts): 88/88 mapped across Phases 1-8. No orphans, no duplicates.**
**v2 (Balances): 11/11 mapped across Phases 9-11.**

| Category | Count | Phases |
|----------|-------|--------|
| SRC (Source Verification) | 5 | 1 |
| INP (Production Input) | 8 | 3 |
| COST (Cost Model) | 8 | 4 |
| INC (Incentive Engine) | 10 | 2 (×9), 4 (×1) |
| OUT (Outputs) | 4 | 4 |
| PRV (Provenance and Proof) | 7 | 2 (×3), 6 (×2), 8 (×2) |
| JUR (Curated Jurisdictions) | 5 | 2 (×1), 3 (×1), 5 (×3) |
| AGT (Agentic Jobs) | 11 | 5 (×6), 7 (×5) |
| UI (Interface) | 12 | 6 (×9), 7 (×1), 8 (×2) |
| SHP (Delivery and Compliance) | 14 | 1 (×8), 3 (×1), 5 (×1), 7 (×1), 8 (×3) |
| DMO (Demo Narrative) | 4 | 8 |
| **v1 total** | **88** | |
| IDX (Public Index) | 9 | 9 (×3), 10 (×6) |
| REV (Reverse Mode) | 1 | 11 |
| DEP (Deeper Breakdown) | 1 | 11 |
| **v2 total** | **11** | |

---
*Roadmap created: 2026-08-24*
