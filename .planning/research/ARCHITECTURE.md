# Architecture Research

**Domain:** Multi-jurisdiction financial modelling engine with an agentic research/validation layer (film production incentive comparison)
**Researched:** 2026-08-23 (revised same day — hosting target changed from Google Cloud to AWS Lightsail per owner directive; AI-services boundary unchanged)
**Confidence:** MEDIUM-HIGH — component design is HIGH confidence (standard patterns from tax/payroll rule engines, ADK docs, Parallel SDK docs, all checked live); specific numeric rule values are inherited from `feasibility-incentives.md` and carry that document's own confidence caveats (NY cap, GA withholding rate, etc. — resolved in Phase 0, not this document).

**Infrastructure note (read before the rest of this document):** the owner has an AWS Lightsail instance available and hosting will most likely be AWS, not Google Cloud. This is permitted — the hackathon restricts *AI services only* (Google Cloud AI, via `google-adk` / `google-genai` / `google-generativeai` / `google-cloud-aiplatform`, plus Parallel); hosting, databases, storage, and schedulers are unrestricted and may be AWS. Every infrastructure recommendation below (compute, storage, scheduling) targets AWS/Lightsail. The AI boundary is absolute and does not move with hosting: **no AWS AI service — Textract, Bedrock, Comprehend, SageMaker, or any other — may perform any extraction, generation, or reasoning step anywhere in this system.** This is called out explicitly at the one place it is most likely to be reached for by habit (Job 1's PDF ingest, Q4) but applies everywhere.

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (SPA — map / slider / ranked list / gap panel / proof panel)   │
│  Static bundle on the Lightsail instance (nginx) or S3 + CloudFront      │
└───────────────────────────┬────────────────────────────────────────────-┘
                             │ HTTPS (JSON + SSE)
┌───────────────────────────▼──────────────────────────────────────────────┐
│  API LAYER — FastAPI, single process on the AWS Lightsail instance       │
│  (uvicorn behind nginx; systemd-supervised)                              │
│  /price  /figure/{id}  /cities/research (SSE)  /jurisdictions            │
│  /validation/summary  /index/*  (Balances)                               │
└───────┬───────────────────────────────────────┬─────────────────────────-┘
        │                                        │
┌───────▼────────────────────┐   ┌───────────────▼───────────────────────┐
│  CORE COMPUTATION PIPELINE  │   │  AGENTIC LAYER (google-adk)            │
│  (pure Python, no LLM)      │   │  Job 1: Validation loop (SequentialAgent)│
│  Spec→Budget→Localize→      │   │  Job 2: Live jurisdiction build (Sequential+Parallel Agent) │
│  QualifyingBase→Credit→     │   │  Tools: Parallel Search/Task API,      │
│  NetCash→Rank→GapDecompose  │   │  google-genai structured extraction    │
│  Emits: Figure trees        │   │  (Gemini ONLY — no AWS AI service)     │
└───────┬──────────────────-─┘   └───────────────┬───────────────────────-┘
        │  reads                                  │ writes (new/updated)
┌───────▼─────────────────────────────────────────▼───────────────────────┐
│  DATA FRESHNESS GATE  (single repository layer — the caching boundary)   │
│  get_or_refresh(key, data_class, ttl) — every external read goes through │
│  it. Stamps live_fetched_this_run + date_checked on every Figure.        │
└───────┬─────────────────────┬──────────────────────────┬────────────────┘
        │                     │                           │
┌───────▼───────────┐  ┌──────▼─────────────────┐  ┌──────▼───────────────┐
│ CURATED STORE      │  │ LIVE-CACHE / JOB STATE  │  │ EXTERNAL SOURCES      │
│ Postgres (self-     │  │ Postgres (research_jobs,│  │ GSA / State Dept per  │
│ hosted on instance  │  │ cap-consumption cache,  │  │ diem, union rate     │
│ or RDS) — YAML in    │  │ FX cache), TTL columns  │  │ cards, FX API,        │
│ repo is source of    │  │ checked at read time     │  │ Parallel Search,      │
│ truth, mirrored in   │  │                          │  │ NY ESD / CA / NJEDA / │
│ at deploy            │  │                          │  │ CT disclosure docs    │
└──────────────────────┘  └──────────────────────────┘  └───────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  BALANCES: systemd timer on the Lightsail instance → CLI job process     │
│  (reuses Core Pipeline as a library) → writes immutable index_run row    │
│  to Postgres + mirrors the snapshot as an immutable JSON object to S3 →  │
│  diffed against prior run for the change log → served at permanent      │
│  figure URLs (API + direct S3 object)                                   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|-------------------------|
| Frontend SPA | Map, slider, ranked list, gap panel, proof panel; every number is a clickable reference to a `figure_id` | React/Vite or Next static export; served either from the Lightsail instance via nginx alongside the API, or from S3 + CloudFront if the team prefers to decouple static hosting from the compute instance. Map via MapLibre GL (no Google Maps billing entanglement). |
| API layer | Auth-free public HTTP surface; validates `ProductionSpec`; orchestrates pipeline calls; streams agent progress | FastAPI, single `uvicorn` process on the Lightsail instance, `systemd`-supervised for auto-restart, `nginx` in front for TLS/static-file serving |
| Core computation pipeline | Deterministic, jurisdiction-agnostic budget localization and generic rule application; the thing that must be identical for every city | Pure Python module, no network calls, no LLM calls, unit-testable in isolation |
| Jurisdiction rule engine | Interprets `JurisdictionRuleSet` declaratively; the ONE place base/tier/cap/mechanism logic executes | Python module `engine/`, generic interpreter + escape-hatch handler registry |
| Agentic layer (Job 1) | Ingest a new disclosure document → structured rows → recompute → accuracy metric → drift flag | `google-adk` `SequentialAgent`, tools = Parallel Task API + **Gemini (google-genai) for all document extraction — never Textract** |
| Agentic layer (Job 2) | Discover, extract, validate, price, and label an uncurated jurisdiction live | `google-adk` `SequentialAgent` (with a `ParallelAgent` sub-step for national+regional discovery), same tools |
| Data Freshness Gate | Single enforcement point for the caching boundary; the only place that decides "fetch live vs serve cached" | One repository class, `get_or_refresh()`, called by everything else — nothing else talks to Postgres or external APIs directly |
| Curated store | Versioned, human-reviewed jurisdiction rules and validation pairs — the audit trail | YAML files in the public repo (git-versioned, the actual source of truth), mirrored into Postgres at deploy/startup for query convenience |
| Live-cache / job-state store | TTL'd cache for volatile data, live-researched jurisdictions, and durable background-job state | Postgres tables (`cap_consumption_cache`, `fx_cache`, `live_jurisdictions`, `research_jobs`) with TTL/`last_updated` columns checked at read time |
| Balances scheduler | Runs the same engine against a fixed reference production on a fixed cadence, stores immutable snapshots, computes movement and change log | `systemd` timer on the Lightsail instance invoking a CLI entrypoint that imports the Core Pipeline package |

---

## Q1 — The Core Computation Pipeline: component boundaries and seams

The pipeline is a strict, one-directional chain of pure functions. Each stage takes one immutable input and returns one immutable output; nothing downstream can leak into upstream logic. This is what makes "add a jurisdiction" additive: only two stages (4 and 5 below) ever consult jurisdiction-specific data, and even they consult *data*, not per-jurisdiction *code*.

```
ProductionSpec (7 inputs, jurisdiction-agnostic)
        │
        ▼
[1] BudgetModelBuilder      →  CanonicalBudget
        │   (department ratios inferred from crew tier; ATL/BTL split;
        │    resident/nonresident split placeholder; line items: labour,
        │    housing, per diem, flights, stages, equipment, permits, trucking)
        │   JURISDICTION-AGNOSTIC. One budget, period.
        ▼
[2] CityLocalizer (× each candidate city) → LocalizedBudget[city]
        │   Applies CityCostProfile: union rate cards, GSA/State Dept per
        │   diem, flights/housing indices, stage/equipment/permit/trucking
        │   rates, FX. Same CanonicalBudget in, city-priced line items out.
        │   JURISDICTION-AGNOSTIC (this is cost, not incentive rules).
        ▼
[3] QualifyingBaseCalculator (× each city, per programme)  ← reads JurisdictionRuleSet.base_definition
        │   LocalizedBudget → QualifyingBase (a Figure)
        │   ONLY jurisdiction-specific stage. Generic interpreter reads
        │   base_definition.type (total_spend / labour_only / lesser_of /
        │   local_hires_only) off the YAML — no per-jurisdiction Python.
        ▼
[4] CreditCalculator          ← reads JurisdictionRuleSet.rate_structure, caps, per_person_ceiling
        │   QualifyingBase → GrossCredit (a Figure)
        │   Applies an ORDERED, DATA-DECLARED sequence of adjustment steps:
        │   per_person_ceiling → uplift_stacking_rules → tier/blend rate →
        │   per_project_cap → annual_programme_cap (live consumption check).
        │   The ORDER is a field in the YAML, not a code branch — this is
        │   what "ceilings/tiers/caps/uplifts applied in order" means
        │   structurally: order is data, application is generic code.
        ▼
[5] NetCashConverter          ← reads JurisdictionRuleSet.mechanism/taxability/audit/transfer_discount
        │   GrossCredit → NetCash (a Figure) + ArrivalTiming
        │   Exactly 4 pure functions keyed by `mechanism` enum:
        │   refundable() / transferable() / rebate() / nonrefundable().
        │   NOT one function per jurisdiction — one function per mechanism,
        │   parameterized by that jurisdiction's numbers.
        ▼
[6] LandedCostAggregator      →  TotalLandedCost[city] (Figure tree)
        │   All LocalizedBudget non-incentive costs, minus NetCash, timed.
        ▼
[7] Ranker (× start-date/quarter)  →  RankedCityList
        ▼
[8] GapDecomposer (pick any 2)     →  GapBreakdown (component-by-component diff)
```

**The seam that matters most:** stages 1–2 (budget + cost localization) know nothing about incentive rules. Stages 3–5 (the incentive math) know nothing about how the budget was built — they consume `LocalizedBudget` and `JurisdictionRuleSet` and produce `Figure`s. This means the incentive engine can be fully unit-tested against a fixed `LocalizedBudget` fixture using only the 11 validation pairs, without ever touching per diem tables or union rate cards. That decoupling is also what makes Job 1 (recompute against a disclosure) cheap: it constructs a synthetic `QualifyingBase` directly from the disclosed dollar figure and runs only stages 4–5, skipping 1–3 entirely, because the disclosure gives you the qualifying base already computed by the state — you are only checking the state's own rate/tier/cap/mechanism math, not re-deriving their spend estimate.

**Where jurisdiction-specific logic lives, concretely:**
- 95% of jurisdictions: entirely in the `JurisdictionRuleSet` YAML/JSON document (schema below), interpreted by one generic engine (`engine/rules.py`).
- The remainder (genuinely irregular logic that doesn't fit the declarative vocabulary — e.g., Canada's federal-vs-provincial residency-pool mismatch, where the *set of people counted as eligible labour* differs between the two credits being stacked): a named Python function in `engine/handlers/`, registered by an ID string that the YAML references (`custom_handler_id: "ca_federal_provincial_residency_split"`). This keeps the escape hatch auditable — the YAML tells a reader exactly which file to open, and the handler registry is one small file, not scattered per-jurisdiction classes.
- Adding a jurisdiction = write one YAML file + (usually) zero handler functions + the validation pairs it can be checked against. No engine code changes. This is the concrete meaning of "additive, not invasive."

---

## Q2 — The Jurisdiction Rule Schema

**Recommendation: hybrid, weighted heavily declarative.** One generic engine interprets a YAML/JSON document per jurisdiction-programme; a small, named, registry-based Python handler is the escape hatch for the rare case that doesn't fit. This mirrors how mature multi-jurisdiction tax/payroll compliance systems are built in practice — configuration-driven rule definitions with condition sets and rate mappings, versioned, with a testing harness of real scenarios per jurisdiction, is the standard shape (Symmetry Tax Engine, Nected-style rules engines). A pure strategy-class-per-jurisdiction design was rejected: with 4 curated + N live-researched jurisdictions, a class-per-jurisdiction approach means the LLM-built Job 2 models would need to *generate executable Python*, which is both an audit and a safety problem (a public repo running LLM-authored code against untrusted regional programmes). A pure "one big YAML, no escape hatch" design was also rejected: New Mexico's dual-cap stacking and Canada's cross-jurisdiction residency-pool mismatch do not reduce to declarative fields without contortion. The hybrid gets auditability (read the YAML, understand the rule) without forcing every irregularity into the declarative vocabulary at the cost of correctness.

**Auditability requirement, satisfied concretely:** the YAML for every curated jurisdiction lives in the public repo in plain text (git-versioned — the source of truth, not a database row), each field traceable to a `sources[]` entry with a URL and accessed date. A reviewer (or a hackathon judge) can open `jurisdictions/us-ny.yaml` and verify the $700M/$800M cap resolution and its citation without reading any code.

### Schema (concrete field list)

```yaml
# jurisdictions/<id>.yaml  — one file per jurisdiction; a jurisdiction may
# declare multiple stackable/exclusive programmes (e.g. GA base + GEP uplift
# are modelled as two programme entries with a stacking rule between them).

jurisdiction:
  id: string                       # "us-ny", "us-ga", "gb-uk", "ca-on"
  name: string
  country_code: string             # ISO 3166-1 alpha-2
  level: enum[national, state, provincial, city]
  parent_id: string | null         # regional layering: "gb-bristol" → parent "gb-uk"
  currency: string                 # ISO 4217
  status: enum[curated_validated, live_researched, no_programme_found]
  effective_dates:
    rule_version_effective_from: date
    rule_version_effective_to: date | null
    source_checked_date: date
  sources:
    - url: string
      title: string
      accessed_date: date
      confidence: enum[HIGH, MEDIUM, LOW]   # from classify-confidence seam

programmes:                        # list — allows stackable/exclusive programmes
  - id: string                     # "us-ga-base", "us-ga-gep-uplift"
    name: string
    requires_separate_application: boolean
    stacks_with: [programme_id]
    mutually_exclusive_with: [programme_id]

    mechanism: enum[refundable, transferable, rebate_grant, nonrefundable_credit]
    taxable: boolean

    base_definition:
      type: enum[total_qualified_spend, labour_only, lesser_of_pct_core_or_actual_local, local_hires_only, custom]
      pct_core_cap: float | null          # e.g. 0.80 for UK
      excluded_line_items: [string]       # e.g. ["imported_crew_per_diem"] for labour-only bases
      custom_handler_id: string | null    # escape hatch

    per_person_ceiling:
      applies: boolean
      w2_cap_amount: {value: number, currency: string} | null
      loanout_exempt: boolean
      loanout_withholding_rate: float | null
      loanout_withholding_confirmed: boolean   # false while a rate is disputed (e.g. GA 4.99% vs 5.75%)

    rate_structure:
      type: enum[flat, tiered_by_spend, blended_by_ceiling_split, headcount_scaled]
      base_rate: float
      tiers: [{threshold_low: number, threshold_high: number | null, rate: float}]
      uplifts:
        - id: string
          name: string
          additional_rate: float
          stackable: boolean
          conditions: string                # human-readable; not evaluated by engine unless codified below
          requires_separate_application: boolean
      ceiling_split:                        # UK-style: enhanced rate on first N, standard on remainder
        enhanced_threshold: {value: number, currency: string} | null
        enhanced_rate: float | null
        standard_rate: float | null
      headcount_scale: [{budget_threshold: number, max_headcount: int}] | null   # NM-style sliding scale

    minimum_spend: {value: number, currency: string} | null

    caps:
      per_project_cap: {value: number, currency: string} | null
      annual_programme_cap:
        amount: {value: number, currency: string} | null
        period: enum[calendar_year, fiscal_year] | null
        escalator_schedule: [{period_label: string, amount: number}] | null   # NM-style step-ups
      # consumption state is LIVE DATA, never stored here — see Q5. This
      # section declares the cap EXISTS; the freshness gate resolves how
      # much of it is left, at query time.
      cap_consumption_check:
        method: enum[live_research, official_dashboard, manual, not_applicable]
        source_url: string | null

    audit:
      mandatory: boolean
      fee_schedule: [{spend_threshold_low: number, spend_threshold_high: number | null,
                       fee_primary: number, fee_third_party_auditor: number | null}]

    timing:
      terms_lock_at: enum[application, start_of_principal_photography, completion]
      application_window: string
      decision_sla_days: int | null
      payout_lag:
        description: string
        typical_days: int
        interest_paid: boolean

    transfer_discount:
      applies: boolean
      typical_rate_low: float | null
      typical_rate_high: float | null
      source_note: string | null

    residency_rules:
      resident_definition: string
      nonresident_treatment: string
      custom_handler_id: string | null   # e.g. Ontario/federal pool mismatch

    validation:
      validated: boolean
      validation_pairs:
        - production_name: string
          disclosed_qualified_spend: {value: number, currency: string}
          disclosed_credit_issued_or_allocated: {value: number, currency: string}
          disclosure_stage: enum[audited_issued, allocation_estimate]
          source_url: string
          implied_rate: float
      mean_error_pct: float | null       # rolling, written by Job 1
      last_checked_against_disclosure: date | null
```

This schema directly expresses every element the question requires: base definition (`base_definition.type`), per-person ceilings and loan-out treatment (`per_person_ceiling`), tiers and uplifts (`rate_structure`), per-project cap (`caps.per_project_cap`), annual programme cap with consumption state split cleanly into declared-cap-exists (here) vs. live-consumption (Q5) (`caps.annual_programme_cap` + `cap_consumption_check`), payout mechanism and taxability (`mechanism`, `taxable`), audit fee schedule (`audit.fee_schedule`), when terms lock (`timing.terms_lock_at`), and effective dates (`effective_dates`).

**Live-researched jurisdictions (Job 2 output) populate exactly this same schema**, with `status: live_researched`, `validation.validated: false`, `validation.validation_pairs: []`, and every field that could not be confirmed left `null` with its confidence noted in `sources[].confidence` — never guessed. This is the concrete mechanism by which "a live-built model gets coerced into the same schema as a curated one" (Q4): the extraction agent's structured-output contract *is* this YAML schema (via a Pydantic model mirroring it), so there is no separate "researched-jurisdiction shape" to reconcile later.

---

## Q3 — Determinism and Explainability: the Figure/provenance pattern

**Recommendation: an immutable `Figure` value object whose own derivation chain IS the audit trail. No separate global trace/ledger object, and no full event-sourcing infrastructure.**

Three patterns were weighed:

1. **Global mutable trace/audit-log threaded through every call** — rejected. It works, but it means every function either takes a `trace` parameter (pollutes every signature, exactly what the question asks to avoid) or writes to a module-level/contextvar log (hidden coupling, hard to test in isolation, easy to silently drop entries).
2. **Full event-sourced computation** (every step is an event, final state is a fold over events, replayable) — rejected as over-engineering for 17 days. Nothing in this system needs replay-from-events or temporal queries over the *computation* itself; Balances needs historical *results* stored, which is satisfied by snapshotting final Figure trees, not by event-sourcing the arithmetic.
3. **Self-describing value object (`Figure`) forming a DAG via its own `inputs` field** — recommended.

```python
@dataclass(frozen=True)
class Figure:
    value: Decimal
    unit: str                          # "USD", "GBP", "pct", "days"
    label: str                         # "Qualifying base after GA per-person ceiling"
    derivation: tuple[str, ...]        # ordered human-readable reasoning steps
    inputs: tuple["Figure", ...]       # other Figures this was computed from — the DAG edge
    source_url: str | None
    date_checked: date | None
    confidence: Literal["validated", "researched"]
    live_fetched_this_run: bool
    figure_id: str                     # stable id, assigned at creation (content-hash or ULID)
```

Every pipeline stage (Q1) returns `Figure` objects instead of raw `Decimal`s. A `Figure` that combines other `Figure`s (e.g., `GrossCredit` built from `QualifyingBase` after a ceiling) simply lists those as `inputs` and appends its own reasoning line to `derivation` — it does not need to know or copy its inputs' full history, because the DAG is walkable at render time by following `inputs` recursively. This is exactly the cheap scoring move the brief names: rendering "only $500K of the $2M lead qualifies — Georgia per-person ceiling" is just `derivation[-1]` on the relevant `Figure`, and the full chain back to raw union rate cards is one recursive walk, not a separate query.

Practical consequences:
- **No pollution of signatures:** functions take and return `Figure`s (or tuples of them) as their normal typed values — provenance travels *with the data*, not alongside it as a second parameter.
- **Testable in isolation:** a unit test constructs a `Figure` fixture and asserts on `.value` and `.derivation` without any global state.
- **Serializes directly to the API response and to Balances snapshots:** a `Figure` is a plain dataclass — `asdict()` gives you the JSON shape for `/api/v1/figure/{id}` for free, and storing a whole `Figure` tree as a JSON column in Postgres (mirrored to S3 for permanence) is how index snapshots and the change log (Q8) are built — the change log is a diff over `Figure` trees, not a separate subsystem.
- **The engine never discards a reason:** every jurisdiction-specific adjustment step in stage 4 (Q1) *must* append a `derivation` line even when it does nothing (e.g., "no per-person ceiling applies in this jurisdiction") — this is enforced by the generic interpreter always calling every declared adjustment step, so silence is never mistaken for "not considered."

---

## Q4 — The Agentic Layer

Both jobs are built as `google-adk` pipelines: deterministic `SequentialAgent` orchestration of discrete steps, each step either a plain Python function (deterministic — extraction post-processing, recompute, scoring) or an LLM step (Gemini via `google-genai`, used specifically for unstructured-document extraction and structured output). `ParallelAgent` is used where sub-steps are independent (e.g., discovering national vs. regional programmes for a city). Parallel's Task API (`parallel-web` SDK) is the tool an ADK step calls for live web research — it returns cross-referenced, source-attributed results, which is what makes citation-per-field possible.

> **AI-services boundary — non-negotiable, stated once here because this is where it is most likely to be violated by habit:** every extraction step below — PDF table parsing, HTML table parsing, CSV structuring, free-text-to-schema mapping — **must go through Gemini** (`google-genai` or `google-cloud-aiplatform`). **AWS Textract is forbidden**, even though parsing government PDF tables (Job 1's NY/CA/NJ ingest) is exactly the task Textract is marketed for and is the single most likely accidental violation on this project. The same applies to Bedrock, Comprehend, and SageMaker, or any other AWS AI/ML service, anywhere in this system. Hosting the *process* that calls Gemini on AWS is fine; having AWS *services* do any AI work is not.

### Job 1 — Continuous validation (also silent model-rot detection)

```
Trigger: new disclosure document available (event-driven — a systemd timer
polls the 4 known disclosure URLs on a cadence matching each publisher's
own schedule: NY quarterly, CA/NJ per-update, CT per-refresh)

[1] DisclosureIngestAgent (LLM step — Gemini structured output on PDF/HTML/CSV;
    NEVER Textract/Bedrock/Comprehend, see boundary note above)
    Raw source document is fetched once and mirrored verbatim to S3
    BEFORE extraction (auditability: the exact byte-for-byte document a
    figure derives from is permanently retrievable even if the government
    page later changes or 404s).
    in:  {jurisdiction_id, source_url, raw_document}
    out: DisclosureRow[] = [{production_name, jurisdiction_id, qualified_spend,
                              nys_spend_or_equivalent, credit_issued_or_allocated,
                              disclosure_stage, disclosure_date, source_url,
                              source_document_id}]

[2] MatchAgent (deterministic)
    in:  DisclosureRow[], existing validation_pairs (Postgres)
    out: {new_rows: DisclosureRow[], already_known: DisclosureRow[]}
    GATE: rows with an unparseable qualified_spend or credit value are
    routed to a ManualReviewQueue, not silently dropped.

[3] RecomputeAgent (deterministic — calls engine stages 4-5 directly,
    NOT the full pipeline, since the disclosed qualified_spend already
    IS the QualifyingBase)
    in:  new_rows, JurisdictionRuleSet
    out: {production_name, computed_credit: Figure, disclosed_credit,
          error_pct}
    GATE: engine exception on a row → row flagged "recompute_failed",
    surfaced, never silently coerced to a number.

[4] ScoreAgent (deterministic)
    in:  all recompute results for the jurisdiction
    out: {jurisdiction_id, mean_error_pct, n_pairs, updated validation_pairs[]}
    Writes back into JurisdictionRuleSet.programmes[].validation.

[5] DriftGateAgent (LLM step — only invoked if error_pct exceeds a
    threshold, e.g. 5%)
    in:  the offending row, current JurisdictionRuleSet YAML, disclosure text
    out: DriftFlag = {jurisdiction_id, likely_cause: string,
                       suggested_rule_change: string | null,
                       confidence: LOW|MEDIUM|HIGH}
    This NEVER auto-edits the YAML. It writes a DriftFlag record for
    human review — the honest way to "detect silent model rot" without
    letting an LLM silently rewrite the audited rule file.
```

Structured output contracts at every step are Pydantic models; ADK's `output_key` writes each step's result into shared session state for the next step, which is the documented ADK mechanism for passing data through a `SequentialAgent` without ad hoc plumbing.

### Job 2 — Unknown jurisdiction, live

```
Trigger: user enters a city with no matching jurisdiction.id in the curated store

[1] DiscoveryAgent (ParallelAgent: two branches run concurrently)
    branch A: Parallel Search — "{country} national film/TV production tax
              incentive programme"
    branch B: Parallel Search — "{region/city} film incentive top-up OR
              regional film rebate {country}"
    out: DiscoveryResult = {national_candidate: {name, source_urls[]} | null,
                             regional_candidate: {name, source_urls[]} | null}
    GATE: if branch A returns nothing → short-circuit to
    status: no_programme_found (a valid terminal state, not an error).

[2] ExtractionAgent (LLM step, Gemini response_schema = the JurisdictionRuleSet
    Pydantic model from Q2 — same schema as curated jurisdictions; never
    Textract/Bedrock/Comprehend)
    in:  fetched pages/PDFs from step 1
    out: a full JurisdictionRuleSet document, status: live_researched,
         every unconfirmed field explicitly null, with a parallel
         field_confidence map: {field_path: LOW|MEDIUM|HIGH}
    This step IS the coercion into the curated schema — there is no
    separate "researched jurisdiction" shape to reconcile.

[3] ValidationGateAgent (deterministic — a completeness checklist, not an LLM)
    in:  the extracted JurisdictionRuleSet
    out: {complete: bool, missing_required: [field_path],
          decision: enum[proceed, partial_price_with_caveats, no_programme_found]}
    Required-for-pricing minimum: base_definition.type, rate_structure.base_rate,
    mechanism. Missing any of these → decision = no_programme_found or
    partial_price_with_caveats (price what's known, flag the rest LOW).

[4] PricingAgent (deterministic — reuses engine stages 3-5 UNCHANGED)
    in:  LocalizedBudget (from the core pipeline) + the new JurisdictionRuleSet
    out: full Figure tree, identical shape to a curated jurisdiction's output
    This is why schema unification in step 2 matters: one engine prices
    both curated and live-researched jurisdictions with no branching.

[5] LabelAgent (deterministic)
    stamps status: live_researched everywhere in the output, sets
    confidence: "researched" on every resulting Figure, writes the new
    JurisdictionRuleSet to the live-cache store (Q5) with a TTL, and
    returns the full priced result plus every source_url collected.
```

**Failure and low confidence are represented, never hidden**, at three levels: (a) per-field in the YAML (`null` + `field_confidence: LOW` rather than an invented plausible number), (b) per-programme (`status: no_programme_found` is a first-class, displayable terminal state — the UI shows "no programme found" as a real answer, not an error page), (c) per-Figure (`confidence: "researched"` propagates to every number derived from a live-built jurisdiction, so the UI can visually distinguish a validated NY figure from a researched Bristol one without a separate lookup).

---

## Q5 — The Caching Boundary, Deployment Topology, and Latency

**Single enforcement point:** a `DataFreshnessGate.get_or_refresh(key, data_class, ttl)` repository function. It is the *only* code in the system permitted to call an external API (GSA, State Dept, FX provider, Parallel) or read a cache row directly. Every pipeline stage, every agent step, asks the gate for data; nothing reaches around it. This makes the boundary reviewable in one file, which matters for a public repo.

| Data class | TTL | Enforced by |
|---|---|---|
| FX rates | Daily | gate checks `fetched_at` vs. 24h in the `fx_cache` Postgres table, else re-pulls from an FX provider (non-AI service, unrestricted) |
| Cap consumption / programme open-closed status | Daily–weekly | gate re-checks `cap_consumption_check.source_url` per the jurisdiction's own update cadence, cached in `cap_consumption_cache` |
| Hotel / seasonal cost data | Weekly | gate re-pulls per-diem-adjacent seasonal indices |
| Curated jurisdiction rules | Monthly + event-driven | NOT read through the live gate at all in normal operation — loaded from the versioned curated store (YAML in repo → Postgres mirror); only Job 1's DriftFlag (human-reviewed) or a scheduled monthly re-check triggers a re-read |
| Union rate cards | Annual, step-ups pre-loaded | same as curated rules — versioned, not live |
| Live-researched jurisdiction (Job 2 result) | 7–30 days (recommend 14) | gate caches the full `JurisdictionRuleSet` keyed by jurisdiction id in `live_jurisdictions`; a second user asking about the same city inside the TTL gets the cached model, still correctly labelled with its *original* `date_checked`, not today's date |

Every `Figure` records `live_fetched_this_run: bool` and `date_checked: date` regardless of cache hit or miss — a cache hit still shows the true original check date, so the UI never overstates freshness (this is the specific honesty constraint called out in Key Decisions: "avoids overselling freshness").

### Deployment topology and background execution (single Lightsail instance)

The backend runs as a **single FastAPI process** on the Lightsail instance (uvicorn behind nginx, `systemd`-supervised). This is not a serverless platform, so Job 2's live-research work cannot assume ephemeral auto-scaled concurrency — it has to be designed as an explicit background task inside a process that can restart without silently losing or hanging a request.

**Recommendation: an in-process `asyncio` background task, hardened by a durable job-state table — not a separate message broker/queue service**, which would be disproportionate infrastructure for a single instance and a 17-day build.

- `POST /api/v1/cities/research` inserts a row into a `research_jobs` Postgres table (`job_id`, `status: pending`, `created_at`), returns `job_id` immediately, and starts an `asyncio.create_task` running the ADK pipeline.
- After **every** pipeline step, the task synchronously writes its status into that same row (`status`, `current_step`, `detail`, `last_updated`, partial results so far) before proceeding. This write is the actual durability boundary — the in-memory task itself is disposable.
- `GET /api/v1/cities/research/{job_id}/stream` (SSE) tails the `research_jobs` row (polling it internally every 500ms–1s) and re-emits any change as an SSE event. Because it reads the persisted row rather than the in-memory task, a client that disconnects and reconnects (a dropped connection, a refreshed tab) resumes exactly where the job's row says it is, without re-triggering already-completed Parallel/Gemini calls.
- **What happens if the process restarts mid-job:** the in-memory `asyncio` task dies with the process. The `research_jobs` row is left at whatever it last wrote. A staleness check (comparing `last_updated` to "now" whenever the row is read) reclassifies any row with no update for >90 seconds as `status: interrupted — process restarted, please retry`. This is surfaced to the user as an honest terminal state — exactly the same treatment as `no_programme_found` — rather than a client hanging on a dead stream indefinitely. Given the 17-day window, retry-by-resubmission is an acceptable answer to a mid-job restart; true step-level resumption (restart from the last completed step instead of from scratch) is a reasonable post-Milestone-1 enhancement, not required now.
- `systemd` supervises the FastAPI process itself (auto-restart on crash) — which is also what makes the interruption case above a real scenario worth designing for, not a hypothetical.
- This same durable-row pattern is reused, at lower stakes, for the Balances scheduled job (Q8): the job writes its own progress/status so a stuck or failed scheduled run is visible rather than silently missing.

### Latency budget and progress feedback

A cold Job 2 run (Discovery → Extraction → Validation Gate → Pricing → Label) realistically costs 30–90 seconds, dominated by Parallel Search + Gemini extraction latency.

- Each ADK pipeline step emits a real event on completion — never a synthetic delay. Example stream:
  `{"step":"discovery","status":"done","detail":"Found AVEC/IFTC (UK national scheme)"} → {"step":"discovery","status":"done","detail":"Checking for regional top-up..."} → {"step":"extraction","status":"running"} → {"step":"extraction","status":"done","field_confidence_summary":{...}} → {"step":"pricing","status":"done"} → {"final": {...priced result...}}`
  This satisfies the "never fake progress" constraint literally: every emitted event corresponds to a completed pipeline stage recorded in `research_jobs`, not a timer.
- Target: first event within 2s (acknowledging receipt), an event at least every 10–15s thereafter, hard ceiling ~120s after which the endpoint returns a partial result labelled `no_programme_found — research incomplete, retry` rather than hanging indefinitely.
- Fallback for clients that can't consume SSE (or proxies/CDNs that buffer it): `GET /api/v1/cities/research/{job_id}/status` polling the same `research_jobs` row, documented as the degraded path.

---

## Q6 — API and Frontend Contract

**Slider design decision: one request returns the full quarterly time series per city; the slider re-indexes client-side.** Re-requesting per drag position cannot "feel live" over a network round trip involving jurisdiction rule evaluation across every candidate city; pre-computing a bounded window (recommend 8 quarters forward from the earliest allowed start) and shipping it in one payload makes dragging instantaneous because it's a local array index, not a fetch. Only a change to the production spec or the city list triggers a new `POST /price`.

### Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/price` | POST | Body: `ProductionSpec` + `candidate_cities[]`. Returns the full multi-city, multi-quarter priced result (below). |
| `/api/v1/price/{run_id}/gap` | GET (`?city_a=&city_b=&quarter=`) | Server-computed decomposed gap for a permalink/share case; the frontend can also compute this client-side from the same payload for zero-latency pick-any-two interaction |
| `/api/v1/figure/{figure_id}` | GET | Full `Figure` — derivation chain, source_url, date_checked, confidence, live_fetched_this_run. What every clickable number resolves to. |
| `/api/v1/jurisdictions` | GET | List of jurisdictions with `status` (curated_validated / live_researched / none yet) — drives initial map coloring/legend |
| `/api/v1/cities/research` | POST (SSE) | Job 2 entry point for an uncurated city |
| `/api/v1/cities/research/{job_id}/status` | GET | Polling fallback for the same job, backed by the same `research_jobs` row |
| `/api/v1/validation/summary` | GET | Job 1's rolling accuracy metric — "tested against N government-disclosed awards, mean error X%" — used by both the calculator's proof panel and Balances |
| `/api/v1/index/latest` | GET | Balances — latest reference-production snapshot |
| `/api/v1/index/history` | GET | Balances — time series for movement charts |
| `/api/v1/index/changelog/{date}` | GET | Balances — dated change-log entries |

### Response shape (the part that makes every number clickable)

Numbers are never bare — every value in the payload is a lightweight `FigureRef`, not a raw number, keeping the main payload lean while still making every figure independently addressable:

```json
{
  "run_id": "run_9c2f",
  "cities": [
    {
      "city_id": "us-ny-nyc",
      "jurisdiction_status": "curated_validated",
      "quarters": [
        {
          "quarter_label": "2027-Q1",
          "start_date": "2027-01-01",
          "total_landed_cost": {"value": 48250000, "unit": "USD", "figure_id": "f_a1", "confidence": "validated"},
          "components": {
            "labour": {"value": 21000000, "unit": "USD", "figure_id": "f_a2", "confidence": "validated"},
            "housing_per_diem": {"value": 3100000, "unit": "USD", "figure_id": "f_a3", "confidence": "validated"},
            "stages_equipment": {"value": 5200000, "unit": "USD", "figure_id": "f_a4", "confidence": "validated"},
            "incentive_net_cash": {"value": -9600000, "unit": "USD", "figure_id": "f_a5", "confidence": "validated"}
          },
          "incentive_arrival": {"estimated_date": "2028-04-01", "figure_id": "f_a6"}
        }
      ]
    }
  ]
}
```

`GET /api/v1/figure/f_a5` lazily returns the full derivation chain (the per-person ceiling line, the tier applied, the transfer discount, the audit fee) — this keeps `/price` fast enough for slider responsiveness while every number remains one click from its government source.

---

## Q7 — Build Order and Critical Path

Phase 0 (source verification: reconcile NY's cap, confirm the CT CSV schema, lock the 11 validation pairs) is already decided and not re-litigated here. Everything below assumes it lands first because both the schema (Q2) and Job 1 (Q4) need its outputs to be correct rather than merely plausible.

```
Day 0-1   Phase 0 — source verification (decided)
          IN PARALLEL: instance provisioning (nginx, systemd unit files,
          Postgres, an S3 bucket for source-document/snapshot mirrors) —
          cheap, non-blocking, do it alongside Phase 0/1.
                │
Day 2-4   Phase 1 — CRITICAL PATH, cannot parallelize meaningfully:
          JurisdictionRuleSet schema + Figure/provenance pattern + generic
          rule engine skeleton (stages 3-5) + CanonicalBudget model skeleton
          (stages 1-2). This is the spine every jurisdiction, both agent
          jobs, and the API response shape all plug into.
                │
          Phase 2 — THINNEST VERTICAL SLICE (ships end of this window):
          one hardcoded jurisdiction (New York — gold-standard disclosure,
          the Anora anchor) wired end-to-end: minimal frontend form → API
          → engine → Figure output → hosted URL on the Lightsail instance
          showing "$3,964,760 qualified spend → $991,190 credit issued"
          with its citation. This is the first REAL CITED NUMBER on a
          hosted URL — hit this milestone before anything else broadens.
                │
        ┌───────┴────────────────────────────────────────────┐
Day 5-9 │ PARALLELIZABLE (all depend only on Phase 1 landing) │
        ├──────────────────────────────────────────────────────
        │  Track A: CA, NJ, CT jurisdiction YAMLs + validation
        │           pairs — independent of each other, independent
        │           of Track B/C, can be split across sessions/people
        │  Track B: Frontend build-out (map, slider, ranked list,
        │           gap panel, proof panel) against the Phase 1/2
        │           API contract, using NY + mocked cities until
        │           Track A lands
        │  Track C: Job 1 validation-loop agent — can start against
        │           NY alone (lower risk: known jurisdiction, known
        │           correct answer) while Track A finishes CA/NJ/CT
        └──────────────────────────────────────────────────────┘
                │
Day 10-12 Phase 4 — Job 2 live-research agent. Sequenced AFTER Job 1
          on purpose: it reuses the same extraction/structured-output
          machinery at materially higher risk (unknown jurisdiction,
          unknown correct answer), so Job 1 is the cheaper place to
          find ADK/Parallel integration problems first. (If two people
          are available, Job 1 and Job 2 can run concurrently instead —
          note this as the one place solo vs. team changes the order.)
                │
Day 12-14 Phase 5 — Caching boundary (DataFreshnessGate) + durable job-state
          table + SSE progress streaming + full quarter-series wiring for
          the slider + seasonal/per-diem/FX live data wired through the gate
                │
Day 14-15 Phase 6 — Demo-critical polish: UK naive-math-wrong worked
          example, the ranking-inversion case, proof panel, citations
          UI pass, demo video script
                │
Day 15-16 Buffer + SHIP GATE — Milestone 1 (Accounts) complete;
          this alone satisfies the hosted-URL Definition of Done
                │
Day 16-17 Milestone 2 (Balances), TIME-BOXED AND CUTTABLE:
          reference production definition, systemd timer job, historical
          snapshot storage (Postgres + S3), change log, reverse mode.
          If Accounts slips, Balances is what gets cut — it is
          explicitly the next milestone, not part of the submission
          gate.
```

**Explicitly parallelizable:** the four jurisdiction models (Track A) are independent of each other by construction — the schema is additive per Q1/Q2 — and independent of frontend work (Track B) once the API response shape is fixed, which is why locking that shape during Phase 1 (even before all cities are priced) is itself high-leverage even though the frontend isn't formally "critical path."

**Genuinely sequential (critical path):** Phase 1 (schema+engine) blocks everything; Phase 2 (vertical slice) should not be skipped even under time pressure because it is the cheapest way to prove the hosted-URL-with-a-real-cited-number claim before investing in breadth; Job 2 depends on Job 1's plumbing being proven if built solo.

---

## Q8 — Reference Production and Index Architecture (Balances)

- **Where the schedule runs:** recommend a **`systemd` timer** on the Lightsail instance (or, if the implementer prefers, a plain crontab entry — functionally equivalent at this scale), invoking a small CLI entrypoint (`python -m prodfin.jobs.run_index`) that imports and calls the same Core Pipeline library used by the interactive calculator. This keeps the scheduler a thin trigger around a reusable, independently-testable job function, never a bespoke script duplicating pipeline logic. A `systemd` timer unit is a plain text file checked into the repo (`deploy/prodfin-index.timer` + `.service`) — itself auditable, since a reviewer can read the exact schedule and command without touching any cloud console. This is recommended over **EventBridge Scheduler** because the instance is already provisioned and always-on; EventBridge would add a managed AWS component whose only job is to periodically hit an endpoint that a local timer does natively, for no benefit at this scale (one instance, a handful of runs a day/week) and one more moving part to explain in the write-up. **If** the team later wants managed retry/alerting/observability decoupled from the instance's own uptime, EventBridge Scheduler invoking an authenticated HTTPS trigger endpoint on the instance is the natural upgrade path — worth noting as a post-Milestone-1 option, not required now.
- **Historical storage:** recommend **Postgres** (self-hosted on the Lightsail instance, or Amazon RDS if the instance shouldn't also run the database) as the primary store for `index_runs` — one row per run holding `run_id`, `run_date`, the reference-production spec hash, `engine_version`, the `jurisdiction_ruleset_version` used per city, and a JSON column with the full Figure tree. Postgres over SQLite specifically because movement queries ("how has NY's landed cost changed over the last 8 runs") are exactly what SQL time-series aggregation is for, and a single co-located Postgres instance is simple to provision and back up on Lightsail. In parallel, **mirror every run's JSON snapshot to S3** (`s3://prodfin-index/runs/{run_id}.json`) as an immutable, independently-fetchable object — this is the auditability-weighted choice: an S3 object is a permanent, content-addressable artifact that survives even if the API or database schema changes later, and can be linked to directly (`/api/v1/index/history` can proxy or redirect to the S3 URL) without depending on the live API server staying up in its current shape. Raw fetched government source documents (the PDFs/CSVs Job 1 ingests) are mirrored to S3 the same way, verbatim, before any extraction happens (see Q4) — so a citation always resolves to the exact byte-for-byte document a figure was derived from, not a live government URL that might later change or 404.
- **Change log attribution:** unchanged from the original design — diff the new run's Figure tree against the immediately prior run's, component by component; attribute the cause by comparing `source_url` / `jurisdiction_ruleset_version` between the two Figures (rule change) versus only `date_checked` advancing on the same source (routine refresh). This logic lives in the Core Pipeline library, not in the scheduler, so it runs identically whether triggered by `systemd`, a manual CLI invocation, or (later) EventBridge.
- **Permanent per-data-point URLs:** every `Figure`'s `figure_id` is stable at creation and, combined with the S3-mirrored run snapshot, gives two durable citation paths: `GET /api/v1/figure/{figure_id}` for the live API's rendered view, and the raw S3 JSON object for a citation that outlives any particular API deployment. Nothing is ever deleted from either store.

---

## Anti-Patterns

### Anti-Pattern 1: Per-jurisdiction Python subclasses
**What people do:** one `GeorgiaIncentive`, `NewYorkIncentive`, `OntarioIncentive` class implementing a shared interface.
**Why it's wrong:** every new jurisdiction (curated or, worse, LLM-built at request time) requires a code change and a code review; it is the opposite of additive, and it makes an LLM-authored jurisdiction (Job 2) mean LLM-authored *executable code* landing in a public repo — an audit and safety problem.
**Do this instead:** one generic engine interpreting a declarative `JurisdictionRuleSet`, with a small named handler registry for true exceptions only.

### Anti-Pattern 2: Ranking on headline rate, or accepting a budget as input
**What people do:** "enter your budget, see states sorted by rate."
**Why it's wrong:** explicitly named as wrong by 20–40% in the sourced research and explicitly out of scope in `PROJECT.md`; also makes the whole comparison circular, since a dollar buys a different production in each city.
**Do this instead:** the pipeline in Q1 — one canonical budget, localized per city, ranked on net landed cost.

### Anti-Pattern 3: A progress bar driven by a timer instead of real pipeline events
**What people do:** `sleep(3)` behind a spinner while "researching."
**Why it's wrong:** explicitly named in `PROJECT.md` as a Stage One disqualifier ("a `sleep()` behind a progress bar is a Stage One death").
**Do this instead:** the SSE contract in Q5 — every emitted event corresponds to a real, completed ADK pipeline step recorded in `research_jobs`.

### Anti-Pattern 4: Reaching for an AWS AI service because it's convenient on the hosting platform
**What people do:** since the backend runs on AWS, use Textract for the PDF tables in Job 1 (it's "right there," IAM is already set up, and it's genuinely good at exactly this kind of table extraction).
**Why it's wrong:** the AI-services boundary is Google Cloud AI plus Parallel only, independent of where the process is hosted. Textract, Bedrock, Comprehend, and SageMaker are all disqualifying, and Textract is the single most likely accidental violation because table-extraction-from-PDF is its flagship use case.
**Do this instead:** every extraction/structured-output step goes through Gemini (`google-genai`/`google-cloud-aiplatform`), full stop — hosting infrastructure and AI-service selection are two independent decisions in this project, and only the first one is AWS.

---

## Sources

- `feasibility-incentives.md`, `idea-2-incentives.md`, `productionfinance-brief.md`, `.planning/PROJECT.md` (project-supplied primary research and constraints)
- [Google ADK — Sequential workflow agents](https://google.github.io/adk-docs/agents/workflow-agents/sequential-agents/) — `SequentialAgent`/`ParallelAgent` orchestration, shared session state via `output_key`
- [Developer's guide to multi-agent patterns in ADK](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)
- [Parallel API Overview](https://docs.parallel.ai/getting-started/overview) and [Parallel Python SDK](https://github.com/parallel-web/parallel-sdk-python) — Task API / Task Groups for concurrent, source-attributed research
- [Rule Engine Design Pattern](https://www.nected.ai/us/blog-us/rules-engine-design-pattern) and [Symmetry payroll tax compliance architecture](https://www.symmetry.com/payroll-tax-compliance-infrastructure) — declarative, versioned, configuration-driven rule engines as the standard shape for multi-jurisdiction compliance systems, cross-checked against this project's own normalization requirement
- Hosting/infrastructure recommendations (AWS Lightsail, systemd timers, Postgres, S3) reflect an owner-supplied constraint update dated 2026-08-23 and standard AWS single-instance deployment practice, not a separate research pass — no additional external sourcing was needed for this part.

---
*Architecture research for: ProductionFinance*
*Researched: 2026-08-23 (revised same day for AWS hosting constraint)*
