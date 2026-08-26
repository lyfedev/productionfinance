# Requirements: ProductionFinance

**Defined:** 2026-08-24
**Core Value:** Total landed cost of one identical production, priced per city, with every figure sourced, dated, and provably matching what a government actually paid.

**Milestone mapping:** v1 = **Accounts** (the hosted private calculator — the hackathon submission, due 2026-09-09 14:00 PDT). v2 = **Balances** (the scheduled public index).

---

## v1 Requirements — Milestone: Accounts

### Source Verification

Resolve before modelling. Wrong inputs produce confidently wrong outputs, and the product's entire claim is correctness.

- [x] **SRC-01**: New York's annual cap is reconciled against a primary source (tax.ny.gov or enacted FY2026 budget bill text). Working hypothesis to confirm or refute: $700M base plus a separate $100M independent-film pool, not a $700M/$800M dispute.
- [x] **SRC-02**: Connecticut open-data CSV column headers are confirmed by opening the actual endpoint, before CT's rule model or ingestion logic is written
- [x] **SRC-03**: All 11 sourced production/award validation pairs are locked into test fixtures with their source document URLs and disclosure stage (issued / allocated / estimated) recorded
- [x] **SRC-04**: Partner track confirmed — **Parallel** (owner-confirmed 2026-08-24). Parallel's Search API must be called at runtime via the official `parallel-web` SDK. The "Our track: IBM" line in `hackathon-brief.md` refers to the sibling animatic project and does not apply here. *Resolved before planning; re-verify against the submission portal when the entry is filed.*
- [x] **SRC-05**: Georgia loan-out withholding rate is confirmed against a dated Georgia DOR source. Working hypothesis: 5.75% is pre-2024-reform, 4.99% is current.

### Production Input

- [x] **INP-01**: User can specify production type and scale (feature / limited series / episodic)
- [x] **INP-02**: User can specify shoot days, split between stage and location
- [x] **INP-03**: User can specify crew size, or select a tier from which department ratios are inferred
- [x] **INP-04**: User can specify principal cast count and how many are imported
- [x] **INP-05**: User can specify how much crew is imported versus hired locally
- [x] **INP-06**: User can specify a start window by quarter
- [x] **INP-07**: User can name the candidate cities to be priced — the system never suggests them
- [x] **INP-08**: System rejects any budget figure as input; cost is only ever an output

### Cost Model

- [x] **COST-01**: One identical budget model is localized per city — comparison is never made against published rates
- [ ] **COST-02**: Labour is localized against published union rate cards (IATSE locals, SAG-AFTRA, DGA, WGA, BECTU, ACTRA)
- [x] **COST-03**: Labour cost includes fringe and payroll burden, not bare card rates
- [ ] **COST-04**: Housing and meals use GSA per diem by US county and State Department foreign per diem, displayed with an explicit label that these are reimbursement ceilings and not market hotel rates
- [ ] **COST-05**: Flights and housing are computed for imported crew and cast specifically
- [ ] **COST-06**: Stage, equipment, permit, location and trucking costs are included, with estimated lines labelled as estimates
- [ ] **COST-07**: Start quarter drives seasonal cost variation, not only incentive availability
- [ ] **COST-08**: Multi-currency costs are converted via a dated FX rate carried as a cited figure

### Incentive Engine

- [x] **INC-01**: Qualifying base is computed under each jurisdiction's own definition — total local spend, labour only, lesser-of formulas, or local-hires-only
- [x] **INC-02**: Per-person ceilings are applied, including differing loan-out versus W-2 treatment
- [x] **INC-03**: Tiers and uplifts are applied in the correct jurisdiction-specific order, including stacking rules between national and regional programmes
- [x] **INC-04**: Per-project caps and annual programme caps are both modelled
- [x] **INC-05**: Availability is reported separately from eligibility — whether the annual allocation still has money in it is its own answer
- [x] **INC-06**: Gross incentive is converted to net cash by mechanism: refundable credit, transferable credit sold at broker discount, direct rebate, or non-refundable, with audit fees deducted
- [x] **INC-07**: Taxable incentives are reported net of corporation tax
- [x] **INC-08**: Estimated cash arrival timing is reported alongside value
- [x] **INC-09**: Minimum spend thresholds and cliff effects are modelled
- [ ] **INC-10**: Sales tax and hotel occupancy tax exemptions are modelled as separate stackable cost reductions where they exist

