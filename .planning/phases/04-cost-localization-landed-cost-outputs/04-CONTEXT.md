# Phase 4: Cost Localization & Landed-Cost Outputs - Context

**Gathered:** 2026-08-26
**Status:** Ready for planning

<domain>
## Phase Boundary

The cost half of the pipeline. ARCHITECTURE.md Q1 stages `[1] BudgetModelBuilder` → `[2] CityLocalizer` → `[6] LandedCostAggregator` → `[7] Ranker` → `[8] GapDecomposer`. This is where a `ProductionSpec` finally becomes dollars.

**What lands:**

1. **One canonical budget (COST-01).** A single jurisdiction-agnostic `CanonicalBudget` derived from the `ProductionSpec` — department ratios inferred from crew tier, ATL/BTL/Post account tags, line items for labour, housing, per diem, flights, stages, equipment, permits, locations, trucking. **One budget, built once, identical for every city.** The comparison is never made against published rates and never against a per-city budget.
2. **Per-city localization (COST-02…COST-06).** A committed `CityCostProfile` per city prices that identical budget: union rate cards with fringe and payroll burden, GSA/State Dept per diem, flights and housing for imported crew and cast specifically, stages, equipment, permits, locations, trucking.
3. **Seasonality (COST-07).** Start quarter moves the cost figures, sourced-only — see **D-64**.
4. **Currency (COST-08).** A non-USD city converts at a dated FX rate carried as its own cited `Figure`, and currency is a first-class gap component.
5. **Stackable cost reductions (INC-10).** Sales-tax and hotel-occupancy exemptions reduce the cost lines they apply to, as separate named figures — never netted into the incentive number.
6. **The outputs (OUT-01, OUT-02, OUT-03).** Total landed cost per city, ranked; the gap between any two cities decomposed by component; and the single input that most moves that gap, as a delta.
7. **The D-36 seam closes.** A **modelled** qualified spend reaches `price_jurisdiction` for the first time. Route A returns dollars. Everything in **D-71…D-73** exists to keep that number from ever wearing a disclosed number's clothes.

**Not in this phase:**

- **No jurisdiction rule files.** CA, NJ and CT rule files are Phase 5 (JUR-02/03/04). A `CityCostProfile` is a genuinely different artifact from a `JurisdictionRuleSet` — one prices hotels and wage scale, the other reproduces a government award — and Phase 4 owns only the first. See **D-53**.
- **No agent jobs.** Neither `google-genai` nor `parallel-web` is imported. Job 1 is Phase 5, Job 2 is Phase 7.
- **No runtime network call at all** — see **D-57**. Phase 4 is offline-deterministic.
- **No interface treatment.** Server-rendered Jinja over the same JSON handlers (D-42/D-43). The map, slider, ranked-list treatment and the assumptions panel (PRV-04) are Phase 6.
- **No live research.** An uncurated city keeps its Phase 3 behaviour (D-40) and gains a cost profile only if one is committed for it.
- **No chart-of-accounts *view*.** The account tags land; the rendered breakdown does not. See **D-77**.

**A phase-boundary fact the planner and verifier both need.** Only New York has a rule file today. Phase 4 therefore produces a **structurally complete** ranked list containing **one** net-ranked city until Phase 5 lands. That is expected, not a gap. Phase 4's verification asserts on the machinery (aggregator, ranker, band separation, per-component decomposition, sensitivity) plus a **real, complete, cost-only two-city gap** between New York and Los Angeles — which is every component of OUT-02 except the incentive term. Do not fail Phase 4 for a Phase 5 dependency, and do not pull a Phase 5 rule file forward to manufacture a second net-ranked city (**D-55**).

</domain>

<decisions>
## Implementation Decisions

The user delegated all four gray areas — *"you decide all, give your most thoughtful answer"* — the same posture as Phases 1 and 3. Every decision below is Claude's call, made against ROADMAP.md, REQUIREMENTS.md, PROJECT.md, `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md` Part E, and the Phase 1/2/3 artifacts. Each carries its rationale so it can be overturned on sight rather than re-derived.

Numbering continues from Phase 3's D-31…D-52.

### The city set, and what "ranked" is allowed to mean

- **D-53: A `CityCostProfile` is Phase 4's artifact; a `JurisdictionRuleSet` is Phase 5's, and building the first does not touch the second.** ARCHITECTURE.md Q1 is explicit that stage `[2] CityLocalizer` is "JURISDICTION-AGNOSTIC (this is cost, not incentive rules)." A Los Angeles cost profile needs IATSE Local 80/600/700 scale, LA County GSA per diem and stage/equipment references; it needs nothing from `us-ca.yaml`. Phase 4 may therefore build cost profiles for cities whose rule files do not exist yet, with no scope collision. — **Reversibility:** costly — Phases 5, 6, 7 and 9 all bind to the profile shape; merging cost and rule data into one file later would break `engine/`'s jurisdiction-agnostic guarantee (JUR-05) at the same time.

