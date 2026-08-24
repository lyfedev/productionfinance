# Feasibility: AI agent for film/TV production incentive optimization

**Investigated:** 2026-08-20 · **Scope:** does the data exist to build and *validate* a "where should we shoot this to maximize the incentive?" agent
**Verdict:** **QUALIFIED YES.** The research and computation are hard but tractable. The data-currency problem is real but is an argument *for* a live-research agent, not against it. The one genuine structural gap is validation coverage — it works in New York and California, and does not work in Georgia.

---

## 0. TL;DR for a build decision

| Question | Answer |
|---|---|
| Do authoritative databases exist? | Yes — several free vendor tools. **None has an API or bulk download.** Everything is web UI or PDF. |
| Best single source of truth? | **No single one.** Per-jurisdiction government primary source is truth; Olsberg·SPI Global Incentives Index is the best non-vendor global compilation; NCSL is the best free US index (but ~12 months stale). |
| Is the computation trivial? | **No.** Every jurisdiction examined has at least 3 of: non-total-spend base, blended rate bands, caps that clip the base before the rate, per-person compensation ceilings, residency-contingent eligibility, and a gross→net conversion. Naive "spend × rate" was **44% wrong** in a worked UK example. |
| How fast do rules go stale? | ~10–12 material changes/year across the jurisdictions that matter. High-volatility tier (CA/NY/TX/NJ/IL/LA/GA) half-life is **~3 months**. |
| Can I validate against real disclosed awards? | **Yes in NY (gold standard), CA and NJ (good). No in Georgia, UK, Canada, Ontario, Australia.** 11 named test cases below. |
| Biggest obstacle? | Not research, not math. **Validation coverage is asymmetric** — the states that publish enough to validate against are not the states where the tool's answer matters most. |

---

## 1. SOURCE DATA — where the rules actually live

### The headline negative finding

**No source, anywhere, offers a public developer API or a bulk structured-data download of production incentive terms.** Every tool found is a click-through web map, a PDF, or (in one case) a chatbot. This was checked across EP, Wrapbook, Cast & Crew, The Location Guide, Screen Global Production, NCSL, and every government site visited. This is a negative finding from public product/marketing pages — it does not rule out an unadvertised enterprise data feed at EP or Cast & Crew, which could not be confirmed without a sales conversation.

**Implication:** there is no "buy the database" path. Any build is a research-agent build. That is also the moat — nobody publicly offers structured, queryable incentive data.

### Vendor tools (free, public, no login — funded as lead-gen for payroll/finance services)

| Source | URL | Access | Interface | Currency | Coverage |
|---|---|---|---|---|---|
| **Entertainment Partners — Incentives Map** | https://www.ep.com/production-incentives/incentives-map/ | Free, public, no login | Web UI map. Also an **Incentives Estimator** (US only) at /incentives-estimator/ and a **3-jurisdiction comparison tool** at /jurisdiction-comparison/ | No visible "last updated"; site footer © 2026 | EP *claims* 120+ jurisdictions, six continents — their claim, not independently counted |
| **Wrapbook — Production Incentive Center** | https://www.wrapbook.com/production-incentives | Free, public | Web UI + incentive finder questionnaire + state map (/state-map) + compare-states + government-forms library. Also an **AI incentives chatbot** (/ai-production-incentives-tool) that self-discloses it "might hallucinate" | **Verified current** — feed carried an August 2026 update post | US states + Puerto Rico. No structured non-US coverage |
| **Cast & Crew — Incentives Map** | https://www.castandcrew.com/services/incentives-map/ | Free, public | JS-rendered map widget (could not read the live data via fetch); 6-jurisdiction comparison; downloadable **TIP Guide** PDF (2024 edition) | Page metadata modified 2026-06-16. Their **Canada map PDF is dated January 2020** — confirmed stale | US + Canada + intl per marketing copy |
| **Media Services** | mediaservices.com | — | **RETIRED.** Acquired by Cast & Crew (2020); the incentive-database URL now 301-redirects to castandcrew.com/services/incentives-map/ (verified by fetch) | n/a | Do not treat as a separate source |

### Association / research

- **AFCI** — https://afci.org , directory at http://directory.afci.org/. **Does NOT run a searchable incentive database.** It is a membership association; the Global Member Directory is a directory *of film commissions*, not of incentive terms. Member gating on community.afci.org could not be inspected. Site copy conflicts internally on membership size (~300 vs "360 commissions from 40 countries") — unresolved. AFCI's real contribution is co-publishing with Olsberg·SPI.
- **Olsberg·SPI — Global Incentives Index** — the best **non-vendor, global, cross-jurisdiction** compilation found. Commissioned by the MPA. Free PDF. Editions confirmed: 2023, a Nov 2024 white paper, and **Global Incentives Index 2025 (May 2025)**. Landing: https://www.o-spi.com/projects/global-film-production-incentives-white-paper and https://www.motionpictures.org/advocacy/driving-local-economies/production-incentives/. Claims 100+ active incentives profiled (their claim; PDF body not opened). **PDF only, roughly annual — static.** No 2026 edition found.

### Government / policy aggregators