### Outputs

- [ ] **OUT-01**: Total landed cost is reported per candidate city, ranked
- [ ] **OUT-02**: Cost gap between any two cities is reported, decomposed by component
- [ ] **OUT-03**: Sensitivity is displayed — which single input most moves the gap, shown as a delta and never as a prescriptive recommendation
- [x] **OUT-04**: Cost breakdown is available aligned to the standard ATL / BTL / Post chart of accounts *(stretch for Accounts; full treatment in Balances)*

### Provenance and Proof

- [x] **PRV-01**: Every figure carries a source link and the date it was checked
- [x] **PRV-02**: Every figure carries a confidence tier — validated or researched — and the two are visually distinguishable, never presented with equal weight
- [x] **PRV-03**: Every computed figure carries its derivation reason as readable text (e.g. "only $500K of the $2M lead qualifies — Georgia per-person ceiling")
- [ ] **PRV-04**: A consolidated, printable assumptions panel lists every rate used, each with its own source and date
- [ ] **PRV-05**: A persistent in-product methodology page explains how figures are computed and is linkable
- [ ] **PRV-06**: The running validation-loop accuracy figure is visible inside Accounts itself, on the hosted page — not only in Balances
- [ ] **PRV-07**: Conflicting authoritative sources are surfaced as an unresolved conflict rather than silently resolved to one value

### Curated Jurisdictions

The four where per-production government disclosure exists, so every model is provable.

- [x] **JUR-01**: New York — validated model, reproducing NY ESD quarterly report figures
- [ ] **JUR-02**: California — validated model against the Film Commission approved projects list, with allocation-stage figures labelled as such
- [ ] **JUR-03**: New Jersey — validated model against NJEDA activity reports, with estimated figures labelled as such
- [ ] **JUR-04**: Connecticut — validated model against the Connecticut open data CSV
- [x] **JUR-05**: Adding a jurisdiction is additive — a new rule file, not changes to the engine

### Agentic Jobs

- [ ] **AGT-01**: Job 1 ingests a published government disclosure document and extracts every production/award pair
- [ ] **AGT-02**: Job 1 re-runs the model against each extracted pair and reports accuracy
- [ ] **AGT-03**: Job 1 reproduces at least three published government award figures exactly
- [ ] **AGT-04**: Job 1 classifies every result into an explicit mismatch taxonomy — exact match, explained variance, or unexplained — built in from the start rather than retrofitted
- [ ] **AGT-05**: Job 2 researches a city with no curated model live, builds a model on the fly, prices it, and labels the result unvalidated
- [ ] **AGT-06**: Job 2 returns "no programme found" as a legitimate result rather than inventing one
- [ ] **AGT-07**: Job 2 coerces live-researched jurisdictions into the same schema as curated ones
- [ ] **AGT-08**: Extraction guardrails are enforced — groundedness checks on extracted quotes, preference for primary government domains over secondary summaries, locale-aware number parsing, and classification of proposed bills versus enacted law
- [ ] **AGT-09**: All document and PDF extraction runs through the permitted Google SDK — never AWS Textract or any other non-permitted AI service
- [ ] **AGT-10**: The caching boundary is enforced at a single point: curated rules cached, while cap consumption, programme open/closed status, FX and uncurated-city research are live
- [ ] **AGT-11**: Live research jobs have durable state and survive a process restart without hanging

### Interface

