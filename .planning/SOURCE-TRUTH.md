# Source Truth

This file is the answer record for Phase 1's four source-verification
questions. Each entry below carries: the question verbatim from
`REQUIREMENTS.md`, the answer, the primary-source URL(s), `date_checked`, a
confidence tier, and what the evidence did to any stated working hypothesis
(D-12). Every figure quoted below was transcribed from a raw text extraction of
an archived document (`pdftotext -layout` for PDFs, direct `curl`/fetch for
HTML) — never from an LLM summary. Every document cited as primary has a row in
`sources/MANIFEST.yaml` whose recorded sha256 matches the archived file on disk;
`tests/test_source_truth.py` proves that reconciliation on every run.

Phase 2's rule files cite both this file's entries and the primary URLs
directly — this reasoning is the argument for the encoded constants, not itself
rule data.

---

## SRC-01 — New York's annual cap

**Question (verbatim, REQUIREMENTS.md):** New York's annual cap is reconciled
against a primary source (tax.ny.gov or enacted FY2026 budget bill text).
Working hypothesis to confirm or refute: $700M base plus a separate $100M
independent-film pool, not a $700M/$800M dispute.

**Answer: CLOSED against the enacted budget bill text.** The base Film
Production and Post-Production Tax Credit Program is capped at **$700 million
per year** (of which up to $45 million may go to post-production), allocated
2024 through **2036**. This is a *separate, additional* program from the
**Empire State Independent Film Production Credit**, capped at **$100 million
per year**, split into **Pool 1 (~$20 million/year)** for productions with
qualified costs of $10 million or less and **Pool 2 (~$80 million/year)** for
productions above that threshold. The two programs are never summed into a
single reported cap in this record: **$700 million** and **$100 million** are
reported as two separate figures with two separate sources, because Phase 2's
rule files need them separable (different statutory sections, different
eligibility, different allocation offices).

**$700M base + $100M independent pool = $800M** — which is exactly the figure
the May 2026 Agreed-Upon-Procedures (AUP) document states. The AUP document's
sentence ("Program credits of $800 million per year can be allocated...")
reuses the same construction as the Guidelines PDF's $700M sentence, but
substitutes the *combined* total into a sentence that reads, structurally, as
describing the base program alone. Nothing in the enacted statute supports an
$800 million *base-program* figure at any point through the most recent check
available (see Method below) — the AUP document's number is best explained as
an internal drafting imprecision (reusing prior boilerplate with the combined
total substituted in), not a further legislative change to the base cap.

### Primary sources

1. **The enacted budget bill itself — top of the precedence ordering
   (PITFALLS.md §D2).** S. 3009--C / A. 3009--C, the New York State
   2025-2026 Revenue Budget Bill, signed into law as **Chapter 59 of the Laws
   of 2025** on **2025-05-09** (confirmed via the bill's own recorded
   Actions: "05/09/2025 signed chap.59"). Fetched directly from the NY State
   Senate's own bill-PDF endpoint, `https://legislation.nysenate.gov/pdf/bills/2025/S3009C`,
   and archived at `sources/ny/2026-08-24-ny-enacted-budget-film-credit-extract.pdf`
   (sha256 `8ce03a1d3d4a0d9c7e658dc7e48eb769adf6174d6c1593531da4ad7f7b07ba1d`).
   Extracted with `pdftotext -layout` (raw text, not an LLM summary).
   - **Part I, Section 3** amends paragraph 4 of subdivision (e) of Tax Law
     section 24 ("Additional pool 2"). The tracked-changes bracket notation in
     the bill text shows only the sunset year changing —
     `"...seven hundred million dollars each year starting in two thousand
     twenty-four through two thousand [thirty-four] thirty-six..."` — the
     dollar figure (`seven hundred million dollars`) is **not** bracketed as
     changed; only `thirty-four` (2034) is struck and replaced with
     `thirty-six` (2036). The bill also confirms `"forty-five million dollars
     of the annual allocation shall be available for the empire state film
     post production credit... in each year starting in two thousand
     twenty-four through two thousand [thirty-four] thirty-six"` — the $45M
     post-production earmark, unchanged in amount, extension only.
   - **Part I, Section 9** adds a **new Tax Law section 24-d**, "Empire state
     independent film production credit": `"the aggregate amount of tax
     credits allowed... in any calendar year shall be (1) twenty million
     dollars for qualified films with a budget of less than ten million
     dollars of qualified production costs; and (2) eighty million dollars
     for qualified films with a budget of ten million dollars or more of
     qualified production costs."` This is the statutory origin of the
     $20M/$80M split — a brand-new section of the tax law, not a rewording of
     the base program's cap.