- **D-54: The committed city set has a floor of three and a declared stretch.** The floor is **New York, NY** (the only curated jurisdiction; the Anora anchor), **Los Angeles, CA** (the canonical producer comparison and the demo's ranking-inversion beat) and **London, UK** (the non-USD city success criterion 4 requires; Phase 2's `synthetic-uk-style.yaml` worked example already exercises GBP arithmetic). The stretch, in this order, is **Atlanta, GA**, **Newark/Jersey City, NJ**, **Hartford, CT**. Rationale: three profiles is enough to prove every output in the phase — a rank, a two-city decomposed gap, a currency component and a seasonality delta — and each additional profile is sourcing work, which is the phase's real cost. Atlanta leads the stretch because Georgia has no per-production disclosure and never will (PROJECT.md), so it is the cleanest proof that cost localization is genuinely independent of the incentive side, and it is the home of the naive-arithmetic demo beat.

- **D-55: The ranked list is ranked on NET landed cost, and only cities whose incentive is actually modelled are ranked.** Every other city appears in the same response, ordered by cost, in a **visibly separate band** carrying its cost-only total and an explicit `incentive_not_modelled` state. Never interleaved with net-ranked cities as though comparable. Rationale: PROJECT.md's whole thesis is that the ranking inverts once net cash and timing apply; a list that silently mixes net totals with gross totals is the exact error the product exists to correct, and it would do it inside the product's headline output. The band structure also degrades correctly in both directions — Phase 5's rule files promote cities into the ranked band with no code change, and Phase 7's live-researched cities join it labelled `researched`. — **Reversibility:** costly — Phase 6's ranked list and Phase 10's published index both render against this two-band shape.

