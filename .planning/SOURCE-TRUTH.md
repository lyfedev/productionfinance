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
