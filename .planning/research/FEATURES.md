# Feature Research

**Domain:** Film/TV production cost-estimation and incentive-comparison tools
**Researched:** 2026-08-23
**Confidence:** MEDIUM-HIGH (competitor feature claims sourced to vendor pages and third-party reviews, dated where the vendor discloses a date; no vendor discloses full methodology, so absence-of-feature claims are as reliable as public marketing pages get — an unadvertised enterprise tier at EP or Cast & Crew cannot be ruled out, consistent with the caveat already in `feasibility-incentives.md`)

This file does not re-derive jurisdiction rules, validation-pair data, or volatility findings — all of that is established in `feasibility-incentives.md` and `idea-2-incentives.md`. This file answers one question: **given the field that already exists, what features are expected, what would differentiate, what should be avoided, and what does the current requirement list miss.**

---

## 1. Competitive Survey

Every incumbent found is free, public, no-login, and funded as lead-generation for a payroll/production-accounting business (Wrapbook: payroll processing at ~$18/transaction per G2/Capterra; EP and Cast & Crew: payroll, residuals, and non-union rate-card data sold separately — the thing `feasibility-incentives.md` already names as "what EP and Cast & Crew sell"). None of them charges for the comparison tool itself. **The business model is identical across the whole field: the incentive tool is a funnel, not a product.** ProductionFinance has no funnel to protect, which is itself a positioning note, not a feature.