- **NCSL — State Film and Television Incentive Programs** — https://www.ncsl.org/fiscal/state-film-and-television-incentive-programs. Free, public, no login. One row per US state/territory (56 rows incl. DC, PR, territories), a plain-English paragraph each, plus an outbound link to the official state film office page. **Verified on-page: "Updated August 27, 2025" — i.e. ~12 months stale as of today.** Best free non-vendor US index; use it as a *jurisdiction directory with authoritative outbound links*, never as a rate table.
- **Individual state film offices** — the actual ground truth per state (film.ca.gov, dor.georgia.gov, nmfilm.com, gov.texas.gov/film, etc.). Free, public, **no APIs found on any**. Currency varies state by state on each legislature's calendar.
- **MPA production incentives hub** — https://www.motionpictures.org/advocacy/driving-local-economies/production-incentives/. Actively maintained (metadata modified 2026-08-19). Economic-impact studies, not rate tables.

### Paid / gated

- **The Location Guide — Global Filming Incentives** — https://www.thelocationguide.com/incentives/. **Subscription paywall, confirmed** — the fetched page is a marketing blurb only; the data sits behind the gate. Marketing copy claims "every incentive for any production" plus a comparison tool. Currency and jurisdiction count unverifiable from outside.
- **Screen Global Production (formerly KFTV)** — https://www.screenglobalproduction.com/country. Country guides with a "Latest Tax Incentives" section appear free to browse, but the section rendered empty on fetch (likely JS). Historically an annual PDF guide — so up to a year of lag. Trade press, not primary.

### Ruled out / not real

- **Reel-Scout** (reel-scout.com) is SaaS sold *to individual film commissions* for their own project/location management — **not** a multi-jurisdiction incentive database.
- **FilmUSA** — no distinct product found by that name.
- **ProductionHUB** — not investigated in depth; unverified either way.
- **Variety / Deadline incentive charts** — point-in-time journalism, not a standing database.

### Key non-US primary sources

- Ontario Creates — https://www.ontariocreates.ca/tax-incentives (OFTTC / OPSTC / OIDMTC)
- CAVCO (Canada federal) — https://www.canada.ca/en/canadian-heritage/services/funding/cavco-tax-credits
- BFI / British Film Commission — https://www.bfi.org.uk/apply-british-certification-expenditure-credits and https://britishfilmcommission.org.uk/plan-your-production/accessing-uk-tax-reliefs
- HMRC Creative Industries Expenditure Credit Manual — https://www.gov.uk/hmrc-internal-manuals/creative-industries-expenditure-credit-manual
- Hungarian National Film Institute — https://nfi.hu/en/filming-in-hungary/hungarian-film-incentive
- Czech Film Fund / Czech Film Commission — https://www.filmcommission.cz/en/production-incentives , https://sfa.gov.cz/production-incentives
- Screen Australia Producer Offset — https://www.screenaustralia.gov.au/producer-offset

---

## 2. STRUCTURE AND COMPLEXITY — what one program actually consists of

Four programs examined against primary sources. **Two premises in the original brief did not survive verification and are corrected here.**

### Corrections to common assumptions

- **Georgia HB 1180 (the 2024 bill to cap transferability) DID NOT BECOME LAW.** It passed the House in Feb 2024 and died in the Senate/conference. Georgia's credit remains **uncapped and fully transferable** as of Aug 2026. What *did* happen in 2025–26 is different and smaller: a DOR audit-procedure streamlining (Policy Bulletin IT-2025-01, effective 3/12/2025) and a separate, capped **postproduction** credit (H.B. 129, tax years from 1/1/2026).
- **New Mexico's 2023 overhaul was HB 547** (Ch. 211, signed 4/7/2023), not "SB 304." No SB 304 tied to these changes was found in NM legislative or TRD records.

### GEORGIA
Primary: https://dor.georgia.gov/required-mandatory-film-tax-credit-audit-fees · https://dor.georgia.gov/film-tax-credits/film-tax-credit-resources

- **Base:** 20% of qualified GA production/postproduction spend. **Minimum spend $500,000.**
- **Uplift:** +10% "Georgia Entertainment Promotion" (GEP) for embedding a 5-second GA logo + link in the distributed product. **Legally a separate credit with its own application and certification — not automatic**, and not paid until proof of multi-market distribution is filed within 5 years of the base certificate. Not available to commercials. Max 30%.
- **Caps:** none. No per-project cap, no annual program cap. Georgia is the outlier.
- **Per-person:** W-2 compensation qualifies only up to **$500,000/person**. 1099/loan-out payments are **not** subject to that cap but trigger GA withholding registration (rate cited variously ~4.99% / 5.75% — *unverified which is current*).
- **Mandatory audit** for all projects certified on/after 1/1/2023. Fee tiers: $500K–$5M spend → $5,000 (DOR-conducted) / $3,250 (DOR portion if using an eligible outside auditor); $5–10M → $12,500 / $6,500; $10M+ → $25,000 / $9,750.
- **Transferable, not refundable.** No statutory buyback. Sold via brokers at (industry-sourced, not primary) **~85–92 cents on the dollar**, clean fully-audited credits at the high end.
- **New, separate program (2026):** H.B. 129 postproduction credit — 20% base + 10% if also shot in GA + 5% rural = up to 35%, min $500K spend / $100K GA payroll. **But capped at $10M total across all claimants for 2026–2031, first-come-first-served, DOR pre-approval required.**

