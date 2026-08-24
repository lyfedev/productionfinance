# ProductionFinance

## What This Is

A system that prices the same film production in every city a producer is considering, and reports the true landed cost of each — labour, housing, stages, equipment, travel, currency, and the production incentive net of audit fees, transfer discount, tax and timing. The headline output is the cost gap between two cities, decomposed into its components. A second mode runs the same engine on a fixed reference production, on a schedule, and publishes the result as a public index.

Primary user: a producer or line producer choosing where to shoot. Secondary: film commissions, unions, state economic development bodies and trade press — consumers of the published index.

## Core Value

Total landed cost of one identical production, priced per city, with every figure sourced, dated, and provably matching what a government actually paid.

## Business Context

- **Customer**: Producers and line producers making a location decision worth tens of millions; secondarily the institutions that cite the published index.
- **Revenue model**: Not monetized in this milestone set. Built as a hackathon submission; the public index is the top-of-funnel artifact if it is ever commercialized.
- **Success metric**: Mean error against government-disclosed award figures, across every production/award pair the validation loop has ingested.
- **Strategy notes**: `productionfinance-brief.md`, `idea-2-incentives.md`, `feasibility-incentives.md`, `hackathon-brief.md` (all in repo root)

## Milestones

Two milestones, both inside the hackathon window.

### Milestone 1 — Accounts (current)

The private calculator, end to end and hosted. Physical inputs plus a user-named city list produce total landed cost per city and the decomposed gap, every figure cited and dated. Four validated jurisdictions; any other city researched live at request time and labelled unvalidated. Both agentic jobs live here. **This is the hackathon submission** — it alone satisfies the hosted-URL Definition of Done.

### Milestone 2 — Balances (next)

The public index. The reference production priced across a fixed city set on a schedule, published with movement and a dated change log. Plus reverse mode: for a chosen city, what change would close its gap against the leader.

## Requirements

### Validated

(None yet — ship to validate)

### Active — Accounts

- [ ] Resolve open source questions before modelling: reconcile New York's annual cap ($700M vs $800M) at tax.ny.gov, confirm the Connecticut open-data CSV column headers, lock the 11 sourced production/award validation pairs
- [ ] Accept the seven physical inputs: production type and scale; shoot days split stage vs location; crew size or tier from which department ratios are inferred; principal cast count and how many imported; crew imported vs hired locally; start window by quarter; candidate cities named by the user
- [ ] Reject any budget figure as input — cost is computed per city, never supplied
- [ ] Localize one identical budget model against each city's local costs: union rate cards, GSA county per diem (US) and State Department foreign per diem, flights and housing for imported crew, stages, equipment, permits, trucking
- [ ] Compute the qualifying base under each jurisdiction's own definition — total local spend, labour only, lesser-of formulas, local-hires-only — including per-person ceilings and loan-out treatment
- [ ] Apply ceilings, tiers, caps and uplifts in the correct order per jurisdiction
- [ ] Convert gross incentive to net cash by mechanism: refundable credit, transferable credit sold at broker discount, taxable credit, direct rebate — and estimate when the cash actually arrives
- [ ] Distinguish eligibility from availability: whether a programme's annual allocation still has money in it is a separate question from whether the production qualifies
- [ ] Make start date change the result, through both incentive availability and seasonal cost variation
- [ ] Output total landed cost per candidate city, ranked
- [ ] Output the cost gap between any two cities, decomposed by component
- [ ] Carry a source link and date-checked on every figure
- [ ] Carry a confidence tier on every figure: validated or researched
- [ ] Curated validated models for four jurisdictions: New York, California, New Jersey, Connecticut
- [ ] Agent Job 1 — validation loop: ingest a published government disclosure, pull every production/award pair, re-run the model against each, report accuracy. Reproduce at least three published award figures exactly.
- [ ] Agent Job 2 — live research: a city with no curated model is entered, researched live via Parallel Search, priced, and labelled unvalidated. "No programme found" is an acceptable result.
- [ ] Hosted web UI that an anonymous visitor can use to price a described production across named cities
- [ ] Public repository with an OSI-approved license detectable in the About section
- [ ] Demo video, 3 minutes or under, showing the system functioning
- [ ] Written description covering features, technologies, data sources and findings

### Active — Balances

- [ ] Fixed reference production definition — the methodology, not a shortcut
- [ ] Reference production priced across a fixed city set on a schedule
- [ ] Published index with movement and a dated change log
- [ ] Reverse mode: for a chosen city, what change would close its gap against the leader
- [ ] Publish the running accuracy figure from the validation loop