- [ ] **UI-01**: A hosted URL prices a described production across named cities for an anonymous, unauthenticated visitor
- [ ] **UI-02**: A map displays candidate cities coloured by total landed cost
- [ ] **UI-03**: A start-date slider reorders the ranking live as it moves
- [ ] **UI-04**: A ranked list shows net cost, incentive value, and when the cash arrives
- [ ] **UI-05**: Selecting any two cities shows the decomposed gap between them
- [ ] **UI-06**: Every number on screen is clickable through to its rule, source and date checked
- [ ] **UI-07**: A proof panel shows a reproduced government figure alongside the government document
- [ ] **UI-08**: A comparison can be shared as a permalink URL encoding its inputs — the only persistence mechanism, since there is no login
- [ ] **UI-09**: A comparison can be exported as a document a producer can hand upward
- [ ] **UI-10**: Live research shows informative progress and terminal error states, never a silent spinner that can time out
- [ ] **UI-11**: Costs can be displayed in a chosen currency, with dual display where a government figure is in another currency
- [ ] **UI-12**: A shared link shows what changed since it was created

### Delivery and Compliance

Stage One judging is pass/fail and partly automated. Each of these is a gate, not a nicety.

- [ ] **SHP-01**: The vockell.com Lightsail instance is resized to 2 GB via snapshot-and-restore, preserving its static IP
- [x] **SHP-02**: Python 3.10 or newer is installed on the host, isolated from the system Python that Bitnami and Apache depend on
- [x] **SHP-03**: The public hostname resolves to the deploy target — satisfied by the existing `vockell.com` A record under the D-14 path-mount decision (`https://vockell.com/finance`). No subdomain record was created because none is required; the propagation delay this requirement was written to front-load no longer exists. Original wording read "A subdomain DNS record exists and resolves — created early, as it is the only item carrying propagation delay"; reworded 2026-08-25 to match what was actually built rather than leave a satisfied-looking claim about a record that does not exist.
- [x] **SHP-04**: The application runs under systemd and is reverse-proxied through Apache with a valid TLS certificate, without disturbing the live vockell.com site
- [ ] **SHP-05**: A permitted Google SDK is imported and genuinely called at runtime, verified by a timestamped log line at the call site
- [ ] **SHP-06**: Parallel's Search API is genuinely called at runtime via the official `parallel-web` SDK, verified the same way — unconditional, the track is confirmed as Parallel
- [x] **SHP-07**: The resolved lockfile contains none of litellm, openai, anthropic, langchain, langgraph, crewai or llama-index — checked automatically, and `google-adk` is installed bare, never with `[all]`, `[extensions]` or `[test]`
- [x] **SHP-08**: The repository is public with an OSI-approved license detectable in the GitHub About section, not merely a LICENSE file
- [x] **SHP-09**: All commits fall within the contest window opened 2026-07-27
- [x] **SHP-10**: No secret is ever committed — the repository is public
- [ ] **SHP-11**: A demo video of 3 minutes or under shows the system functioning, with the pain landed in the first 15 seconds
- [ ] **SHP-12**: A written description covers features, technologies, data sources and findings
- [ ] **SHP-13**: The hosted URL is verified working from a logged-out browser on a different network than the development machine, as the final pre-submission step
- [x] **SHP-14**: A validation test suite runs in CI on every commit, asserting exact equality against disclosed government figures — and is proven non-vacuous by deliberately breaking a rule value and confirming the suite catches it

### Demo Narrative

Four beats the brief requires the system to be able to show.

- [ ] **DMO-01**: Open on validation — reproduce a published government award figure exactly, with the government document alongside it
- [ ] **DMO-02**: Show a case where naive percentage arithmetic is badly wrong (the £18M UK example overstates by 44%)
- [ ] **DMO-03**: Show a ranking that inverts once net cash and timing replace headline rate
- [ ] **DMO-04**: Show a city with no curated model being researched live and priced, labelled unvalidated

---

## v2 Requirements — Milestone: Balances

Deferred to the second milestone. Cuttable as a whole if Accounts slips, since Accounts alone satisfies the hosted-URL Definition of Done.

### Public Index

