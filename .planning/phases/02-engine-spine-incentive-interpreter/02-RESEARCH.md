# Phase 2: Engine Spine & Incentive Interpreter - Research

**Researched:** 2026-08-25
**Domain:** Deterministic rule-interpretation engine (jurisdiction incentive math), not external tech selection
**Confidence:** HIGH

## Summary

Per the phase brief, external technology is already locked (`google-genai`, `parallel-web`, FastAPI, Pydantic v2, stdlib `decimal.Decimal`, YAML-in-repo, pytest — see `.claude/CLAUDE.md`) and the architecture is already specified in `.planning/research/ARCHITECTURE.md` Q1-Q3 (the pipeline seam, the `JurisdictionRuleSet` schema, the `Figure` value object). This research therefore does not re-litigate stack choices. It instead does three things the phase brief asks for directly: (1) reads what Phase 1 actually shipped so Phase 2 extends it rather than re-deriving it, (2) enumerates the fixed rule-dimension set for the mandated dated scope-freeze note, and (3) verifies — by executing code against this repo's actual locked dependency versions and Phase 1's actual committed fixtures — several concrete correctness hazards that are easy to get subtly, silently wrong: a float/Decimal precision bug in rate parsing, a rounding-mode gap in exact-match assertions, and a cliff-vs-blended ambiguity in "tiered" rate structures that ARCHITECTURE.md's schema allows but does not disambiguate.

Three findings changed what would otherwise have been the default (and wrong) implementation choice, all verified by direct execution against this repo's own `uv.lock` versions this session (Python 3.12.14 via `uv run`, `pydantic==2.13.4`, `pyyaml==6.0.3`):