| Tool | What it lets a user do | Charges | Where it stops |
|---|---|---|---|
| **Entertainment Partners (EP)** — Incentives Map, Incentives Estimator, Jurisdiction Comparison ([ep.com/production-incentives](https://www.ep.com/production-incentives/)) | Browse a map of 120+ claimed jurisdictions (EP's own claim, not independently counted); run a US/Canada estimator; compare **up to 3 jurisdictions side by side** ([jurisdiction-comparison](https://www.ep.com/production-incentives/jurisdiction-comparison/)) showing rate, what qualifies, application deadlines, sunset dates, links to legislation | Free; lead-gen for EP payroll/finance services | Headline rate and eligibility only. No budget/landed-cost model, no net-cash conversion, no arrival timing, no per-figure source+date stamp on the comparison page itself (dates appear at page-metadata level, not per rule), no live research for uncurated jurisdictions |
| **Wrapbook** — State Map, Incentive Finder, Compare States, AI incentives chatbot ([wrapbook.com/production-incentives](https://www.wrapbook.com/production-incentives)) | Search/select states, view expandable per-state cards (spend %, ATL/BTL resident/non-resident rates, min spend, caps, loan-out/withholding, audit and screen-credit requirements, qualifying production types, film-office contact); ask a GPT-4-trained chatbot incentive questions | Free tool; Wrapbook's core business charges a payroll processing fee (~$18/transaction, no monthly fee) | The chatbot **self-discloses it "might generate or 'hallucinate' information that may not be accurate or exist in the original training data"** and Wrapbook's own fallback for complex questions is "chat with our in-house film incentives expert" — i.e., the vendor's own escape hatch from its AI tool is a human. Each state card does carry a "Last Updated Date" field, but staleness is uneven and disclosed rather than solved: sampled dates ranged from July 2026 (California) to October 2024 (Arkansas) at the same fetch |
| **Cast & Crew** — Incentives Map, Multi-Jurisdiction Comparison, TIP Guide PDF, Incentives Estimator ([castandcrew.com/services/financial-services](https://www.castandcrew.com/services/financial-services/)) | Rollover/click map, compare **up to 6 jurisdictions**, run "what-if" scenarios, download a periodically-republished TIP Guide PDF | Free; lead-gen for C&C payroll/accounting/finance services | Map is a JS-rendered widget — not independently fetchable/citable to a specific figure. Confirmed-stale artifact in the wild: their Canada incentives PDF is dated January 2020. No landed-cost or net-cash modeling; TIP Guide is a manually-refreshed PDF (editions found from 2015, 2016, 2017–18, 2024 — an annual-ish cadence, not live) |
| **Media Services** | — | — | **Retired.** Acquired by Cast & Crew in 2020; its incentive-database URL now 301-redirects to Cast & Crew's map (confirmed by fetch). Evidence this category consolidates into the payroll incumbents rather than sustaining an independent product |
| **ProdPro** ([prodpro.com](https://prodpro.com/)) | Daily-updated production-tracking/job-intelligence feed — "what's shooting where, who's hiring" | Subscription (industry-intel product) | **Not a comparable competitor.** It is a production-tracking database, not a budget or incentive tool. No incentive modeling, no comparison feature. Listed here to close it out, not to profile it further |
| **Film Incentive Solutions** | — | — | Could not confirm this exists as a distinct named product via web search (searches surfaced only adjacent generic results). Treat as **unconfirmed/low-signal** — do not build competitive strategy against a product that could not be verified |
| **Olsberg·SPI Global Incentives Index** ([o-spi.com](https://www.o-spi.com/projects/blog-global-incentives-index)) | Free PDF covering 121+ incentives (May 2025 edition), standardized fields per programme: type, rate, uplifts, caps, sunset dates, eligibility, updated **twice a year**, published via *World of Locations* magazine | Free PDF | It is a **directory, not a calculator.** No per-production computation, no landed cost, no net-cash conversion, no live query interface, no reproducibility claim against a government-disclosed figure. Best non-vendor global reference, worst-in-class for freshness (semi-annual, manual) |

### What is table stakes because every tool in the category has it

1. **Side-by-side multi-jurisdiction comparison UI** (EP: 3-way; Cast & Crew: 6-way; Wrapbook: unlimited cards). A tool in this category that can only show one city at a time will read as broken against user expectations set by every incumbent.
2. **Free, public, no-login access.** Every tool surveyed is open. Matches PROJECT.md's anonymous-visitor requirement already — no gap here.
3. **A downloadable/printable take-away artifact.** Cast & Crew's TIP Guide PDF and Wrapbook's per-state cards both exist because a producer needs something to save or forward, not just a page to read once. **This is the single clearest gap — see Section 3.**
4. **A per-jurisdiction "last updated" or date stamp**, however imperfectly executed (Wrapbook explicit; EP and Cast & Crew weaker). PROJECT.md's "source link and date-checked on every figure" already exceeds every incumbent's practice here — confirmed strength, not a gap.
5. **A fallback path for what the tool can't answer confidently.** Every incumbent has one — Wrapbook's is a named human expert; EP/Cast & Crew's is "talk to our advisors." ProductionFinance's equivalent is the "researched, not validated" label on Job 2's live-research output. This is structurally the same feature with a better trust story (a labeled, sourced answer instead of a phone-a-human punt) — worth stating explicitly as the intentional analogue, not a gap.
6. **An estimator that outputs a single number, not just a rate table.** EP and Cast & Crew both ship an "Incentives Estimator" precisely because "35%" is not what a producer wants — they want a dollar figure. ProductionFinance already does this correctly in shape (landed cost, not incentive %) — but the *expectation* that the tool always resolves to one concrete number is table stakes regardless of methodology, and the UI must never leave a user looking at a rate with no dollar figure attached.

---

## 2. What a Line Producer Actually Needs

**Budget structure.** Every industry-standard budget (Movie Magic Budgeting, Hot Budget, Showbiz Budgeting, and every template surveyed) uses the same three-tier chart of accounts: **Above-the-Line** (story/rights, producer, director, cast), **Below-the-Line** (production staff, extras, art/set construction, special effects, camera, sound, electrical, transportation, locations, wardrobe, makeup/hair, production film/lab, tests), and **Post-Production** (editing, music, post sound, post film/lab, titles), with **fringes** calculated either per-department or at the whole-budget level and displayed as their own line just above each section total ([Movie Magic Budgeting manual](https://mmb-docs.ep.com/Topsheet/Topsheet_Structure.html)). This is the mental model every line producer already has open in another window while evaluating a location.

**How the comparison actually gets made today.** There is no comparison *product* in active use by line producers — the workflow is manual: call vendors directly (camera houses, stage operators) for local quotes, build a Movie Magic or Hot Budget file per city by hand, and layer an incentive estimate from EP/Wrapbook/Cast & Crew's rate table on top, matched against known caps and cash-flow timing from experience. **The deliverable a line producer hands upward is a spreadsheet**, not a dashboard — this is consistent across every source found (Saturation.io, Topsheet.io, Filmustage, Jungle Software budgeting guides).

**What earns trust versus what gets dismissed.** Two signals recur:
- A figure a line producer can trace to a rate card or a call they could personally verify (a union scale rate, a per diem table, a stage day rate) is trusted; a figure presented only as a rolled-up total is not. This means citation needs to reach **line-item granularity**, not just a single citation on the headline number — PROJECT.md's "source link and date-checked on every figure" is already aimed at this, but the UI needs a drill-down path from the total down to each rate used, not merely a link on the final number.
- A tool that outputs in the shape a line producer already works in (ATL/BTL/Post, or at minimum department-level: labour, art, camera, transportation, locations) is legible immediately; a tool that outputs an unfamiliar taxonomy (e.g., "labour / housing / stage / incentive" as PROJECT.md's current example decomposition does) requires the producer to re-map it mentally before trusting it. This is a genuine but scoped gap — see Section 3.

---

## 3. Feature Gaps in the Current Plan

PROJECT.md's Active requirements for Accounts and Balances were read in full. The following are table-stakes-for-this-category features that are **absent** from both lists. Ranked by how directly they affect adoption/trust, with milestone assignment and complexity.

| # | Gap | Why it's table stakes here | Milestone | Complexity |
|---|---|---|---|---|
| 1 | **Export/share deliverable** — a PDF or spreadsheet a producer can hand to a studio or financier | Every incumbent ships a takeaway artifact (TIP Guide PDF, state cards). Every line-producer workflow terminates in a document handed upward, not a live dashboard someone else has to load. Currently nothing in PROJECT.md produces an artifact that leaves the browser. | Accounts | LOW–MEDIUM (render existing computed output + citations to PDF; no new modeling) |
| 2 | **Shareable/permalink URL that encodes a comparison's inputs** | Since Accounts deliberately has no login (anonymous-visitor DoD), there is no way to persist or hand off a specific comparison except screenshotting it. A URL that reconstructs the exact input vector is the cheapest possible substitute for save/auth and is the mechanism by which the export in gap #1 gets *sent* to someone else. | Accounts | LOW (encode inputs in query string; no persistence layer required) |
| 3 | **Assumptions panel — one consolidated, printable view of every rate used** in a given city's run (union scale rate, per-diem rate, FX rate, broker discount %, audit-fee tier, corporation-tax rate), each with its own source+date | PROJECT.md requires a source+date **per figure**, which is necessary but not sufficient — this is scattered across many clickable numbers. Every credible index reviewed in Section 5 (Case-Shiller, Big Mac Index, Tax Foundation) publishes a **consolidated** methodology/assumptions statement, not just inline citations. This is the single feature most directly responsible for a skeptical line producer (or a hackathon judge) trusting the number instead of spot-checking it. | Accounts | MEDIUM (aggregation of already-computed per-figure citations into one view; no new data) |
| 4 | **Sensitivity display** — show which single input, if changed, moves the landed-cost gap the most (e.g., "principal cast imported: 3→1 changes the gap by $X") | Distinct from Balances' reverse mode (which solves for what a *city* would need to change). This is about the *producer's own* input assumptions — the ones most likely to be soft guesses (crew tier, imported-cast count) at the point a producer is comparing cities. Nothing in PROJECT.md surfaces which input the answer is most sensitive to. Must **display a delta, not prescribe an action** — see anti-feature note in Section 5. | Accounts | MEDIUM (re-run the deterministic model with perturbed inputs — architecture already supports this since computation is per-city and deterministic) |
| 5 | **Multi-currency / dual-currency display toggle** | FX is load-bearing (Budapest, Prague, and London are named candidate cities in idea-2-incentives.md) yet PROJECT.md never mentions currency display. The UK worked example (£18M → £5.38M net) is denominated in GBP in the source document — showing only a USD-converted figure without a toggle to the government document's native currency weakens the exact-reproduction proof, because a judge checking the source PDF is checking a GBP figure, and the tool should show that figure before conversion. | Accounts | LOW (display concern; underlying FX rate is already a required live-cached data point per idea-2's tiered-refresh table) |
| 6 | **Per-department cost breakdown aligned to ATL/BTL/Post** (or at minimum: labour, art/construction, camera, transportation, locations) rather than only the current four-component decomposition (labour, housing/per diem, stage, incentive) | Section 2's finding: a line producer's trust model is built around the standard chart of accounts. A breakdown in an unfamiliar taxonomy requires manual re-mapping before it's usable. This is a differentiator-strength gap, not a hard blocker — the current four-component split is defensible for a hackathon demo, but a producer audience will ask "where's art department, where's transportation" the first time they compare it to their own top sheet. | Accounts (stretch) / Balances (full) | MEDIUM–HIGH (requires inferring department-level ratios from the crew-tier input, which idea-2-incentives.md already gestures at for crew size but doesn't extend to full department cost distribution) |
| 7 | **Persistent, linkable "How we compute this" methodology page**, distinct from the hackathon written-description DoD artifact | DoD item #6 ("written description covering features, technologies, data sources and findings") is a **submission** artifact, not an in-product page a producer or judge lands on later. Every credible index reviewed in Section 5 has a standing, URL-addressable methodology page. Nothing in Accounts' requirements creates one inside the hosted product itself. | Accounts | LOW (mostly a static page assembled from already-required content: input schema, jurisdiction list, confidence-tier definitions, refresh cadence) |
| 8 | **Visible validation-loop accuracy figure inside Accounts**, not only as a Balances feature | Job 1 (the validation loop) runs *in Accounts* per PROJECT.md's own Key Decisions table, and reproducing published award figures is Demo Requirement #1 — the single most credibility-bearing thing the product does. But "publish the running accuracy figure" is currently listed only under Balances' Active requirements. If Accounts (the actual hackathon submission) doesn't surface its own accuracy number on its own hosted page, the strongest asset is invisible to anyone who only sees the Accounts URL. | Accounts | LOW (surface a number Job 1 already computes; no new computation) |
| 9 | **"What changed since I last looked" for a shared/linked scenario** | PROJECT.md has this shape only for the public index (Balances' dated change log). If gap #2 (shareable URL) is built, a cheap diff — "this figure was $X when you last checked, now $Y, because [jurisdiction] changed on [date]" — reinforces the freshness message without overclaiming daily research, matching the already-adopted "sell breadth and normalization, not velocity" positioning. | Accounts (depends on gap #2) | LOW, contingent on gap #2 existing first |

**Highest-value flags for the roadmap:** gaps #1, #3, and #8 are the cheapest and most load-bearing — they turn already-computed data into a trust-building artifact with no new modeling work, and their absence is the most likely reason a judge or producer would distrust an otherwise-correct number.

---

## 4. The Proof/Credibility Feature Set

Surveyed patterns from data products whose entire value proposition is "trust this number": S&P/Case-Shiller, The Economist's Big Mac Index, Numbeo, the Tax Foundation's State Tax Competitiveness Index, and FiveThirtyEight's "Checking Our Work" transparency practice.

| Pattern | Where seen | Applicability to ProductionFinance |
|---|---|---|
| **Full published methodology document**, versioned, with explicit "no methodological changes this year" or a changelog of what changed | Case-Shiller (S&P methodology PDF); Tax Foundation ("no methodological changes were adopted between the 2025 and 2026 editions... apply retroactively for apples-to-apples") | Already partially covered by Balances' "fixed reference production definition — the methodology, not a shortcut." **Gap #7 extends this into Accounts.** |
| **Open, versioned raw-data downloads per release**, tagged and diffable | Big Mac Index's GitHub repo — every release ships CSV/Excel with the calculation code alongside it | Not present anywhere in PROJECT.md. Recommend a CSV/JSON export of the Balances index history as a Balances feature (see Section 6) |
| **Per-metric data-recency/confidence labeling**, with an explicit fallback rule when fresh data is thin (Numbeo: 12 months default, up to 24 months for low-sample cities, disclosed as such) | Numbeo | Directly validates PROJECT.md's existing two-tier confidence system (validated/researched) as the right shape — no change needed, but the UI should state the fallback rule (what triggers "researched" vs "validated") as plainly as Numbeo states its recency window |
| **"Checking Our Work"** — a standing, dedicated page that shows forecast/estimate accuracy against realized outcomes, treated as core brand content rather than a footnote | FiveThirtyEight | This is the closest existing pattern to what PROJECT.md's validation loop already does (reproduce government-disclosed awards, report mean error). **Gap #8 is exactly this pattern, currently missing its Accounts-side surface.** |
| **Side-by-side reproduction against a named external document** | Not found in any competitor surveyed — none of EP, Cast & Crew, Wrapbook, or Olsberg·SPI make a to-the-dollar reproduction claim against a government-published figure | This is ProductionFinance's strongest, most unique pattern and has **no incumbent precedent to copy** — it exceeds every pattern found elsewhere in the survey, including FiveThirtyEight's own practice (which shows calibration, not exact reproduction). The Anora proof panel described in idea-2-incentives.md is already the correct shape; the recommendation is to make sure the government PDF itself is embedded or one click away, not merely cited by URL, since "here is the actual page" is stronger than "here is a link to the page." |

**The strongest concrete presentation pattern, synthesized:** a permanent, linkable proof panel per validated jurisdiction showing (a) the input the government document discloses (e.g., Anora's $3,964,760 qualified spend), (b) the tool's computed output next to the government's disclosed output side by side, (c) a link to *and* a rendered excerpt of the source PDF, and (d) the date the figure was last reconciled. This out-does every incumbent because none of them make a reproduction claim at all — the bar to clear is near-zero, which is also why it should not be diluted by also trying to claim daily freshness (already correctly avoided per PROJECT.md's Out of Scope list).

---

## 5. Anti-Features

PROJECT.md already excludes: headline-rate ranking, budget as input, creative/location suitability, sunset dates as a decision input, "live daily research" as the differentiator, uncurated validated models for GA/NM/IL/LA/UK/Canada, ancillary ROI/economic-impact multipliers, and non-union local labour rates. The following are **additional** traps specific to this category, found during this research pass and not already covered.

| Anti-Feature | Why it looks attractive | Why it's a trap here | Do instead |
|---|---|---|---|
| **A conversational Q&A chatbot as the primary interface** | Wrapbook already normalized the idea that "ask it a question about incentives" is a reasonable product shape, and it feels modern | This is precisely Wrapbook's self-disclosed liability ("might hallucinate"), and PROJECT.md's own differentiator language explicitly rejects "AI answers incentive questions" as the value prop. A chat surface on top of Job 1/Job 2 output would re-introduce exactly the trust problem the validation loop exists to solve, even if the underlying computation is correct — a chat box reads as "ask an AI," not "check our work" | Render Job 1 and Job 2 output as structured, cited, inspectable results only. If a natural-language input box is wanted for the physical-input intake, keep it strictly as a form-filling assist, never as the channel that returns the final dollar figure. |
| **Chasing a large jurisdiction-count claim** ("we cover 100+ jurisdictions") as a headline stat | EP claims 120+, Olsberg·SPI claims 121 — it reads as comprehensive and is easy to say | It's an unverifiable, unearned claim exactly like the ones this project is positioned against ("every competing tool says 'estimated'"). A large uncurated-jurisdiction count with no validation is the same overclaim structure as a headline incentive rate — impressive-sounding and checkable-and-disprovable by a judge who picks one at random | Lead with the **smaller, provable** number: 4 curated jurisdictions, N reproduced government awards, X% mean error. Depth and proof over breadth — this is already the project's stated differentiator; make sure no UI element undercuts it by foregrounding a raw jurisdiction count instead. |
| **Opaque, JS-rendered comparison widgets that can't be linked to or cited at the figure level** | Fast to build with a client-side map/chart library, looks polished | Cast & Crew's map is exactly this — not independently fetchable, not citable to a specific number, effectively un-auditable from outside. It is the structural opposite of "every number clickable." | Every displayed figure must be a server-rendered, individually addressable value with its own citation — this is already the design intent per idea-2-incentives.md ("every number clickable → the rule, the source, the date checked"); flagging here only as an explicit thing to avoid regressing into for UI polish reasons. |
| **A downloadable bulk export of the full underlying incentive ruleset** (as opposed to the reference-production index results) | Feels generous — "give away the data nobody else publishes," reinforcing the "no API exists anywhere" moat narrative | It would be re-scraped and rehosted immediately with the validation-loop provenance stripped off, handing away the actual differentiator (the computation and its proof) for nothing in return. It's also the exact unadvertised product EP/Cast & Crew are speculated to gatekeep behind an enterprise sales conversation — building it for free undercuts nothing of theirs and gives away everything of ours. | Publish only the **computed index results** (Balances' reference-production output, per Section 6) as a versioned download — never the raw normalized rule corpus itself. |
| **Sensitivity analysis that prescribes an action** ("move 2 roles to local hire to save $400K") rather than only displaying a delta | Feels like a natural next step once sensitivity display (gap #4) exists, and producers would probably want the advice | This slides into exactly the "recommending on suitability" territory PROJECT.md already excludes for creative/logistical reasons — an input-level recommendation ("hire locally instead of importing") is a casting/staffing recommendation, not a landed-cost figure, and invites the same trust break as suggesting Budapest for a Pacific-set script | Show the delta only: "this input, if changed, moves the gap by $X." Never phrase it as a recommendation to change the production. |
| **A live-updating "as of right now" cap-consumption ticker** presented without the caching-boundary caveat | Feels like a strong freshness demo — "watch the number change in real time" | PROJECT.md's own caching boundary explicitly scopes what's live (cap consumption, programme status, FX) vs. cached (curated rules) — a UI element that implies everything is live-refreshed at page-load frequency overclaims exactly the freshness story the project has deliberately chosen not to sell, and a judge who refreshes the page twice in a row and sees no change will notice the gap between implication and reality | Show a "checked as of [date/time]" stamp on live-fetched data points (cap status, FX), consistent with the source+date requirement already in place — don't imply continuous polling if the underlying refresh cadence is daily/weekly, per the tiered-refresh table in idea-2-incentives.md. |

---

## 6. Public Index Features (Balances milestone)

Comparable published indices surveyed: S&P/Case-Shiller, The Economist's Big Mac Index, Numbeo Cost of Living, Tax Foundation's State Tax Competitiveness Index. (ITEP and RIAA/Nielsen-style reports were searched but did not surface material beyond what the four above already establish; not profiled separately to avoid padding.)

| Feature | Precedent | Currently in PROJECT.md (Balances)? | Recommendation |
|---|---|---|---|
| Methodology page, versioned | Case-Shiller (S&P PDF); Tax Foundation (explicit "no changes this year" note, retroactive apples-to-apples) | Partially — "fixed reference production definition — the methodology, not a shortcut" | Make the methodology a standing, linkable page with an explicit changelog of what changed release-over-release |
| Versioned raw-data download (CSV/JSON) | Big Mac Index — every GitHub release ships the CSV *and* the calculation code | **Absent.** PROJECT.md's "movement and a dated change log" implies a UI feed, not a downloadable dataset | Add a CSV/JSON export of the index history per scheduled run — this is the single feature most responsible for a dataset becoming citable by journalists/researchers rather than just readable |
| Movement/delta display | Case-Shiller (month-over-month, base-period-indexed); Big Mac Index (raw vs. GDP-adjusted) | Present — "published index with movement" | Covered |
| Dated change log | All four | Present | Covered |
| Permanent URL per data point/period | Big Mac Index (tagged GitHub releases); Tax Foundation (one persistent doc URL per year's edition) | **Absent.** No permalink/URL structure specified for periodic runs | Recommend a stable URL per scheduled run (e.g., a dated or quarter-stamped path) so trade press and film commissions can cite a specific figure permanently, not just "the current homepage number" |
| Press-ready auto-generated one-liner summarizing the period's movement | Not explicitly found in any surveyed index as an automated feature, but is exactly the framing idea-2-incentives.md already wants ("a daily 'why is everyone leaving town' number") | **Absent as a stated feature.** The positioning exists in strategy docs but isn't listed as a UI requirement | Cheap given the deltas are already computed: auto-generate a one-sentence summary per run (e.g., "Los Angeles fell to #4 this quarter as [state]'s uncapped credit widened the gap by $X") — this is what a journalist would quote directly |
| Confidence/recency labeling per data point | Numbeo (12–24 month recency window, disclosed) | Present via validated/researched tiers | Covered — no incumbent goes further than this |
| Embeddable widget | Not confirmed as a strong pattern in any of the four surveyed indices | Absent | Low priority — do not invest here; no evidence it drives citability in this category |

---

## Feature Dependencies

```
Assumptions Panel (gap #3)
    └──requires──> Per-figure source+date citation (already in PROJECT.md, Accounts)

Shareable/permalink URL (gap #2)
    └──enables──> Export/share PDF deliverable (gap #1)
    └──enables──> "What changed since I last looked" (gap #9)

Sensitivity display (gap #4)
    └──requires──> Deterministic per-city recomputation (already architected, per idea-2-incentives.md)

Visible validation-loop accuracy in Accounts (gap #8)
    └──requires──> Agent Job 1 — validation loop (already Active, Accounts)

Per-department (ATL/BTL/Post) breakdown (gap #6)
    └──requires──> Department-ratio inference from crew tier (partially implied by existing "crew size or tier... department ratios inferred" requirement — needs to be extended from a ratio input assumption into an output-level breakdown)

Public index versioned CSV/JSON download (Section 6)
    └──requires──> Reference production priced on a schedule (already Active, Balances)

Permanent URL per index run (Section 6)
    └──enhances──> Public index versioned download (citability compounds when both exist together)

Press-ready one-liner (Section 6)
    └──requires──> Movement/delta computation (already Active, Balances)

Conversational chatbot interface [ANTI-FEATURE]
    └──conflicts with──> Per-figure citation/proof panel (a chat answer cannot carry the same auditable citation structure as a rendered figure)
```

### Dependency Notes

- **Assumptions panel requires per-figure citation:** the panel is an aggregation view over data the per-figure citation requirement already produces — no new sourcing work, only a new consolidated presentation of existing sourced figures.
- **Shareable URL enables export and "what changed":** without a way to address a specific comparison by URL, there is nothing to export *to* someone else or diff against a prior visit. Build the URL scheme first; export and diff follow cheaply.
- **Sensitivity display requires deterministic recomputation:** the model is already deterministic math per city (per idea-2-incentives.md's "delete the agent, what's left" analysis), so perturbing one input and re-running is architecturally free — this is a UI/orchestration feature, not a new modeling capability.
- **Per-department breakdown requires extending an existing assumption, not adding a new one:** PROJECT.md already infers department ratios from crew tier as an *input-side* mechanism; turning that into an *output-side* per-department cost line is a scope extension of an already-planned capability, not a new one.

---

## MVP Definition

### Launch With (Accounts, v1 — the hackathon submission)

- [ ] Export/share PDF of a computed comparison (gap #1) — essential because the category's table-stakes deliverable is a document a producer can hand upward, and none exists otherwise
- [ ] Shareable permalink URL encoding comparison inputs (gap #2) — essential as the cheapest possible stand-in for save/auth given the no-login constraint, and a prerequisite for the export above actually reaching anyone
- [ ] Consolidated assumptions panel (gap #3) — essential for the credibility case; costs nothing new to compute, only to present
- [ ] Visible validation-loop accuracy figure surfaced on the Accounts hosted page itself (gap #8) — essential because Accounts alone satisfies the hosted-URL Definition of Done, and this is the single strongest credibility asset the product has

### Add After Validation (Accounts, v1.x)

- [ ] Sensitivity display for physical-input assumptions (gap #4) — add once the core landed-cost computation is proven correct; this is a UI layer on top of an already-deterministic model
- [ ] Multi-currency display toggle (gap #5) — add once international candidate cities (Budapest, Prague, London) are actually in the demo path; trivial once FX is already a live-cached data point
- [ ] Persistent methodology page inside the product (gap #7) — add once the DoD written-description content exists, since it is largely a repackaging of that same content into a linkable in-product page

### Future Consideration (Balances / v2+)

- [ ] Per-department (ATL/BTL/Post-aligned) cost breakdown (gap #6) — defer; requires extending the department-ratio inference from an input assumption into a full output breakdown, and the current four-component decomposition is defensible for the hackathon demo
- [ ] Public index versioned CSV/JSON download (Section 6) — natural Balances feature once the reference production is running on a schedule
- [ ] Permanent URL per index run (Section 6) — pairs with the download above
- [ ] Press-ready auto-generated one-liner per index period (Section 6) — cheap once movement/delta is computed, but not required for the Accounts submission
- [ ] "What changed since I last looked" diff for a shared scenario (gap #9) — depends on gap #2 existing and is lower priority than the index-level change log, which is already Active for Balances

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---|---|---|---|
| Export/share PDF (gap #1) | HIGH | LOW–MEDIUM | P1 |
| Shareable permalink URL (gap #2) | HIGH | LOW | P1 |
| Assumptions panel (gap #3) | HIGH | MEDIUM | P1 |
| Visible validation accuracy in Accounts (gap #8) | HIGH | LOW | P1 |
| Sensitivity display (gap #4) | MEDIUM | MEDIUM | P2 |
| Multi-currency toggle (gap #5) | MEDIUM | LOW | P2 |
| Persistent methodology page (gap #7) | MEDIUM | LOW | P2 |
| "What changed since I last looked" (gap #9) | LOW–MEDIUM | LOW (contingent) | P2 |
| Per-department breakdown (gap #6) | MEDIUM | MEDIUM–HIGH | P3 |
| Public index CSV/JSON download | MEDIUM | LOW | P2 (Balances) |
| Permanent URL per index run | MEDIUM | LOW | P2 (Balances) |
| Press-ready one-liner | LOW–MEDIUM | LOW | P3 (Balances) |
| Embeddable widget | LOW | MEDIUM | P3 (not recommended — no evidence of payoff) |

**Priority key:**
- P1: Must have for launch (Accounts hackathon submission)
- P2: Should have, add when possible within the 17-day window
- P3: Nice to have, future consideration (Balances or post-hackathon)

---

## Competitor Feature Analysis

| Feature | EP | Cast & Crew | Wrapbook | ProductionFinance's approach |
|---|---|---|---|---|
| Jurisdiction comparison | Up to 3 side by side | Up to 6 side by side | Unlimited cards | Cities named by the user, unlimited — already exceeds the field |
| Output shape | Headline rate + estimator dollar figure | Headline rate + estimator dollar figure | Headline rate | Total landed cost (not incentive size) — the category's only tool computing this |
| Net cash / timing | Not modeled | Not modeled | Not modeled | Modeled explicitly (mechanism, discount, tax, arrival timing) — no incumbent does this at all |
| Proof against a government-disclosed figure | None | None | None | Core differentiator — no incumbent precedent found anywhere in this survey |
| Fallback for unknown/uncurated cases | Phone/contact an advisor | Phone/contact an advisor | Named human expert (chatbot's own escape hatch) | Labeled live research ("researched, not validated") — same function, stronger trust story |
| Takeaway artifact | None found (web-only) | Downloadable TIP Guide PDF (static, annual-ish) | Per-state cards (no combined export found) | **Gap #1** — recommend building this; no incumbent's version is comparison-specific or up to date |
| Confidence/freshness labeling | Page metadata only | Page metadata only | Explicit "Last Updated Date" per state, uneven | Two-tier validated/researched system — already ahead of the field |

---

## Sources

- [Entertainment Partners — Jurisdiction Comparison Tool](https://www.ep.com/production-incentives/jurisdiction-comparison/)
- [Entertainment Partners — Incentives Estimator](https://www.ep.com/production-incentives/incentives-estimator/)
- [Entertainment Partners — Production Incentives hub](https://www.ep.com/production-incentives/)
- [Wrapbook — Compare States](https://www.wrapbook.com/production-incentives/compare-states)
- [Wrapbook — AI Production Incentives Tool](https://www.wrapbook.com/production-incentives/ai-production-incentives-tool)
- [Wrapbook — Production Incentive Center](https://www.wrapbook.com/production-incentives)
- [Cast & Crew — Incentives Map and Comparison Tool](https://castandcrew.com/production-incentive-map-us)
- [Cast & Crew — 2024 TIP Guide PDF](https://www.castandcrew.com/wp-content/uploads/2024/03/2024-TIP-GUIDE.pdf)
- [ProdPro](https://prodpro.com/)
- [Olsberg·SPI — Global Incentives Index, May 2025 update](https://www.o-spi.com/news/incentive-index-may-2025)
- [Movie Magic Budgeting — Topsheet Structure manual](https://mmb-docs.ep.com/Topsheet/Topsheet_Structure.html)
- [Saturation.io — Film Budget Top Sheet / Breakdown by Department](https://saturation.io/blog/film-budget-top-sheet)
- [Topsheet.io — Budget Like a Line Producer](https://www.topsheet.io/blog/budget-like-a-line-producer)
- [S&P/Cotality Case-Shiller Home Price Indices methodology](https://www.spglobal.com/spdji/tc/documents/methodologies/methodology-sp-cotality-cs-home-price-indices.pdf)
- [The Economist's Big Mac Index — GitHub data and methodology repo](https://github.com/TheEconomist/big-mac-data)
- [Numbeo — Understanding Cost of Living Indexes](https://www.numbeo.com/cost-of-living/cpi_explained.jsp)
- [Numbeo — Methodology and Motivation](https://www.numbeo.com/common/motivation_and_methodology.jsp)
- [Tax Foundation — 2026 State Tax Competitiveness Index](https://taxfoundation.org/research/all/state/2026-state-tax-competitiveness-index/)
- [FiveThirtyEight's Open Data Initiatives — Data Journalism Awards profile](https://datajournalismawards.org/projects/fivethirtyeights-open-data-intiatives/)
- Internal: `/Volumes/VM3/vockelldev/cinemachallenge/prodfin/.planning/PROJECT.md`, `idea-2-incentives.md`, `feasibility-incentives.md`, `productionfinance-brief.md` (required reading, not re-derived)

---
*Feature research for: Film/TV production cost-estimation and incentive-comparison tools*
*Researched: 2026-08-23*