- **IDX-01**: A fixed reference production is defined — the methodology, not a shortcut
- **IDX-02**: The reference production is priced across a fixed city set on a schedule
- **IDX-03**: The index is published with movement between runs
- **IDX-04**: A dated change log attributes each movement to its cause
- **IDX-05**: The validation-loop accuracy figure is republished alongside the index
- **IDX-06**: Historical runs are stored so movement is computable over time
- **IDX-07**: A versioned dataset is downloadable
- **IDX-08**: Permanent URLs address individual data points
- **IDX-09**: A standing public methodology page documents the reference production and the model

### Reverse Mode

- **REV-01**: For a chosen city, report what change would close its gap against the leader

### Deeper Breakdown

- **DEP-01**: Full per-department cost breakdown aligned to the standard chart of accounts

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Ranking on headline incentive rate | What every existing tool does, and wrong by 20 to 40 percent |
| Budget figure as an input | Circular — a dollar buys a different production in each city |
| Creative or logistical location suitability | The user names the cities; suggesting Budapest for a script needing the Pacific loses a film person's trust instantly |
| Sunset and expiry dates as a decision input | Terms lock at application, so a future expiry cannot affect a current production. Scheduled future improvements remain in scope. |
| Live daily research as the differentiator | Rules change roughly annually per jurisdiction. Overclaiming freshness invites a judge to check and disprove it. |
| Validated models for Georgia, New Mexico, Illinois, Louisiana, UK, Canada | No per-production disclosure exists, so the validation loop cannot close. Reachable via live research, labelled unvalidated. |
| Ireland as a validated jurisdiction | Publishes banded figures only — cannot support exact reproduction |
| Economic impact / ROI figures | Politically contested; industry-funded studies and independent state auditors disagree sharply. Would require exposing the multiplier assumption on screen or it becomes advocacy. |
| Non-union local labour rates | Not public. That is what Entertainment Partners and Cast & Crew sell. |
| A conversational chatbot interface | The incumbent (Wrapbook) ships one that self-discloses it may hallucinate, and falls back to a named human for hard questions. Verified citation beats conversation in this category. |
| User accounts and login | The hosted URL must work for an anonymous visitor; permalinks (UI-08) provide persistence instead |
| Docker on the host | A second memory-hungry daemon on a 2 GB box shared with Apache and MySQL. systemd-supervised uvicorn instead. |
| Caddy for TLS | Cannot bind ports 80/443 while Apache holds them for the live vockell.com site. Certbot via Apache instead. |
| A second database engine (Postgres) in Accounts | SQLite has no server process and no steady-state memory cost, on a box where memory is the binding constraint. Revisit for Balances only with a measurement. |
| AWS AI services | Every one is a Stage One disqualification. AWS Textract is the specific trap, since parsing government PDFs is exactly what it is for. |

---

## Traceability

Every v1 requirement maps to exactly one phase in `.planning/ROADMAP.md`. No orphans, no duplicates.

