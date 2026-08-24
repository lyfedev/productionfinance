# ProductionFinance — project brief

Brief, not a spec. Write the spec before building.

---

## WHAT TO BUILD

A system that prices the same film production in every city a producer is considering, and reports the true landed cost of each: labour, housing, stages, equipment, travel, currency, and the production incentive net of fees, discounts, tax and timing.

Output is total cost, not incentive size. The headline output is the cost gap between two cities, broken down into its components.

A second mode runs the same engine on a fixed reference production, on a schedule, and publishes the result as a public index.

## USERS

Primary: a producer or line producer choosing where to shoot.
Secondary: film commissions, unions, state economic development bodies, trade press — consumers of the published index.

## INPUTS

1. Production type and scale
2. Shoot days, split between stage and location
3. Crew size, or a tier from which department ratios are inferred
4. Principal cast count, and how many are imported
5. Crew imported versus hired locally
6. Start window, by quarter
7. Candidate cities — the user names them

No budget figure is accepted as input. Cost is an output, computed per city.

## OUTPUTS

- Total landed cost per candidate city
- Incentive value net of audit fees, transfer discount and corporation tax, plus when the cash actually arrives
- Cost gap between any two cities, decomposed by component
- Every figure carries a source link and the date it was checked
- Every figure carries a confidence tier: validated or researched
- Reverse mode: for a chosen city, what change would close its gap against the leader
- Published index: the reference production priced across a fixed city set, on a schedule, with movement and a dated change log

## REQUIRED BEHAVIOUR

- Prices one identical production across all candidate cities. Comparison is only valid against a common budget model, not against published rates.
- Distinguishes eligibility from availability. Whether a programme's annual allocation still has money in it is a separate question from whether the production qualifies, and it changes the answer.
- Models net cash and arrival timing. A refundable credit, a transferable credit sold at a discount, a taxable credit, and a direct rebate are not equivalent at the same headline percentage.
- Start date changes the result, through both incentive availability and seasonal cost variation.
- Two confidence tiers. A curated set of jurisdictions with models validated against published government awards, and any other city researched live at request time and labelled as unvalidated.
- Continuous validation. When a government publishes a new disclosure report, ingest it, re-run the model against every production/award pair in it, and report accuracy. Drift against new disclosures is the detection mechanism for rules that changed without notice.

## HARD CONSTRAINTS

*(Apply if submitted to the Agentic Cinema hackathon. See `hackathon-brief.md`.)*

- Submission deadline: 2026-09-09, 14:00 PDT.
- Partner track is Parallel. Parallel's Search API must be called at runtime, via the official SDK or a supported integration.
- AI services: Google Cloud only, plus Parallel. No other AI models, agent frameworks or AI APIs. Non-AI third-party services are unrestricted.
- Google Cloud SDK imported and called at runtime. Accepted packages: `google-adk`, `google-genai`, `google-generativeai`, `google-cloud-aiplatform`. These are PyPI names and eligibility screening is partly automated, so the agent and backend must be Python. Front end language is unconstrained.
- Must run on web. A hosted URL is required and must work for an anonymous visitor.
- Public repository with an OSI-approved license detectable in the repository About section.
- New code only, authored within the contest window (opened 2026-07-27).

## DEMO REQUIREMENTS

- Open on validation. Reproduce a published government award figure exactly, and show the government document alongside it. Anora, New York: $3,964,760 qualified spend produced a $991,190 credit issued. Ten further sourced pairs are in `feasibility-incentives.md`.
- Show a case where naive percentage arithmetic is badly wrong. The £18M UK example overstates by 44%.
- Show a ranking that inverts once net cash and timing are applied instead of headline rate.
- Show a city the system has no curated model for being researched live and priced, labelled as unvalidated.
- Unlike the animatic project, open city input is permitted and expected. It is the agentic demonstration. "No programme found" is an acceptable result.

## KNOWN DATA SOURCES

No incentives API or bulk download exists anywhere. All rule data is unstructured government pages and PDFs.

- Rules: government film office sites are the only authority. NCSL index is stale — use as a link directory only. Olsberg·SPI Global Incentives Index, free PDF.
- Validation, both sides published: New York ESD quarterly reports (audited, gold standard), California Film Commission approved projects list (allocation stage), NJEDA activity reports (estimated), Connecticut open data CSV.
- No per-production disclosure exists for Georgia, New Mexico, Illinois, Louisiana, the UK or Canada. Ireland publishes bands only.
- Labour: published union rate cards — IATSE locals, SAG-AFTRA, DGA, WGA, BECTU, ACTRA. Non-union local rates are not public.
- Housing and meals: GSA per diem by US county, annual. State Department foreign per diem, monthly. Both free and authoritative.
- Stage, equipment, permit and location fees: often published by facilities and film offices.

## NON-GOALS

Do not build these. They are excluded deliberately.

- Ranking on headline incentive rate. It is what every existing tool does and it is wrong by 20 to 40 percent.
- Accepting a budget figure as an input. A dollar buys a different production in each city, which makes the comparison circular.
- Recommending locations on creative or logistical suitability. The user names the cities.
- Reporting sunset or expiry dates as a decision input. Terms lock at application, so a future expiry does not affect a current production. Scheduled future improvements are in scope; expiries are not.
- Claiming live daily research as the product differentiator. Rules change roughly annually per jurisdiction. Match refresh cadence to each data type's actual volatility.

## SUPPLIED MATERIAL

- `feasibility-incentives.md` — source research, roughly 40 primary sources, 11 validated production/award pairs, worked examples, per-jurisdiction rule detail
- `idea-2-incentives.md` — product decisions already made, UX, scoring analysis, primer on how incentives work
- `hackathon-brief.md` — competition rules and submission requirements

## DEFINITION OF DONE

1. Hosted URL prices a described production across named cities and returns total landed cost, decomposed gap, and cited figures.
2. A city with no curated model can be entered and is researched live, labelled unvalidated.
3. The validation loop reproduces at least three published government award figures.
4. Repository is public, licensed, and runs from its own instructions.
5. Demo video, 3 minutes or under, showing the system functioning.
6. Written description covering features, technologies, data sources, and findings.

## OPEN DATA QUESTIONS TO RESOLVE BEFORE BUILDING

- New York's current annual cap is reported at both $700M and $800M. Reconcile at tax.ny.gov.
- Georgia loan-out withholding rate is cited at both 4.99% and 5.75%.
- New Mexico HB 237, a proposed repeal of the state film incentive, outcome unknown.
- Connecticut open data CSV column headers unverified.
- Ireland Section 481 CSV — confirm whether all rows are banded or some carry exact figures.