2. **NY State Film Tax Credit Program Guidelines**, dated 2025-04-18, fetched
   from `https://esd.ny.gov/sites/default/files/media/document/Film_Credit_Guidelines_W_Appendix_20250418_0.pdf`,
   archived at `sources/ny/2026-08-24-esd-film-credit-guidelines.pdf` (sha256
   `42ffc801a4ff61f00ad71e38d3dc869f52ddf4d227f727181902989a7a489d14`).
   Page 1: `"Program credits of $700 million per year can be allocated...
   Up to $45 million of the $700 million may be dedicated to supporting and
   growing the post-production industry."` This document pre-dates the
   enacted bill's sunset-year extension and still says "until 2034" — a
   stale duration figure, but a correct dollar figure.

3. **NYS Film Tax Credit Program — Agreed Upon Procedures**, dated May 2026,
   fetched from `https://esd.ny.gov/sites/default/files/media/document/Film-Prod-CPA-AUP-May2026.pdf`,
   archived at `sources/ny/2026-08-24-esd-film-prod-cpa-aup.pdf` (sha256
   `95b60708e11bc26833ce4e860ea8b2c5807d1192052b54a8ef7227dc6e3c2118`). Page
   1, "Background": `"Program credits of $800 million per year can be
   allocated and used to encourage companies to produce projects in New York
   which help create and maintain industry jobs."` This is the anomalous
   sentence the whole entry exists to explain — see Answer above.

4. **Live esd.ny.gov Film Production program page**,
   `https://www.esd.ny.gov/new-york-state-film-tax-credit-program-production`,
   fetched by direct `curl` this session (raw bytes, not the WebFetch/LLM
   summary 01-RESEARCH.md relied on), archived at
   `sources/ny/2026-08-24-esd-live-film-production-page.html` (sha256
   `6aa32a02893ef19846168c3737d289faec09e5b61549c6f7eabfc257550ccee9`).
   Verbatim: `"This tax credit is funded at $700 million a year through
   2036."` — matches the enacted bill's 2036 sunset extension exactly.

5. **Live esd.ny.gov Independent Film Production program page**,
   `https://www.esd.ny.gov/new-york-state-independent-film-production-tax-credit-program`,
   fetched by direct `curl` this session, archived at
   `sources/ny/2026-08-24-esd-independent-film-production-page.html` (sha256
   `716eebc6c016bcb6253af44b3e787641c8b0a10471c48372b5feeefabe580a51`).
   Verbatim: `"This tax credit is funded at $100 million per calendar
   year."` ... `"Pool 1 with approximately $20 million annually is for
   productions with $10 million or less in qualified costs."` ... `"Pool 2
   with approximately $80 million annually is for productions with more than
   $10 million in qualified costs."`

### Method note — how the enacted statute was reached

`www.nysenate.gov/legislation/laws/TAX/24` (the codified Tax Law section 24
page the research recommended checking) returned a Cloudflare
bot-verification challenge to both a direct `curl` fetch and a headless-browser
fetch this session — the page never rendered past "Performing security
verification." Rather than give up on statute-level confirmation, two
independent routes were used instead:

- The **actual enacted bill text** was fetched directly from the NY Senate's
  own PDF-serving subdomain, `legislation.nysenate.gov` (not
  `www.nysenate.gov`), which was not behind the same challenge. This is not a
  workaround of lower evidentiary value than the codified-law page — it is
  the bill itself, Chapter 59 of the Laws of 2025, which is *more* directly
  primary than a codified-law summary page.
