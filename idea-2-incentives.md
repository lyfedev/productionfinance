# Idea 2 — the production cost & incentive engine

*Worked 2026-08-22. Research backing: `feasibility-incentives.md` (334 lines, ~40 primary sources).*
*Partner fit: **Parallel** (live research over unstructured government sources — no API exists anywhere).*

---

## THE 30 SECONDS

> A fifty-million-dollar film can shoot in Atlanta, Toronto, Prague or Budapest. Pick right and a government hands you fifteen million back. Pick wrong and you leave eight million on the table.
>
> The rules live in a hundred different governments, change constantly, and the advertised percentage is never what you actually get.
>
> Describe your production. It prices the same movie in every city you're considering — labour, hotels, stages, travel, and the incentive — and tells you what it actually costs.
>
> Then it shows you the same number the New York government published, and they match to the dollar.

**Positioning (Dave):** *"we do hard work to support important decisions"* and *"we give Hollywood a daily 'why is everyone leaving town' number."*

---

## TWO ARTIFACTS, ONE ENGINE

**The index** — public. The engine run daily on a fixed **reference production**, published as a ranked number with movement and a "why it changed" feed. This is the runaway-production story with arithmetic under it. Audience: film commissions, IATSE, state economic development, trade press, legislators — people who *cite* numbers.

**The calculator** — private. Same engine, your production instead of the reference one.

The reference production isn't a shortcut, it's the **methodology**: you can't compare rates, you have to push one identical budget through every jurisdiction's rules.

---

## HOW INCENTIVES ACTUALLY WORK

*(Primer — everything complicated comes from two words: what "qualifies," and how they "give it back.")*

### The base — never your whole budget
- **Total local spend** — Georgia
- **Labour only** — Ontario
- **Lesser of 80% of core spend, or actual local spend** — UK
- **Local hires only** — many programs exclude anyone flown in

Plus per-person ceilings. Georgia: a $2M W-2 lead actor contributes only **$500K** to the base. Paid through a loan-out company, the full $2M counts. *Same dollar, different base, decided by a payroll structuring choice.*

### Four payout mechanisms, not worth the same
| Mechanism | What happens | Real value |
|---|---|---|
| **Refundable credit** | Production owes no local tax, state cuts a cheque | Full value, but delayed — New Mexico can be a year out, no interest |
| **Transferable credit** | You can't use it, so you **sell** it to a local taxpayer via broker | Georgia's 30% sells at ~85–92¢ → ~26%, minus a $25,000 audit fee at the $10M tier |
| **Rebate / grant** | Direct cash from a fund, outside the tax system | Simplest — but funds run dry (Czech, March 2026) |
| **Non-refundable** | Only offsets tax you owe there | Usually worthless to a production |

**And some are taxable.** UK's 34%/53% are income to the company — 25.5%/39.75% after corporation tax.

### Why the headline always lies
Georgia, $10M spend including a $2M W-2 lead. Advertised 30% = $3M. Only $500K of the actor qualifies → base $8.5M → $2.55M. Minus the audit fee, sold at 88¢. **You bank ~$2.2M on an advertised $3M, twelve months later.**

UK, £18M film: naive £9.54M → correct £5.38M net. **44% overstatement.**

### Caps — the part nobody models
**Per-project** (max any one film gets) and **annual programme** (total handed out that year, usually first-come). When the annual pot empties the terms are still perfect and the answer is still zero. Czech: unchanged rules, fund exhausted March 2026, reopened September 2026.

**"What are the rules" and "is there money left right now" are different questions. Only the second decides where a film shoots.**

---

## THE MODEL

### ❌ What we're NOT doing
**No budget input.** Circular — a dollar buys a different movie in each place, and the labour differential is frequently *larger* than the incentive. An incentives-only index publishes a misleading answer to "why is everyone leaving town," and a knowledgeable reader would tear it apart.

### ✅ Physical inputs → landed cost

**Six inputs plus a city list:**
1. Type and scale — feature / limited series / episodic
2. Shoot days, split stage vs. location
3. Crew size (or a tier, and it infers department ratios)
4. Principal cast — how many, how many imported
5. Crew flown in vs. hired locally
6. Start window — a quarter
7. **The cities they're considering** — *they pick, we price*