### NEW MEXICO
Primary: FYI-370 rev. 6/4/2024 — https://www.tax.newmexico.gov/tax-professionals/wp-content/uploads/sites/6/2022/12/FYI-370.pdf (full text read)

- **Base:** 25% of direct production + postproduction expenditures subject to NM tax.
- **Uplifts** (HB 547 rates, productions starting pre-production on/after 7/1/2023):
  - **+10% Rural** — spend on location ≥60 miles from the county-seat city hall of a "Class A county" (net taxable property value >$7.5B, i.e. ABQ/Santa Fe metro). Was 5% pre-2023.
  - **+5%** for *either* TV Pilot/Series (order ≥6 episodes, ≥$50K/ep NM budget) *or* Qualified Production Facility (sound stage ≥7,000 sq ft / 18 ft ceiling, or 50+ acre standing set). **Mutually exclusive — cannot stack both.**
  - **Non-Resident BTL Crew credit (NRCE): +15%** of nonresident below-the-line wages, but capped at 15% of the production's total NM BTL wage budget **and** capped by a headcount sliding scale (5 positions up to $2.75M NM budget; 10 up to $7.5M; 15 up to $11M; +1 per additional $10M; +5 if a pilot goes to series; hard ceiling 20).
- **"NM Film Partner"** is a defined legal status (company that bought or signed a 10-year lease on a qualified production facility). Pre-7/1/2028, Partners can count nonresident BTL wages up to 100% of resident BTL wages instead of the headcount table, subject to a 72-hour resident-hire notice. **Same production, same spend, different answer depending on the applicant's status.**
- **Dollar caps on the credit:** nonresident performing-artist portion ≤$5M/production; Film Partner nonresident *above-the-line* portion ≤$10M/production and $40M/year aggregate (unused rolls forward). Both can apply → up to $15M for one production.
- **Line-item caps:** vehicle rental $150/day/person; lodging $300/person/day; crew gifts $100/person; on-camera artwork/jewelry ≤$2,500.
- **Rolling statutory annual cap:** FY23 $110M → FY24 $120M → FY25 $130M → **FY26 $140M** → FY27 $150M → FY28 $160M permanent. Fiscal-year expenditure ceiling tracked monthly by TRD; no lottery.
- **No minimum spend** found in the primary source.
- **Refundable.** Assignable **once** to a financial institution or defined authorized third party; never re-assignable.
- **CPA audit mandatory** if the requested credit exceeds $5M; CPA must be NM-licensed.
- **Window:** apply within 1 year of the last NM expenditure (expenditure date = incurred, not paid). TRD has 120 days to decide. Refund only claimable after the company's tax year closes, then up to **16 weeks** processing. No interest paid.

### ONTARIO + CANADA FEDERAL
Primary: https://www.ontariocreates.ca/tax-incentives/ofttc · https://www.ontariocreates.ca/tax-incentives/opstc

- **OFTTC** (domestic/CanCon): **35% of eligible Ontario LABOUR expenditure only** — not total budget. 40% on the first $240K of labour for first-time producers. **+10% regional bonus** for shooting substantially outside the GTA. Requires 6 CanCon points, ≥75% of final costs as Ontario spend, commercial-exploitation agreement, and (post-8/24/2023 PP start) a screen credit.
- **OPSTC** (foreign/service): **21.5% of all qualifying production expenditure** — broader base (labour + service contracts + tangible property/equipment/studio rental). **But Ontario labour must be ≥25% of claimed QPE or QPE is capped at 4× labour.** No per-project or annual cap. Min production cost >$1M CAD (series: <30-min eps >$100K, ≥30-min >$200K).
- **OFTTC and OPSTC are mutually exclusive on the same title.**
- **Federal stack:** CPTC (CanCon) = 25% of qualified labour, itself capped at 60% of total production cost net of assistance (≈15% of budget max). PSTC (foreign/service) = 16% of qualified Canadian labour. **OPSTC (21.5%) + PSTC (16%) combine — but on different, overlapping bases.**
- **The grind:** government "assistance" (grants, subsidies, forgivable loans — explicitly *not* other tax credits or bona fide loans) reduces the qualifying base. Tax credits don't grind each other; a separate grant does. What counts as "assistance" vs a bona fide investment is a documented CRA dispute area with its own application policy.
- **Residency mismatch:** Ontario credits require Ontario tax residency (as of Dec 31 before PP); federal requires Canadian residency. A BC crew member's wages count federally but not provincially — **the eligible labour pool differs depending on which credit you're computing.**
- Refundable net of tax owing. OPSTC admin fee 0.15% of eligible expenditures (min $5,000 / max $15,000), +$100 if filed >24 months after the fiscal year-end following PP start.

### UNITED KINGDOM — AVEC / IFTC
Primary: https://www.bfi.org.uk/apply-british-certification-expenditure-credits/about-uk-creative-industry-expenditure-credits