| Requirement | Phase | Milestone | Status |
|-------------|-------|-----------|--------|
| SRC-01 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Complete |
| SRC-02 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Complete |
| SRC-03 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Complete |
| SRC-04 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Complete |
| SRC-05 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Complete |
| INP-01 | Phase 3 — New York End-to-End: The Anora Proof | 1 — Accounts | Complete |
| INP-02 | Phase 3 — New York End-to-End: The Anora Proof | 1 — Accounts | Complete |
| INP-03 | Phase 3 — New York End-to-End: The Anora Proof | 1 — Accounts | Complete |
| INP-04 | Phase 3 — New York End-to-End: The Anora Proof | 1 — Accounts | Complete |
| INP-05 | Phase 3 — New York End-to-End: The Anora Proof | 1 — Accounts | Complete |
| INP-06 | Phase 3 — New York End-to-End: The Anora Proof | 1 — Accounts | Complete |
| INP-07 | Phase 3 — New York End-to-End: The Anora Proof | 1 — Accounts | Complete |
| INP-08 | Phase 3 — New York End-to-End: The Anora Proof | 1 — Accounts | Complete |
| COST-01 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Complete |
| COST-02 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Pending |
| COST-03 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Complete |
| COST-04 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Pending |
| COST-05 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Pending |
| COST-06 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Pending |
| COST-07 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Pending |
| COST-08 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Pending |
| INC-01 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| INC-02 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| INC-03 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| INC-04 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| INC-05 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| INC-06 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| INC-07 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| INC-08 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| INC-09 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| INC-10 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Pending |
| OUT-01 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Pending |
| OUT-02 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Pending |
| OUT-03 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Pending |
| OUT-04 | Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | Complete |
| PRV-01 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| PRV-02 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| PRV-03 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| PRV-04 | Phase 6 — The Interface | 1 — Accounts | Pending |
| PRV-05 | Phase 6 — The Interface | 1 — Accounts | Pending |
| PRV-06 | Phase 8 — Demo Proof, Export & Submission | 1 — Accounts | Pending |
| PRV-07 | Phase 8 — Demo Proof, Export & Submission | 1 — Accounts | Pending |
| JUR-01 | Phase 3 — New York End-to-End: The Anora Proof | 1 — Accounts | Complete |
| JUR-02 | Phase 5 — Curated Breadth & the Validation Loop | 1 — Accounts | Pending |
| JUR-03 | Phase 5 — Curated Breadth & the Validation Loop | 1 — Accounts | Pending |
| JUR-04 | Phase 5 — Curated Breadth & the Validation Loop | 1 — Accounts | Pending |
| JUR-05 | Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | Complete |
| AGT-01 | Phase 5 — Curated Breadth & the Validation Loop | 1 — Accounts | Pending |
| AGT-02 | Phase 5 — Curated Breadth & the Validation Loop | 1 — Accounts | Pending |
| AGT-03 | Phase 5 — Curated Breadth & the Validation Loop | 1 — Accounts | Pending |
| AGT-04 | Phase 5 — Curated Breadth & the Validation Loop | 1 — Accounts | Pending |
| AGT-05 | Phase 7 — Live Research, Caching & Durable Jobs | 1 — Accounts | Pending |
| AGT-06 | Phase 7 — Live Research, Caching & Durable Jobs | 1 — Accounts | Pending |
| AGT-07 | Phase 7 — Live Research, Caching & Durable Jobs | 1 — Accounts | Pending |
| AGT-08 | Phase 5 — Curated Breadth & the Validation Loop | 1 — Accounts | Pending |
| AGT-09 | Phase 5 — Curated Breadth & the Validation Loop | 1 — Accounts | Pending |
| AGT-10 | Phase 7 — Live Research, Caching & Durable Jobs | 1 — Accounts | Pending |
| AGT-11 | Phase 7 — Live Research, Caching & Durable Jobs | 1 — Accounts | Pending |
| UI-01 | Phase 6 — The Interface | 1 — Accounts | Pending |
| UI-02 | Phase 6 — The Interface | 1 — Accounts | Pending |
| UI-03 | Phase 6 — The Interface | 1 — Accounts | Pending |
| UI-04 | Phase 6 — The Interface | 1 — Accounts | Pending |
| UI-05 | Phase 6 — The Interface | 1 — Accounts | Pending |
| UI-06 | Phase 6 — The Interface | 1 — Accounts | Pending |
| UI-07 | Phase 8 — Demo Proof, Export & Submission | 1 — Accounts | Pending |
| UI-08 | Phase 6 — The Interface | 1 — Accounts | Pending |
| UI-09 | Phase 8 — Demo Proof, Export & Submission | 1 — Accounts | Pending |
| UI-10 | Phase 7 — Live Research, Caching & Durable Jobs | 1 — Accounts | Pending |
| UI-11 | Phase 6 — The Interface | 1 — Accounts | Pending |
| UI-12 | Phase 6 — The Interface | 1 — Accounts | Pending |
| SHP-01 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Pending |
| SHP-02 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Complete |
| SHP-03 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Complete |
| SHP-04 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Complete |
| SHP-05 | Phase 5 — Curated Breadth & the Validation Loop | 1 — Accounts | Pending |
| SHP-06 | Phase 7 — Live Research, Caching & Durable Jobs | 1 — Accounts | Pending |
| SHP-07 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Complete |
| SHP-08 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Complete |
| SHP-09 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Complete |
| SHP-10 | Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | Complete |
| SHP-11 | Phase 8 — Demo Proof, Export & Submission | 1 — Accounts | Pending |
| SHP-12 | Phase 8 — Demo Proof, Export & Submission | 1 — Accounts | Pending |
| SHP-13 | Phase 8 — Demo Proof, Export & Submission | 1 — Accounts | Pending |
| SHP-14 | Phase 3 — New York End-to-End: The Anora Proof | 1 — Accounts | Complete |
| DMO-01 | Phase 8 — Demo Proof, Export & Submission | 1 — Accounts | Pending |
| DMO-02 | Phase 8 — Demo Proof, Export & Submission | 1 — Accounts | Pending |
| DMO-03 | Phase 8 — Demo Proof, Export & Submission | 1 — Accounts | Pending |
| DMO-04 | Phase 8 — Demo Proof, Export & Submission | 1 — Accounts | Pending |
| IDX-01 | Phase 9 — Reference Production & Scheduled Index Runs | 2 — Balances | Pending |
| IDX-02 | Phase 9 — Reference Production & Scheduled Index Runs | 2 — Balances | Pending |
| IDX-03 | Phase 10 — The Published Index | 2 — Balances | Pending |
| IDX-04 | Phase 10 — The Published Index | 2 — Balances | Pending |
| IDX-05 | Phase 10 — The Published Index | 2 — Balances | Pending |
| IDX-06 | Phase 9 — Reference Production & Scheduled Index Runs | 2 — Balances | Pending |
| IDX-07 | Phase 10 — The Published Index | 2 — Balances | Pending |
| IDX-08 | Phase 10 — The Published Index | 2 — Balances | Pending |
| IDX-09 | Phase 10 — The Published Index | 2 — Balances | Pending |
| REV-01 | Phase 11 — Reverse Mode & Chart-of-Accounts Depth | 2 — Balances | Pending |
| DEP-01 | Phase 11 — Reverse Mode & Chart-of-Accounts Depth | 2 — Balances | Pending |

