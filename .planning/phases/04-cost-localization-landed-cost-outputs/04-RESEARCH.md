# Phase 4: Cost Localization & Landed-Cost Outputs - Research

**Researched:** 2026-08-26
**Domain:** Deterministic cost-modelling engine extension (Python/Pydantic/Decimal) — no new external dependency, no runtime network call
**Confidence:** MEDIUM — the engine-side design is HIGH confidence (mirrors four already-proven Phase 2/3 patterns exactly); the underlying cost DATA (per-diem seasonality, union fringe percentages, stage/equipment reference rates) is a mix of HIGH-confidence primary-source figures and MEDIUM/LOW-confidence industry commentary that the plan must treat as `basis: estimated` or `modelling_assumption`, never `sourced`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Numbering continues from Phase 3's D-31…D-52. All decisions below were made by Claude under full delegation ("you decide all") — every one carries stated rationale and is a working decision, not a fixed requirement, EXCEPT the four flagged load-bearing on the project's honesty claim (D-56, D-59/D-63, D-64, D-72), which should be escalated rather than quietly reversed if inconvenient.

- **D-53:** A `CityCostProfile` is Phase 4's artifact; a `JurisdictionRuleSet` is Phase 5's, and building the first does not touch the second. `CityLocalizer` is JURISDICTION-AGNOSTIC. A Los Angeles cost profile needs IATSE Local 80/600/700 scale, LA County GSA per diem and stage/equipment references — nothing from `us-ca.yaml`. Phase 4 may build cost profiles for cities whose rule files do not exist yet. Reversibility: costly.
- **D-54:** The committed city set has a floor of three (**New York, NY**; **Los Angeles, CA**; **London, UK**) and a declared stretch, in order: **Atlanta, GA**, **Newark/Jersey City, NJ**, **Hartford, CT**.
- **D-55:** The ranked list is ranked on NET landed cost, and only cities whose incentive is actually modelled are ranked. Every other city appears in the same response, ordered by cost, in a visibly separate band carrying its cost-only total and an explicit `incentive_not_modelled` state. Never interleaved with net-ranked cities. Reversibility: costly.
- **D-56 (REJECTED, load-bearing):** treating an unmodelled incentive as `$0`. A city with no rule file has an **unknown** incentive, not a zero one. `engine.net_cash.transferable` already refuses to convert at an unsourced discount rate rather than inventing a midpoint — the same refusal shape applies here. Reversibility: one-way.
- **D-57:** Phase 4 makes no runtime network call, and adds no new dependency. Every cost input lands as a committed, dated snapshot in the repo, read with the `pyyaml` already in `pyproject.toml`. Reversibility: reversible.
- **D-58:** A new orthogonal `basis` field on cost figures. `Figure.confidence` gains no third value. Values: `sourced` (a published rate card row, a GSA per diem row), `estimated` (computed from a sourced input by a disclosed method), `modelling_assumption` (no public source exists anywhere; `data/crew_tiers.yaml`'s `basis: modelling_assumption` is the precedent). Reversibility: costly.
- **D-59 (load-bearing):** `basis` degrades to the weakest input, exactly like `combined_confidence` — and never defaults to `sourced` on an empty input list. **Landmine:** `engine/figure.py::combined_confidence` returns `"validated"` for an empty sequence — correct for its own use, a trap if copied. `combined_basis` must raise, or return the weakest value, on an empty sequence; never mirror that default. Reversibility: one-way.
- **D-60:** Acknowledged gaps (overtime, turnaround penalties, meal penalties, kit fees, non-union local differentials, negotiated hotel rates) are a declared exclusion list, not a `$0` line. Rendered as a named, first-class list of what this model does not price, attached to the total.
- **D-61:** The per-diem ceiling caveat is a structural field on the Figure itself, not UI copy — *"federal reimbursement ceiling, not a market rate; actual cost is likely higher, especially in peak season or a tight-inventory market."*
- **D-62:** Fringe and payroll burden are their own line, never folded into the wage line. Sourced per union where the union publishes its fringe schedule (`basis: sourced`); a blanket multiplier only where it does not, with the method disclosed (`basis: estimated`).
- **D-63 (load-bearing):** A CI gate asserting that no `Figure` reachable from a Route A total carries `confidence: "validated"`. Walk the recursive `inputs` DAG from the total and fail on any `validated` node. Reversibility: costly.
- **D-64 (load-bearing):** Seasonality is sourced-only. It rides on published per-diem month bands and nothing else. Seasonal stage availability, crew scarcity and equipment demand are not published anywhere and are declared acknowledged gaps under D-60. **Open question the user flagged:** this rests on GSA publishing monthly lodging rates for the floor cities — confirm before planning around it. **RESOLVED BELOW with a correction — see Open Questions.** Reversibility: reversible.
- **D-65:** A shoot calendar is derived, because housing nights require one anyway. Spread `shoot_days_stage + shoot_days_location` across calendar months from the start quarter at a declared shooting-days-per-week rate (`basis: modelling_assumption`, named in the assumptions list), then weight each month's per-diem band by nights falling in it.
- **D-66:** The response names its quarter-invariant lines — which lines did NOT move with the quarter, not just which did.
- **D-67:** Sensitivity is perturbation, one input at a time, re-running the real pipeline. Never an analytic derivative — the model has cliffs (minimum-spend, tiered rate bands, `blended_by_ceiling_split`, per-project cap) a derivative cannot see.
- **D-68:** Per-input step sizes are declared in a small committed YAML table (mirrors `tests/mutation_targets.yaml`), each in its own natural unit, displayed on every row. No shared scale across incommensurable inputs.
- **D-69:** A perturbation that crosses a cliff says so, on that row.
- **D-70:** A CI grep over the sensitivity output strings for prescriptive vocabulary (*"recommend", "should", "consider", "best", "optimal", "you could"*) — fail on a hit.
- **D-71:** Route A returns dollars now, and its qualified spend is never `validated` (forced by D-59). `SPEND_NOT_DERIVED` in `app/services/spec.py` is retired and replaced by a real figure — retired, not left dangling.
- **D-72 (load-bearing):** A validation pair may never route through the budget model, and a test asserts it. Disclosures publish qualified spend and the award, NOT the production's input vector. Validation pairs keep feeding disclosed spend directly into `price_jurisdiction`. Reversibility: one-way.
- **D-73:** Route A and Route B stay visibly distinct. From Phase 4 both return a credit figure; the only difference is where the qualified spend came from — modelled versus disclosed.
- **D-74:** FX is a committed dated snapshot, and a missing pair is a refusal, not a cross-rate. `data/fx/` records `base`, `quote`, `rate`, `as_of_date`, `source_url`, `retrieved_at`, surfaced as its own `Figure` with `basis: sourced`.
- **D-75:** Currency is a first-class component of the gap decomposition, not a hidden conversion. A London-vs-New-York gap must show how much of the difference is the FX rate on its own line.
- **D-76:** INC-10's exemptions are cost reductions and never touch the incentive figure. A sales-tax or hotel-occupancy exemption reduces the cost line it applies to, as its own named sourced stackable figure.
- **D-77:** OUT-04 — tag every budget line with its ATL/BTL/Post account at creation; do not build the view. Tagging costs nothing at model-definition time; the rendered breakdown is Phase 11's. Reversibility: reversible.
- **D-78:** Golden cost tests — a fixed `ProductionSpec` plus fixed cost profiles must produce exact `Decimal` totals in CI. All cost arithmetic goes through `engine/rounding.py::quantize_money`, `Decimal` only, every numeric value quoted (RD-01).

### Claude's Discretion

Every decision above is Claude's discretion — the user delegated all four gray areas in full ("you decide all, give your most thoughtful answer"). Downstream agents should treat them as working decisions with stated rationale, and overturn any of them on the user's word without needing to re-argue the case. Four are load-bearing on the project's honesty claim and should be escalated rather than quietly reversed if inconvenient: **D-56**, **D-59/D-63**, **D-64**, **D-72**.

### Deferred Ideas (OUT OF SCOPE)

- CA / NJ / CT jurisdiction rule files and Job 1 — Phase 5. Phase 4 builds cost profiles for cities in those jurisdictions; it does not build their rule files.
- `DataFreshnessGate` and the live cache boundary — Phase 7. Phase 4's committed snapshots become its cold-start seed.
- Live FX, live per diem, live rate-card refresh — Phase 7. Phase 4 commits dated snapshots.
- The map, slider, ranked-list treatment and the consolidated printable assumptions panel (PRV-04) — Phase 6. Phase 4 owes the data; Phase 6 owes the panel.
- The rendered ATL/BTL/Post chart-of-accounts view (OUT-04) — tags land here, the view is Phase 11's.
- Overtime, turnaround penalties, meal penalties, kit fees, non-union local differentials, negotiated hotel rates — declared acknowledged gaps, not modelled in Accounts.
- Seasonal stage / crew / equipment variation — an acknowledged gap under D-64 until a sourced index exists. Not a multiplier, ever.
- Reverse mode ("what change would close this gap") — Phase 11.
- Extending the mutation table (D-51) to a cost anchor — Phase 8's SHP-14 re-proof, once D-78's golden cost totals exist.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COST-01 | One identical budget model localized per city — never compared against published rates | `engine/budget.py` (new, `BudgetModelBuilder`) below; verified `ProductionSpec` contract at `engine/spec.py:60-134` is the single input it consumes |
| COST-02 | Labour localized against published union rate cards (IATSE, SAG-AFTRA, DGA, WGA, BECTU, ACTRA) | IATSE Local 600 (`icg600.com`) and SAG-AFTRA (`sagaftra.org`) publish official rate-card PDFs — see Standard Stack / Sources. BECTU publishes department rate cards (`bectu.org.uk`, `britishfilmdesigners.com`) — same shape. |
| COST-03 | Labour includes fringe and payroll burden, not bare scale | D-62; PITFALLS E1; SAG-AFTRA P&H 21% and DGA P&H 22.25% (2026) are union-published percentages — `sourced`. A blanket IATSE-wide "35-45%" figure found in this session is industry commentary, not a union document — `estimated`/`ASSUMED`, see Assumptions Log. |
| COST-04 | GSA/State Dept per diem, labelled as reimbursement ceiling not market rate | D-61; PITFALLS E4; verified below that NYC per diem varies by month and LA County per diem is FLAT for FY2026 — this is the D-64 open question, resolved |
| COST-05 | Flights/housing computed for imported crew and cast specifically | D-65's shoot-calendar-derived nights; `ProductionSpec.crew_imported_count` / `principal_cast_imported_count` already exist at `engine/spec.py:75,79` |
| COST-06 | Stage/equipment/permit/location/trucking, estimated lines labelled | No government source exists for any of these — confirmed by this session's search (see Common Pitfalls). All `basis: estimated` or `modelling_assumption`, never `sourced`. |
| COST-07 | Start quarter drives seasonal cost variation, not only incentive availability | D-64/D-65/D-66; per-diem month-band data confirmed to exist (NYC) and not exist (LA County) — the per-city fallback in D-64 is load-bearing here |
| COST-08 | Multi-currency via a dated, cited FX rate | D-74; Frankfurter API (`frankfurter.dev`) confirmed no-key, historical-date endpoint — committed as a snapshot, never called at runtime (D-57) |
| INC-10 | Sales tax / hotel occupancy exemptions as separate stackable cost reductions | D-76 — same `Figure` + `basis` pattern as every other cost line, attached to the cost side, never netted into the credit |
| OUT-01 | Total landed cost per city, ranked | D-55's two-band ranking; `engine/ranker.py` (new) |
| OUT-02 | Gap between two cities, decomposed by component | D-75; `engine/gap.py` (new); the NY-vs-LA cost-only gap is the phase's real, complete demo output per CONTEXT.md's phase-boundary note |
| OUT-03 | Sensitivity — single input that most moves the gap, as a delta, never prescriptive | D-67…D-70; re-run-the-pipeline perturbation, declared step table, cliff-crossing detection, CI vocabulary grep |
| OUT-04 | ATL/BTL/Post chart-of-accounts alignment (stretch) | D-77 — tag only, no view. Standard ATL/BTL department-ratio percentages found this session are industry-commentary blog aggregates, not a primary source — `ASSUMED`, tag every line `basis: modelling_assumption` |
</phase_requirements>

## Summary

Phase 4 extends four already-proven Phase 2/3 patterns onto the cost side rather than inventing new ones: the immutable, self-citing `Figure` (`engine/figure.py`), the pinned `Decimal` rounding call site (`engine/rounding.py::quantize_money`), the refuse-rather-than-invent convention (`engine.net_cash.transferable` returning `low`/`high`/`point=None` instead of a fabricated midpoint), and the committed-YAML-in-repo data layer (`jurisdictions/*.yaml`, `data/crew_tiers.yaml`). The one genuinely new structural element is D-58's `basis` field — a third, orthogonal provenance axis distinct from `Figure.confidence` (validated/researched) and `Source.confidence` (HIGH/MEDIUM/LOW) — which must be added carefully: `Figure` is a frozen `kw_only` dataclass with **no defaulted fields except `figure_id`** (`engine/figure.py:54-74`, verified), so adding `basis` as a bare required field would break every existing `Figure(...)` construction site across `engine/credit.py`, `engine/net_cash.py`, `engine/qualifying_base.py` and `engine/pipeline.py`. The plan should default `basis: Basis | None = None` and treat non-`None` as the cost-side signal — D-58 itself frames this as an axis specific to cost figures, not a retrofit of the whole incentive engine.

This session's own research resolves the phase's single flagged open question with a correction: **GSA's FY2026 per diem rate for New York County genuinely varies by month** ($179–$342/night across the year — [CITED: gsa.gov FY2026 per-diem lookup, fetched via WebFetch this session]), but **Los Angeles County's FY2026 rate is flat** at $191/night for every month ([CITED: gsa.gov FY2026 per-diem lookup, fetched via WebFetch this session]) — LA is not designated a seasonal Non-Standard Area for FY2026. **Confidence note:** these two figures were read through a WebFetch pass (an AI-summarized reading of the official GSA page, not a raw table/CSV opened byte-for-byte) — the seam's own `classify-confidence --provider webfetch --verified` call returns `LOW`, not `HIGH`, precisely because AI-summarized table extraction can misread a cell. Tag these `[CITED]`, not `[VERIFIED]`, and re-confirm the exact month-by-month figures directly from the GSA bulk CSV/Excel file (`gsa.gov/travel/plan-a-trip/per-diem-rates/per-diem-files`) before committing them to `data/per_diem/*.yaml` with `basis: sourced` — the *existence* of monthly variation for NY and its *absence* for LA is the load-bearing structural finding this research delivers with confidence; the exact per-month dollar figures are directionally reliable but not yet re-verified against the raw file. D-64's own stated fallback — "seasonality is sourced where a month band exists and explicitly absent where it does not, stated per city, never backfilled with a multiplier" — is therefore the operative rule, not a hypothetical: New York's OUT-02 gap decomposition will show a genuine per-diem seasonal swing; Los Angeles's will not, and the response must say so explicitly (this is exactly what D-66 already requires).

The cost side of this phase divides cleanly into two data-honesty tiers. Tier one is genuinely `sourced`: GSA domestic per diem (bulk CSV/Excel, no API key, at `gsa.gov/travel/plan-a-trip/per-diem-rates/per-diem-files`), State Department foreign per diem (published monthly, Excel bulk download, `allowances.state.gov`), IATSE Local 600's official rate-card PDFs (`icg600.com`), SAG-AFTRA's published theatrical/low-budget scale (`sagaftra.org`), DGA's published Pension & Health contribution percentages, BECTU/PACT department rate cards (`bectu.org.uk`, official union site), and Frankfurter's dated FX rates. Tier two has no government or union primary source anywhere and must never be labelled `sourced`: stage/equipment/permit/trucking/location day rates (studio marketing pages, wildly variable, no standardized public rate card — confirmed by this session's search), department-ratio percentages for ATL/BTL/Post tagging (industry-blog aggregates, not a primary document), and any blanket cross-union fringe percentage not tied to a specific union's own published schedule.

**Primary recommendation:** Build the six new pipeline stages (`BudgetModelBuilder`, `CityLocalizer`, `LandedCostAggregator`, `Ranker`, `GapDecomposer`, plus a seasonality/FX support layer) as new single-purpose modules in `engine/`, one per stage, mirroring the existing `qualifying_base.py` → `credit.py` → `net_cash.py` → `pipeline.py` shape exactly. Add `basis` to `Figure` as `Optional`, default `None`. Commit all new reference data as quoted-string YAML under `data/` and `sources/`, following `data/crew_tiers.yaml` and `sources/MANIFEST.yaml`'s existing conventions byte-for-byte. Do this and every COST/OUT/INC-10 requirement is addressable with zero new runtime dependencies and zero new network calls, exactly as D-57 requires.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CanonicalBudget construction | Engine (`engine/budget.py`, new) | — | Jurisdiction-agnostic per ARCHITECTURE.md Q1 stage [1] and D-53 — pure function over `ProductionSpec` + `data/crew_tiers.yaml`, no HTTP, no per-city branch |
| Per-city cost localization | Engine (`engine/cost_localizer.py`, new) | Data (`data/cost_profiles/*.yaml`) | ARCHITECTURE.md Q1 stage [2] is explicit: "JURISDICTION-AGNOSTIC (this is cost, not incentive rules)" — the engine reads a `CityCostProfile`, never a jurisdiction id |
| Union rate card / fringe lookup | Data (`data/union_rates/*.yaml`) | Engine (reader) | Committed snapshot per D-57; no live union-agreement API exists to call even if network were allowed |
| GSA / State Dept per diem, seasonality | Data (`data/per_diem/*.yaml`) | Engine (`engine/seasonality.py`, new) | D-57 commits the snapshot; D-65's shoot-calendar derivation and month-weighting is pure engine logic over that committed table |
| FX conversion | Data (`data/fx/*.yaml`) | Engine (`engine/fx.py`, new) | D-74 — committed dated snapshot, refuse-rather-than-cross-rate logic lives in the engine reader |
| Qualifying base / credit / net cash (Route A, now dollar-producing) | Engine (existing `engine/qualifying_base.py`, `credit.py`, `pipeline.py`) | App (`app/services/spec.py`) | D-71 reverses the Route A import boundary — the app service layer now legitimately calls into the engine pricing path it previously forbade itself from importing |
| Route A HTTP handling, form validation | App (`app/routers/spec.py`, `app/services/spec.py`) | — | Unchanged tier — D-71 changes what the service *returns*, not which tier owns HTTP/validation |
| Ranking, gap decomposition, sensitivity display | Engine (`engine/ranker.py`, `engine/gap.py`, new) | App (JSON serialization) | Pure `Decimal` computation belongs in the engine per the established `figure_to_dict` boundary (`engine/figure_serialize.py:26-42`, verified) — the app layer only serializes, never computes |
| Rendered UI (ranked list, map, gap panel) | Out of scope this phase | Phase 6 | CONTEXT.md "Not in this phase" — server-rendered Jinja over the same JSON handlers is Phase 6's work; Phase 4 owes the JSON contract only |

## Standard Stack

### Core

No new core dependency. Phase 4 is explicitly constrained by D-57 to add **zero** new packages — every cost input is a committed snapshot read with the `pyyaml` already declared in `pyproject.toml` (`pyyaml==6.0.3`, verified — `pyproject.toml`, read this session). `decimal.Decimal` (stdlib) remains the only arithmetic type, quantized exclusively through `engine/rounding.py::quantize_money` (verified, `engine/rounding.py:28-37`).

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pyyaml` | `6.0.3` [VERIFIED: pyproject.toml, read this session] | Parse new `data/cost_profiles/*.yaml`, `data/per_diem/*.yaml`, `data/fx/*.yaml`, `data/union_rates/*.yaml` | Already the repo's only YAML loader (`engine.spec.resolve_crew_tier` uses `yaml.safe_load` exclusively — `engine/spec.py:158`, verified). Adding a second YAML library would violate D-57 for no benefit. |
| `pydantic` | `>=2` [VERIFIED: pyproject.toml] | `CityCostProfile`, per-diem-table, FX-snapshot, union-rate schema models — mirrors `engine/models.py`'s `StrictModel`/`Jurisdiction`/`Source` pattern (`engine/models.py:94-153`, verified) | Same reasons Phase 2 chose it: `extra="forbid"` on every schema model catches a typo'd YAML field at load time, not at a later `.get()` call |
| `decimal.Decimal` | stdlib | All new cost arithmetic | `engine/rounding.py`'s docstring states the repo's single-call-site rounding rule explicitly — no new `.quantize()` call site anywhere, cost side included (verified) |

### Supporting

No new supporting libraries. RD-01's "every numeric YAML value is a quoted string" convention (verified at `jurisdictions/us-ny.yaml:74` — `base_rate: "0.25"`, and `data/crew_tiers.yaml:30-43` — every `headcount_low`/`headcount_high` quoted) extends unchanged to every new data file this phase adds.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Committed YAML snapshots (per D-57) | A live GSA API call (`api.gsa.gov/travel/perdiem/v2/...`, requires a free API key — confirmed this session) | Rejected by D-57 explicitly: adds a runtime network dependency and an API-key secret to a phase whose entire cost side must be offline-deterministic for D-78's golden tests to be meaningful in CI |
| Committed YAML snapshots for FX | Live call to Frankfurter (`api.frankfurter.dev`, no key required — confirmed this session, `frankfurter.dev`) | Same D-57 rejection — Frankfurter is the correct *source* to pull the one-time snapshot from, never a runtime call site in this phase (Phase 7 wraps it live later per D-57's own reversibility note) |
| A single blanket cross-union fringe multiplier | Per-union sourced fringe schedules (SAG-AFTRA 21% P&H, DGA 22.25% P&H for post-2026-07-01 principal photography, both union-published) | D-62 requires sourcing per union where the union publishes its own schedule — a blanket multiplier is only the fallback where no union-specific figure exists, and must carry `basis: estimated` with the method disclosed, never `sourced` |

**Installation:** None. `uv sync` already installs everything this phase needs.

**Version verification:** `pyproject.toml` was read directly this session (`pyproject.toml:1-24`) — `pyyaml==6.0.3`, `pydantic>=2`, `fastapi==0.141.1` all already pinned. No `npm view`/`pip index versions` verification is needed because no new package is being added.

## Package Legitimacy Audit

**Not applicable — this phase installs zero external packages.** D-57 is explicit: "Phase 4 makes no runtime network call, and adds no new dependency." `pyproject.toml` was read this session and confirmed to contain no cost-model-specific addition is required (`fastapi`, `jinja2`, `pydantic`, `python-multipart`, `pyyaml`, `uvicorn`; dev: `pytest`, `ruff`, `httpx` — verified, `pyproject.toml:1-24`). If a plan for this phase proposes adding any package (e.g. a currency-formatting library, a CSV-parsing helper), that is a scope error per CONTEXT.md's own explicit constraint and should be flagged, not executed.

**Packages removed due to [SLOP] verdict:** none — no packages were evaluated because none are proposed.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
ProductionSpec (existing, engine/spec.py)
        │
        ▼
[1] BudgetModelBuilder (NEW: engine/budget.py)
        │   reads data/crew_tiers.yaml (extended with department-ratio
        │   columns per D-38) + ATL/BTL/Post tags (D-77)
        │   → CanonicalBudget (jurisdiction-agnostic, one per production)
        ▼
[2] CityLocalizer (NEW: engine/cost_localizer.py)  × each candidate city
        │   reads data/cost_profiles/<city>.yaml (CityCostProfile)
        │     ├─ data/union_rates/*.yaml  (COST-02/COST-03)
        │     ├─ data/per_diem/*.yaml     (COST-04, via engine/seasonality.py)
        │     ├─ data/fx/*.yaml           (COST-08, via engine/fx.py)
        │     └─ stage/equipment/permit/location/trucking refs (COST-06)
        │   → LocalizedBudget[city] (Figure tree, every line basis-tagged)
        ▼
   ┌────┴─────────────────────────────────┐
   │ cost side (this phase, new)          │ incentive side (EXISTING,
   │                                       │ Phase 2/3 — unchanged)
   ▼                                       ▼
[6] LandedCostAggregator (NEW)      [3][4][5] price_jurisdiction (EXISTING)
   │  non-incentive cost total        engine/pipeline.py:price_jurisdiction
   │  minus net_cash (when a rule     — now fed a MODELLED qualified spend
   │  file exists) OR marked          for the first time (D-71), via the
   │  incentive_not_modelled (D-56)   D-02 SpendBreakdown boundary
   └────────────────┬──────────────────────┘
                     ▼
        TotalLandedCost[city]  (Figure tree, basis-degraded per D-59)
                     │
                     ▼
[7] Ranker (NEW: engine/ranker.py)
        │   two-band split (D-55): net-ranked vs incentive_not_modelled
        ▼
[8] GapDecomposer (NEW: engine/gap.py)   pick any 2 cities
        │   component-by-component diff, currency as its own line (D-75)
        │
        └──▶ Sensitivity (NEW, same module or engine/sensitivity.py)
                 perturb one declared input at a time (data/sensitivity_steps.yaml,
                 D-68), re-run [1]→[8], report the delta + cliff-crossing (D-69)
```

### Recommended Project Structure

```
engine/
├── budget.py                # NEW — stage [1] BudgetModelBuilder
├── cost_localizer.py         # NEW — stage [2] CityLocalizer
├── cost_profile.py           # NEW — CityCostProfile Pydantic schema + load_cost_profile()
├── seasonality.py            # NEW — shoot-calendar derivation (D-65), month-weighted per diem
├── fx.py                     # NEW — dated FX snapshot lookup, refuse-not-cross-rate (D-74)
├── landed_cost.py            # NEW — stage [6] LandedCostAggregator
├── ranker.py                 # NEW — stage [7] Ranker, two-band split (D-55)
├── gap.py                    # NEW — stage [8] GapDecomposer, currency component (D-75)
├── sensitivity.py            # NEW — OUT-03 perturbation engine (D-67..D-70)
├── figure.py                 # MODIFIED — add optional `basis` field (D-58)
├── figure_serialize.py       # MODIFIED — serialize `basis` (D-58)
├── qualifying_base.py        # UNCHANGED (D-02 boundary intact)
├── credit.py                 # UNCHANGED
├── net_cash.py                # UNCHANGED
├── pipeline.py                # UNCHANGED (price_jurisdiction signature intact — D-71 changes the caller, not this function)
├── models.py                  # UNCHANGED (JurisdictionRuleSet untouched per CONTEXT.md canonical_refs)
└── spec.py                    # extended: data/crew_tiers.yaml gains department-ratio columns (D-38)

data/
├── crew_tiers.yaml            # EXTENDED — department-ratio + ATL/BTL/Post columns (D-38/D-77)
├── cost_profiles/
│   ├── us-ny-new-york.yaml
│   ├── us-ca-los-angeles.yaml
│   ├── gb-london.yaml
│   └── ...stretch cities
├── per_diem/
│   ├── gsa/us-ny-new-york-county.yaml
│   ├── gsa/us-ca-los-angeles-county.yaml
│   └── state-dept/gb-london.yaml
├── union_rates/
│   ├── iatse-600.yaml
│   ├── sag-aftra.yaml
│   ├── dga.yaml
│   └── bectu.yaml
├── fx/
│   └── gbp-usd.yaml
└── sensitivity_steps.yaml     # NEW — D-68's declared step table

sources/
├── MANIFEST.yaml              # EXTENDED — new entries for every archived doc below
├── gsa/                       # archived per-diem CSV/PDF snapshots
├── state-dept/                # archived foreign per-diem snapshots
├── unions/                    # archived rate-card PDFs (IATSE, SAG-AFTRA, DGA, BECTU)
└── fx/                        # archived Frankfurter response snapshot

app/services/
└── spec.py                    # MODIFIED — D-71 reverses the import-boundary guard; SPEND_NOT_DERIVED retired

tests/
├── test_engine_budget.py
├── test_engine_cost_localizer.py
├── test_engine_cost_profile.py
├── test_engine_seasonality.py
├── test_engine_fx.py
├── test_engine_landed_cost.py
├── test_engine_ranker.py
├── test_engine_gap.py
├── test_engine_sensitivity.py
├── test_golden_cost.py        # D-78
├── test_route_a_basis_walk.py # D-63's CI gate, as a pytest test
└── fixtures/cost_profiles/*.yaml  # synthetic profiles, mirrors tests/fixtures/jurisdictions/synthetic-*.yaml
```

### Pattern 1: The `basis` field must default to `None`, never be a bare required field

**What:** `Figure` (`engine/figure.py:54-74`, verified) is `@dataclass(frozen=True, kw_only=True)` with every field required except `figure_id`. Every existing call site across `engine/credit.py`, `engine/net_cash.py`, `engine/qualifying_base.py` and `engine/pipeline.py` constructs `Figure(...)` without a `basis` argument.

**When to use:** Any time this phase adds a field to `Figure`.

**Example (the addition, not existing code):**
```python
# engine/figure.py — additive change only
Basis = Literal["sourced", "estimated", "modelling_assumption"]

@dataclass(frozen=True, kw_only=True)
class Figure:
    value: Decimal
    unit: str
    label: str
    derivation: tuple[str, ...]
    inputs: tuple["Figure", ...]
    source_url: str | None
    date_checked: date | None
    confidence: Confidence
    live_fetched_this_run: bool
    basis: Basis | None = None      # NEW — D-58, orthogonal to confidence
    figure_id: str = field(default_factory=_new_figure_id)


def combined_basis(inputs: Sequence[Figure]) -> Basis:
    """Mirrors combined_confidence's shape (engine/figure.py:98-109) but
    inverts its one landmine: never default on an empty sequence."""
    present = [f.basis for f in inputs if f.basis is not None]
    if not present:
        raise ValueError(
            "combined_basis called on a sequence with no basis-carrying "
            "inputs — this must never silently default to the strongest "
            "tier (D-59's explicit landmine warning)"
        )
    order = {"modelling_assumption": 0, "estimated": 1, "sourced": 2}
    return min(present, key=lambda b: order[b])
```
**Why `None` and not a required field:** the incentive-side pipeline (Phase 2/3, untouched by this phase per CONTEXT.md canonical_refs) has no concept of this axis — retrofitting `basis` onto every `Figure(...)` call in `credit.py`/`net_cash.py`/`qualifying_base.py` is out of this phase's scope and D-58 itself frames `basis` as specific to "cost figures," not universal.

### Pattern 2: Refuse rather than invent (D-56, D-74) — reuse the proven shape

**What:** `engine.net_cash.transferable` (verified, `engine/net_cash.py:154-186`) raises `ValueError` when `transfer_discount` doesn't fully declare its rate range, and when it does, returns a `low`/`high` pair with `point=None` rather than a fabricated midpoint (`NetCashResult`, `engine/net_cash.py:51-62`, verified — docstring states explicitly: *"a single midpoint must never be presented as a point estimate"*).

**When to use:** An unranked city (D-56) and a missing FX pair (D-74) both need this exact shape.

**Example:**
```python
# engine/fx.py — mirrors engine/net_cash.py:154-186's refusal shape
def convert(amount: Decimal, base: str, quote: str, snapshot_dir: Path) -> Figure:
    pair_path = snapshot_dir / f"{base.lower()}-{quote.lower()}.yaml"
    if not pair_path.exists():
        raise ValueError(
            f"no committed FX snapshot for {base}->{quote} — refuse rather "
            f"than derive through a third currency (D-74, mirrors "
            f"engine.net_cash.transferable's refuse-rather-than-invent rule)"
        )
    # ... load, quantize via engine.rounding.quantize_money, return Figure(basis="sourced", ...)
```

### Pattern 3: The two-band ranked list (D-55)

**What:** Every city gets a fully-computed cost-only total; only cities with a modelled net cash figure enter the ranked band.

**When to use:** `engine/ranker.py`, stage [7].

**Example:**
```python
@dataclass(frozen=True)
class RankedCity:
    city_id: str
    total_landed_cost: Figure          # cost-only or net, depending on band
    band: Literal["net_ranked", "incentive_not_modelled"]
    reason: str | None                  # populated only for incentive_not_modelled


def rank(localized_by_city: dict[str, LocalizedBudget], ruleset_by_jurisdiction: dict[str, JurisdictionRuleSet | None]) -> list[RankedCity]:
    ranked, unranked = [], []
    for city_id, budget in localized_by_city.items():
        jurisdiction_id = budget.jurisdiction_id  # may be None (D-53 — cost profile needs no rule file)
        ruleset = ruleset_by_jurisdiction.get(jurisdiction_id) if jurisdiction_id else None
        if ruleset is None:
            unranked.append(RankedCity(
                city_id=city_id,
                total_landed_cost=budget.cost_only_total,   # D-56 — never $0, cost-only total instead
                band="incentive_not_modelled",
                reason="no curated or live-researched rule file exists for this jurisdiction yet",
            ))
            continue
        # ... price_jurisdiction(ruleset, modelled_qualified_spend), then net total
        ranked.append(RankedCity(city_id=city_id, total_landed_cost=net_total, band="net_ranked", reason=None))
    ranked.sort(key=lambda c: c.total_landed_cost.value)
    unranked.sort(key=lambda c: c.total_landed_cost.value)
    return ranked + unranked   # never interleaved (D-55)
```

### Anti-Patterns to Avoid

- **Defaulting an unranked city's incentive to `$0`:** D-56, rejected explicitly and flagged load-bearing. A silent zero penalizes every unmodelled city by the full value of its programme and is indistinguishable from a real, sourced zero.
- **Applying a seasonal multiplier to stages, crew, or equipment:** D-64, flagged load-bearing. No source exists for this anywhere; it would be an invented number applied to the largest cost lines, moving the headline ranking on fabricated grounds (PITFALLS E3's execution trap, generalized).
- **Rounding anywhere except `quantize_money`:** verified single-call-site convention (`engine/rounding.py:1-9`, docstring states this explicitly) — a second `.quantize()` call site on the cost side reintroduces the exact float/rounding-mode ambiguity the module exists to eliminate.
- **Feeding a validation-pair fixture through `BudgetModelBuilder`:** D-72, flagged load-bearing, one-way. Disclosures publish qualified spend and the award, never the input vector — routing a fixture's `ProductionSpec` through the new budget model to compare against a disclosed award would fabricate the input vector and produce a green result that means nothing.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Money arithmetic | A new `Money` class or float-based arithmetic | `decimal.Decimal` + `engine/rounding.py::quantize_money` (existing) | Already proven, already the single pinned rounding call site; a second implementation on the cost side is the exact class of bug RD-01 exists to prevent |
| YAML parsing | A custom parser or `yaml.load` (unsafe) | `yaml.safe_load`, exactly as `engine.spec.resolve_crew_tier` already does (`engine/spec.py:158`, verified) | `yaml.load` without `Loader=SafeLoader` can construct arbitrary Python objects from untrusted YAML — this repo's one existing YAML read site already avoids it; every new one must too |
| Confidence/provenance degradation logic | A bespoke per-cost-line confidence rule | `combined_basis`, mirroring `combined_confidence`'s exact shape (`engine/figure.py:98-109`) minus its empty-sequence landmine | The weakest-input-wins rule is already implemented once correctly for `confidence`; re-deriving it for `basis` independently risks a subtly different (and wrong) aggregation rule |
| FX cross-rate derivation | Deriving GBP→USD via a third currency when a direct pair is missing | Refuse, per D-74 | A derived cross-rate through USD/EUR/whatever is an invented number wearing a sourced figure's clothes — exactly the class of dishonesty D-56/D-74 both exist to prevent |
| Sensitivity via calculus | An analytic derivative / gradient of the pricing function | Literal re-run of the pipeline per input, one perturbation at a time (D-67) | The pipeline has hard cliffs (minimum-spend threshold, tiered rate bands, `blended_by_ceiling_split`, per-project cap's strictly-greater-than boundary) a derivative cannot see — this is not a precision tradeoff, it's categorically wrong in the cases that matter most |

**Key insight:** every "don't hand-roll" item above is not a third-party-library recommendation (none applies — D-57 forbids new dependencies) but a "don't re-derive a pattern this repo already solved correctly once" caution. The risk profile of this phase is re-implementing an existing convention slightly wrong, not choosing the wrong library.

## Common Pitfalls

### Pitfall 1: Treating an industry-commentary fringe percentage as `sourced`
**What goes wrong:** This session's research surfaced a "35-45%" IATSE blanket fringe figure from payroll-vendor blog content (`cmsproductions.com`, `topsheet.io` — non-primary sources), alongside genuinely union-published figures (SAG-AFTRA's 21% P&H, DGA's 22.25% P&H for post-2026-07-01 principal photography — both from union-adjacent payroll summaries this session, still requiring primary-document verification before the plan commits a number as `sourced`).
**Why it happens:** the blog aggregator numbers are more convenient to find and read than the actual union basic agreement PDF, and they look identically formatted to a real citation.
**How to avoid:** every fringe percentage this phase commits to `data/union_rates/*.yaml` must trace to the union's OWN published document (an ICG 600 rate card, a SAG-AFTRA agreement summary page, a DGA basic agreement excerpt) before it is tagged `basis: sourced`. Anything sourced only from a payroll-vendor blog is `basis: estimated` at best, with the method and the actual source disclosed on the figure (PITFALLS E1/E5's exact prescription).
**Warning signs:** a rate that "everyone quotes" but that traces back to the same three or four SEO blog posts, not the union's own site.

### Pitfall 2: Assuming both floor cities have seasonal per diem (the flagged D-64 assumption)
**What goes wrong:** CONTEXT.md flagged this explicitly as unverified. This session's WebFetch pass against the official GSA page confirmed it is **half true**: New York County genuinely varies by month ([CITED: gsa.gov, WebFetch this session] $179 low / $342 high), but **Los Angeles County's FY2026 rate is flat** at $191 for every month ([CITED: gsa.gov, WebFetch this session]) — LA is not a seasonal Non-Standard Area this fiscal year. A plan that assumes both floor cities produce a seasonal swing will either crash on LA's missing month bands or silently fabricate one. Re-confirm the exact figures against the raw GSA bulk file before committing (see Summary's confidence note) — the NY-seasonal/LA-flat structural asymmetry is the reliable part of this finding.
**Why it happens:** GSA does list LA as a Non-Standard Area (so it's tempting to assume NSA implies month-banded), but NSA status and seasonal banding are independent — LA is priced with a single year-round lodging max for FY2026.
**How to avoid:** implement exactly D-64's own stated fallback — seasonality is sourced per city where a month band exists, and explicitly absent where it does not. Do not derive or interpolate a seasonal curve for LA from NY's pattern.
**Warning signs:** a plan or test fixture that hardcodes "every city has 12 monthly per-diem rows" instead of reading whatever row count each city's committed snapshot actually has.

### Pitfall 3: Presenting a GSA/State-Dept figure as a market hotel rate
**What goes wrong:** GSA per diem (and State Dept foreign per diem) are federal reimbursement ceilings, not surveyed market rates — PITFALLS E4 (verified, `.planning/research/PITFALLS.md:204-208`) documents this gap is real and has widened. Displaying the raw number unqualified understates housing cost and, because the gap varies by market, distorts the cross-city comparison.
**Why it happens:** it's the only free, structured, government-published number that exists for housing cost — the temptation is to treat "free and government-published" as "market-accurate."
**How to avoid:** D-61's structural fix — the caveat string lives ON the `Figure` itself (not in a template), so it survives every downstream rewrite (Phase 6, Phase 8, Phase 10).
**Warning signs:** any code path that constructs a per-diem `Figure` without setting the caveat field.

### Pitfall 4: No public rate card exists for stages/equipment/permits/trucking — treating a studio's marketing page as authoritative
**What goes wrong:** this session's search confirmed there is no standardized public rate card for sound stages (individual studio pages quote wildly different numbers — a $19/hr Giggster listing next to a $3,500/shoot-day standing-set rate, neither representative of what a real production actually negotiates). Presenting either as `sourced` misrepresents an anecdotal marketing figure as a government-or-union-grade citation.
**Why it happens:** these are the only numbers that come up in a search, and they look plausible.
**How to avoid:** label every stage/equipment/permit/location/trucking figure `basis: estimated` (if derived from a disclosed reference point, e.g. an explicitly-named studio's published day rate used as an anchor) or `basis: modelling_assumption` (if no defensible anchor exists at all) — never `sourced`. This is COST-06's own explicit requirement ("estimated lines labelled as estimates").
**Warning signs:** a `data/cost_profiles/*.yaml` stage-cost line with `basis: sourced` and a `source_url` pointing at a studio's own rental listing page rather than a government or union document.

### Pitfall 5: `combined_basis` silently defaulting to the strongest tier on an empty sequence
**What goes wrong:** this is D-59's explicitly named landmine, copied verbatim from a real trap already present in the codebase — `combined_confidence` (verified, `engine/figure.py:98-109`) returns `"validated"` for an empty sequence, which is correct for its own call sites but would be a serious bug if `combined_basis` copied the same default, since an empty-inputs total would then silently claim the STRONGEST basis tier (`sourced`) rather than raising or defaulting to the weakest.
**Why it happens:** the two functions look structurally identical and it's natural to copy-paste the pattern without re-deriving the default.
**How to avoid:** `combined_basis` must raise `ValueError` on an empty sequence (see Pattern 1's code example above), or explicitly default to the WEAKEST tier — never the strongest, and never silently mirror `combined_confidence`'s specific default.
**Warning signs:** a `combined_basis` implementation whose empty-sequence branch reads `return "sourced"` — this is the exact one-line bug D-59 names in advance.

## Code Examples

### `figure_to_dict` must serialize the new field (D-58's JSON contract)
```python
# engine/figure_serialize.py — additive line only, existing structure verified
# (engine/figure_serialize.py:26-42)
def figure_to_dict(figure: Figure) -> dict:
    return {
        "figure_id": figure.figure_id,
        "value": str(figure.value),
        "unit": figure.unit,
        "label": figure.label,
        "derivation": list(figure.derivation),
        "source_url": figure.source_url,
        "date_checked": figure.date_checked.isoformat() if figure.date_checked else None,
        "confidence": figure.confidence,
        "basis": figure.basis,              # NEW — None for incentive-side figures
        "live_fetched_this_run": figure.live_fetched_this_run,
        "inputs": [figure_to_dict(child) for child in figure.inputs],
    }
```

### RD-01 convention applied to a new per-diem snapshot
```yaml
# data/per_diem/gsa/us-ny-new-york-county.yaml
# Source: gsa.gov FY2026 per-diem lookup (fetched and archived this session).
# Every numeric value is a quoted string (RD-01) — matches jurisdictions/
# us-ny.yaml:74's `base_rate: "0.25"` convention exactly.
fiscal_year: "2026"
county: "New York County, NY"
source_url: "https://www.gsa.gov/travel/plan-book/per-diem-rates/per-diem-rates-results?action=perdiems_report&city=New+York&fiscal_year=2026&state=NY&zip="
retrieved_at: "2026-08-26"
mie_daily: "92"
lodging_by_month:
  "2025-10": "342"
  "2025-11": "342"
  "2025-12": "342"
  "2026-01": "179"
  "2026-02": "179"
  "2026-03": "281"
  "2026-04": "281"
  "2026-05": "281"
  "2026-06": "281"
  "2026-07": "237"
  "2026-08": "237"
  "2026-09": "342"
ceiling_caveat: >
  Federal reimbursement ceiling, not a market rate; actual cost is likely
  higher, especially in peak season or a tight-inventory market. (D-61)
```

```yaml
# data/per_diem/gsa/us-ca-los-angeles-county.yaml
# LA County FY2026 has NO seasonal banding — confirmed this session.
fiscal_year: "2026"
county: "Los Angeles / Orange / Ventura / Edwards AFB less the city of Santa Monica"
source_url: "https://www.gsa.gov/travel/plan-book/per-diem-rates/per-diem-rates-results?action=perdiems_report&city=Los+Angeles&fiscal_year=2026&state=CA&zip="
retrieved_at: "2026-08-26"
mie_daily: "86"
lodging_flat_rate: "191"     # single rate, all 12 months — no lodging_by_month key present
ceiling_caveat: >
  Federal reimbursement ceiling, not a market rate; actual cost is likely
  higher, especially in peak season or a tight-inventory market. (D-61)
seasonality_note: >
  FY2026 GSA lodging rate for this county does not vary by month — this is
  a genuine absence of a seasonal signal, not an omission. Per D-64's
  fallback: sourced where a month band exists (New York), explicitly
  absent where it does not (Los Angeles). Never backfilled with a
  multiplier.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Ranking cities on headline incentive rate | Ranking on net landed cost, with unranked cities in a visibly separate band (D-55) | This phase | Directly implements PROJECT.md's core thesis and REQUIREMENTS.md's "Out of Scope" table entry ("Ranking on headline incentive rate ... wrong by 20 to 40 percent") |
| A single blanket cost-per-day figure for housing | Month-banded GSA/State-Dept per diem where a band exists, flat where it doesn't (D-64, this session's finding) | This phase | Makes the seasonality claim in OUT-02/COST-07 genuinely checkable per city rather than uniformly assumed |
| GSA per diem presented as a hotel rate | GSA per diem presented with a structural ceiling-vs-market caveat on the `Figure` itself (D-61) | This phase | PITFALLS E4's "cheap fix, outsized credibility payoff" — now a schema-level guarantee, not UI copy that can be dropped in a later rewrite |

**Deprecated/outdated:** `SPEND_NOT_DERIVED` in `app/services/spec.py` (verified, `app/services/spec.py:53-57`) is retired by D-71 — its replacement is a real `Figure`, not a rewritten string. The retirement must be explicit (the constant removed and its test coverage updated), not left as unreachable dead code.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "IATSE fringe benefits add 35-45% on top of union crew rate" is a usable planning figure | COST-03, Pitfall 1 | Sourced only from payroll-vendor blog commentary this session, not a union basic agreement document — if committed as `basis: sourced` it misrepresents an industry rule-of-thumb as a citable figure; must be `basis: estimated` with the blog-vendor source disclosed, or replaced by a per-local sourced figure before the plan executes |
| A2 | DGA's 22.25% Pension & Health contribution rate (for principal photography starting on/after 2026-07-01) is accurate and current | COST-03 | Sourced from a payroll-vendor summary page this session, not DGA's own basic agreement PDF directly — needs primary-document confirmation during data collection, same tier as A1 |
| A3 | Standard ATL/BTL/Post department-ratio percentages (camera 4-8% of BTL, grip & electric 8-15%, etc.) are usable for OUT-04's account tagging | OUT-04, Standard Stack | These are industry-blog aggregate figures (Vitrina, Saturation.io, Thoolie), not a primary accounting-standard document — must be tagged `basis: modelling_assumption` exactly like `data/crew_tiers.yaml`'s existing headcount bands, never `sourced` |
| A4 | State Department foreign per diem publishes a genuine month-by-month lodging table for London (analogous to GSA's domestic NSA month bands), not just a single current rate | COST-04, COST-07 | This session confirmed rates are "established monthly" and "updated monthly, effective 1st of month" but could not directly pull a month-by-month historical table for London specifically — if London in fact carries only a single current-month rate rather than a genuine seasonal band, London's seasonality treatment falls under D-64's "absent" branch alongside (or instead of) LA, which changes what COST-07's cross-city seasonality claim can honestly say. Needs direct verification against `allowances.state.gov`'s DSSR Section 925 table during data collection, before committing London's per-diem snapshot. |
| A5 | Stage/equipment/permit/trucking anchor figures found this session (Giggster/BLT/Riverfront Stages listings) are representative enough to use as `basis: estimated` anchors | COST-06 | These are individual marketing listings with no standardization — using any single one as an "anchor" risks presenting an outlier as typical; the plan should treat this as the phase's most genuinely under-sourced cost category and consider whether a named, disclosed range (not a point estimate) is more honest than a single anchor figure |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **D-64's flagged assumption — RESOLVED WITH A CORRECTION.**
   - What we know: GSA's FY2026 per diem for New York County genuinely varies by month ($179 low, January/February; $342 high, October/December/September) — [CITED: gsa.gov FY2026 per-diem lookup for New York, fetched via WebFetch this session]. Los Angeles County's FY2026 rate is flat at $191/night, all 12 months — [CITED: gsa.gov FY2026 per-diem lookup for Los Angeles, fetched via WebFetch this session]. Both figures come from an AI-summarized WebFetch read of the official page, not a raw CSV/table open — `classify-confidence --provider webfetch --verified` scores this LOW, not HIGH, so treat the exact dollar figures as needing one more direct-file confirmation pass, while the NY-varies/LA-flat structural finding itself is the reliable takeaway.
   - What's unclear: whether this pattern (NY seasonal, LA flat) holds for future fiscal years, or is specific to FY2026's NSA designations — GSA revisits NSA status annually, so a future re-fetch (Phase 7's live gate) could see LA gain seasonal banding or NY lose it.
   - Recommendation: implement D-64's own stated fallback exactly as written — per-city, never interpolated, never backfilled. Do not build a data model that assumes every city has 12 monthly rows; build one where a city's committed snapshot may have either a `lodging_by_month` map or a single `lodging_flat_rate` scalar, and the seasonality display branches structurally on which key is present (see Code Examples above). Before committing either snapshot to `data/per_diem/` with `basis: sourced`, open the actual GSA bulk CSV/Excel file directly (not via a WebFetch summarization) to confirm the exact per-month cents.

2. **London's per-diem seasonality (State Department) — not fully resolved this session.**
   - What we know: State Department foreign per diem rates are described as monthly-updated in general, and DSSR Section 925 is the governing regulation.
   - What's unclear: whether London specifically carries a genuine month-by-month lodging table (like NY) or a single current rate that merely gets republished each month without changing (which would functionally behave like LA's flat case for this project's purposes, even though the update *cadence* differs from a true seasonal band).
   - Recommendation: fetch `allowances.state.gov`'s actual London row (or the DSSR Section 925 table) directly during data collection — a plan task, not something this research session could fully close without navigating a stateful lookup tool. Budget for the possibility that London falls into D-64's "absent" branch.

3. **Whether Route A's D-71 reversal needs the `total_budget` refusal check to survive unchanged.**
   - What we know: `handle_spec_submission` (verified, `app/services/spec.py:120-172`) currently refuses any submission naming a `total_budget` field BEFORE constructing a `ProductionSpec` — this is INP-08's enforcement and is untouched by D-71 (D-71 changes what a *valid* submission returns, not the refusal check itself).
   - What's unclear: nothing structural — this is confirmed by direct read. Flagged here only so the plan doesn't accidentally touch `REFUSAL_REASON`/the budget-refusal branch while implementing D-71's dollar-returning change.
   - Recommendation: the plan should treat `handle_spec_submission`'s lines 134-137 (budget refusal, verified) as a fixed pre-condition that D-71's new logic runs *after*, never before.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| GSA per diem bulk files (`gsa.gov/travel/plan-a-trip/per-diem-rates/per-diem-files`) | COST-04 data collection (one-time, not runtime) | [CITED: found via WebSearch this session, page not itself opened] no API key required for the CSV/Excel bulk-download page | current FY2026 | The keyed JSON API (`api.gsa.gov/travel/perdiem/v2/...`) was directly opened via WebFetch this session and does require a free registered API key — prefer the no-key bulk-file page since D-57 forbids any runtime dependency on a key anyway; confirm the bulk-file page's exact URL and format during data collection |
| State Dept foreign per diem (`allowances.state.gov`) | COST-04 data collection for London (one-time) | [CITED: allowances.state.gov, described this session] Excel bulk download exists; exact London month-table structure not directly confirmed — see Open Question 2 | current | None needed — this is a one-time data-collection step, not a runtime dependency, per D-57 |
| Union rate-card PDFs (ICG600/IATSE 600, SAG-AFTRA, DGA, BECTU) | COST-02/COST-03 data collection (one-time) | [VERIFIED: `icg600.com`, `sagaftra.org`, `bectu.org.uk` all confirmed to publish current rate-card PDFs this session] | 2024-2025/2025-2026 agreement years, varies by union | None needed — one-time archival per `sources/MANIFEST.yaml`'s existing D-08/D-10 convention |
| Frankfurter FX API (`api.frankfurter.dev`) | COST-08 data collection for the GBP-USD snapshot (one-time) | Already researched and confirmed by `.planning/research/STACK.md` (no key, no documented quota) — not re-verified live this session since D-57 makes this a one-time pull, not a runtime call | current | None needed |
| `pyyaml`, `pydantic`, `decimal` | All new data readers | [VERIFIED: pyproject.toml, read this session] already installed, `uv sync` covers it | pyyaml==6.0.3, pydantic>=2 | N/A |

**Missing dependencies with no fallback:** none — every dependency this phase needs is either already installed or is a one-time, no-key data-collection fetch that does not become a runtime dependency (D-57).

**Missing dependencies with fallback:** GSA's keyed JSON API has a no-key bulk-file alternative (used instead, per above).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 [VERIFIED: pyproject.toml, read this session] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]` [VERIFIED, read this session] |
| Quick run command | `uv run pytest tests/test_engine_budget.py tests/test_engine_cost_localizer.py -q` (per-module, during a task) |
| Full suite command | `uv run --frozen pytest tests/ -q` [VERIFIED: `.github/workflows/ci.yml`, this exact command already runs in the `tests` CI job, read this session] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COST-01 | `BudgetModelBuilder` produces one identical `CanonicalBudget` regardless of candidate city | unit | `pytest tests/test_engine_budget.py -q` | ❌ Wave 0 |
| COST-02/03 | Labour localization applies union scale + fringe, both as separate `Figure`s | unit | `pytest tests/test_engine_cost_localizer.py -q` | ❌ Wave 0 |
| COST-04 | Per-diem figure carries the D-61 ceiling caveat structurally | unit | `pytest tests/test_engine_seasonality.py -q` | ❌ Wave 0 |
| COST-05 | Flights/housing computed only for imported crew/cast counts | unit | `pytest tests/test_engine_cost_localizer.py -q` | ❌ Wave 0 |
| COST-06 | Stage/equipment/permit/trucking lines never carry `basis: sourced` | unit | `pytest tests/test_engine_cost_profile.py -q` | ❌ Wave 0 |
| COST-07 | Changing `start_quarter` changes the total via per-diem seasonality where a month band exists, and states explicitly where it does not | integration | `pytest tests/test_engine_seasonality.py -q` | ❌ Wave 0 |
| COST-08 | FX conversion cites a dated `Figure`; missing pair raises rather than cross-rates | unit | `pytest tests/test_engine_fx.py -q` | ❌ Wave 0 |
| INC-10 | Tax exemptions reduce cost lines, never the credit figure | unit | `pytest tests/test_engine_cost_localizer.py -q` | ❌ Wave 0 |
| OUT-01 | Ranked list two-band split (D-55); unranked never `$0` | unit | `pytest tests/test_engine_ranker.py -q` | ❌ Wave 0 |
| OUT-02 | NY-vs-LA gap fully decomposed, cost-only, real numbers | integration (golden) | `pytest tests/test_golden_cost.py -q` | ❌ Wave 0 |
| OUT-03 | Sensitivity perturbation, declared step shown, cliff crossing flagged, no prescriptive vocabulary | unit + string-scan | `pytest tests/test_engine_sensitivity.py -q` | ❌ Wave 0 |
| D-63 (CI gate) | No `Figure` reachable from a Route A total carries `confidence: "validated"` | integration | `pytest tests/test_route_a_basis_walk.py -q` | ❌ Wave 0 |
| D-72 (guard) | A validation-pair fixture is never routed through `BudgetModelBuilder` | integration | extend `tests/test_engine_against_validation_pairs.py` [VERIFIED: file exists, `tests/` listing this session] | Extend existing |
| D-78 (golden) | Fixed `ProductionSpec` + fixed cost profiles → exact `Decimal` totals | golden/regression | `pytest tests/test_golden_cost.py -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the relevant module's own test file (e.g. `pytest tests/test_engine_fx.py -q`)
- **Per wave merge:** `uv run --frozen pytest tests/ -q` (existing CI `tests` job)
- **Phase gate:** full suite green, plus the D-63 basis-walk test and the D-78 golden-cost test both present and passing, before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_engine_budget.py` — covers COST-01
- [ ] `tests/test_engine_cost_localizer.py` — covers COST-02/03/05/06, INC-10
- [ ] `tests/test_engine_cost_profile.py` — schema-load test for `CityCostProfile`, mirrors `engine/models.py::load_ruleset`'s existing test pattern
- [ ] `tests/test_engine_seasonality.py` — covers COST-04/07, including the NY-seasonal/LA-flat branch from this session's finding
- [ ] `tests/test_engine_fx.py` — covers COST-08, including the missing-pair refusal path
- [ ] `tests/test_engine_landed_cost.py` — stage [6] aggregation
- [ ] `tests/test_engine_ranker.py` — covers OUT-01, the two-band split, the never-`$0` guarantee
- [ ] `tests/test_engine_gap.py` — covers OUT-02, currency as its own component (D-75)
- [ ] `tests/test_engine_sensitivity.py` — covers OUT-03, including a vocabulary-grep assertion against sensitivity output strings (D-70)
- [ ] `tests/test_golden_cost.py` — D-78's fixed-input exact-total regression test
- [ ] `tests/test_route_a_basis_walk.py` — D-63's CI gate, implemented as a pytest test walking `figure_to_dict`'s recursive `inputs` output
- [ ] `tests/fixtures/cost_profiles/*.yaml` — synthetic cost profiles mirroring `tests/fixtures/jurisdictions/synthetic-*.yaml`'s existing convention [VERIFIED: directory exists, referenced in CONTEXT.md canonical_refs and confirmed present this session]
- [ ] Framework install: none — pytest is already installed

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V1 Architecture | yes | No new trust boundary — Phase 4 adds no runtime network call (D-57) and no new user-facing input field; Route A's existing `ProductionSpec` validation (Phase 3, unchanged) remains the only visitor-supplied input surface this phase's new code touches |
| V5 Input Validation | yes | Every new schema (`CityCostProfile`, per-diem table, FX snapshot, union-rate table) uses `pydantic.BaseModel` with `extra="forbid"`, mirroring `engine/models.py::StrictModel` (`engine/models.py:94-97`, verified) and `engine/spec.py::StrictModel` (`engine/spec.py:43-49`, verified) exactly |
| V5 (YAML-specific) | yes | Every new YAML reader must use `yaml.safe_load` exclusively — never `yaml.load`/`yaml.unsafe_load` — matching the repo's one existing precedent (`engine/spec.py:158`'s docstring states this explicitly: "Loads with `yaml.safe_load` only (never the unsafe/generic loader)", verified) |
| V6 Cryptography | no | Not applicable — no secrets, no crypto operation in this phase |
| V10 SSRF | no | Not applicable by construction — D-57 forbids any runtime network call in this phase; there is no code path that could be pointed at an attacker-controlled URL because there is no runtime URL-fetching code path at all |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| A malformed or hand-edited committed YAML data file crashes the app at import time rather than failing a load-time schema check | Denial of Service (data-integrity variant) | `pydantic.BaseModel` with `extra="forbid"` on every new schema, loaded via `yaml.safe_load` then `Model.model_validate(...)` — a malformed file fails fast at startup/test time, not mid-request |
| A future contributor adds a new cost-data reader that calls `yaml.load()` without a safe loader | Tampering (arbitrary object construction from untrusted YAML) | Code review checklist item / ruff or a repo-local test asserting every `yaml.load(` call site in `engine/` and `data/`-adjacent readers passes `Loader=yaml.SafeLoader` or uses `yaml.safe_load` directly |
| A `basis` or `confidence` field silently defaults to the strongest tier when no input is present (D-59's landmine) | Repudiation / information-disclosure-adjacent (a false honesty claim) | `combined_basis` raises on an empty sequence rather than defaulting (Pattern 1 / Pitfall 5 above); this is enforced by `tests/test_route_a_basis_walk.py`'s D-63 gate at the integration level |

## Sources

### Primary (HIGH confidence)
- `pyproject.toml` — read directly this session; dependency list, pytest/ruff versions
- `.github/workflows/ci.yml` — read directly this session; existing CI job shapes (lockfile-scan, vendor-scan, commit-window, secret-scan, tests, mutation-check)
- `engine/figure.py` — read directly this session, lines 1-110; `Figure` dataclass shape, `combined_confidence`'s empty-sequence default (the D-59 landmine, confirmed verbatim)
- `engine/figure_serialize.py` — read directly this session, lines 1-43
- `engine/spec.py` — read directly this session, lines 1-172; `ProductionSpec`, `CrewHeadcount`, `resolve_crew_tier`'s `yaml.safe_load`-only convention
- `engine/pipeline.py` — read directly this session, lines 1-277; `price_jurisdiction`, mutual-exclusivity resolution, total-figure construction
- `engine/net_cash.py` — read directly this session, lines 1-282; the four mechanism functions, `transferable`'s refuse-rather-than-invent shape
- `engine/qualifying_base.py` — read directly this session, lines 1-333; `SpendBreakdown`, `compute_qualifying_base`, the D-02 interpreter-only boundary in code
- `engine/rounding.py` — read directly this session, full file; the single pinned `quantize_money` call site
- `engine/models.py` — read directly this session, lines 94-153; `StrictModel`, `Source`, `Jurisdiction`, `BaseDefinition`
- `app/services/spec.py` — read directly this session, full file; `SPEND_NOT_DERIVED`, `REFUSAL_REASON`, `handle_spec_submission`
- `app/services/city_lookup.py` — read directly this session, full file
- `app/services/_paths.py` — read directly this session, full file; `REPO_ROOT` convention
- `tests/test_app_spec_route.py` — read directly this session, lines 230-264; the D-71-affected import-boundary guard test
- `tests/mutation_targets.yaml` — read directly this session, full file; the D-68 declared-table-in-data precedent
- `data/crew_tiers.yaml` — read directly this session, full file; the `basis: modelling_assumption` precedent D-58's vocabulary is taken from
- `jurisdictions/us-ny.yaml` — read directly this session, full file; RD-01 quoted-decimal convention, `Source`/`Jurisdiction` shape in practice
- `.planning/WINDOWS.md` — read directly this session; CT's open transfer-discount gap (#3), confirming Hartford's `incentive_not_modelled` fate under D-55
- `.planning/research/ARCHITECTURE.md` Q1 (lines 79-137), Q5 (411-448), Q6 (451-503) — read directly this session
- `.planning/research/PITFALLS.md` Part E (187-213), Part F (216-236) — read directly this session
- `open.gsa.gov/api/perdiem/` — fetched via WebFetch and read directly this session; API key requirement, endpoint shapes, monthly-variation confirmation. This one is HIGH confidence: the claims extracted (key required, rate limit, endpoint URL shapes) are structural/textual, not tabular-numeric, so WebFetch's summarization risk is low.

### Secondary (MEDIUM confidence)
- `gsa.gov` FY2026 per-diem lookup for New York, NY — fetched via WebFetch this session; month-by-month lodging table ($179-$342). Downgraded from VERIFIED to CITED per `classify-confidence --provider webfetch --verified` returning LOW for AI-summarized tabular extraction — re-confirm against the raw bulk file before committing exact dollar figures to `data/`.
- `gsa.gov` FY2026 per-diem lookup for Los Angeles, CA — fetched via WebFetch this session; flat $191 rate, no monthly variation. Same downgrade and same re-confirmation note as above.
- `icg600.com` (International Cinematographers Guild, IATSE Local 600) rate-card PDF listings — found via WebSearch this session, official union domain, not independently opened as a PDF
- `sagaftra.org` Low Budget / Theatrical rate pages — found via WebSearch this session, official union domain
- `bectu.org.uk`, `britishfilmdesigners.com` (BECTU-affiliated) rate-card pages — found via WebSearch this session
- `allowances.state.gov` — fetched via WebFetch this session; confirmed monthly-update cadence and bulk-Excel download, London-specific month table not directly opened
- `.planning/research/STACK.md` — Frankfurter FX API endpoint/key claims (previously researched, cited here, not re-verified live this session per D-57)

### Tertiary (LOW confidence — flagged in Assumptions Log)
- Payroll-vendor blog aggregation of DGA/IATSE fringe percentages (`cmsproductions.com`, `topsheet.io`, `greenslate.com`) — WebSearch only, not the union's own document
- Industry-blog ATL/BTL/Post department-ratio percentages (`vitrina.ai`, `saturation.io`, `thoolie.com`) — WebSearch only, not a primary accounting-standard document
- Individual stage-rental marketing listings (Giggster, BLT Studios, Riverfront Stages) — WebSearch only, non-standardized, non-authoritative for a cross-city comparison

## Metadata

**Confidence breakdown:**
- Engine/architecture design: HIGH — every new module mirrors an already-proven, directly-read Phase 2/3 pattern (`Figure`, `quantize_money`, refuse-rather-than-invent, committed YAML)
- Cost data provenance (union rates, per diem): MEDIUM-HIGH for the primary-source figures (GSA, State Dept cadence, union rate-card existence), LOW for the specific percentages quoted only by payroll-vendor blogs (flagged in Assumptions Log)
- Seasonality (D-64): MEDIUM-HIGH — the open question is structurally resolved (a genuine per-city asymmetry exists: NY seasonal, LA flat) via a WebFetch pass against the official GSA page this session, but the exact dollar figures are CITED, not VERIFIED (`classify-confidence --provider webfetch --verified` returns LOW), so the plan must re-confirm exact numbers against the raw GSA bulk file before committing them to `data/` with `basis: sourced`
- Stage/equipment/permit/trucking data: LOW — confirmed no standardized public source exists; the plan must treat this as the phase's most honestly under-sourced category

**Research date:** 2026-08-26
**Valid until:** GSA/State Dept per-diem figures: re-verify at FY2027 rollover (~2026-10-01) or before any live demo after that date. Union rate-card figures: re-verify against the union's own document before committing any percentage as `basis: sourced` — this research only confirmed the cards EXIST publicly, not the exact current numbers beyond what's quoted above. Engine architecture guidance: valid for the life of this phase; not time-sensitive.