1. **PyYAML parses an unquoted rate like `0.263` as a native Python `float`.** Passing that float directly into `Decimal(x)` (rather than `Decimal(str(x))`) produces garbage past the 15th significant digit (`Decimal('0.263')` vs `Decimal('0.26300000000000001154...')`). ARCHITECTURE.md's schema literally types rate fields as `float` (`base_rate: float`, `additional_rate: float`) — if implemented literally, this reintroduces exactly the float-precision bug D-03 already fenced off for money fields, just for rates instead. **Pydantic v2's `Decimal` field validator, however, safely converts a Python float via its string representation** (`Decimal(rate=0.263)` on a `Decimal`-typed field yields `Decimal('0.263')`, confirmed this session) — so the fix is to type every numeric rule-file field `Decimal` in the Pydantic model (never `float`), and additionally to quote every rate/threshold value as a YAML string, matching the money-field convention Phase 1 already established in `tests/test_validation_pair_fixtures.py`.
2. **Exact-match assertions require an explicit, documented rounding mode — truncation is provably wrong.** Connecticut's `Christmas Always` fixture (`tests/fixtures/validation_pairs/ct_christmas_always.yaml`) computes to exactly `$1,159,501.50` before rounding (`$3,865,005 × 30%`); the disclosed, asserted figure is `$1,159,502`. `ROUND_HALF_UP` and `ROUND_HALF_EVEN` both happen to agree on this specific value, but Python's `Decimal` module default context is `ROUND_HALF_EVEN`, not `ROUND_HALF_UP`, and nothing in the codebase currently pins one — a future exact-mode fixture landing on an odd-dollar `.50` will silently expose whichever one is actually in effect. This must be a named, tested constant, not an implicit default.
3. **Connecticut's `tiered_by_spend` rate structure is a cliff/threshold lookup (the whole qualifying base gets one rate, selected by which band the total falls in), not a marginal/blended calculation** — confirmed by recomputing both interpretations against the disclosed `Christmas Always` figure this session: the cliff interpretation (`$3,865,005 × 30%` flat) reproduces `$1,159,502` exactly; the blended/marginal interpretation (10% on the first $500K, 15% on the next $500K, 30% on the remainder) produces `$984,501.50` — off by nearly $175,000. This is architecturally distinct from the UK's `blended_by_ceiling_split` (which genuinely *is* two rates summed within one production, per ARCHITECTURE.md's schema). Implementing `tiered_by_spend` as a marginal calculation instead of a lookup would be a subtly wrong, plausible-looking bug.

**Primary recommendation:** Build the generic interpreter exactly to ARCHITECTURE.md Q1-Q3's design, but (a) type every rule-file numeric field `Decimal` and quote it as a YAML string — never `float`; (b) pin `ROUND_HALF_UP` as an explicit, named, tested rounding constant used at every point money is quantized to whole cents/dollars; (c) implement `tiered_by_spend` as a single-rate-lookup-by-band, distinct in code from `blended_by_ceiling_split`'s two-rates-summed; and (d) build the real `jurisdictions/us-ny.yaml` and `jurisdictions/us-ct.yaml` rule files in this phase (not synthetic-only fixtures) as the primary proof vehicle for success criteria 1-3, directly exercising Phase 1's already-committed `ny_anora.yaml`, `ny_succession_s4.yaml`, `ny_gilded_age_s2.yaml`, and `ct_christmas_always.yaml` at the interpreter level per D-02 (qualified spend in, net cash out — no cost-localization pipeline exists yet and none is needed for this).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INC-01 | Qualifying base computed under each jurisdiction's own definition (total spend / labour-only / lesser-of / local-hires-only) | Architecture Patterns diagram (`QualifyingBaseCalculator`), Scope-Freeze Note item 1, Validation Architecture test row |
| INC-02 | Per-person ceilings, incl. loan-out vs. W-2 treatment | Pitfall 4 (ceiling applies to base, before rate — verified against GA worked example), Scope-Freeze Note item 2 (GA's 5-tier schedule, not a scalar) |
| INC-03 | Tiers/uplifts applied in correct order, incl. national/regional stacking | Pitfall 3 (cliff vs. blended dispatch, verified), A1.1 stacking rule (sum dollars, never percentages), Code Examples |
| INC-04 | Per-project and annual programme caps | Architecture Patterns diagram (CreditCalculator steps 4-5), Open Question 1 (per-component vs. global cap ambiguity, flagged not resolved), Validation Architecture boundary test row |
| INC-05 | Availability reported separately from eligibility | Architectural Responsibility Map (cap-consumption state is a Phase 7 concern, Phase 2 accepts it as an input), Validation Architecture test row |
| INC-06 | Gross incentive converted to net cash by mechanism, net of audit fees | Architecture Patterns diagram (`NetCashConverter`, 4 mechanism functions), Code Examples (`quantize_money`), Validation Architecture test row |
| INC-07 | Taxable incentives reported net of corporation tax | Validation Architecture (UK £18M golden-value regression test, from `feasibility-incentives.md`'s own worked numbers) |
| INC-08 | Estimated cash arrival timing reported alongside value | Scope-Freeze Note item 8 (display only, not discounted — explicit scope cut per PITFALLS A1.11), Validation Architecture test row |
| INC-09 | Minimum spend thresholds and cliff effects | Pitfall/A1.6 cross-reference, Scope-Freeze Note item 9, Validation Architecture boundary test row |
| JUR-05 | Adding a jurisdiction is additive — rule file only, no engine change | Recommended Project Structure (`tests/fixtures/jurisdictions/` kept structurally separate from `jurisdictions/`), Validation Architecture (structural `git diff` check, not just a passing test) |
| PRV-01 | Every figure carries a source link and date checked | Pattern 2 (never-silent derivation), Validation Architecture test row |
| PRV-02 | Every figure carries a confidence tier (validated/researched), visually distinguishable | `Figure` dataclass definition (Code Examples), Validation Architecture test row — note the visual-distinguishability half is Phase 6's job, Phase 2 only guarantees the closed-enum data contract |
| PRV-03 | Every computed figure carries a readable derivation reason | Pattern 2, Pitfall 4/5, Validation Architecture test row |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Qualifying-base computation (base_definition interpretation) | Core computation pipeline (pure Python) | Jurisdiction rule engine | Stage 3 of the pipeline per ARCHITECTURE.md Q1; jurisdiction-specific but reads *data*, never per-jurisdiction code |
| Credit calculation (ceilings, tiers, uplifts, caps) | Jurisdiction rule engine (`engine/rules.py`) | — | The one place base/tier/cap/mechanism logic executes; a generic interpreter, not per-jurisdiction classes (Anti-Pattern 1 in ARCHITECTURE.md) |
| Net-cash conversion (mechanism → cash, audit fees, timing) | Jurisdiction rule engine | — | Exactly 4 pure functions keyed by `mechanism` enum, parameterized by jurisdiction numbers — not one function per jurisdiction |
| Provenance / derivation tracking | Core computation pipeline (the `Figure` type) | — | Travels with the data as a return-value field, not a side-channel trace object — no global state, no signature pollution |
| Rule-file loading & validation | Jurisdiction rule engine (schema layer) | — | Pydantic models validate YAML on load; this is also the escape-hatch handler registry's home |
| Custom handler escape hatch | Jurisdiction rule engine (`engine/handlers/`) | — | A small, named, ID-string-registered Python function set — never dynamic `getattr`/`importlib` from untrusted rule-file strings (see Security Domain) |
| Cap-consumption / live availability state | Data Freshness Gate (future phase) | Jurisdiction rule engine (consumes it as an input) | Phase 2 accepts availability state as a passed-in value/interface; it does not fetch it — that's Phase 7's `DataFreshnessGate` |
| Cost localization (budget → localized line items) | Core computation pipeline (stages 1-2) | — | Explicitly out of Phase 2 scope (Phase 4) — the engine consumes a `LocalizedBudget`-shaped input it does not itself produce yet |
| HTTP API / UI wiring | API layer (future phase) | — | Phase 2 ships no endpoints; Phase 3 wires the engine to `/price` and the input contract |

## Package Legitimacy Audit

No new external packages are introduced by this phase. `pydantic` (2.13.4) is already resolved in `uv.lock` as a transitive dependency of `fastapi==0.141.1` (confirmed by reading `uv.lock` this session: `name = "pydantic"` / `version = "2.13.4"`, `pydantic-core` `2.46.4`) — Phase 2 only needs to add it as an **explicit** `pyproject.toml` dependency (not new to the lockfile, just newly imported directly by name). `pyyaml==6.0.3` is already an explicit direct dependency (`pyproject.toml`, confirmed by reading this session). `decimal` and `dataclasses` are stdlib. No `npm view`/`pip index versions`-style registry check is needed since no new package enters the dependency graph; this section exists to record that check was considered and found not applicable, not to skip it silently.

| Package | Registry | Status | Disposition |
|---------|----------|--------|-------------|
| `pydantic` | PyPI | Already resolved 2.13.4, transitively via `fastapi` | No action — add explicit `pydantic>=2` line to `pyproject.toml` dependencies for direct-import clarity |
| `pyyaml` | PyPI | Already an explicit dependency, 6.0.3 | No action |

**Packages removed due to [SLOP] verdict:** none. **Packages flagged as suspicious [SUS]:** none.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic` | 2.13.4 (locked in `uv.lock`, transitively via FastAPI) [VERIFIED: uv.lock read this session] | `JurisdictionRuleSet` schema validation on YAML load; `model_json_schema()` doubles as the Gemini structured-extraction contract in a later phase (per `.claude/CLAUDE.md`) | Already resolved in this repo; no new dependency; matches CLAUDE.md's explicit recommendation |
| `decimal.Decimal` | stdlib | All monetary and rate arithmetic | Locked by CLAUDE.md; `py-moneyed` is explicitly forbidden (unmaintained since Nov 2022) |
| `pyyaml` | 6.0.3 [VERIFIED: pyproject.toml + uv.lock read this session] | Loading `jurisdictions/*.yaml` rule files | Already the project's YAML library; `yaml.safe_load` only — never `yaml.load`/`yaml.unsafe_load` (see Security Domain) |
| `pytest` | 9.1.1 [VERIFIED: pyproject.toml read this session] | Engine unit tests, boundary/cliff tests, validation-pair-driven interpreter tests | Already the project's test runner; `testpaths = ["tests"]` in `pyproject.toml` means new engine tests are picked up with zero CI config changes |

### Supporting

No new supporting libraries. A frozen `dataclass` (stdlib, not Pydantic) is the correct implementation vehicle for the `Figure` value object specifically — ARCHITECTURE.md Q3 evaluates and rejects a global mutable trace object and full event-sourcing in favor of this, and a plain frozen dataclass (not a Pydantic model) is appropriate here because `Figure` is an *engine-internal output* the engine itself constructs and controls, not external input requiring validation — Pydantic's validation overhead buys nothing for a value the engine already knows is well-formed by construction, whereas `JurisdictionRuleSet` (external YAML input) genuinely needs Pydantic's parse/validate/error-report behavior.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic `Decimal`-typed rate fields | `float`-typed fields as ARCHITECTURE.md's schema literally lists them | Rejected — verified this session to silently corrupt any rate that isn't an exact power-of-two fraction (0.25 is safe; 0.263, 0.30, 0.35 are not) once passed through `Decimal()` without care. This is not a style preference; it is a correctness bug with no compensating benefit. |
| A frozen `dataclass` for `Figure` | A Pydantic `BaseModel` for `Figure` | Pydantic validation is unneeded overhead for an engine-constructed, engine-controlled value; `asdict()` on a frozen dataclass already gives free JSON serialization for the future `/api/v1/figure/{id}` endpoint (Phase 6) |
| Explicit handler registry (dict literal, ID string → function) | `getattr`/`importlib.import_module` resolving `custom_handler_id` dynamically | Dynamic resolution from a rule-file string is a code-execution vector once Job 2 (Phase 7) starts writing LLM-extracted rule files with a `custom_handler_id` field — see Security Domain |

**Installation:**
```bash
# No new packages. Add pydantic as an explicit direct dependency for clarity:
uv add pydantic
```

**Version verification:** `pydantic` 2.13.4 and `pydantic-core` 2.46.4 confirmed already present via `grep -A3 '^name = "pydantic"' uv.lock` this session — no registry lookup needed since nothing new is being added to the resolved dependency graph.

## Architecture Patterns

### System Architecture Diagram

```
JurisdictionRuleSet YAML file (jurisdictions/<id>.yaml, git-versioned)
                │
                │  yaml.safe_load()  [NEVER yaml.load/unsafe_load — see Security Domain]
                ▼
Pydantic model validation  (JurisdictionRuleSet, Decimal-typed money/rate fields)
                │  raises on unknown enum values / missing required fields
                │  (fail loud on a malformed rule file, never silently default)
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  QualifyingBaseCalculator                                            │
│  in:  LocalizedBudget-shaped input (Phase 2: a direct qualified_spend│
│        Decimal, per D-02 — no cost-localization pipeline exists yet) │
│        + JurisdictionRuleSet.programmes[i].base_definition           │
│  reads base_definition.type → dispatches to one of 4 generic         │
│  handlers (total_qualified_spend / labour_only /                     │
│  lesser_of_pct_core_or_actual_local / local_hires_only) or the       │
│  custom_handler_id registry for the escape hatch                     │
│  out: QualifyingBase (a Figure, derivation = ["base type: X"])       │
└───────────────────────────┬────────────────────────────────────────-┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  CreditCalculator — ORDERED, DATA-DECLARED adjustment sequence:      │
│  1. per_person_ceiling  (W-2 capped / loan-out uncapped+withholding) │
│     — applied to the BASE, before the rate (verified against the    │
│     GA worked example: $10M spend, $2M W-2 lead → $8.5M ceiling-    │
│     adjusted base × 30% = $2.55M, matching feasibility-incentives.md│
│     exactly — this is not stage-4-clips-the-dollar-output, it is    │
│     stage-4-clips-the-base-before-the-rate)                          │
│  2. uplift_stacking_rules (additive to base rate; independent-dollar│
│     stacking across programmes per A1.1 — NEVER sum percentages     │
│     across programmes with different bases)                          │
│  3. tier / blend rate — dispatches on rate_structure.type:           │
│       flat            → one rate, whole base                        │
│       tiered_by_spend  → LOOKUP: whole base × the ONE rate for the   │
│                          band the total falls in (verified against  │
│                          CT: $3,865,005 × 30% = $1,159,502 exact —   │
│                          NOT a marginal/blended calculation)          │
│       blended_by_ceiling_split → TWO rates, both applied, summed     │
│                          (UK-style: enhanced rate on first N, std    │
│                          rate on remainder — genuinely different     │
│                          from tiered_by_spend, do not conflate)      │
│       headcount_scaled → NM-style sliding scale, out of Phase 2's    │
│                          curated-jurisdiction scope but the generic  │
│                          dispatch shape must accommodate it           │
│  4. per_project_cap     (clip, if declared)                          │
│  5. annual_programme_cap — Phase 2 accepts consumption state as an   │
│     INPUT (a passed-in "remaining" value), never fetches it — cap    │
│     EXISTENCE is rule data (this phase), cap CONSUMPTION is live     │
│     data (Phase 7's DataFreshnessGate)                                │
│  Each step appends a derivation line EVEN WHEN A NO-OP               │
│  ("no per-person ceiling applies in this jurisdiction") — never      │
│  silent (ARCHITECTURE.md Q3's stated invariant)                      │
│  out: GrossCredit (a Figure, inputs=(QualifyingBase,))               │
└───────────────────────────┬────────────────────────────────────────-┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  NetCashConverter — 4 pure functions keyed by `mechanism`:           │
│  refundable() / transferable() / rebate_grant() /                    │
│  nonrefundable_credit() [taxable, net of corporation tax]            │
│  Each: deduct audit fee (cliff-tiered by spend threshold, GA-style   │
│  $500K-5M/$5-10M/$10M+ boundaries) → apply mechanism-specific         │
│  conversion (transfer_discount rate / corporation tax rate / none)   │
│  → quantize to whole cents using the pinned ROUND_HALF_UP constant   │
│  out: NetCash (a Figure) + ArrivalTiming (terms_lock_at + payout_lag)│
│  Explicit invariant (A1.5): net cash output NEVER feeds back into    │
│  step 1's qualifying-base input for the same production/jurisdiction │
└─────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
engine/
├── __init__.py
├── models.py          # Pydantic: JurisdictionRuleSet, Programme, BaseDefinition,
│                       #   PerPersonCeiling, RateStructure, Caps, Audit, Timing,
│                       #   TransferDiscount, Validation — all Decimal-typed numeric fields
├── figure.py           # frozen dataclass Figure (value, unit, label, derivation,
│                       #   inputs, source_url, date_checked, confidence, figure_id,
│                       #   live_fetched_this_run)
├── rounding.py          # ROUND_HALF_UP as a single named, imported constant + a
│                       #   quantize_money(value: Decimal) -> Decimal helper — one
│                       #   place, so a future change is a one-line diff, not a grep
├── qualifying_base.py   # base_definition.type dispatch (4 generic handlers)
├── credit.py           # per_person_ceiling → uplift_stacking → rate → caps sequence
├── net_cash.py          # 4 mechanism functions
└── handlers/
    ├── __init__.py      # REGISTRY: dict[str, Callable] — explicit allow-list, no
    │                    #   dynamic import (see Security Domain)
    └── ...               # named escape-hatch functions, referenced by
                          #   custom_handler_id string in a rule file

jurisdictions/
├── us-ny.yaml           # real curated jurisdiction — proves the interpreter against
│                        #   Anora/Succession S4/Gilded Age S2 (D-05 anchors)
└── us-ct.yaml           # real curated jurisdiction — proves tiered_by_spend against
                         #   Christmas Always (D-05's third exact-mode anchor)

tests/
├── fixtures/
│   ├── validation_pairs/   # ALREADY EXISTS (Phase 1) — do not duplicate or move
│   └── jurisdictions/       # NEW — throwaway/synthetic rule files for boundary
│       │                    #   tests and the JUR-05 additivity proof; kept
│       │                    #   structurally separate from jurisdictions/ (real,
│       │                    #   curated, cited data) so a reviewer never confuses
│       │                    #   a test fixture with a production rule file
│       ├── zz-fixture-throwaway.yaml   # JUR-05 proof jurisdiction
│       ├── synthetic-ga-style.yaml     # per-person ceiling + cliff + uncapped
│       ├── synthetic-uk-style.yaml     # blended_by_ceiling_split + taxable mechanism
│       └── synthetic-stacking.yaml     # national+regional stacking, independent bases
├── test_engine_models.py         # Pydantic Decimal-typing regression test (Finding 1)
├── test_engine_rounding.py       # ROUND_HALF_UP pinning + the CT half-cent case
├── test_engine_qualifying_base.py
├── test_engine_credit.py         # ordering hazards, per-person ceiling, tiers/uplifts
├── test_engine_net_cash.py       # 4 mechanisms, audit fee cliffs, timing
├── test_engine_figure_provenance.py   # PRV-01/02/03 as executable assertions
├── test_engine_jurisdiction_additivity.py   # JUR-05 — see Validation Architecture
└── test_engine_against_validation_pairs.py  # imports the existing
                                              #   tests/fixtures/validation_pairs/
                                              #   *.yaml fixtures and drives them
                                              #   through the real NY/CT rule files
```

### Pattern 1: Decimal-safe rule-file loading
**What:** Every numeric field on the Pydantic `JurisdictionRuleSet` model that represents money, a rate, a percentage, or a threshold is typed `Decimal`, never `float` or `int`. Every such value in the YAML source is written as a quoted string.
**When to use:** Always, for every field in `engine/models.py`. This is not a per-field judgment call — apply it uniformly, the same way Phase 1's `test_validation_pair_fixtures.py` uniformly requires `MONEY_FIELDS` to be YAML strings.
**Example:**
```python
# Source: verified this session against pydantic==2.13.4 (this repo's locked version)
from decimal import Decimal
from pydantic import BaseModel

class RateStructure(BaseModel):
    base_rate: Decimal          # NOT float — see Finding 1
    # ...

# jurisdictions/us-ct.yaml (excerpt)
# rate_structure:
#   type: tiered_by_spend
#   tiers:
#     - {threshold_low: "100000", threshold_high: "500000", rate: "0.10"}
#     - {threshold_low: "500000", threshold_high: "1000000", rate: "0.15"}
#     - {threshold_low: "1000000", threshold_high: null, rate: "0.30"}
```

### Pattern 2: Never-silent derivation
**What:** Every adjustment step in `CreditCalculator` (per_person_ceiling, uplift_stacking, tier/rate, per_project_cap, annual_programme_cap) unconditionally appends a `derivation` line to the `Figure` it returns, including a no-op line ("no per-person ceiling declared for this programme") when the step does nothing.
**When to use:** Every step, every programme, unconditionally — this is the concrete mechanism PRV-03 depends on and the concrete mechanism that makes "only $500K of the $2M lead qualifies — Georgia per-person ceiling" (the example named in `REQUIREMENTS.md` PRV-03) a one-line render (`derivation[-1]`) rather than a bespoke sentence-generation feature.
**Example:**
```python
# Source: pattern specified in .planning/research/ARCHITECTURE.md Q3
if programme.per_person_ceiling.applies:
    figure = figure.with_step(f"per-person ceiling applied: ${ceiling_amount} cap on {role}")
else:
    figure = figure.with_step("no per-person ceiling applies in this jurisdiction")
```

### Anti-Patterns to Avoid
- **Per-jurisdiction Python subclasses:** ARCHITECTURE.md Anti-Pattern 1 — one generic interpreter, small named handler registry for true exceptions only. This is what makes JUR-05's success criterion possible at all.
- **Summing percentages across stacked programmes:** A1.1 — always sum independent dollar outputs computed against each programme's own base, never add two rates together and apply the sum to one base.
- **Interpolating across a cliff threshold:** A1.6 — minimum-spend thresholds, audit-fee tier boundaries, and NM-style headcount steps are discrete step functions; a production one dollar below a threshold gets a different (often zero) result than one dollar above it, and this must be a literal boundary test, not an assumption.
- **`Decimal(some_float)` anywhere in the codebase:** Finding 1 — always `Decimal(str(x))` if a float is ever unavoidable, though the correct fix is to never have a bare `float` rule-file field in the first place.
- **Dynamic resolution of `custom_handler_id`:** see Security Domain — `getattr`/`importlib` from a rule-file string is a code-injection vector once LLM-extracted rule files exist (Phase 7).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML rule-file schema validation | Hand-rolled dict-key checking with manual error messages | Pydantic `BaseModel` with typed fields and enum `Literal`s | Free, structured validation errors; `model_json_schema()` doubles as the future Gemini extraction contract at zero extra cost |
| Money/rate arithmetic precision | A custom fixed-point integer-cents scheme | `decimal.Decimal` with an explicit quantize step and a pinned rounding mode | Already the locked project convention (D-03); reinventing fixed-point arithmetic is exactly the kind of scope creep the phase brief's "no fresh research needed" instruction warns against |
| A generic "compute a percentage of a base" utility that silently assumes marginal/blended tiering | An ad hoc loop that sums tier bands | Two explicit, separately-named functions — `lookup_flat_rate_by_band()` for `tiered_by_spend` and `blend_two_rates_by_ceiling()` for `blended_by_ceiling_split` | Finding 3 shows these are NOT interchangeable; naming them differently in code makes the distinction impossible to blur by accident during a later edit |

**Key insight:** every "don't hand-roll" item above is really the same lesson stated three ways: the arithmetic in this domain is genuinely non-trivial (feasibility-incentives.md §2's own conclusion: "this is a real modeling problem, not a lookup table"), and building generic-looking-but-actually-wrong shortcuts is easier to do than it looks and is caught only by testing at exactly the boundaries where jurisdictions actually differ — flat vs. cliff-tiered vs. blended, ceiling-before-rate, cliff not ramp.

## Common Pitfalls

### Pitfall 1: Float-typed rate fields silently corrupt exact-match validation
**What goes wrong:** A rate like `0.263` or `0.30`, loaded from unquoted YAML and typed `float` in the Pydantic model, is not exactly representable in binary floating point. Passing it through `Decimal(x)` (as opposed to `Decimal(str(x))`) produces a value with ~17 significant digits of garbage past the intended precision, which then propagates through multiplication against a multi-million-dollar base.
**Why it happens:** ARCHITECTURE.md's schema literally lists rate fields as `float` (a shorthand for "this is a fractional number," not a deliberate typing decision), and PyYAML's default parsing of an unquoted decimal literal is a native Python `float`.
**How to avoid:** Type every rate/threshold/money field `Decimal` on the Pydantic model (verified this session: Pydantic v2's `Decimal` validator safely converts even a bare float input via its string representation) and additionally quote every such value as a YAML string, matching Phase 1's existing money-field convention.
**Warning signs:** Any exact-mode fixture test failing by a sub-cent amount that "should" be exact; any code path calling `Decimal()` on a variable whose type annotation is `float`.

### Pitfall 2: Implicit rounding mode
**What goes wrong:** Python's `decimal` module default context rounding is `ROUND_HALF_EVEN`. Nowhere in the codebase is a rounding mode currently pinned. A future rule file (or a currently-untested combination of existing fixtures) can land exactly on a `.50` cent/dollar boundary where `ROUND_HALF_UP` and `ROUND_HALF_EVEN` diverge, and the currently-passing CT fixture (`$1,159,501.50 → $1,159,502`, where both modes happen to agree) provides false confidence that rounding "just works."
**Why it happens:** Nobody deliberately chose a rounding mode; it defaulted silently.
**How to avoid:** Define `ROUND_HALF_UP` as a single named import in `engine/rounding.py`, used at every quantize call site. Write an explicit test with a constructed value where `ROUND_HALF_UP` and `ROUND_HALF_EVEN` disagree (e.g., a base/rate combination producing an odd-cent `X.5`) to prove the pinned mode is actually in effect, not merely declared.
**Warning signs:** Any `.quantize()` call without an explicit `rounding=` argument; any test fixture whose exact-mode assertion happens to land on a value where the two common rounding modes agree (masks the bug rather than catching it).

### Pitfall 3: Conflating cliff-tiered and blended rate structures
**What goes wrong:** `tiered_by_spend` (CT: whole base at one rate, selected by band) and `blended_by_ceiling_split` (UK: two rates, both applied, summed across a split) look similar — both involve "tiers" or "bands" — but are computed completely differently. Implementing one as if it were the other produces a plausible-looking but wrong number (verified this session: the marginal/blended interpretation of CT's structure is off by ~$175,000 against the disclosed figure).
**Why it happens:** "Tiered" is a natural-language word that maps to genuinely different mechanisms in different jurisdictions, and the two are easy to conflate when writing a single generic "apply the rate bands" function.
**How to avoid:** Two separate, separately-named, separately-tested functions in `engine/credit.py`, dispatched strictly on `rate_structure.type`. Test both against a real figure (CT's `Christmas Always` for the cliff case; the £18M UK worked example from `feasibility-incentives.md` for the blended case — see Validation Architecture).
**Warning signs:** A single function handling both `tiered_by_spend` and `blended_by_ceiling_split` via a shared code path with a branch inside it, rather than two distinct call sites.

### Pitfall 4: Per-person ceiling applied at the wrong pipeline stage
**What goes wrong:** It's tempting to treat the per-person ceiling as a post-hoc clip on the final credit dollar amount (stage 5-adjacent), rather than as an adjustment to the qualifying base before the rate is applied (stage-4-first-step, per ARCHITECTURE.md Q1). Applying it in the wrong order produces a different, wrong number whenever the base includes a per-person line item near the ceiling.
**Why it happens:** "Ceiling" sounds like a cap on the output, not an input.
**How to avoid:** Verified this session against `feasibility-incentives.md`'s worked GA example: $10M spend including a $2M W-2 lead-actor deal → ceiling reduces the *base* to $8.5M *before* the 30% rate is applied → $2.55M. This confirms ARCHITECTURE.md Q1's declared order (`per_person_ceiling` is step 1 of `CreditCalculator`, consuming `QualifyingBase` as its input) is correct; implement it exactly in that order and add this worked example as a regression test.
**Warning signs:** A per-person ceiling implementation that operates on `GrossCredit.value` rather than on a base amount before multiplication by the rate.

### Pitfall 5: `diversity_credit_amount` accidentally folded into the primary credit assertion
**What goes wrong:** NY's disclosure (and Phase 1's `ny_anora.yaml` fixture) carries a separate `diversity_credit_amount` field ($4,956 for Anora) alongside `credit_amount` ($991,190). The fixture's own notes confirm the validated 25.0% implied rate is `credit_amount` alone (`$991,190 / $3,964,760`) — the diversity credit is a distinct NY program not itemized in this phase's scope.
**Why it happens:** Both fields are disclosed together in the same table row, inviting an accidental sum.
**How to avoid:** Do not model NY's diversity/equity bonus credit in Phase 2 (it is not named in INC-01..09 or in any Phase 2 success criterion). Assert the interpreter's output against `credit_amount` only, exactly as the existing fixture's own documented implied-rate math does. State this exclusion explicitly in the scope-freeze note (see below) as a disclosed simplification, not a silent gap.
**Warning signs:** A test asserting against `credit_amount + diversity_credit_amount`, or a jurisdiction rule file that tries to model the diversity credit without a corresponding phase requirement asking for it.

## Scope-Freeze Note (dated, per ROADMAP's explicit instruction)

**Date:** 2026-08-25. This is the fixed set of rule dimensions Phase 2's generic engine models for the four curated jurisdictions (NY, CT built now; CA, NJ deferred to Phase 5 per JUR-02/03's phase mapping) and any future jurisdiction reachable through the same schema. Anything not on this list is explicitly out of scope for Phase 2 and must be named as a disclosed simplification if it is skipped rather than silently absent.

**In scope:**
1. **Base definition types** (INC-01): `total_qualified_spend`, `labour_only`, `lesser_of_pct_core_or_actual_local`, `local_hires_only`, plus the `custom_handler_id` escape hatch for anything genuinely irregular.
2. **Per-person ceilings** (INC-02): W-2 cap amount, loan-out exemption flag, loan-out withholding rate — as a **schedule**, not a scalar (Georgia's confirmed 5-tier declining schedule in `SOURCE-TRUTH.md` SRC-05 is the concrete proof this must be a lookup-by-effective-date table, not a single number).
3. **Rate structures** (INC-03): `flat`, `tiered_by_spend` (cliff lookup — Finding 3), `blended_by_ceiling_split` (two-rate blend), `headcount_scaled` (NM-style, dispatch shape only — no curated jurisdiction needs it yet). Uplifts: stackable/non-stackable flag, separate-application flag, additive to base rate.
4. **Stacking across national/regional programmes** (INC-03): sum independent dollar outputs from independently-computed bases; never sum percentages (A1.1). Check for a grinding/assistance-reduction clause between stacked programmes before summing.
5. **Caps** (INC-04): `per_project_cap`, `annual_programme_cap` (declared existence only — consumption state is a Phase 2 input parameter, not something Phase 2 fetches; see Architectural Responsibility Map).
6. **Availability vs. eligibility** (INC-05): reported as two independent fields/booleans, never conflated into one answer.
7. **Net-cash mechanisms** (INC-06): `refundable`, `transferable` (with broker discount rate), `rebate_grant`, `nonrefundable_credit` (taxable, net of corporation tax — INC-07). Audit fees: cliff-tiered by spend threshold, deducted before/as part of net cash.
8. **Cash-arrival timing** (INC-08): `terms_lock_at` + `payout_lag.typical_days`, reported as its own field alongside net cash value. **Explicit scope cut, stated per PITFALLS.md A1.11's own recommendation:** timing is *displayed*, not *discounted to present value*, in this phase. Do not claim otherwise in any UI copy a later phase writes.
9. **Minimum-spend cliffs** (INC-09): hard step functions, tested at threshold-1/threshold/threshold+1, never interpolated (A1.6).
10. **Provenance** (PRV-01/02/03): every `Figure` carries `source_url`, `date_checked`, `confidence` ∈ {`validated`, `researched`}, and a non-empty `derivation` tuple with at least one entry per adjustment step applied (including no-op steps).
11. **Additivity proof** (JUR-05): a throwaway fixture jurisdiction, structurally distinct from the curated `jurisdictions/` directory, added with zero diffs to any `engine/*.py` file.

**Explicitly out of scope for Phase 2** (disclosed simplifications, not silent gaps):
- **Sales tax / hotel occupancy tax exemptions** (INC-10) — Phase 4's requirement, not Phase 2's. Do not let engine scope drift into modeling these.
- **Time-value-of-money discounting on delayed cash** (A1.11) — display only, per above.
- **NY's diversity/equity bonus credit** — disclosed in the source data (Pitfall 5) but not itemized; assert against `credit_amount` alone.
- **Cost localization** (COST-01..08) — Phase 4's requirement. Phase 2's `QualifyingBaseCalculator` accepts a qualified-spend `Decimal` directly (per D-02), not a full `LocalizedBudget`.
- **Cap-consumption fetching, programme open/closed live status, FX rates** — Phase 7's `DataFreshnessGate`. Phase 2 accepts these as passed-in parameters/interfaces, never fetches them.
- **California and New Jersey curated rule files** (JUR-02/03) — Phase 5's requirement, per `REQUIREMENTS.md` traceability table. Phase 2 builds NY and CT only, as the two jurisdictions whose exact-mode D-05 anchor fixtures already exist and directly exercise `flat` and `tiered_by_spend` rate structures respectively.
- **Georgia, New Mexico, UK, Canada as curated jurisdictions** — never curated (no per-production disclosure exists per `feasibility-incentives.md` §4), reachable only via Job 2 live research in a later phase. The UK worked example is used in Phase 2 purely as an engine-correctness regression test (see Validation Architecture) — it is a golden-value test, not a curated jurisdiction file, and must not be represented as one.

## Runtime State Inventory

Not applicable — Phase 2 is greenfield engine construction, not a rename/refactor/migration. No prior runtime state (stored data, live service config, OS-registered state, secrets, build artifacts) references anything Phase 2 renames or moves.

## Code Examples

### The Figure value object (frozen dataclass)
```python
# Source: .planning/research/ARCHITECTURE.md Q3, reproduced verbatim as the
# specified design — this is the schema Phase 2 must implement, not a new
# proposal.
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal

@dataclass(frozen=True)
class Figure:
    value: Decimal
    unit: str
    label: str
    derivation: tuple[str, ...]
    inputs: tuple["Figure", ...]
    source_url: str | None
    date_checked: date | None
    confidence: Literal["validated", "researched"]
    live_fetched_this_run: bool
    figure_id: str
```

### Safe Decimal parsing from a Pydantic model (Finding 1, executed and confirmed this session)
```python
# Confirmed this session against pydantic==2.13.4, this repo's locked version:
#   M(rate=0.263).rate == Decimal('0.263')  →  True
#   M(rate=0.263).rate == Decimal(0.263)    →  False (the naive/wrong conversion)
# The Pydantic Decimal validator does the safe str()-mediated conversion even
# when given a bare float — but only if the field is typed Decimal, which is
# why every rule-file numeric field must be, regardless of what ARCHITECTURE.md's
# schema listing literally writes as "float".
from decimal import Decimal
from pydantic import BaseModel

class RateStructure(BaseModel):
    base_rate: Decimal
```

### Pinned rounding (Finding 2)
```python
# engine/rounding.py
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
DOLLAR = Decimal("1")

def quantize_money(value: Decimal, *, to: Decimal = DOLLAR) -> Decimal:
    """The single call site for rounding a computed money value.

    ROUND_HALF_UP is the pinned mode — Python's Decimal default context is
    ROUND_HALF_EVEN, which happens to agree with ROUND_HALF_UP on the one
    currently-committed fixture that lands on a .50 boundary (CT's
    Christmas Always: $1,159,501.50 -> $1,159,502) but is not guaranteed to
    for a future fixture. Pin explicitly; do not rely on the ambient default.
    """
    return value.quantize(to, rounding=ROUND_HALF_UP)
```

### Cliff vs. blended rate dispatch (Finding 3)
```python
# engine/credit.py — two distinct functions, never one shared branch
from decimal import Decimal

def lookup_flat_rate_by_band(base: Decimal, tiers: list["Tier"]) -> Decimal:
    """tiered_by_spend: the WHOLE base gets ONE rate, selected by which
    band `base` falls into. Verified against CT's Christmas Always:
    $3,865,005 (falls in the >$1,000,000 band) x 0.30 = $1,159,501.50,
    quantized -> $1,159,502, exact match to the disclosed figure."""
    for tier in tiers:
        if tier.threshold_low <= base and (
            tier.threshold_high is None or base < tier.threshold_high
        ):
            return base * tier.rate
    raise ValueError(f"base {base} matches no declared tier band")

def blend_two_rates_by_ceiling(
    base: Decimal, enhanced_threshold: Decimal, enhanced_rate: Decimal, standard_rate: Decimal
) -> Decimal:
    """blended_by_ceiling_split: UK-style. The first `enhanced_threshold`
    of base gets `enhanced_rate`; the remainder gets `standard_rate`. Both
    slices are computed and SUMMED — genuinely different from the lookup
    above, never share a code path with it."""
    enhanced_slice = min(base, enhanced_threshold)
    standard_slice = max(Decimal(0), base - enhanced_threshold)
    return enhanced_slice * enhanced_rate + standard_slice * standard_rate
```

## State of the Art

Not applicable in the conventional sense (this is not a fast-moving library/framework domain) — the one relevant "state of the art" fact is that ARCHITECTURE.md's own schema (Q2) was written with `float` type annotations for rate fields, which this research supersedes for the actual Pydantic implementation (use `Decimal`). This is noted here rather than silently overridden because ARCHITECTURE.md is the phase's authoritative design document and a planner reading both should understand this is a refinement discovered by execution, not a disagreement to relitigate.

| Old Approach (as literally written in ARCHITECTURE.md Q2) | Current Recommendation | When Changed | Impact |
|---|---|---|---|
| Rate fields typed `float` in the schema listing | Rate fields typed `Decimal`, quoted as YAML strings | This research session, verified by execution | Prevents a silent precision bug in exact-mode validation-pair assertions |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The declared adjustment order (per_person_ceiling → uplift_stacking → tier/rate → per_project_cap → annual_programme_cap) is universal across all four curated jurisdictions, not just the one worked example (GA) it was cross-checked against | Architecture Patterns / Pattern 1, Pitfall 4 | If a future jurisdiction (e.g., NM's per-programme-component caps applied before summing, rather than a single global post-hoc clip) genuinely needs a different order, the schema's `application_order` would need to become jurisdiction-declared data rather than fixed engine logic — worth a discuss-phase question if NM or a similarly-structured jurisdiction is ever curated |
| A2 | `jurisdictions/us-ny.yaml` should be built in Phase 2 (not deferred to Phase 3) as the primary proof vehicle for Phase 2's own success criteria | Summary, Recommended Project Structure | If the planner instead defers all real jurisdiction files to Phase 3, Phase 2's success criteria 1-3 would need to be demonstrated purely against synthetic fixtures, which is weaker evidence and duplicates work when Phase 3 builds the "real" file anyway — flagged as a recommendation with stated rationale, not asserted as the only valid split |
| A3 | ROUND_HALF_UP (not ROUND_HALF_EVEN or another mode) is the correct convention to pin, absent a specific statutory rounding instruction from any of the four curated jurisdictions' primary sources | Pitfall 2, Code Examples | None of NY/CA/NJ/CT's primary sources (as archived in Phase 1's `sources/`) were re-read this session specifically for a stated rounding rule; if one jurisdiction's statute specifies a different rounding convention, that jurisdiction's rule file should override the engine default rather than the global constant changing |

**If this table is empty:** N/A — see above.

## Open Questions

1. **Does every curated/future jurisdiction truly apply caps as one global post-hoc clip on the final credit, or do some (e.g., New Mexico's per-component dollar caps: nonresident performing-artist ≤$5M, Film Partner nonresident ATL ≤$10M/project and $40M/year, both potentially applying to the *same* production before a combined total is reached) require caps to apply to sub-components of the credit before they're summed?**
   - What we know: ARCHITECTURE.md Q1's stage-4 pipeline applies `per_project_cap`/`annual_programme_cap` as the last two steps against one `GrossCredit` value. GA (no caps at all) and CT (single flat programme, no sub-component split) are consistent with this. NM's structure (per feasibility-incentives.md) suggests caps might sometimes need to apply per-component before a sum.
   - What's unclear: neither of Phase 2's two build targets (NY, CT) exercises this ambiguity, so it can be deferred safely — but a future jurisdiction (Phase 5's CA/NJ, or any Job 2 live-researched one) might need the schema's `caps` structure to become per-programme-component rather than per-programme-total.
   - Recommendation: build to the single-global-cap design now (matches NY and CT exactly); leave a code comment at the cap-application call site noting this open question so a future jurisdiction that needs per-component caps doesn't require a silent, undocumented reinterpretation.

2. **Is the £18M UK worked example (used here as a golden-value regression test for `blended_by_ceiling_split` + taxable-mechanism math) appropriate to build as a full `jurisdictions/` rule file in Phase 2, or should it remain a hardcoded test fixture only?**
   - What we know: UK is never a curated jurisdiction (no per-production disclosure exists — feasibility-incentives.md §4) and is explicitly named in DMO-02 as a later-phase demo beat, not a Phase 2 deliverable.
   - What's unclear: whether building it as a `tests/fixtures/jurisdictions/synthetic-uk-style.yaml` (recommended above) versus a hardcoded Python dict in the test file itself is the right level of realism for Phase 2's purposes.
   - Recommendation: build it as a YAML fixture under `tests/fixtures/jurisdictions/`, not `jurisdictions/` — this both proves the engine handles `blended_by_ceiling_split` + taxable mechanism against real numbers, and doubles as a second data point (alongside the throwaway fixture) demonstrating the schema's generality, at zero extra cost since the numbers are already fully worked out in `feasibility-incentives.md`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Engine code | ✓ | 3.12.14 (`/opt/prodfin/.venv`, per `01-08-SUMMARY.md`; 3.12 locally via `uv run`) | — |
| `pydantic` | Rule-file schema validation | ✓ [VERIFIED: uv.lock read this session] | 2.13.4 (transitively resolved via `fastapi`) | — |
| `pyyaml` | Rule-file loading | ✓ [VERIFIED: pyproject.toml read this session] | 6.0.3 | — |
| `pytest` | Engine test suite | ✓ [VERIFIED: pyproject.toml read this session] | 9.1.1 | — |

No missing dependencies. Nothing in this phase requires provisioning, registry lookups, or new installs beyond `uv add pydantic` for explicit-import clarity.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` [VERIFIED: pyproject.toml:20-21 read this session] |
| Quick run command | `uv run pytest tests/test_engine_*.py -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INC-01 | Four base-definition types each compute a distinct qualifying base from the same input budget | unit | `uv run pytest tests/test_engine_qualifying_base.py::test_base_definition_types -x` | ❌ Wave 0 |
| INC-02 | Per-person ceiling: W-2 capped at boundary-1/boundary/boundary+1; loan-out uncapped but withholding applied; verified against the GA worked example ($10M/$2M lead → $8.5M base → $2.55M credit) | unit + boundary | `uv run pytest tests/test_engine_credit.py::test_per_person_ceiling_w2_vs_loanout -x` | ❌ Wave 0 |
| INC-03 | Tier/uplift ordering is read from data (swap declared order in a synthetic fixture, assert output changes); `tiered_by_spend` vs `blended_by_ceiling_split` produce different, individually-correct results; national+regional stacking sums independent dollar outputs, never percentages | unit + golden-value | `uv run pytest tests/test_engine_credit.py::test_tier_dispatch_and_stacking -x` | ❌ Wave 0 |
| INC-04 | Per-project and annual caps clip at boundary-1/boundary/boundary+1 | boundary | `uv run pytest tests/test_engine_credit.py::test_cap_boundaries -x` | ❌ Wave 0 |
| INC-05 | Eligible-but-cap-exhausted production reports `eligible=True, available=False` as two independent fields | unit | `uv run pytest tests/test_engine_credit.py::test_availability_separate_from_eligibility -x` | ❌ Wave 0 |
| INC-06 | Each of 4 mechanisms (refundable/transferable/rebate_grant/nonrefundable_credit) nets audit fee correctly at fee-tier boundaries ($5M/$10M cliffs) | unit + boundary | `uv run pytest tests/test_engine_net_cash.py::test_mechanism_conversions -x` | ❌ Wave 0 |
| INC-07 | Taxable mechanism nets corporation tax; golden-value regression against the £18M UK worked example (£7.176M gross → ~£5.38M net) | golden-value | `uv run pytest tests/test_engine_net_cash.py::test_taxable_mechanism_uk_worked_example -x` | ❌ Wave 0 |
| INC-08 | `ArrivalTiming` present alongside `NetCash` for every mechanism; displayed, not discounted (per the stated scope cut) | unit | `uv run pytest tests/test_engine_net_cash.py::test_arrival_timing_present -x` | ❌ Wave 0 |
| INC-09 | Minimum-spend cliff: threshold-$1/threshold/threshold+$1 produce $0/full-rate/full-rate, never a ramp | boundary | `uv run pytest tests/test_engine_qualifying_base.py::test_minimum_spend_cliff -x` | ❌ Wave 0 |
| JUR-05 | A throwaway jurisdiction YAML is added with **zero diffs to any `engine/*.py` file** — verified structurally, not just by YAML validity | structural + unit | `uv run pytest tests/test_engine_jurisdiction_additivity.py -x` (asserts the fixture prices correctly) + a documented manual/CI check: `git diff --name-only <fixture-commit> | grep -c '^engine/'` must equal 0 | ❌ Wave 0 |
| PRV-01 | Every `Figure` in a computed tree carries `source_url` and `date_checked`, or an explicit documented null | property | `uv run pytest tests/test_engine_figure_provenance.py::test_every_figure_has_source_or_explicit_null -x` | ❌ Wave 0 |
| PRV-02 | `Figure.confidence` is always exactly `"validated"` or `"researched"` — no third value, no default | schema | `uv run pytest tests/test_engine_figure_provenance.py::test_confidence_is_closed_enum -x` | ❌ Wave 0 |
| PRV-03 | Every adjustment step appends a non-empty derivation line, including no-op steps | property | `uv run pytest tests/test_engine_figure_provenance.py::test_derivation_never_empty_including_noops -x` | ❌ Wave 0 |
| (interpreter proof, D-02) | NY rule file reproduces Anora ($991,190 exact), Succession S4 ($25,747,913 exact), Gilded Age S2 (bounded, 150bps); CT rule file reproduces Christmas Always ($1,159,502 exact) | golden-value, imports existing fixtures | `uv run pytest tests/test_engine_against_validation_pairs.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_engine_*.py -q`
- **Per wave merge:** `uv run pytest tests/ -q` (full suite, including Phase 1's existing 35 tests — Phase 2 must not regress them)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `engine/__init__.py`, `engine/models.py`, `engine/figure.py`, `engine/rounding.py`, `engine/qualifying_base.py`, `engine/credit.py`, `engine/net_cash.py`, `engine/handlers/__init__.py` — no engine code exists yet (confirmed this session: `find . -iname "*engine*"` returns only this phase's planning directory)
- [ ] `jurisdictions/us-ny.yaml`, `jurisdictions/us-ct.yaml` — real curated rule files, do not exist yet
- [ ] `tests/fixtures/jurisdictions/` — new directory, throwaway/synthetic fixtures for boundary tests and the JUR-05 proof
- [ ] `tests/test_engine_*.py` (8 files, listed in Phase Requirements → Test Map) — none exist yet
- [ ] `pydantic` explicit dependency line in `pyproject.toml` — currently transitive-only

*(No gap in shared test infrastructure or CI config: `pyproject.toml`'s `testpaths = ["tests"]` already picks up any new file under `tests/`, and no CI workflow changes are needed — Phase 1's `.github/workflows/ci.yml` already runs `pytest tests/` as a required job.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Phase 2 ships no HTTP endpoints; no auth surface exists yet |
| V3 Session Management | No | Same as above |
| V4 Access Control | Partial — the handler registry | The `custom_handler_id` escape hatch is a closed, explicit dict-literal allow-list (`engine/handlers/__init__.py`) mapping known ID strings to specific function references — never `getattr(module, id_string)` or `importlib.import_module(id_string)` resolving a string that ultimately originates from a rule file. This matters now even though Phase 2's own rule files are human-written and repo-committed, because Phase 7's Job 2 will feed LLM-extracted YAML through this exact same schema, and an unconstrained dynamic-resolution pattern established now becomes a code-execution vector once that YAML's provenance is no longer "human-reviewed, git-committed" but "LLM output validated only by schema shape." |
| V5 Input Validation | Yes | Two controls: (1) `yaml.safe_load()` only, everywhere a `.yaml` rule file is read — never `yaml.load()`/`yaml.unsafe_load()`, which can deserialize arbitrary Python objects from a crafted YAML document (a well-known PyYAML CVE class); Phase 1's existing test code already follows this convention (`tests/test_validation_pair_fixtures.py` uses `yaml.safe_load`), so Phase 2 continues an established, correct pattern rather than introducing a new one. (2) Pydantic's closed `Literal`/enum types on every classification field (`mechanism`, `base_definition.type`, `rate_structure.type`, `status`) — an unrecognized value in a rule file must raise a validation error, never silently fall through to a default behavior. |
| V6 Cryptography | No | No cryptographic operations in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary object deserialization via `yaml.load()`/`yaml.unsafe_load()` on a rule file | Tampering / Elevation of Privilege | `yaml.safe_load()` exclusively — already the established Phase 1 convention, continue it |
| A malformed or adversarial rule file silently coerced into a plausible-looking (but wrong) computation via a permissive schema | Tampering | Pydantic's closed enums + required fields; fail loud (raise) on an unrecognized `mechanism`/`base_definition.type`/`rate_structure.type` value rather than defaulting |
| Future dynamic resolution of `custom_handler_id` from LLM-extracted (Phase 7) rule-file content | Tampering / Elevation of Privilege (code execution) | Explicit dict-literal allow-list registry, established in this phase, before Job 2 (Phase 7) ever produces untrusted rule-file content that references it |
| Float-precision rate corruption silently producing a wrong-but-plausible incentive figure | Tampering (unintentional, but the same effect as a data-integrity attack — a wrong number presented with full confidence) | Decimal-typed fields + quoted YAML strings (Finding 1); this is a correctness issue rather than a classic security threat, but is included here because the project's own core security/credibility property is "every figure provably matches what a government actually paid" — a silent precision bug is a direct violation of that property |

## Sources

### Primary (HIGH confidence)
- `.planning/research/ARCHITECTURE.md` (Q1-Q3, Q7) — the authoritative pipeline seam, `JurisdictionRuleSet` schema, and `Figure` provenance pattern this phase implements
- `.planning/phases/01-foundations-source-truth-deploy-path/01-CONTEXT.md` — D-01 through D-30, especially D-02 (interpreter-only validation boundary), D-03/D-04/D-05/D-06/D-07 (fixture contract)
- `.planning/SOURCE-TRUTH.md` — SRC-01, SRC-02, SRC-05 verified constants (NY $700M/$100M split, CT CSV schema and its 6 data-quality gotchas, GA's 5-tier loan-out withholding schedule)
- `tests/fixtures/validation_pairs/*.yaml` (12 files, read directly this session) — the concrete D-02/D-05 anchor fixtures this phase's engine must reproduce
- `feasibility-incentives.md` (read in full this session) — the source of every worked example and rule-dimension enumeration cited above (GA per-person ceiling worked example, UK £18M worked example, CT tier structure raw data, A1.1-A1.11 pitfalls' underlying facts)
- `.planning/research/PITFALLS.md` Part A (A1.1-A1.11), Part B (B1-B5), Part H (H2, H3) — read in full this session
- `pyproject.toml`, `uv.lock` (read directly this session) — locked dependency versions
- Direct execution this session (`uv run python3 -c "..."` against this repo's actual `pydantic==2.13.4`, Python 3.12.14) — Findings 1, 2, 3 are each independently reproducible by re-running the commands shown in Code Examples

### Secondary (MEDIUM confidence)
- None — every claim in this document is either read directly from a repo file this session or verified by direct code execution against this repo's own locked versions.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; every version confirmed by reading `uv.lock`/`pyproject.toml` this session
- Architecture: HIGH — implements ARCHITECTURE.md's already-specified design, with three corrections verified by direct execution rather than asserted
- Pitfalls: HIGH — every pitfall in this document is either a verified execution result (Findings 1-3) or a direct citation of PITFALLS.md/feasibility-incentives.md content already vetted in Phase 1's research pass

**Research date:** 2026-08-25
**Valid until:** No expiry in the conventional sense — this is internal engine design, not external API/library research subject to drift. Re-verify only if `pydantic` is upgraded past 2.13.4 in a way that could change `Decimal` coercion behavior (unlikely; this is stable, documented pydantic-core behavior, not an implementation accident).