- **AVEC replaced Film Tax Relief / HETV / Animation / Children's TV relief from 1 Jan 2024.** Standard **34% gross** taxable credit (**≈25.5% net** after corporation tax). Children's/animated TV and animated film: 39% gross (≈29.25% net).
- **IFTC (Independent Film Tax Credit): 53% gross (≈39.75% net)** — requires (a) principal photography on/after 1 April 2024, (b) total core expenditure ≤£23.5M, and (c) one of three creative-connection tests (UK-resident lead director, UK-resident lead writer, or official co-production).
- **The enhanced rate applies only to the FIRST £15M of core expenditure.** A £15–23.5M film is a hard blend: IFTC on the first £15M, standard AVEC on the remainder.
- **Qualifying expenditure = the LESSER of 80% of total core expenditure OR actual UK core expenditure.** Even a 100%-UK film only gets credit on 80% of core spend. **The 80% cap always bites.**
- Core expenditure excludes marketing/distribution. "UK-ness" is where a good/service is *used or consumed*, not the payee's nationality.
- Min UK spend 10% of core. No cap on standard AVEC; IFTC implicitly capped at ≈£6.36M gross via the £15M ceiling.
- **Transition dates:** AVEC claimable from 1 Jan 2024; mandatory for new productions from 1 April 2025; old reliefs fully sunset 1 April 2027. IFTC claims open to HMRC from 1 April 2025. A separate **VFX uplift** (5%, net 29.25%) exists within standard AVEC — **not available to IFTC claimants** — for VFX spend from 1 Jan 2025, with UK VFX costs exempted from the 80% cap.
- Two-agency split: BFI issues the certificate (cultural test or treaty co-pro); HMRC administers the claim against Corporation Tax.

### Is the arithmetic non-trivial? Yes. Two worked examples.

**UK IFTC, £18M film, 100% UK spend**

- Naive: £18M × 53% = **£9.54M**. Wrong on four axes.
- Correct: split at the £15M enhanced ceiling → £15M IFTC slice + £3M standard slice. Apply the 80%-of-core cap to each (it binds, since UK spend exceeds 80% of core): £15M × 80% = £12M × 53% = **£6.36M gross**; £3M × 80% = £2.4M × 34% = **£816,000 gross**. Total gross **£7.176M** — already 25% below naive. Net of ~25% corporation tax ≈ **£5.38M cash**.
- **The naive number is 44% too high** versus the figure that actually hits the bank.

**Georgia, $10M GA spend including a $2M lead-actor deal**

- Naive: $10M × 30% = **$3M**.
- If the actor is paid **W-2**: only $500K of the $2M qualifies. Base shrinks to $8.5M → **$2.55M**.
- If paid via **loan-out**: full $2M qualifies (no cap), but triggers a separate GA withholding obligation on the loan-out entity.
- **Same dollar, same production, different qualified-spend base — decided by a payroll-structuring choice made independently of the tax team.** Then subtract the mandatory audit fee ($25,000 tier) and apply the ~85–92¢ transfer discount to convert credit to cash.

**Every jurisdiction examined has at least three of:** (a) a base that isn't total spend (labour-only vs QPE vs core expenditure), (b) tiered/blended rates splitting one budget across bands, (c) caps that clip the base *before* the rate applies, (d) per-person or per-role compensation ceilings, (e) residency-contingent eligibility changing which line items count at all, (f) mutually-exclusive uplifts, and (g) a gross→net conversion (corporation tax, transfer discount, refund timing) between the headline rate and actual cash.

**Conclusion: this is a real modeling problem, not a lookup table.** A credible tool must model a *budget*, not a *number*.

---

## 3. VOLATILITY — how fast the rules move

**~10–12 material changes per year** across the ~15 jurisdictions a production actually compares. Confirmed, dated events in the last 24 months:

### United States

- **CALIFORNIA — PASSED, IN EFFECT (twice in one summer).** AB 132 (budget trailer) raised the annual cap **$330M → $750M/yr for 5 years**; signed 6/27/2025, effective 7/1/2025. AB 1138 ("Program 4.0"), signed 7/2–3/2025, raised the base credit to **35% (up to 40%** with an out-of-LA-County/VFX uplift), removed the $100M budget cap that had excluded tentpoles, expanded eligibility to animation, large-scale competition/reality, and shortened episodics, and made credits **fully refundable**.
  https://film.ca.gov/tax-credit/ · https://www.gov.ca.gov/2025/07/02/governor-newsom-marks-historic-expansion-of-californias-film-and-television-tax-credit-program-announces-16-new-projects-to-film-in-the-golden-state/
- **NEW YORK — PASSED.** FY2026 budget (spring 2025): annual cap raised; **sources disagree — $700M vs $800M — reconcile at tax.ny.gov before quoting.** New **$100M independent film pool** ($20M for sub-$10M-budget films, $80M for larger indies), applications opened July 2025. Post/VFX/animation threshold cut from 20%-of-VFX-budget or $3M to **10% or $500K**; in-state spend eligibility threshold cut 75% → **51%**; $45M/yr post set-aside through 2036. Removed the $500K ATL compensation cap. New "Production Plus" bonus (5–10%). Program extended to **2036**.
  https://www.nyc.gov/site/mome/news/05092025-ny-tax-credit.page · https://www.tax.ny.gov/legal/2025/pit-corp-changes.htm