- As corroboration only (not required to reach the answer above), the
  codified Tax Law section 24 text was independently cross-checked via an
  Internet Archive Wayback Machine capture of the exact
  `www.nysenate.gov/legislation/laws/TAX/24` URL (timestamp `2025-09-12`,
  i.e. after the bill's 2025-05-09 enactment) and via
  `newyork.public.law`'s mirror of the same section, whose own footer states
  its "Original Source" is `www.nysenate.gov/legislation/laws/TAX/24`,
  "last accessed Aug. 22, 2026" — two days before this session. Both show
  identical "seven hundred million dollars each year... through two thousand
  thirty-six" text, six months apart, with no intervening change — consistent
  with (not proof beyond the bill text itself of) no further FY2027 budget
  action having raised the base cap.

Neither of these two mirrors was archived into `sources/` — they were used
only as corroboration of a conclusion the enacted bill PDF (archived, hashed,
cited above) already establishes on its own.

**date_checked:** 2026-08-24

**Confidence:** HIGH for the $700M base-program figure (2024-2036, $45M
post-production earmark) and the $100M independent-film pool with its
$20M/$80M split — both read directly from the enacted bill's own tracked-changes
text, not inferred. HIGH for the resolution of the AUP document's $800M
figure as the combined total. The one honest residual uncertainty: this
entry cannot rule out, with the same directness as the bill text itself, a
FY2027 (or later) budget action between 2026-08-24 and any future date that
might change these figures again — `www.nysenate.gov` remained
Cloudflare-blocked throughout this session, so a live re-check at that
specific URL was not possible. The archived enacted-bill PDF and the two
live esd.ny.gov pages (both fetched today) are what this answer stands on.

### What was refuted or refined (D-12)

The stated working hypothesis — **"$700M base plus a separate $100M
independent-film pool, not a $700M/$800M dispute"** — is **confirmed**, not
refuted. What 01-RESEARCH.md's session left open, and what this entry closes,
is a *narrower* question the hypothesis didn't originally anticipate: a third
official ESD document (the May 2026 AUP), more recently dated than the
Guidelines PDF and read as describing the base program specifically, stated
$800 million where the hypothesis's own logic would only expect $700 million.
Two explanations were on the table:

1. The AUP document reused the Guidelines PDF's sentence structure but
   substituted the combined figure by imprecision — the base program's own
   cap remains $700M.
2. A further budget action between April 2025 and May 2026 raised the base
   program's own cap to $800M independent of the indie-film pool.

**Explanation 1 is confirmed; explanation 2 is refuted.** The enacted bill
(Chapter 59 of the Laws of 2025, archived above) shows the base program's
cap dollar figure untouched — only the 2034-to-2036 sunset extension was
amended — and no evidence of any subsequent base-cap-raising action was found
in either the current esd.ny.gov live page or the two independent statute
mirrors described in the Method note, both dated within days of this session.
Per D-13, this is recorded as a closed answer with its reasoning, not as an
unresolved conflict — the evidence genuinely closes it, rather than requiring
an arbitrary pick between two live possibilities.

---

## SRC-02 — Connecticut open-data CSV column headers

**Question (verbatim, REQUIREMENTS.md):** Connecticut open-data CSV column
headers are confirmed by opening the actual endpoint, before CT's rule model
or ingestion logic is written.

**Answer: seven columns, verbatim, in this published order:**

```
"Production Company","Qualified CT Expenditures","Date Issued","Amount of Tax Credit Issued","Program Name","Statutory Reference","Municipality"
```

`Production Company`, `Qualified CT Expenditures`, `Date Issued`, `Amount of
Tax Credit Issued`, `Program Name`, `Statutory Reference`, `Municipality`.
The schema itself implies **issued-stage disclosure** — the columns are
`Date Issued` and `Amount of Tax Credit Issued`, not an allocation/estimate
figure — which is what makes Connecticut a strong validation source and what
plan 01-04's `ct_christmas_always.yaml` fixture relies on.

**Primary source:** endpoint
`https://data.ct.gov/api/v3/views/kjsu-mdny/export.csv?accessType=DOWNLOAD`
(dataset landing page `https://data.ct.gov/d/kjsu-mdny`). Plan 01-04 already
archived this file byte-for-byte at
`sources/ct/2026-08-24-ct-film-tax-credits-issued.csv` (sha256
`2b249b80d393d57ff849ee1f1630f3fc6acd0aaecf216c938fc3bb93e7ddfe87`) — this
entry cites that archived file rather than re-fetching, per plan
instruction, and every claim below was independently re-verified this
session directly against those already-archived bytes (not against
01-RESEARCH.md's prose). The file's original sha256 is unchanged.

**Six data-quality artifacts, each confirmed by direct inspection of the
archived file this session** — every one of these is a bug waiting to
happen in Phase 5's ingestion:

1. **A blank row immediately follows the header row** (`,,,,,,`, line 2) — a
   naive parser reading row 2 as the first data row gets an empty record;
   must be skipped.
2. **Monetary values are quoted text strings with a `$` and thousands
   commas**, e.g. `"$175,772.00"` — not raw numeric; requires stripping
   `$`/`,` before `Decimal()` parsing.
3. **At least one inconsistent trailing-period formatting artifact** — two
   confirmed directly this session: `"$9,937,981.00."` (Stephen David
   Entertainment, LLC, issued 2022-09-02) and `"$1,732,800.00."` (Christmas
   Fix, LLC, issued 2023-04-23) — a strict parser must tolerate/strip a
   trailing period rather than fail outright.
4. **`Municipality` is blank for some rows.** Confirmed directly this
   session: four World Wrestling Entertainment / WWE rows dated
   **2009-07-21** have an empty `Municipality` field (a fifth WWE row on the
   same date has `Municipality` filled as `Stamford`) — **note this
   corrects 01-RESEARCH.md's prose, which attributed the blank-Municipality
   observation to "early... entries from 2007"; the file's actual earliest
   row (2007-08-10, Orange Lion Productions, LLC) has `Municipality`
   filled ("Fairfield"), and the blank rows independently re-verified this
   session are dated 2009-07-21, not 2007.** `Municipality` must be
   nullable in the fixture/ingestion schema, not required.
5. **Dates in `Date Issued` are ISO 8601 with a time component**
   (`YYYY-MM-DDTHH:MM:SS.sss`, e.g. `2007-08-10T00:00:00.000`), even though
   these are calendar-date events — parse as datetime and truncate to date.
6. **`Program Name` covers at least three distinct statutory programs
   sharing this one CSV**, confirmed directly this session by inspecting
   sample rows for each: `"Film and Digital Media Production Tax Credit"`
   (`CGS 12-217jj`), `"Film Infrastructure Tax Credit"` (`CGS 12-217kk`),
   and `"Digital Animation Production Company Tax Credit"`
   (`CGS 12-217ll`). The CT `JurisdictionRuleSet` (Phase 2/5) needs to
   decide explicitly whether it models all three or scopes to just the
   production credit (§12-217jj) — this file does not distinguish them by
   column, only by row value, so ingestion logic must filter on
   `Program Name`.

**Row count:** 660 total lines (1 header + 1 blank + 658 data rows), spanning
2007-08-10 through 2024-10-25.

**date_checked:** 2026-08-24

**Confidence:** HIGH — direct byte-for-byte re-inspection of the already-archived
live-endpoint export.

**What was refuted or refined (D-12):** REQUIREMENTS.md states no working
hypothesis for this question (D-12's stated hypotheses cover the New York
cap and the Georgia rate only). This entry has nothing to confirm or refute
against a prior guess — what it does refine is 01-RESEARCH.md's own prose:
the blank-`Municipality` observation is corrected from "2007" to the
directly-verified "2009-07-21," per artifact 4 above.

---

## SRC-05 — Georgia loan-out withholding rate

**Question (verbatim, REQUIREMENTS.md):** Georgia loan-out withholding rate
is confirmed against a dated Georgia DOR source. Working hypothesis: 5.75%
is pre-2024-reform, 4.99% is current.

**Answer: a five-year declining schedule, not a single step.** The
withholding rate, exactly as the Georgia Department of Revenue's own page
prints it:

```
January 1, 2026 - Current = 4.99%
January 1, 2025 - December 31, 2025 = 5.19%
January 1, 2024-December 31, 2024 = 5.39%
January 1, 2023 -December 31, 2023 = 5.49%
December 31. 2022 - Prior = 5.75%
```

Each rate is recorded above exactly as the decimal string the source prints
— `4.99%`, `5.19%`, `5.39%`, `5.49%`, `5.75%` — never rounded, never
converted to a float, never collapsed to a single current rate. A
production's terms lock at application; a lookup one day either side of a
boundary must resolve to the correct band, and only the full five-tier
schedule supports that.

**Primary source (rate schedule):**
`https://dor.georgia.gov/film-tax-credits/film-tax-credit-resources`,
fetched by direct `curl` this session (raw HTML, not an LLM summary),
archived at `sources/ga/2026-08-24-dor-film-tax-credit-resources.html`
(sha256 `fddc5cc771fffe854a0d4dec5cb1ba2b08c717b2b66e3b0090500d16d8d8a002`).
Under the page's `Withholding Rate` heading, verbatim as quoted above. This
page sits under the DOR site's `Taxes > Tax Credits > Film Tax Credits >
Film Tax Credit Resources` section specifically — not the general personal
income tax section — but the sentence on this page alone does not explicitly
name loan-out withholding; see below for the document that closes that gap.

**Primary source (explicit loan-out tie):**
`https://dor.georgia.gov/instructions-production-companies`
("Instructions for Production Companies"), linked from the withholding
instructions hub page, fetched by direct `curl` this session, archived at
`sources/ga/2026-08-24-dor-instructions-for-production-companies.html`
(sha256 `6f9809442d8704855096c609027c6ef94e5dcf0fb5818f00363fd58fbff29c16`).
Verbatim: `"The production company or qualified interactive entertainment
production company (or their payroll service providers) shall withhold
Georgia Income Tax at the current annual rate on all payments to loan-out
companies for services performed in Georgia."` — citing `O.C.G.A. §
48-7-40.26` and `Regulation 560-7-8-45`. This is the explicit sentence
01-RESEARCH.md recommended finding before finalizing this entry: it
directly names loan-out companies, and states the rate applied to their
payments is Georgia's "current annual rate" — the same rate the
`Withholding Rate` table above states.

The withholding-instructions hub page itself
(`https://dor.georgia.gov/film-tax-credit-withholding-instructions-and-forms`,
archived at
`sources/ga/2026-08-24-dor-film-tax-credit-withholding-instructions.html`,
sha256 `3d3c45e6fccd0bd50633544c41af0ca1ce0311a8cf08f1c0be594e68468f8939`)
links both the rate-table page and the Instructions for Production
Companies page from the same "Film Tax Credit Withholding" navigation
context, and separately links a third page confirming the G2-FP/G2-FL
forms are issued specifically "to the loan out company" for "the amount of
film withholding."

**date_checked:** 2026-08-24

**Confidence:** HIGH for the rate figures and the five-year schedule
(unchanged from 01-RESEARCH.md's direct fetch). **The loan-out-specificity
claim is raised from 01-RESEARCH.md's MEDIUM caveat to HIGH** — an explicit
primary-source sentence naming loan-out-company payments and citing the
governing statute/regulation was found on the second page 01-RESEARCH.md
recommended opening. One honest caveat kept rather than smoothed over: the
explicit "loan-out companies... current annual rate" sentence and the
`Withholding Rate` table with its five-tier schedule live on two different
DOR pages, not one — the tie between "this specific schedule" and "loan-out
withholding" is made via the "current annual rate" phrase plus both pages
sharing the same Film Tax Credit Withholding site section, not by a single
sentence that states both the schedule and "loan-out" together. This is not
promoted to a stronger claim than that.

**What was refuted or refined (D-12):** The stated working hypothesis —
**"5.75% is pre-2024-reform, 4.99% is current"** — is **directionally
correct but imprecise, and is refined here.** It is not a single
pre/post-2024 step; it is a five-year declining schedule with three
intermediate values (5.49% for 2023, 5.39% for 2024, 5.19% for 2025) that
the hypothesis did not name and that no prior project document had
recorded. `5.75%` is confirmed as the correct "prior/pre-reform" figure and
`4.99%` as the current 2026 figure, exactly as hypothesized — but a rule
file that encodes only those two values, without the three intermediate
bands, will compute the wrong credit for any production whose terms locked
in 2023, 2024, or 2025.