- **D-56: REJECTED — treating an unmodelled incentive as `$0`.** A city with no rule file does not have a zero incentive; it has an **unknown** one, and substituting zero silently penalises every city we have not yet modelled by the full value of its programme. This is recorded as a rejected option because it is the shortest path to a demo-ready ranking and will look reasonable to a later agent under deadline pressure. The honest substitute already exists in the codebase: `engine.net_cash.transferable` refuses to convert at an unsourced discount rate rather than inventing a midpoint (WINDOWS.md #3), and the same refusal shape applies here. — **Reversibility:** one-way — a fabricated zero inside the headline ranking is the specific dishonesty PRV-02 and the Phase 8 proof panel exist to prevent.

- **D-57: Phase 4 makes no runtime network call, and adds no new dependency.** Every cost input — GSA per diem rows, State Department foreign per diem, union scale and fringe schedules, stage/equipment/permit references, FX — lands as a **committed, dated snapshot in the repo**, read with the `pyyaml` already in `pyproject.toml`. Rationale, four independent reasons pointing the same way: (a) D-08 already established that source documents are archived byte-for-byte in the repo rather than in S3, and this is the same principle applied to derived rate tables; (b) it keeps Phase 4 offline-deterministic, so the golden cost tests of **D-78** can assert exact `Decimal` totals in CI the way the validation pairs already do; (c) ARCHITECTURE.md Q5's `DataFreshnessGate` is Phase 7's artifact, and half-building it here would mean Phase 7 inherits a partial cache boundary rather than writing one; (d) the box is still `nano_2_0` at ~284 MB available. — **Reversibility:** reversible — Phase 7's gate wraps these readers; the snapshot files become its cold-start seed rather than being replaced.

### Cost-line honesty — how an estimate is allowed to reach a total

- **D-58: A new orthogonal `basis` field on cost figures. `Figure.confidence` gains no third value.** `engine/figure.py`'s docstring already states the repo's rule — `Figure.confidence` (`validated` | `researched`) and `sources[].confidence` (`LOW`…`HIGH`) are two vocabularies and "the two are never conflated" (RD-02). Cost provenance is a third, genuinely orthogonal axis: *where the number came from*, not *whether it has been checked against a government disclosure*. Its values, from PITFALLS.md E5:
  - `sourced` — a published rate card row, a GSA per diem row, a published stage rate card
  - `estimated` — computed from a sourced input by a **disclosed method** (a fringe multiplier applied to scale wage; a regional index)
  - `modelling_assumption` — no public source exists anywhere (crew composition, department ratios). `data/crew_tiers.yaml`'s `basis: modelling_assumption` is the precedent and the vocabulary is taken from it deliberately.
  — **Reversibility:** costly — `engine/figure_serialize.py::figure_to_dict` is the JSON contract Phases 6, 8 and 10 render against; adding `basis` is additive now and a coordinated change across four phases later.

- **D-59: `basis` degrades to the weakest input, exactly like `combined_confidence` — and never defaults to `sourced` on an empty input list.** A total containing one `modelling_assumption` line **is** `modelling_assumption` and says so. This is the structural answer to "can an estimated line roll silently into the headline total": it cannot, because the total inherits the weakest basis. **Landmine, stated explicitly:** `engine/figure.py::combined_confidence` returns `"validated"` for an empty sequence — correct for its own use, and a trap if copied. `combined_basis` must raise, or return the weakest value, on an empty sequence; it must never mirror that default. — **Reversibility:** one-way — a cost total that can report `sourced` while containing an assumption is the same class of failure as a modelling assumption wearing a `validated` tier (D-39).

- **D-60: Acknowledged gaps are a declared exclusion list, not a `$0` line.** Overtime, turnaround penalties, meal penalties, kit fees, non-union local differentials and negotiated hotel rates are not priced (PITFALLS E2/E3, PROJECT.md line 78). They are rendered as a named, first-class list of **what this model does not price**, attached to the total. A `$0` line item would be a lie by omission — it asserts the cost is zero rather than that it is unmodelled. `jurisdictions/us-ny.yaml`'s header, which documents what it deliberately does not model, is the precedent.

- **D-61: The per-diem ceiling caveat is a structural field, not UI copy.** The GSA/State Department per-diem figure carries its own disclaimer string on the figure itself — *"federal reimbursement ceiling, not a market rate; actual cost is likely higher, especially in peak season or a tight-inventory market."* Rationale: PITFALLS E4 calls this a one-sentence fix with an outsized credibility payoff, and a sentence that lives in a Jinja template is one Phase 6 rewrite away from being dropped. On the figure, it survives the rewrite. It also survives the JSON boundary, so Phase 6 and Phase 10 cannot render the number without it.

- **D-62: Fringe and payroll burden are their own line, never folded into the wage line.** COST-03 requires burden included; PITFALLS E1 requires the multiplier disclosed. Sourced per union where the union publishes its fringe schedule (`basis: sourced`); a blanket multiplier only where it does not, with the method disclosed (`basis: estimated`). This is the identical treatment the incentive side already gives the audit fee and the transfer discount — show the deduction as its own figure, not as a haircut baked into the headline.

- **D-63: A CI gate asserting that no `Figure` reachable from a Route A total carries `confidence: "validated"`.** D-39 made this promise for one YAML table; Phase 4 generalises it to the entire cost side, where the surface is now hundreds of figures deep. Walk the recursive `inputs` DAG from the total and fail on any `validated` node. Rationale: this repo's established answer to an honesty commitment is a CI job, not a convention — D-28 greps the source tree for forbidden vendor names, D-49 automated the mutation ritual precisely because a one-time check goes stale. — **Reversibility:** costly — Phase 8's proof panel re-proves this claim and reruns whatever shape lands here.

### Seasonality — what actually makes Q1 differ from Q3

- **D-64: Seasonality is sourced-only. It rides on published per-diem month bands and nothing else.** GSA lodging rates and State Department foreign per diem are published by month for seasonal destinations; that is a real, free, authoritative, geography-specific seasonal signal. Nothing else in the cost model has one: seasonal stage availability, crew scarcity and equipment demand are not published anywhere. A modelled seasonal multiplier applied to stages or labour would be an **invented number applied to the largest lines, moving the product's headline ranking** — precisely PITFALLS E3's execution trap. Seasonal stage/crew/equipment variation is therefore declared under **D-60** as an acknowledged gap. — **Reversibility:** reversible — a sourced seasonal index, if one is ever found, plugs into the same per-line hook.

- **D-65: A shoot calendar is derived, because housing nights require one anyway.** COST-05 prices housing for imported crew and cast, which needs *nights*, not shoot days. Spread `shoot_days_stage + shoot_days_location` across calendar months from the start quarter at a **declared shooting-days-per-week rate** (`basis: modelling_assumption`, and named in the assumptions list), then weight each month's per-diem band by nights falling in it. This is not extra work bought for seasonality — it is work COST-05 already requires, and it is what makes the quarter genuinely meaningful for a shoot spanning a quarter boundary.

- **D-66: The response names its quarter-invariant lines.** If only per diem moves with the quarter, the response says which lines did not move, rather than leaving a reader to infer that a small total swing means the model considered everything. Rationale: PITFALLS F2 — the trap is not the scope of the seasonality claim, it is letting the reader assume a wider one.

- **Open question for the researcher, flagged rather than assumed.** D-64 rests on GSA publishing **monthly** lodging rates for the profile cities (New York County and Los Angeles County in the floor set). This is believed true and is the phase's single load-bearing unverified data assumption. **Confirm it against the GSA per-diem files before planning around it.** If a floor city turns out to carry a flat annual rate, the honest fallback is that seasonality is sourced where a month band exists and explicitly absent where it does not — stated per city, never backfilled with a multiplier.

### Sensitivity — OUT-03 without becoming a recommendation

- **D-67: Perturbation, one input at a time, re-running the real pipeline. Never an analytic derivative.** The model is full of cliffs — the minimum-spend cliff, tiered rate bands, `blended_by_ceiling_split`, the per-project cap clip at a strictly-greater-than boundary. A derivative is not merely less precise here, it is **wrong in exactly the interesting cases**, because it cannot see a cliff it did not cross. Cost is not a concern: the pipeline is pure `Decimal` arithmetic over committed data with no network (D-57), so a handful of re-runs is milliseconds.

- **D-68: Per-input step sizes are declared in a small committed YAML table, in each input's own natural unit.** `tests/mutation_targets.yaml` is the precedent and the reason: D-51 put the mutation table in data specifically so a new row is a table addition rather than a script edit. The same applies here. The step is **displayed on every row** — *"+1 shoot day: $X"*, *"+1 imported crew member: $Y"* — which is what makes the ranking honest. There is no shared scale across incommensurable inputs, and inventing one to declare a single winner would be a fabrication; naming the step lets the reader see the comparison is step-relative.

- **D-69: A perturbation that crosses a cliff says so, on that row.** "Crew size 58 → 62 crosses the tier boundary" is the single most useful thing this output can tell a producer, and it is invisible in a bare delta.

- **D-70: A CI grep over the sensitivity output strings for prescriptive vocabulary.** *"recommend", "should", "consider", "best", "optimal", "you could"* — fail on a hit. OUT-03's "never as a prescriptive recommendation" is a product commitment, and this repo's answer to a product commitment is a gate (D-28, D-49, D-63). Without it, "never prescriptive" survives exactly as long as the first person writing UI copy under deadline pressure remembers it.

### The D-36 seam — a modelled spend reaching `price_jurisdiction`

- **D-71: Route A returns dollars now, and its qualified spend is never `validated`.** The spend figure derives from the canonical budget, whose weakest input is a `modelling_assumption` (department ratios), so **D-59** already forces the honest tier and **D-63** enforces it in CI. `SPEND_NOT_DERIVED` in `app/services/spec.py` is retired and replaced by a real figure — retired, not left dangling.

- **D-72: A validation pair may never route through the budget model, and a test asserts it.** D-02 is rated one-way and this is where it becomes attackable: once a spec→spend model exists, feeding a fixture's `ProductionSpec` through it and comparing to a disclosed award looks like a stronger validation than it is. Disclosures publish qualified spend and the award, **not the production's input vector** (`feasibility-incentives.md:263`) — so such a comparison would be measuring a fabricated input vector, and a green result would mean nothing. Validation pairs keep feeding disclosed spend directly into `price_jurisdiction`. — **Reversibility:** one-way — this is the difference between the project's accuracy claim being checkable and being circular.

- **D-73: Route A and Route B stay visibly distinct (D-32 holds), and the reason is now sharper.** In Phase 3 the two routes differed in what they returned. From Phase 4 they both return a credit figure, and the **only** difference is where the qualified spend came from — modelled versus disclosed. That is exactly the thing the page must make visible, and it is the demo's opening beat sitting next to its second one.

- **Existing guard that must be updated, not deleted.** `tests/test_app_spec_route.py:250-258` currently asserts `app/services/spec.py` does **not** import `engine.pipeline` or `engine.qualifying_base`. Phase 4 legitimately reverses that constraint. Replace the assertion with the **D-63** basis walk over Route A's returned tree — do not simply drop it, or the phase silently trades a real structural guard for nothing.

### Currency, tax exemptions, and the cut line

- **D-74: FX is a committed dated snapshot, and a missing pair is a refusal, not a cross-rate.** `data/fx/` records `base`, `quote`, `rate`, `as_of_date`, `source_url`, `retrieved_at`, surfaced as its own `Figure` with `basis: sourced`. COST-08's "dated FX rate carried as a cited figure" is satisfied more auditably by a committed snapshot than by a live call, and Phase 7's freshness gate takes it live later (D-57). If a needed pair is absent, refuse with a stated reason rather than deriving it through a third currency — the same shape as `engine.net_cash.transferable` refusing at an unsourced discount rate.

- **D-75: Currency is a first-class component of the gap decomposition, not a hidden conversion.** PROJECT.md names the components as "labour, housing, stages, equipment, travel, currency" — currency is on that list. A London-vs-New-York gap must show how much of the difference is the FX rate on its own line, at its own date, or the decomposition is not a decomposition.

- **D-76: INC-10's exemptions are cost reductions and never touch the incentive figure.** A sales-tax or hotel-occupancy exemption reduces the cost line it applies to, as its own named sourced stackable figure. Folding it into the credit would corrupt the one number that has to stay reproducible against a government disclosure (D-02) — and the requirement's own wording, "separate stackable cost reductions," says which side of the line it sits on.

- **D-77: OUT-04 — tag every budget line with its ATL/BTL/Post account at creation; do not build the view.** Tagging costs nothing at model-definition time and is expensive to retrofit across every line; the rendered breakdown is the genuinely cuttable half, and Phase 11 owns its full treatment. This is the honest reading of "stretch": ship the data, defer the view. — **Reversibility:** reversible — the view is additive over tagged data.

- **D-78: Golden cost tests — a fixed `ProductionSpec` plus fixed cost profiles must produce exact `Decimal` totals in CI.** D-57 makes the cost side deterministic, which makes this possible; without it, a one-character edit to a rate card moves the headline number and nobody notices until a demo. All cost arithmetic goes through `engine/rounding.py::quantize_money`, `Decimal` only, and every numeric value in a cost profile is a quoted string (RD-01).

### Claude's Discretion

Every decision above is Claude's discretion — the user delegated all four gray areas in full. Downstream agents should treat them as working decisions with stated rationale, and overturn any of them on the user's word without needing to re-argue the case.

Four are load-bearing on the project's honesty claim and should be escalated rather than quietly reversed if they become inconvenient during planning or execution:

- **D-56** — no fabricated `$0` incentive to make the ranking look complete.
- **D-59 / D-63** — a total inherits its weakest basis, and CI proves no cost figure claims `validated`.
- **D-64** — no invented seasonal multiplier on the largest cost lines.
- **D-72** — no validation pair routed through the budget model.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` § "Phase 4: Cost Localization & Landed-Cost Outputs" (lines 164-180) — the goal, the five success criteria, and the **Cut line** naming OUT-04 as the cuttable item
- `.planning/ROADMAP.md` § "Phase 5: Curated Breadth & the Validation Loop" (lines 181-199) — read for the **boundary**: Phase 5 owns the CA/NJ/CT rule files. This is the line D-53 draws.
- `.planning/ROADMAP.md` § "Phase 6: The Interface" (lines 200-217) — note "built against the API contract fixed in Phases 2-3 using New York plus mocked cities until Phase 5 lands"; the roadmap already anticipates the one-net-ranked-city state D-55 produces
- `.planning/REQUIREMENTS.md` lines 35-42 — COST-01 through COST-08 verbatim
- `.planning/REQUIREMENTS.md` line 55 — INC-10 verbatim ("separate stackable cost reductions")
- `.planning/REQUIREMENTS.md` lines 59-62 — OUT-01 through OUT-04, including OUT-04's stretch marking
- `.planning/PROJECT.md` line 78 — non-union local labour rates are not public; the basis for D-60 and for the `modelling_assumption` basis value
- `.planning/PROJECT.md` line 72 — why a budget figure as input makes the comparison circular; still governs Route A after D-71
- `.planning/PROJECT.md` line 96 — the four demo beats; line 114 — the honesty constraint

### Prior-phase decisions that bind this phase
- `.planning/phases/03-new-york-end-to-end-the-anora-proof/03-CONTEXT.md` § **D-36** — the spec-to-spend boundary this phase closes. Read before designing `BudgetModelBuilder`.
- `.planning/phases/03-new-york-end-to-end-the-anora-proof/03-CONTEXT.md` § **D-32, D-33, D-35, D-37** — the two-route split, the rejected pinned-spend preset, the two-layer budget refusal, and what Route A returned before this phase
- `.planning/phases/03-new-york-end-to-end-the-anora-proof/03-CONTEXT.md` § **D-38, D-39** — the crew-tier table and the rule that a modelling assumption may never carry `validated`. D-38 explicitly defers the tier→department-ratio columns to this phase.
- `.planning/phases/03-new-york-end-to-end-the-anora-proof/03-CONTEXT.md` § **D-40, D-43, D-44, D-45, D-46** — free-text cities, API-first, `engine/` stays HTTP-free, the full recursive `Figure` tree serializes, every figure shows source/date/tier/derivation
- `.planning/phases/01-foundations-source-truth-deploy-path/01-CONTEXT.md` § **D-02** — the interpreter-only boundary, rated one-way. D-72 is its defence in this phase.
- `.planning/phases/01-foundations-source-truth-deploy-path/01-CONTEXT.md` § **D-08** — source documents archived byte-for-byte in the repo, not S3; the precedent D-57 extends to rate tables
- `.planning/phases/01-foundations-source-truth-deploy-path/01-CONTEXT.md` § **D-26, D-27, D-28** — CI blocks on red; the grep-the-source-tree precedent behind D-63 and D-70
- `jurisdictions/SCOPE-FREEZE.md` — RD-01…RD-06. **RD-01 (every numeric YAML value is a quoted string) is a hard convention** and applies to every cost profile, per-diem table and FX snapshot this phase writes. **RD-02** (two confidence vocabularies, never conflated) is the reasoning D-58 extends.
- `.planning/STATE.md` § Accumulated Context — the full Phase 1/2/3 decision log, the deferred `01-07` resize, and the measured 284 MB headroom D-57 leans on
- `.planning/WINDOWS.md` — four open entries; **#3** is the refusal-rather-than-invent precedent D-56 and D-74 both cite

### Cost-model traps — read before writing any cost line
- `.planning/research/PITFALLS.md` § **PART E** (lines 187-215) — E1 fringe/burden, E2 overtime/turnaround/meal/kit-fee gaps, E3 non-union rates, E4 the GSA ceiling-vs-market caveat, **E5 the general principle** that every cost line carries the same confidence discipline as an incentive figure. D-58 through D-62 are this section made structural.
- `.planning/research/PITFALLS.md` § **PART F** (F1 visual weight, F2 implied freshness, F4 accuracy-claim scope) — F2 is the basis for D-66

### Architecture
- `.planning/research/ARCHITECTURE.md` § Q1 "The Core Computation Pipeline" (lines 79-137) — **the stage diagram is the map for this phase.** Stages `[1]`, `[2]`, `[6]`, `[7]`, `[8]` are Phase 4's; `[3]`–`[5]` are built. Read "the seam that matters most" paragraph.
- `.planning/research/ARCHITECTURE.md` § Q5 "The Caching Boundary" (lines 411-425) — the tiered-refresh table and `DataFreshnessGate`. **Phase 7's artifact, not Phase 4's** (D-57); read for the shape the committed snapshots must later slot into.
- `.planning/research/ARCHITECTURE.md` § Q6 "API and Frontend Contract" (lines 451-503) — the `/api/v1/price` response shape, the per-quarter time series, and the `FigureRef` pattern. **Read with corrections:** it assumes Postgres and nginx, both overruled by Phase 1's D-08/D-16/D-17.
- `.planning/research/STACK.md` — versions and rationale. Its React/Vite/MapLibre recommendation stays deferred to Phase 6 by D-42.
- `.claude/CLAUDE.md` — the AI-vendor boundary and forbidden-dependency list. Phase 4 adds **no** AI SDK and no new dependency at all; a plan proposing one is a scope error.

### Engine contract (Phases 2-3 output)
- `engine/figure.py` — `Figure`, the closed two-value `Confidence`, and `combined_confidence`. **Read its module docstring's RD-02 note** — it is the reasoning D-58 follows. **Note the empty-sequence default returns `"validated"`** — the landmine D-59 names.
- `engine/figure_serialize.py::figure_to_dict` — the only path a `Figure` takes to JSON. D-58's `basis` field is added here, and this is the contract Phases 6/8/10 render against.
- `engine/spec.py` — `ProductionSpec`, `CrewHeadcount`, `resolve_crew_tier`. The input this phase consumes; its module docstring states the never-a-money-field invariant that survives D-71.
- `engine/pipeline.py::price_jurisdiction(ruleset, qualified_spend)` — takes qualified spend **as an argument**; Phase 4 supplies a modelled one for the first time
- `engine/qualifying_base.py` — `SpendBreakdown` / `SpendBreakdown.from_total()`. Its docstring states the D-02 boundary; Phase 4 builds the localized breakdown that finally feeds it properly.
- `engine/rounding.py::quantize_money` — the single pinned rounding call site. No `.quantize()` anywhere else, cost side included.
- `engine/models.py` — `JurisdictionRuleSet`; **not modified by this phase**
- `data/crew_tiers.yaml` — the `basis: modelling_assumption` / `provenance_note` precedent D-58's vocabulary is taken from, and the table D-38 says gains department-ratio columns here
- `app/services/spec.py` — Route A's handler, `SPEND_NOT_DERIVED` (retired by D-71), and the module-boundary docstring that D-71 reverses
- `app/services/city_lookup.py` — the explicit no-fuzzy-match city allow-list (D-40); cost profiles key off the same resolution
- `tests/mutation_targets.yaml` — the declared-table-in-data precedent D-68 follows
- `tests/test_app_spec_route.py` lines 250-258 — the import guard D-71 reverses and D-63 replaces
- `tests/fixtures/jurisdictions/synthetic-*.yaml` — synthetic rule files for engine tests; the correct home for a multi-city ranking test that must not reach the hosted page (D-55)

### Governing brief
- `productionfinance-brief.md` — governs wherever the two briefs disagree
- `feasibility-incentives.md` line 263 — disclosures give qualified spend and the award, **not the input vector**. The origin of D-02 and therefore of D-72.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`engine/figure.py::Figure`** — already carries `value`, `unit`, `label`, `derivation`, recursive `inputs`, `source_url`, `date_checked`, `confidence`, `live_fetched_this_run`. Every cost line becomes a `Figure`; the only model change this phase needs is D-58's `basis`.
- **`engine/figure.py::combined_confidence`** — the exact shape `combined_basis` mirrors, minus its empty-sequence default (D-59).
- **`engine/rounding.py::quantize_money`** — the pinned `ROUND_HALF_UP` call site, already property-tested. Cost arithmetic uses it; nothing else calls `.quantize()`.
- **`engine/spec.py::ProductionSpec`** — the seven-input contract, validated and round-trippable, built in Phase 3 explicitly as the durable artifact this phase consumes.
- **`data/crew_tiers.yaml` + `resolve_crew_tier`** — the tier→headcount table with its `basis` / `provenance_note` header. D-38 says the department-ratio columns are added here, in the same file, with the same labelling.
- **`engine/pipeline.py::price_jurisdiction`** — complete and proven for New York. Phase 4 changes what feeds it, not how it works.
- **`tests/fixtures/jurisdictions/synthetic-*.yaml`** — eight synthetic rule files already used to exercise engine paths no real jurisdiction covers. The right tool for testing a multi-city net ranking before Phase 5 lands.
- **`.github/workflows/ci.yml`** — six blocking jobs already. D-63's basis walk and D-70's vocabulary grep slot in beside them with the existing `astral-sh/setup-uv@v5` + `uv run --frozen` pattern.

### Established Patterns
- **`engine/` is jurisdiction-agnostic and HTTP-free** (D-44, JUR-05). Cost localization is *also* jurisdiction-agnostic by ARCHITECTURE.md's own stage boundary, so `CityLocalizer` belongs in `engine/` and must not branch on a jurisdiction id.
- **Two confidence vocabularies, never conflated** (RD-02, `engine/figure.py` docstring). D-58 adds a third axis rather than overloading either.
- **Quoted-string decimals everywhere** (RD-01). Every cost profile, per-diem row and FX rate is a quoted string; an unquoted `0.25` parses as a float and corrupts through `Decimal()`.
- **Refuse rather than invent.** `engine.net_cash.transferable` returns a low/high bound with `point=None` rather than a fabricated midpoint, and raises rather than converting at an unsourced rate (WINDOWS #3). D-56 and D-74 are the same rule on the cost side.
- **Provenance is structural, not aspirational.** A figure with no source reports having no source; it does not borrow one. D-61 puts the per-diem caveat on the figure for the same reason.
- **Honesty commitments become CI gates** (D-28 vendor grep, D-49 automated mutation job, D-51 declared table in data). D-63, D-68 and D-70 all follow this precedent rather than adding a convention.
- **Findings are documented, not routed around.** Plan 02-09 recorded a genuine blocker to WINDOWS.md rather than working around it silently.

### Integration Points
- **`app/services/spec.py` is the file this phase changes most.** Its docstring forbids importing `engine.pipeline` / `engine.qualifying_base`, `tests/test_app_spec_route.py:250-258` asserts it, and `SPEND_NOT_DERIVED` is its honest terminal state. D-71 reverses all three — **deliberately, with D-63's guard replacing the deleted one.**
- **`engine/figure_serialize.py::figure_to_dict` is a published contract.** Adding `basis` is additive; Phase 6's click-through panel, Phase 8's proof panel and Phase 10's index all consume this shape.
- **New data directories.** Cost profiles, per-diem snapshots and FX snapshots are new committed data. `data/` (crew_tiers) and `sources/` + `sources/MANIFEST.yaml` (archived documents, D-08/D-10) both already exist — a rate table derived from an archived document belongs in `data/`, and the document it came from belongs in `sources/` with a MANIFEST entry.
- **Deploy:** `git pull` + `deploy/deploy.sh`, `prodfin.service` on `127.0.0.1:8000`, Apache `ProxyPass /finance`. New data files must land inside the deployed tree; module-anchored paths only (`app/services/_paths.py::REPO_ROOT` is the established convention — the systemd unit and pytest run from different working directories).

### Known Constraints
- **WINDOWS.md #3 (open).** `jurisdictions/us-ct.yaml`'s transfer-discount rates are null, so `price_jurisdiction` raises for every active Connecticut pair. Hartford is in D-54's stretch set, and a Hartford cost profile is unaffected — but Hartford can never enter D-55's *net-ranked* band while #3 is open. It would sit in the `incentive_not_modelled` band with a more precise reason: *cannot be converted to net cash — no sourced transfer discount rate.*
- **The box was never resized.** Still `nano_2_0`: 472 MB total, ~284 MB available with `prodfin.service` running. D-57's no-network, no-new-dependency posture keeps this phase's footprint flat.
- **Repo-wide ruff baseline is ~297 findings** (WINDOWS #2, #4) and out of scope per the executor scope-boundary rule. Do not let a cost-model plan turn into a lint cleanup.

</code_context>

<specifics>
## Specific Ideas

- **The floor city set is New York, Los Angeles, London.** NY carries the Anora anchor and the only rule file; NY-vs-LA is the comparison every producer actually makes and the demo's ranking-inversion beat; London supplies the non-USD currency component success criterion 4 requires.
- **The gap that Phase 4 can genuinely show today** is New York vs Los Angeles, cost-only, fully decomposed — labour, housing, per diem, flights, stages, equipment, permits, locations, trucking — with the incentive component present and explicitly pending for LA. That is a real, useful, honest output, not a placeholder.
- **The sensitivity row that earns its place:** *"+1 imported crew member: +$X to the New York–Los Angeles gap"* — with the step shown, the direction shown, and no verb telling anyone what to do.
- **A cliff crossing is the most valuable thing this output can say.** "Crew size 58 → 62 crosses the tier boundary" is information a rate card cannot give a producer, and a bare delta hides it.
- **The per-diem caveat is one sentence and it lives on the figure, not the template.** PITFALLS E4 calls it a cheap fix with an outsized credibility payoff; anyone in the industry knows per diem is not a hotel rate, and an unqualified GSA number is the fastest way to lose them.
- **Two routes, one engine — sharper now.** From this phase both routes return a credit figure and the *only* difference is where the qualified spend came from. That difference is the product.

</specifics>

<deferred>
## Deferred Ideas

- **CA / NJ / CT jurisdiction rule files and Job 1** — Phase 5. Phase 4 builds cost profiles for cities in those jurisdictions (D-53); it does not build their rule files, and must not pull one forward to manufacture a second net-ranked city.
- **`DataFreshnessGate` and the live cache boundary** (ARCHITECTURE Q5) — Phase 7. Phase 4's committed snapshots become its cold-start seed (D-57).
- **Live FX, live per diem, live rate-card refresh** — Phase 7, through the gate. Phase 4 commits dated snapshots.
- **The map, slider, ranked-list treatment and the consolidated printable assumptions panel (PRV-04)** — Phase 6. Phase 4 owes the *data* — per-line `basis`, the acknowledged-gap list, the per-diem caveat, the quarter-invariant line list — and Phase 6 owes the panel.
- **The rendered ATL/BTL/Post chart-of-accounts view (OUT-04)** — tags land here (D-77), the view is Phase 11's full treatment.
- **Overtime, turnaround penalties, meal penalties, kit fees, non-union local differentials, negotiated hotel rates** — declared acknowledged gaps (D-60), not modelled in Accounts. Candidates for Balances only with a real source; PITFALLS E2 is explicit that a 17-day window will not model them honestly.
- **Seasonal stage / crew / equipment variation** — an acknowledged gap under D-64 until a sourced index exists. Not a multiplier, ever.
- **Reverse mode — "what change would close this city's gap"** — Phase 11. D-67's perturbation machinery is the natural substrate for it, which is a reason to build the step table (D-68) as data rather than inline constants.
- **Extending the D-51 mutation table to a cost anchor** — once D-78's golden cost totals exist, a cost-profile rate is a legitimate mutation target proving the cost suite is non-vacuous too. One row, no script change. Phase 8's SHP-14 re-proof is the natural place.

</deferred>

---

*Phase: 4-Cost Localization & Landed-Cost Outputs*
*Context gathered: 2026-08-26*