- **TEXAS — PASSED.** SB 22 signed 6/22/2025, effective 9/1/2025. Creates the **Texas Moving Image Industry Incentive Fund**: $300M every biennium through 2035 (**$1.5B total**), replacing appropriations-dependent grants. Grants up to **31%** of qualified in-state spend.
  https://www.houstonpublicmedia.org/articles/arts-culture/2025/08/27/529561/sept-1-unlocks-first-installment-of-1-5-billion-film-incentive-package-in-texas/
- **LOUISIANA — NEARLY KILLED, SURVIVED REDUCED.** The House voted to **terminate** the credit effective 6/30/2025 during the 2025 tax-reform special session. After public backlash a Senate committee reversed: program kept, **cap cut $150M → $125M** effective 7/1/2025; per-project caps and per-person wage limits removed; **new sunset in 2031**.
  https://lailluminator.com/2025/06/23/louisiana-film/
- **NEVADA — FAILED.** SB 220 would have taken the credit from 15% → **35%** at **$120M/yr for 15 years**. Passed the Assembly 22–20 in the Nov 2025 special session, **died on the Senate floor 11/19/2025**, one vote short (10–8, three absent). Nevada remains on its old small program.
  https://www.leg.state.nv.us/Session/83rd2025/Bills/SB/SB220.pdf
- **NEW JERSEY — PASSED.** Signed 6/30/2025. Program extended 10 years to **2049**. Studio Partner rate 35% → **40%**; Diversity Bonus Credit **eliminated** for applications after 6/30/25; new 4% "Promoting NJ" credit; $20M per-project cap and $3M per-person payroll cap removed; individual compensation cap $500K → $750K.
  https://www.njeda.gov/film/
- **ILLINOIS — PASSED.** SB 1911 signed ~Dec 2025, with a further "sustainable productions" boost signed April 2026. Resident-hire / IL-vendor credit 30% → **35%**; non-resident crew slots 9 → 13. Retroactive to applications on/after 7/1/2025; program extended to **2039**.
  https://dceo.illinois.gov/whyillinois/film/filmtaxcredit.html
- **GEORGIA.** HB 129 revived the postproduction credit (capped $10M / 5 years, first-come). HB 475 extended coverage to streaming platforms. HB 1180's cap-and-limit-transferability effort **stalled** — the main program remains uncapped. DOR audit rules streamlined (IT-2025-01, 3/12/2025).
- **NEW MEXICO.** Statutory cap escalator running: $130M (FY25) → $140M (FY26) → $160M by FY29. A headline "House Bill 237 proposes repeal of state film incentive program" surfaced — **outcome unverified; treat as a live risk item.**
- **ARIZONA.** Pre-scheduled ramp completed: $75M (2023) → $100M (2024) → **$125M/yr from 2025**, flat until the 2043 sunset. No new legislation needed.
- **State count:** multiple 2025–26 trackers converge on **39 US states + DC + Puerto Rico** with active programs. No clean prior-period primary count was found, so treat 39 as a current snapshot, not a trend line. No state fully eliminated its program in the window; none launched from zero.

### International

- **UK.** Three distinct claimable-date events: AVEC claimable from 1/1/2024, **mandatory for new productions 1/4/2025**, old reliefs sunset 1/4/2027. IFTC PP-eligible from 1/4/2024, claimable from 1/4/2025. VFX uplift activity-eligible from 1/1/2025, claimable from 1/4/2025.
- **CANADA — BC.** Film Incentive BC base **35% → 40%** for PP starting after 12/31/2024. Production Services Tax Credit **28% → 36%**, effective January 2025. Interactive Digital Media credit → 25% and made permanent (wages after 8/31/2025).
  https://www2.gov.bc.ca/gov/content/taxes/income-taxes/corporate/credits/film-tv
- **CANADA — Quebec.** Raised the cap on eligible labour expenditures and the base service-credit rate, effective March 2024. **Ontario** — no material 2025 rate change found; treat as stable but re-verify.
- **CZECH REPUBLIC — the cap-exhaustion case study.** New Audiovisual Act effective 1/1/2025 raised the rebate **20% → 25%** (35% animation / no-live-action) and tripled the per-project cap to CZK 450M (~€18M). Then the fund's **cap was exhausted and applications suspended in March 2026**, reopening **September 2026**. https://www.praguereporter.com/home/2026/7/15/czech-film-and-tv-production-incentives-to-reopen-for-applications-from-september/ — **This is the pattern a static database cannot represent at all: the terms were stable while availability went to zero.**
- **HUNGARY.** A 2025 registration cap was introduced and subsequently **removed**; effective incentive can reach 37.5% (30% base + 7.5% non-Hungarian cost inclusion). **Exact date of the cap removal unverified.**
- **ITALY.** Transferable credit now 30%/40%; the "shooting day" requirement removed so post-only projects qualify. **Bill and effective date unverified — needs an Italian government primary source.**
- **SPAIN.** No major national rate change found; 25–30% national with regional top-ups (Canary Islands 45–50%, Basque up to 70%, Navarre 35%). Appears stable, not primary-confirmed.