### Out of Scope

- Ranking on headline incentive rate — it is what every existing tool does and it is wrong by 20 to 40 percent
- Accepting a budget figure as input — a dollar buys a different production in each city, which makes the comparison circular
- Recommending locations on creative or logistical suitability — the user names the cities; suggesting Budapest for a script needing the Pacific loses a film person's trust instantly
- Reporting sunset or expiry dates as a decision input — terms lock at application, so a future expiry does not affect a current production. Scheduled future improvements are in scope; expiries are not.
- Claiming live daily research as the product differentiator — rules change roughly annually per jurisdiction. Overclaiming freshness invites a judge to check and disprove it.
- Validated models for Georgia, New Mexico, Illinois, Louisiana, the UK or Canada — no per-production disclosure exists, so the validation loop cannot close. These are reachable via live research, labelled unvalidated.
- Ancillary economic-impact / ROI figures ("what LA recoups") — politically contested; industry-funded studies and independent state auditors disagree. Any such figure would have to expose its multiplier assumption on screen or it becomes advocacy.
- Non-union local labour rates — not public. That is what Entertainment Partners and Cast & Crew sell.

## Context

**No incentives API or bulk download exists anywhere in the world.** All rule data is unstructured government pages and PDFs. This is the structural reason live research is load-bearing rather than decorative — retrieval is not *a* solution here, it is the only one.

**Where the validation loop closes.** Per-production disclosure showing both qualified spend and credit issued exists in only four places: New York ESD quarterly reports (audited, gold standard), California Film Commission approved projects list (allocation stage), NJEDA activity reports (estimated), Connecticut open data CSV (the only actual CSV endpoint found). Nothing exists for Georgia, New Mexico, Illinois, Louisiana, the UK or Canada; Ireland publishes bands only. This is why the curated set is exactly these four — every curated model is provable against a government document.

**The anchor proof.** Anora, New York: $3,964,760 qualified spend produced a $991,190 credit issued. Ten further sourced pairs are in `feasibility-incentives.md` — Succession S4 ($102.9M → $25.7M), The Gilded Age S2 ($134.3M → $35.3M), Clueless reboot (CA, $46.5M → $16.3M), Joker (NJ, $6.1M → $1.96M) among them. Every competing tool says "estimated"; none can point at a government PDF and say we reproduce this exactly.

**Why naive arithmetic fails.** Georgia, $10M spend including a $2M W-2 lead: advertised 30% = $3M, but only $500K of the actor qualifies, so base $8.5M → $2.55M, minus a $25,000 audit fee, sold at ~88¢ — you bank ~$2.2M on an advertised $3M, twelve months later. The £18M UK example overstates by 44% (£9.54M naive vs £5.38M net). These are the demo's second beat.

**The hard part is normalization**, not research or arithmetic. Reconciling a dozen incompatible programmes into one common schema is real reasoning, done once per jurisdiction. Feasibility research names this explicitly as the real difficulty.

**Free and authoritative non-labour data.** GSA publishes US per diem by county (annual); State Department publishes foreign per diem (monthly). Together these cover the largest non-labour line. Union rate cards are published — IATSE locals, SAG-AFTRA, DGA, WGA, BECTU, ACTRA.

**Known competitor.** Wrapbook ships an AI incentives chatbot that self-discloses it "might hallucinate." The differentiator is not "AI answers incentive questions" — it is verified, cited, net-cash landed-cost modelling with a published validation record.

**Demo requirements** (from the brief, all four must be shown): open on validation, reproducing a published government award figure exactly with the government document alongside it; show a case where naive percentage arithmetic is badly wrong; show a ranking that inverts once net cash and timing are applied instead of headline rate; show a city with no curated model being researched live and priced, labelled unvalidated. Unlike the sibling animatic project, open city input is permitted and expected — it is the agentic demonstration.

**Judging.** Stage One is pass/fail viability, partly automated. Stage Two is four equally weighted criteria: Technological Implementation, Design, Potential Impact, Quality of the Idea — ties broken in that order, Technological Implementation first. The hackathon scorecard ranks "build a real interface" as the single biggest needle-mover because it scores Design and Impact simultaneously. A second cheap scoring move: every computed figure carries its reason as a string, converting a faith claim into an audited one.