*(Location suitability was cut. A tool that suggests Budapest for a script needing the Pacific loses a film person's trust instantly.)*

**Then, per city:** localize the budget against local union rate cards → add flights, housing and per diem for imported crew → stages, equipment, permits, trucking → FX → compute the qualifying base under *that* jurisdiction's definition → apply ceilings, tiers, caps, uplifts in order → convert gross to net cash → estimate arrival timing.

**Output: total net cost of the same movie in each place.** Not incentive size.

### The headline output is the gap, decomposed
> **Los Angeles is $2.6M more than Budapest.**
> Labour $1.1M · Housing and per diem $600K · Stage $400K · Incentive gap $500K
> *Even at 35%, the credit closes less than a fifth of it.*

Nobody publishes that. It's the answer to "why is everyone leaving town" that survives a challenge from someone who knows the business — and it tells a legislator which lever actually matters. Newsom took the credit to 35% and $750M in July 2025; if the gap is mostly hotels and stages, that money bought less than the press release implied.

### The timing dimension
**Sunsets killed** — you lock at application, so a 2031 expiry doesn't touch a 2027 production. Noise.

**Future improvements are the real question, because they change *when* you shoot** — and a production can move its start date far more easily than it can move countries:
- New Mexico's cap escalator: $130M FY25 → $140M FY26 → $160M by FY29. Legislated, dated, certain.
- UK transition dates: AVEC mandatory April 2025, old reliefs dead April 2027, VFX uplift claimable from April 2025.
- Czech reopening September 2026.
- Fiscal-year rollovers on any first-come capped programme.

**And when your terms lock varies by jurisdiction** — application, start of principal photography, or completion. That determines whether a scheduled improvement can still catch you.

**One slider drives two things:** incentive availability *and* cost seasonality (hotel rates, stage demand).

---

## THE UX

**One screen. A map, one slider, a ranked list that reorders live.**

- **Map is the hero** — cities coloured by total net cost. Geography story, no reading required.
- **Start-date slider** — drag it and watch Prague go dark in Q1 because the fund is dry, then light up in Q4. New Mexico deepening as the cap steps.
- **Ranked list** — net cost, incentive, and *when the cash arrives*.
- **Pick any two** → the decomposed gap.
- **Every number clickable** → the rule, the source, the date checked.
- **Proof panel** — small widget, enormous credibility.

**Supporting:** a time scrubber (2016→today) showing California dim, Georgia and Eastern Europe brighten, then California flare back in 2025. And a dated change feed — cheapest possible proof the thing is actually running.

---

## THE AGENT QUESTION — honest resolution

**Dave's interrogation: is this an agent job or a scrape-plus-math job?**

Walked step by step, the runtime is **scrape plus math**. Finding rules is a known URL. Extracting them is a parse. Normalizing twelve schemes into one model is real reasoning — but done **once per jurisdiction**, then hardcoded. Localizing, computing, ranking are all deterministic math.

**The test: delete the agent, what's left?** A good calculator with slightly stale data. ~90% of the value survives.

**So the agent has to earn its place on two jobs that genuinely can't be precomputed:**

### Job 1 — continuous validation
New York publishes quarterly. Each new report drops → agent ingests it → pulls every production/award pair → re-runs the model against each → reports accuracy. Same for California and New Jersey.

**This doubles as change detection.** If Georgia amended a rule and we missed it, nobody would notice — but our numbers would drift against the next batch of published awards. Catches silent model rot without anyone watching.

Gives a living metric instead of a one-time claim: *"tested against 340 government-disclosed awards, mean error 0.4%."*

### Job 2 — unknown jurisdictions, live
User types a city not in the curated set — **Bristol, England.** The agent finds the national scheme (AVEC/IFTC), checks for regional support layered on top, works out which base applies, identifies caps and payout mechanism, builds the model on the fly, prices it, and marks the result **researched, not validated.**

**Two tiers, and the labelling is a feature:** *"we can price anywhere; here's where we can prove we're right."*

That's a demo moment — type a country nobody expected, watch the chain run in ninety seconds with citations.

### Tiered refresh — match cadence to half-life
| Data | Cadence |
|---|---|
| FX | Daily |
| Cap consumption / programme open-closed | Daily–weekly |
| Hotel and seasonal costs | Weekly |
| Incentive rules | Monthly + event-driven |
| Union rate cards | Annual, step-ups pre-loaded |

*Rules change ~10–12 times a year across ~15 jurisdictions — roughly annually each. Don't sell a velocity story that can be checked and disproved. **Sell breadth, normalization, and per-production computation.***

---

## THE ANORA PROOF — plainly

*Anora* shot in New York. New York's economic development agency publishes a quarterly PDF listing every production that received a credit, showing **both** numbers:

**$3,964,760 qualified spend → $991,190 credit issued.**

Feed our tool the same input; if it returns $991,190, our math matches what a government actually paid — against a public document a judge can open and check in thirty seconds.

Every competing tool says "estimated." None can point at a government PDF and say *we reproduce this exactly.*

**Other validated pairs available:** Succession S4 ($102.9M → $25.7M), The Gilded Age S2 ($134.3M → $35.3M), Clueless reboot (CA, $46.5M → $16.3M), Joker (NJ, $6.1M → $1.96M). Eleven sourced pairs in the feasibility file.

---

## DATA AVAILABILITY

| Category | Status |
|---|---|
| **Incentive rules** | Free, authoritative, completely unstructured. **No API or bulk download anywhere.** Government film office pages are the only truth. NCSL index is a year stale — use as a link directory. Olsberg·SPI Global Index free PDF (May 2025). |
| **Validation data** | NY ESD quarterly PDFs = gold standard (both sides). CA live table (allocation stage). NJEDA reports (estimated). Connecticut has an actual CSV endpoint — the only one found. MA/PA: amounts public, spend not. **Georgia, NM, IL, LA, UK, Canada: nothing.** Ireland: banded. |
| **Labour** | Union rate cards published — IATSE locals, SAG-AFTRA, DGA, WGA, BECTU, ACTRA. **Non-union local rates aren't public** — that's what EP and Cast & Crew sell. |
| **Housing & meals** | 🎯 **GSA publishes US per diem by county**, annual. **State Dept publishes foreign per diem**, monthly. Official, granular, free — covers the largest non-labour line. |
| **Other production costs** | Stage and equipment rate cards often published. Permits and location fees via film offices. Trucking is quote-based — needs a labelled estimate. |
| **Ancillary / ROI** | BEA industry GDP + employment by state, BLS NAICS 5121 wage data, state revenue departments, RIMS II multipliers. ⚠️ **Politically contested** — industry-funded studies find strong returns, independent state auditors (Georgia's included) routinely find under a dollar back per dollar given. Any "what LA recoups" figure must expose its multiplier assumption on screen or it becomes advocacy. |

---

## SCORECARD

| Criterion | Score | Notes |
|---|---|---|
| Technological Implementation | **7.5 → 9** | 7.5 as a curated calculator. 9 once Jobs 1 and 2 give the agent work that can't be precomputed. Parallel is load-bearing either way — no API exists, so research is the only path. |
| Design | **8** | Map, one slider, decomposed gap, proof panel. The interaction *is* the insight. |
| Potential Impact | **9** | Tens of millions per decision, a live policy fight, and provably correct. |
| Quality of the Idea | **8** | Landed cost rather than incentive-only is the non-obvious move. |

**Known competitor:** Wrapbook ships an AI incentives chatbot that self-discloses it "might hallucinate." Differentiator is **not** "AI answers incentive questions" — it's **verified, cited, net-cash landed-cost modelling with a published validation record.**

---

## THE PARALLEL JUDGE'S WRITE-UP *(simulated)*

> This is the strongest use of our Search API in the track, for a structural reason: **there is no incentives API anywhere in the world.** Every authoritative source is a government page or a PDF, and the existing commercial tools are stale web UIs. Research isn't *a* solution here, it's the only one. The team worked that out before they picked us.
>
> The retrieval is doing real work. They're running structured extraction across a dozen jurisdictions in parallel — rate, base definition, per-person ceilings, cap status, effective dates — then reconciling incompatible programmes into a common schema. The normalization is the hard part and they've named it as such, which tells me they understand the problem rather than the API.
>
> The availability check impressed me most. Distinguishing "what are the rules" from "is there money left right now" only surfaces from live research, and the Czech case — unchanged terms, exhausted fund, September reopening — is something a cached database cannot represent at any refresh rate.
>
> **Reservations.** What happens on conflicting sources? They flag New York's own cap as reported at both $700M and $800M, and I didn't see the resolution strategy. How do they detect a page changing under them between runs? Some international coverage leans on secondary sources where the primary was unreachable — honest, but weaker. I'd want the caching boundary made explicit: how much is genuinely live at query time versus resolved earlier.
>
> **Overall:** the validation record is what separates this from a research chatbot. Reproducing a published state figure to the dollar is a claim almost nobody in this field makes, and it's independently checkable.

---

## KILLED

- **Ranking on headline rate** — what every existing tool does, and it's wrong by 20–40%.
- **Budget as an input** — circular.
- **Sunset risk** — you lock at application; a future expiry doesn't touch your production.
- **Location suitability** — creative and logistical judgment. The user picks the cities.
- **"Live daily research" as the differentiator** — rules move roughly annually. Overclaiming freshness invites a judge to check and disprove it.

## OPEN ITEMS

- New York's current annual cap — sources give $700M and $800M. Reconcile at tax.ny.gov.
- Georgia loan-out withholding — cited at both 4.99% and 5.75%.
- New Mexico HB 237 (proposed repeal) — outcome unknown, live risk.
- Connecticut CSV column headers — not opened.
- Ireland Section 481 CSV — confirm whether all rows are banded.
- Whether EP or Cast & Crew offer an unadvertised enterprise feed — needs a sales conversation.