### US federal

- **Tariff:** Trump floated a **100% tariff on foreign-made films** on 5/4/2025 and again 9/29/2025. **Never implemented**; mechanism never specified. Status: proposed only.
- **Federal incentive:** Sen. Schiff and IATSE pushed a federal production tax credit as the counter-proposal; a White House meeting occurred Dec 2025. **No federal film incentive has passed or been formally introduced as law.** Status: lobbying stage.

### Practical half-life of a static database

| Tier | Jurisdictions | Half-life |
|---|---|---|
| High volatility | CA, NY, TX, NJ, IL, LA, GA | **~3 months.** A year-old figure is more likely wrong than right. |
| Cap-exhaustion | Czech Republic, and any hard-capped program | **Weeks.** Terms stay stable while *availability* goes to zero mid-year. Unrepresentable in a static table. |
| Slow-moving | AZ, NM (statutory step-ups), Ontario, Spain | ~12 months. Changes are pre-scheduled in statute. |
| Live-fire | Nevada, US federal, Italy, Hungary dates, NY's own cap discrepancy | **Must be verified in real time before quoting.** |

**This is the strongest argument for the agent.** The volatility that makes a static product bad is exactly what a live-research agent is for.

---

## 4. GROUND TRUTH — can the tool be validated against real disclosed awards?

**Answer: YES in a subset of jurisdictions, and the subset is uncomfortably asymmetric.**

### Where the loop closes cleanly

**NEW YORK — the gold standard.** Empire State Development publishes quarterly PDFs containing a **"Final Applications – Credits Issued"** table: production name, studio, company, state of incorporation, county, **Qualified Costs**, **NYS Spend**, total hires, credit-eligible hours, credit-eligible wages, and **Credit Issued Amount**. These are *audited, issued* figures — not projections. Quarterly since 2013 (disclosure requirement), PDFs back to 2017.
Index: https://esd.ny.gov/esd-media-center/reports?tid%5B%5D=516&keys=film · Example: https://esd.ny.gov/sites/default/files/media/document/Q3-Film-Report-2025.pdf

**Both sides of the equation are published**, which makes a genuine re-derivation test possible: feed the published Qualified Costs to the estimator, compare to the published Credit Issued.

### Where the loop closes at the allocation stage

**CALIFORNIA.** https://film.ca.gov/film-and-television-tax-credit-program-approved-projects-list/ — a live HTML table, statutorily mandated (Rev. & Tax. Code §17053.85(h)(2)(A)(i) et seq.), currently carrying allocations dated July 2026. Fields: title, company, production type, indie flag, CA filming days, cast/crew hired, background days, **Qualified Expenditures**, **Credit Allocation**, allocation date. **Caveat: this is the allocation at approval, computed off the applicant's own estimated spend — not a post-completion audited figure.** Validating against it tests "does my tool replicate the state's approval-stage formula," which is still genuinely useful.

**NEW JERSEY.** NJEDA Film Tax Credit Activity Reports — https://www.njeda.gov/film/ (example: https://www.njeda.gov/wp-content/uploads/2022/01/FilmTaxCredit_Activity_Report_01122022.pdf). Fields explicitly labeled **Estimated** Award Amount and **Estimated** Qualified Film Production Expenses, plus location, approval date, diversity-plan flag. Same allocation-stage limitation as CA.

**CONNECTICUT.** A genuine machine-readable open-data feed — https://data.ct.gov/d/kjsu-mdny , CSV at https://data.ct.gov/api/v3/views/kjsu-mdny/export.csv?accessType=DOWNLOAD — described as tax credits issued through 12/31/2025. **Column headers not independently confirmed; download before relying on it.** The only true API/CSV endpoint found anywhere in this entire investigation.

### Where amounts are public but spend is not

- **MASSACHUSETTS** — real per-title dollar figures exist and are public record, but MA DOR does not self-publish a standing list. WBUR obtained 2023 data by formal records request: https://www.wbur.org/news/2025/02/13/massachusetts-film-tax-credits
- **PENNSYLVANIA** — DCED announces named awards periodically; no browsable master list. Reported at https://www.inquirer.com/news/pennsylvania/film-tax-credits-netflix-shane-gillis-philadelphia-economic-impact-20241116.html

### Where the loop does NOT close — the real gap