**Coverage:**

- v1 requirements: 88 total — **88 mapped, 0 unmapped ✓**
- v2 requirements: 11 total — **11 mapped, 0 unmapped ✓**
- Milestone 1 (Accounts) = Phases 1-8. Milestone 2 (Balances) = Phases 9-11, cuttable as a whole.

**Phase load:**

| Phase | Milestone | Requirements |
|-------|-----------|--------------|
| Phase 1 — Foundations: Source Truth & Deploy Path | 1 — Accounts | 13 |
| Phase 2 — Engine Spine & Incentive Interpreter | 1 — Accounts | 13 |
| Phase 3 — New York End-to-End: The Anora Proof | 1 — Accounts | 10 |
| Phase 4 — Cost Localization & Landed-Cost Outputs | 1 — Accounts | 13 |
| Phase 5 — Curated Breadth & the Validation Loop | 1 — Accounts | 10 |
| Phase 6 — The Interface | 1 — Accounts | 11 |
| Phase 7 — Live Research, Caching & Durable Jobs | 1 — Accounts | 7 |
| Phase 8 — Demo Proof, Export & Submission | 1 — Accounts | 11 |
| Phase 9 — Reference Production & Scheduled Index Runs | 2 — Balances | 3 |
| Phase 10 — The Published Index | 2 — Balances | 6 |
| Phase 11 — Reverse Mode & Chart-of-Accounts Depth | 2 — Balances | 2 |

---
*Requirements defined: 2026-08-24*
*Last updated: 2026-08-24 after roadmap creation*