**Note on the supplied material.** `hackathon-brief.md` states "Our track: IBM" and its scorecard concerns the sibling animatic project. For ProductionFinance the track is **Parallel**, per `productionfinance-brief.md` HARD CONSTRAINTS. Where the two disagree, `productionfinance-brief.md` governs.

## Constraints

- **Deadline**: Hackathon submission 2026-09-09, 14:00 PDT — 17 days from project start (2026-08-23). Both milestones must land inside it. Hard.
- **Partner track**: Parallel. Parallel's Search API must be called at runtime, via the official SDK or a supported integration.
- **AI services**: Google Cloud only, plus Parallel. No other AI models, agent frameworks or AI APIs — explicitly including AWS, Microsoft, OpenAI and Anthropic tools.
- **Language**: Google Cloud SDK must be imported and called at runtime. Accepted packages are `google-adk`, `google-genai`, `google-generativeai`, `google-cloud-aiplatform` — PyPI names, and eligibility screening is partly automated, so the agent and backend must be Python. Front-end language is unconstrained.
- **Deployment**: Must run on web. A hosted URL is required and must work for an anonymous visitor.
- **Licensing**: Public repository with an OSI-approved license detectable in the repository About section.
- **Provenance**: New code only, authored within the contest window (opened 2026-07-27). No extending prior work.
- **Hosting / infrastructure**: An existing AWS Lightsail instance is available and is the intended host. AWS may be used for any infrastructure resource needed — S3, RDS, CloudFront, EventBridge/cron, Secrets Manager. Permitted because the hackathon restricts AI services only; non-AI third-party services (hosting, databases, web frameworks, storage, schedulers) are explicitly unrestricted.
- **No AWS AI services — absolute**: Every AWS AI service is a Stage One disqualification. **AWS Textract is the specific trap on this project**: it parses government PDFs, which is exactly what the validation ingest does, so it is the most likely accidental violation. All PDF and document extraction must go through Gemini via a permitted Google package. Also forbidden: Bedrock (including Anthropic models hosted there), SageMaker, Comprehend, Rekognition, Transcribe, Polly, Translate, Kendra, Amazon Q. `boto3` itself is fine — what matters is which endpoints are called.
- **Honesty**: The repo is public and inspectable. Never fake progress; a `sleep()` behind a progress bar is a Stage One death. Never present a researched figure as validated.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Two milestones: Accounts (calculator) then Balances (public index) | Splits by artifact rather than by layer, so Accounts is independently submittable — it alone satisfies the hosted-URL Definition of Done | — Pending |
| Both milestones roadmapped now, tagged by milestone | 17 days to deadline; the whole critical path needs to be visible at once. Ship-gate at the Accounts/Balances boundary. | — Pending |
| Curated validated set is exactly NY, CA, NJ, CT | The only four jurisdictions with per-production disclosure, so every curated model is provable against a government document. Clears the three-reproduced-awards bar with margin. | — Pending |
| Both agent jobs in Accounts | Job 2 (live uncurated city) is Definition of Done #2 and a demo requirement; Job 1 (validation loop) is Definition of Done #3. Balances then reuses Job 1 on a schedule. | — Pending |
| Caching boundary: rules cached, availability live | Curated rules normalized once and stored. Live at query time: cap consumption, programme open/closed status, FX, and full research for uncurated cities. Matches the tiered-refresh half-life table and avoids overselling freshness. | — Pending |
| Reverse mode deferred to Balances | It is the policy-lever feature and its audience — legislators, film commissions, economic development bodies — is the index audience. Keeps Accounts focused on pricing correctly. | — Pending |
| Source verification is the first phase of Accounts | Opens the primary documents, reconciles the NY cap, confirms the CT CSV schema, and locks the validated pairs before any modelling. De-risks everything downstream. | — Pending |
| Accounts UI is the real map/slider/ranked-list treatment, not a form | Design is one of four equally weighted criteria and "build a real interface" is the top-ranked needle-mover in the scorecard. Cannot be allowed to drift into Balances. | — Pending |
| Host on the existing AWS Lightsail instance | Already provisioned and paid for; AWS is permitted for non-AI infrastructure. Removes the Google Cloud hosting question from the critical path. | — Pending |
| Stack otherwise decided by project research | Python backend is mandated; front end, map library and data layer left to STACK.md with current verified versions and rationale | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Business Context check — customer, revenue model, success metric still accurate?
4. Audit Out of Scope — reasons still valid?
5. Update Context with current state

---
*Last updated: 2026-08-23 after initialization*