- **GEORGIA — no per-production disclosure exists at all.** Only aggregate annual totals (~$1B+ FY2021-22). The state's own auditors repeatedly flag transparency as a weakness: https://www.audits.ga.gov/ReportSearch/download/28730 · https://www.gpb.org/news/2022/11/01/whats-wrong-picture-state-auditors-give-georgias-movie-tax-credit-mixed-reviews . Taxpayer-confidentiality provisions constrain even Georgia's own economic-development agency's access to production-level cost data. **Georgia is one of the three largest US programs, uncapped, and the most likely target market for this tool — and it is the one jurisdiction where zero validation data exists.**
- **NEW MEXICO, ILLINOIS, LOUISIANA** — no certified-project list with per-production credit amounts found. LA publishes an aggregate economic-impact report only.
- **UK** — BFI certifies per title, but no BFI or HMRC publication ties a title to its £ AVEC amount. HMRC Creative Industries Statistics are aggregate National Statistics. The amount lives inside a confidential Corporation Tax computation.
- **CANADA (CAVCO)** — https://open.canada.ca/data/en/dataset/43a63c4f-b08e-4c53-99bb-20b90b83c6c0 publishes **production title and certificate holder, and explicitly no credit dollar amount.** CAVCO certifies eligibility; CRA computes the credit inside the confidential return. CSV/XLSX, biannual, most recent list 2026-07-13.
- **IRELAND (Section 481)** — names recipients but reportedly in **bands, not exact figures** (e.g. Netflix's "Mercenary: An Extraction Series" and the Marian Keyes adaptation "Grown Ups" both listed as "€5m to €10m"). https://data.gov.ie/dataset/film-relief-section-481-film-tax-credit · raw CSV: https://www.revenue.ie/en/companies-and-charities/documents/film-relief-beneficiaries-2016-onwards.csv — **open the CSV to confirm whether all rows are banded.** Banding permits order-of-magnitude checks only.
- **ONTARIO CREATES, SCREEN AUSTRALIA, UTAH, MINNESOTA, OKLAHOMA, KENTUCKY** — no per-production dollar disclosure found. (Utah publishes aggregate annual totals and names newly-approved batches; its board minutes were not checked and might carry more.)

### Named validation test cases — 11 sourced production/amount pairs

| Production | Jurisdiction | Disclosed amount | Qualified spend disclosed? | Implied rate | Source |
|---|---|---|---|---|---|
| Succession S4 | NY | $25,747,913 **issued** | Yes — $102,920,384 qualified / $152,802,059 NYS spend | 25.0% | ESD Q3 2025 report |
| The Gilded Age S2 | NY | $35,318,864 **issued** | Yes — $134,340,015 qualified | 26.3% | ESD Q3 2025 report |
| Anora | NY | $991,190 **issued** | Yes — $3,964,760 qualified | 25.0% | ESD Q3 2025 report |
| Clueless S1 (reboot) | CA | $16,335,000 allocated | Yes — $46,522,000 qualified | 35.1% | CA Film Commission list, 7/27/2026 |
| Disney's Hexed | CA | $16,638,000 allocated | Yes — $47,538,000 qualified | 35.0% | CA Film Commission list, 6/22/2026 |
| Joker | NJ | $1,962,642 estimated | Yes — $6,133,257 estimated qualified | 32.0% | NJEDA report, approved 8/13/2019 |
| The Trial of the Chicago 7 | NJ | $5,371,983 estimated | Yes — $17,906,613 estimated qualified | 30.0% | NJEDA report, approved 7/14/2020 |
| Don't Look Up | MA | $46,000,000 | No | — | WBUR / MA DOR records request |
| Madame Web | MA | $23,688,438 | No | — | WBUR / MA DOR records request |
| Creed II | PA | $16,000,000 | No | — | DCED via Philadelphia Inquirer |
| Knock at the Cabin | PA | $5,000,000 | No | — | DCED via Philadelphia Inquirer |

*(Also sourced: Tires S2 (Netflix) PA $5,500,000; A Great Awakening PA $2,600,000; Dexter: New Blood MA $22,994,092.)*

### Honest assessment of the loop

**What works:** for NY, CA and NJ you get *both sides* — the qualified spend and the award. That is a real re-derivation test, and the implied rates above (NY clustering at 25–26%, CA at 35%) already demonstrate the estimator is checkable against published reality.

**Where it gets fuzzy even in the good cases:** the disclosures give total qualified spend and top-line labor/hours/wages — **not the full input vector.** Missing: the resident/non-resident labor split, the ATL/BTL breakdown, and **which specific uplifts were claimed and stacked.** So:

- **Small indies with no uplift claims are your BEST test cases** — precisely because there is nothing to reverse-engineer. Anora is the archetype: $3,964,760 → $991,190 is a clean 25.0%.
- **Big studio productions layering multiple bonuses** degrade the test from "matches to the dollar" to "lands in the right zone." Gilded Age's 26.3% vs Succession's 25.0% is exactly the residue of an uplift you can't see in the published fields.

**The structural asymmetry, stated plainly:** the disclosure-rich jurisdictions (NY, CA, NJ, CT) are broadly the ones with *capped, allocated, application-based* programs — because a cap requires an allocation process, and an allocation process generates a public record. The disclosure-dark jurisdictions (GA, UK, Canada) are the ones where the credit runs through a confidential tax return. **You can validate best where the answer is most constrained, and not at all where the money is loosest.**

---

## 5. THE HARD PART

Ranked, hardest first.

### 1. Normalization, not research or arithmetic — this is the real difficulty

The research is doable: the primary sources are free, public, and findable. The arithmetic is doable: it's complex but deterministic. **The hard part is that the jurisdictions aren't comparable without a common model.** Ontario pays on *labour only*; the UK pays on *the lesser of 80% of core or actual UK core*; Georgia pays on *total qualified spend with a per-person W-2 cap*; New Mexico pays on *NM-taxable spend with a separate headcount-limited nonresident-wage credit*.

To rank these against each other you cannot compare rates. You must model a **budget** — with a labour/non-labour split, a resident/non-resident split, an ATL/BTL split, per-person compensation lines, and a location-day distribution — and push that same budget through every jurisdiction's rules. **The input schema is the product.** Get it wrong and the ranking is noise dressed as precision.

### 2. Converting the credit to cash

A 30% transferable Georgia credit and a 30% refundable New Mexico credit are not worth the same. The honest comparison metric is **net cash to the production, and when it arrives**:

- Georgia: 30% headline, minus the mandatory audit fee ($25,000 at the $10M+ tier), sold at ~85–92¢ → effectively ~26% and a broker relationship.
- New Mexico: 25–40%, refundable, but only claimable after the tax year closes plus up to 16 weeks, with no interest.
- UK: 34% or 53% **gross and taxable** — the net figures are 25.5% and 39.75% after corporation tax.
- Ontario: refundable, net of tax owing, minus a 0.15% admin fee.

**Any tool that ranks on headline rate is wrong.** Ranking on net-cash-and-timing is where the credibility is.

### 3. Availability, not eligibility

The Czech Republic in March 2026 had unchanged, attractive terms and **zero money**. Georgia's new postproduction credit is $10M total across all claimants for six years, first-come. New Mexico runs a rolling FY expenditure ceiling. **"What are the rules" and "is there money left right now" are different questions, and only the second one decides where a film actually shoots.** No static database captures this, and most of the vendor tools don't either.

### 4. Currency

Handled by design if the agent researches live. The ~3-month half-life in the high-volatility tier means a cached database is a liability; a live agent with per-jurisdiction primary-source citations turns the field's biggest weakness into the product's differentiator.

### 5. Validation coverage — the honest constraint

Not hard to *do*, but structurally limited. You can prove the tool in NY/CA/NJ and cannot prove it in Georgia at all. Any credible claim of accuracy has to be scoped to the jurisdictions where ground truth exists, and explicitly caveated elsewhere.

---

### What makes a demo convincing rather than trivial

**Trivial demo:** "Enter your budget, see a ranked list of states with percentages." Anyone believes that's a lookup table, because it is one.

**Convincing demo — five elements:**

1. **Lead with the validation.** Open on Anora: feed the agent New York, $3,964,760 qualified spend, and let it produce $991,190 — then reveal that ESD's published Q3 2025 report says the state issued exactly $991,190. Then do Succession at $102.9M → $25.7M. **Nothing else in the demo will buy as much credibility as one number matching a government PDF.**
2. **Show a case where naive math is badly wrong.** Run the £18M UK film. Show £9.54M naive, then walk the £15M split, the 80% cap, and the corporation-tax haircut down to ~£5.38M net. **A 44% error is the whole argument for the tool's existence.**
3. **Rank on net cash and timing, not headline rate.** Show Georgia's 30% losing to a lower headline rate once the audit fee, the ~88¢ transfer discount, and the 12-month cash lag are priced in. **This is the insight a producer will pay for and a percentage table cannot deliver.**
4. **Cite a live primary source per number, with the date it was checked.** Every figure links to film.ca.gov, dor.georgia.gov, the BFI, or the NM FYI-370 PDF. Then demonstrate currency by showing the agent catching something a static database missed — the Czech fund being closed until September 2026, or California's July 2025 jump to 35%/$750M.
5. **The reverse mode is the closer.** "What would California have to offer to beat Toronto for this production?" is a genuinely different computation — it solves for the delta rather than reporting a maximum, and it must reason across two incompatible bases (Ontario's labour-only OPSTC + federal PSTC stack versus California's 35% on qualified expenditures). **Nobody's incentive map can answer that question. That's the demo moment.**

**One risk to name honestly in any pitch:** Wrapbook already ships an AI incentives chatbot (https://www.wrapbook.com/production-incentives/ai-production-incentives-tool) that self-discloses it "might hallucinate." The differentiator is therefore **not** "AI answers incentive questions" — it's **verified, cited, net-cash modeling with a published validation record against government-disclosed awards.** The validation loop isn't a nice-to-have in this market. It's the product.

---

## Open items / explicitly unverified

- New York's exact current annual cap: sources give **$700M and $800M**. Reconcile against the enacted budget bill at tax.ny.gov.
- Georgia loan-out withholding rate: sources cite both **4.99% and 5.75%**. Unresolved.
- New Mexico **HB 237** (proposed repeal of the film incentive) — outcome unknown. Live risk.
- Hungary's registration-cap removal — exact effective date not pinned.
- Italy's 30%/40% transferable credit and shooting-day removal — no Italian government primary source confirmed.
- Connecticut open-data CSV column headers — not opened; confirm before relying on it.
- Ireland Section 481 CSV — confirm whether *all* rows are banded or some carry exact figures.
- Olsberg·SPI: no 2026 edition of the Global Incentives Index found; newest confirmed is May 2025.
- Whether EP or Cast & Crew offer an unadvertised enterprise data feed — cannot be determined without a sales conversation.
- Utah board minutes may carry per-production dollar detail; not checked.
- ProductionHUB as an incentive source — not investigated.
