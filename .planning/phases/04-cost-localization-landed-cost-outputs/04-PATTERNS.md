# Phase 4: Cost Localization & Landed-Cost Outputs - Pattern Map

**Mapped:** 2026-08-26
**Files analyzed:** 24 (11 new engine modules, 2 modified engine modules, 1 modified app service, ~5 new data directories/files, 1 modified data file, 11 new test files)
**Analogs found:** 24 / 24 (every new file has a direct in-repo analog — this phase is an explicit "mirror four already-proven Phase 2/3 patterns," not new architecture)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `engine/figure.py` (MODIFIED — add `basis`) | model | transform | itself (existing) | exact — additive change to existing file |
| `engine/figure_serialize.py` (MODIFIED — serialize `basis`) | utility | transform | itself (existing) | exact — additive change to existing file |
| `engine/budget.py` (NEW — `BudgetModelBuilder`) | service | transform (pure function, CRUD-shaped) | `engine/qualifying_base.py` | exact — dispatches on declared data, builds a `Figure` tree from a typed input, same shape as `compute_qualifying_base` |
| `engine/cost_profile.py` (NEW — `CityCostProfile` schema + `load_cost_profile()`) | model | file-I/O | `engine/models.py` (`load_ruleset`, `StrictModel`, `Jurisdiction`) | exact — Pydantic schema + YAML loader over a committed rule file, identical shape |
| `engine/cost_localizer.py` (NEW — `CityLocalizer`) | service | transform | `engine/qualifying_base.py` + `engine/credit.py` | exact — reads a typed profile, builds a localized `Figure` tree, jurisdiction-agnostic dispatch |
| `engine/seasonality.py` (NEW — shoot-calendar + month-weighted per diem) | utility | transform | `engine/net_cash.py::_arrival_timing` (date-deriving helper) + `engine/qualifying_base.py` (Figure-building helper) | role-match — a pure calendar-derivation helper feeding a Figure, closest existing shape is `_arrival_timing` |
| `engine/fx.py` (NEW — dated FX snapshot lookup, refuse-not-cross-rate) | service | file-I/O + refusal | `engine.net_cash.transferable` (refusal shape) | exact — this phase's own research explicitly names this as the pattern to mirror |
| `engine/landed_cost.py` (NEW — `LandedCostAggregator`) | service | transform (aggregation/CRUD-shaped) | `engine/pipeline.py::price_jurisdiction` (summation over independent Figures) | exact — sums independent dollar Figures into one total Figure, same `combined_confidence`-style aggregation |
| `engine/ranker.py` (NEW — two-band ranked list) | service | transform | `engine/pipeline.py` (dispatch/aggregation shape) + `engine.net_cash.transferable` (refusal-shaped branch for unranked cities) | role-match — closest existing shape combines pipeline's per-item loop with net_cash's refuse-rather-than-invent branch |
| `engine/gap.py` (NEW — `GapDecomposer`) | service | transform | `engine/pipeline.py` (component-by-component Figure composition) | role-match — no direct component-diff analog exists; pipeline's per-programme Figure composition is closest |
| `engine/sensitivity.py` (NEW — perturbation engine) | service | batch (re-run pipeline N times) | `tests/mutation_targets.yaml` + `.github/scripts/mutation-check.sh` (the mutation-and-rerun shape) + `engine/pipeline.py` (the thing being re-run) | role-match — this phase's own research names `tests/mutation_targets.yaml` as the exact precedent for the declared-step-table half |
| `data/crew_tiers.yaml` (MODIFIED — add department-ratio/ATL-BTL-Post columns) | config | file-I/O | itself (existing) | exact — additive columns to existing file, same `basis`/`provenance_note` header convention |
| `data/cost_profiles/*.yaml` (NEW, one per city) | config | file-I/O | `jurisdictions/us-ny.yaml` (rule-file shape) | exact — committed, quoted-string YAML rule file per entity |
| `data/per_diem/**/*.yaml` (NEW) | config | file-I/O | `data/crew_tiers.yaml` (committed modelling-assumption table) | exact — same quoted-string, sourced/estimated header convention |
| `data/union_rates/*.yaml` (NEW) | config | file-I/O | `data/crew_tiers.yaml` | exact |
| `data/fx/*.yaml` (NEW) | config | file-I/O | `data/crew_tiers.yaml` (committed snapshot table shape) | role-match — same committed-table shape, different domain |
| `data/sensitivity_steps.yaml` (NEW) | config | file-I/O | `tests/mutation_targets.yaml` | exact — this phase's own research names this as the direct precedent |
| `app/services/spec.py` (MODIFIED — D-71 reverses the import boundary, retires `SPEND_NOT_DERIVED`) | service | request-response | itself (existing) | exact — modifying the existing Route A handler in place |
| `tests/test_engine_budget.py` (NEW) | test | — | `tests/test_engine_qualifying_base.py` | exact |
| `tests/test_engine_cost_localizer.py` (NEW) | test | — | `tests/test_engine_credit.py` / `tests/test_engine_net_cash.py` | exact |
| `tests/test_engine_cost_profile.py` (NEW) | test | — | `tests/test_engine_models.py` | exact |
| `tests/test_engine_fx.py` (NEW) | test | — | `tests/test_engine_net_cash.py` (the `transferable` refusal tests) | exact |
| `tests/test_engine_ranker.py`, `test_engine_gap.py`, `test_engine_sensitivity.py`, `test_engine_landed_cost.py`, `test_engine_seasonality.py` (NEW) | test | — | `tests/test_engine_against_validation_pairs.py` (fixture-driven, sorted-glob, fail-loud pattern) | role-match |
| `tests/test_golden_cost.py` (NEW, D-78) | test | — | `tests/test_engine_against_validation_pairs.py` (exact-`Decimal` fixture assertions) | exact |
| `tests/test_route_a_basis_walk.py` (NEW, D-63's CI gate) | test | — | `tests/test_source_truth.py` (structural CI-gate-as-pytest assertion) + `tests/test_app_spec_route.py:250-258` (the import-boundary assertion being replaced) | exact |

## Pattern Assignments

### `engine/figure.py` (MODIFIED)

**Analog:** itself, current state read in full (`engine/figure.py:1-110`)

**Current shape to preserve** — `Figure` is `@dataclass(frozen=True, kw_only=True)`; every field is required except `figure_id` which has a `default_factory`:
```python
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
    figure_id: str = field(default_factory=_new_figure_id)
```

**Addition per D-58** (must go after all required fields, must default to `None` — see RESEARCH.md Pattern 1, and CONTEXT.md D-58/D-59):
```python
Basis = Literal["sourced", "estimated", "modelling_assumption"]
# ... on Figure:
    basis: Basis | None = None      # NEW — orthogonal to confidence, defaults None
```

**The landmine to avoid — `combined_confidence`'s exact shape, inverted default:**
```python
def combined_confidence(inputs: Sequence[Figure]) -> Confidence:
    """... An empty sequence defaults to "validated" — there is nothing
    weaker to inherit from."""
    if any(figure.confidence == "researched" for figure in inputs):
        return "researched"
    return "validated"
```
`combined_basis` must mirror this shape (weakest-wins iteration) but **must not** return a default on an empty sequence — D-59 requires raising `ValueError` instead (see RESEARCH.md Pattern 1's full `combined_basis` code example for the exact function to write).

**Why `basis` must not be a bare required field:** every existing `Figure(...)` construction site in `engine/credit.py`, `engine/net_cash.py`, `engine/qualifying_base.py`, `engine/pipeline.py` omits it; making it required breaks all of them.

---

### `engine/figure_serialize.py` (MODIFIED)

**Analog:** itself, read in full (`engine/figure_serialize.py:1-42`)

**Pattern to extend** — one additive dict key, same recursive-`inputs` shape, `str()` on Decimal, `.isoformat()` on date:
```python
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
        "basis": figure.basis,              # NEW — None for every existing incentive-side Figure
        "live_fetched_this_run": figure.live_fetched_this_run,
        "inputs": [figure_to_dict(child) for child in figure.inputs],
    }
```
**Rule preserved:** never call `dataclasses.asdict(figure)` directly — `Decimal`/`date` are not JSON-native. `figure_to_dict` remains the only path a `Figure` takes to JSON.

---

### `engine/budget.py` (NEW — `BudgetModelBuilder`, stage [1])

**Analog:** `engine/qualifying_base.py::compute_qualifying_base` (full file read, `engine/qualifying_base.py:1-280`)

**Imports pattern** (mirror lines 9-19 of the analog):
```python
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from engine.figure import Confidence, Figure
from engine.spec import ProductionSpec, CrewHeadcount, resolve_crew_tier
```

**Core pattern — a dataclass result type + a builder function that returns a `Figure`,** exactly `SpendBreakdown` + `compute_qualifying_base`'s shape:
```python
@dataclass(frozen=True)
class CanonicalBudget:
    """Mirrors SpendBreakdown's role: a typed, frozen result carrying named
    line-item Decimals plus provenance, never a bare dict."""
    total: Decimal
    line_items: dict[str, Decimal] = field(default_factory=dict)
    # ... department ratios, ATL/BTL/Post tags per line (D-77)

def build_canonical_budget(spec: ProductionSpec, crew_headcount: CrewHeadcount) -> Figure:
    """Pure function over ProductionSpec + data/crew_tiers.yaml (extended,
    D-38) — exactly compute_qualifying_base's shape: build named-line
    sub-Figures, attach each as an `inputs` entry, combine basis across
    them (never confidence — D-58 keeps the axes separate)."""
```

**Error handling pattern** — mirror `_apply_minimum_spend_check`'s "always emit a derivation line, even for the not-applicable branch" discipline: every input choice (e.g. no department-ratio table entry for a given crew tier) must raise or emit an explicit "not declared" derivation line, never silently default.

**Basis propagation (new to this phase, no direct precedent in `qualifying_base.py` since that module has no `basis` concept):** every Figure this builder returns must set `basis="modelling_assumption"` for department-ratio-derived lines, and the top-level `CanonicalBudget` Figure's `basis` must be `combined_basis(line_figures)` — never omitted, never defaulted to `"sourced"`.

---

### `engine/cost_profile.py` (NEW — `CityCostProfile` schema + loader)

**Analog:** `engine/models.py` (`StrictModel`, `Jurisdiction`, `load_ruleset`) — read `engine/spec.py:39-46` for the local-`StrictModel`-mirror convention actually used for a non-`models.py` schema, and `engine/spec.py:158-176` (`resolve_crew_tier`) for the loader shape:

**Imports pattern:**
```python
from __future__ import annotations
from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel, ConfigDict, Field
```

**Core pattern — local `StrictModel` mirror + module-anchored path + `yaml.safe_load` loader**, copied near-verbatim from `engine/spec.py:39-46,62-63,158-176`:
```python
class StrictModel(BaseModel):
    """Local mirror of engine.models.StrictModel — not imported, per the
    same reasoning engine/spec.py gives (a domain model should not drag in
    the whole rule-schema import graph)."""
    model_config = ConfigDict(extra="forbid")

COST_PROFILES_DIR = Path(__file__).resolve().parents[1] / "data" / "cost_profiles"

class CityCostProfile(StrictModel):
    city_id: str
    jurisdiction_id: str | None    # D-53 — may be None; a cost profile needs no rule file
    currency: str
    # ... union_rates, per_diem, fx, stage/equipment/permit/location/trucking refs

def load_cost_profile(path: str | Path) -> CityCostProfile:
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return CityCostProfile.model_validate(raw)
```

**Validation pattern:** `extra="forbid"` on every schema model — same rationale RESEARCH.md gives ("catches a typo'd YAML field at load time, not at a later `.get()` call").

---

### `engine/cost_localizer.py` (NEW — `CityLocalizer`, stage [2])

**Analog:** `engine/qualifying_base.py` (dispatch-and-build-Figure shape) + `engine/credit.py` (per-line Figure composition, not read in full this pass but referenced identically by RESEARCH.md and `net_cash.py`'s own docstring at `engine/net_cash.py:35-38` for the "found by label, never position" convention)

**Core pattern — per-line Figure construction, found by label:**
```python
_QUALIFYING_BASE_LABEL = "Qualifying base"  # engine/net_cash.py:38 precedent

def _find_input_by_label(figure: Figure, label: str) -> Figure:
    for candidate in figure.inputs:
        if candidate.label == label:
            return candidate
    raise ValueError(f"{figure.label!r} carries no {label!r} input")
```
Apply this same by-label lookup discipline (never by position) for every localized line the aggregator later needs to find (labour, housing, per diem, etc.).

**Jurisdiction-agnostic dispatch (D-53):** never branch on a jurisdiction id string — dispatch only on data declared in `CityCostProfile`, mirroring `engine/qualifying_base.py`'s own docstring rule ("the ONLY jurisdiction-specific stage ... even it reads *data* ... never per-jurisdiction Python").

---

### `engine/seasonality.py` (NEW — shoot calendar + month-weighted per diem)

**Analog:** `engine/net_cash.py::_arrival_timing` (`engine/net_cash.py:237-260`) for the date-deriving-helper shape; per-diem month-band absence handling mirrors `engine/qualifying_base.py::_apply_minimum_spend_check`'s "always state the not-applicable branch explicitly" rule.

**Core pattern — a private helper returning a plain dataclass, called by the public builder, exactly `_arrival_timing`'s shape:**
```python
def _shoot_calendar(spec: ProductionSpec, days_per_week: Decimal) -> dict[str, int]:
    """Spread shoot_days_stage + shoot_days_location across calendar
    months from start_quarter/start_year at a declared rate — mirrors
    _arrival_timing's pattern of deriving a calendar fact from a declared
    lag/rate, never left implicit."""
```

**D-64's per-city fallback — explicit absence, never interpolated (mirrors `_apply_minimum_spend_check`'s explicit not-applicable branch):**
```python
if "lodging_by_month" not in per_diem_table:
    return figure.with_step(
        "no month-banded per-diem data exists for this city (D-64) — "
        "seasonality is absent, not backfilled with a multiplier"
    )
```

**Basis:** any Figure built here from `data/per_diem/*.yaml` is `basis="sourced"`; the shoot-calendar's `days_per_week` assumption itself is `basis="modelling_assumption"` and its Figure must be named in the assumptions list (D-65).

---

### `engine/fx.py` (NEW — dated FX lookup, refuse-not-cross-rate)

**Analog:** `engine.net_cash.transferable` (`engine/net_cash.py:154-186`) — this phase's own RESEARCH.md explicitly names this the pattern to mirror.

**The exact refusal shape to copy** (full function read above):
```python
def transferable(programme: Programme, gross_credit: Figure) -> tuple[Figure, Figure]:
    discount = programme.transfer_discount
    if (
        not discount.applies
        or discount.typical_rate_low is None
        or discount.typical_rate_high is None
    ):
        raise ValueError(
            f"{programme.name}: mechanism is 'transferable' but transfer_discount "
            "does not fully declare applies=true, typical_rate_low and "
            "typical_rate_high"
        )
```

**Applied to FX (D-74):**
```python
def convert(amount: Decimal, base: str, quote: str, snapshot_dir: Path) -> Figure:
    pair_path = snapshot_dir / f"{base.lower()}-{quote.lower()}.yaml"
    if not pair_path.exists():
        raise ValueError(
            f"no committed FX snapshot for {base}->{quote} — refuse rather "
            "than derive through a third currency (D-74)"
        )
    # load via yaml.safe_load, quantize via engine.rounding.quantize_money,
    # return Figure(basis="sourced", confidence="researched", ...)
```
**Never** derive a cross-rate through a third currency — this is the same class of dishonesty as `transferable`'s midpoint refusal.

---

### `engine/landed_cost.py` (NEW — `LandedCostAggregator`, stage [6])

**Analog:** `engine/pipeline.py::price_jurisdiction` (full file read above, `engine/pipeline.py:184-256`)

**Core pattern — sum independent Figures, never rates, with `combined_confidence`-style aggregation and full derivation-line accounting:**
```python
total_value = Decimal("0")
total_inputs: list[Figure] = []
for line in localized_lines:
    total_inputs.append(line)         # every line, even non-contributing, carried as inputs
    total_value += line.value
total_value = quantize_money(total_value)

total_figure = Figure(
    value=total_value,
    unit=currency,
    label="Total landed cost",
    derivation=tuple(derivation_lines),
    inputs=tuple(total_inputs),
    source_url=None,
    date_checked=None,
    confidence=combined_confidence(total_inputs),
    basis=combined_basis(total_inputs),   # NEW for this phase — D-59
    live_fetched_this_run=False,
)
```

**D-56/D-60 pattern — acknowledged gaps are a first-class list, not a `$0` line:** mirror `_grinding_clause_lines`'s "state the absence explicitly, attach as its own derivation lines" shape (`engine/pipeline.py:172-192`) for the declared exclusion list (overtime, turnaround, etc.).

---

### `engine/ranker.py` (NEW — two-band ranked list, stage [7])

**Analog:** `engine/pipeline.py` (per-item loop + summation shape) combined with `engine.net_cash.transferable`'s refuse-rather-than-invent branch (D-56)

**Core pattern** (see RESEARCH.md Pattern 3 for the full worked example — reproduced here as the assignment):
```python
@dataclass(frozen=True)
class RankedCity:
    city_id: str
    total_landed_cost: Figure
    band: Literal["net_ranked", "incentive_not_modelled"]
    reason: str | None

def rank(localized_by_city, ruleset_by_jurisdiction) -> list[RankedCity]:
    ranked, unranked = [], []
    for city_id, budget in localized_by_city.items():
        ruleset = ruleset_by_jurisdiction.get(budget.jurisdiction_id) if budget.jurisdiction_id else None
        if ruleset is None:
            unranked.append(RankedCity(
                city_id=city_id,
                total_landed_cost=budget.cost_only_total,   # never $0 — D-56
                band="incentive_not_modelled",
                reason="no curated or live-researched rule file exists for this jurisdiction yet",
            ))
            continue
        # ... price via existing engine.pipeline.price_jurisdiction, net total
        ranked.append(RankedCity(city_id=city_id, total_landed_cost=net_total, band="net_ranked", reason=None))
    ranked.sort(key=lambda c: c.total_landed_cost.value)
    unranked.sort(key=lambda c: c.total_landed_cost.value)
    return ranked + unranked   # D-55 — never interleaved
```

---

### `engine/gap.py` (NEW — `GapDecomposer`, stage [8])

**Analog:** `engine/pipeline.py`'s per-programme Figure composition (no direct diff-analog exists in the codebase; this is the weakest-precedent module in the phase — see "No Analog Found" note below is not applicable since a role-match analog exists, but treat this module with extra scrutiny)

**Pattern to apply:** component-by-component subtraction, each component its own named `Figure`, currency as its own first-class component (D-75) — same "never fold a deduction into another line" discipline as `engine/net_cash.py::transferable`'s treatment of the broker discount as its own visible step, and `_deduct_audit_fee`'s pattern of emitting a derivation line for every deduction rather than baking it silently into the total.

```python
def decompose_gap(city_a: LocalizedBudget, city_b: LocalizedBudget) -> list[Figure]:
    """One Figure per matched component label (labour, housing, per diem,
    stages, equipment, currency, ...) — found by label across both cities'
    line trees, mirroring engine/net_cash.py's by-label lookup discipline,
    never positional pairing."""
```

---

### `engine/sensitivity.py` (NEW — OUT-03 perturbation engine)

**Analog:** `tests/mutation_targets.yaml` (data table, read in full above) + `.github/scripts/mutation-check.sh` (referenced by RESEARCH.md and the CONTEXT.md D-68 precedent; not re-read this pass since the table shape is what matters) + `engine/pipeline.py` as the thing perturbed and re-run

**Data table pattern to mirror exactly** (`tests/mutation_targets.yaml`):
```yaml
mutation_targets:
  - id: "ny-base-rate-one-bp"
    file: "jurisdictions/us-ny.yaml"
    find: 'base_rate: "0.25"'
    replace: 'base_rate: "0.2501"'
    expected_red_test: "..."
    requirement: "SHP-14"
    status: "active"
    why: >
      ...
```
Apply this same "one row = one addition, no script change" shape to `data/sensitivity_steps.yaml` (D-68): one row per perturbable input, each declaring its own natural-unit step, never a shared scale.

**Core computation pattern (D-67):** literal re-run of the full pipeline per perturbation, never an analytic derivative — no direct code analog exists for "re-run the whole pipeline N times," but this is explicitly the correct approach per RESEARCH.md's own "Don't Hand-Roll" table and D-67's own rationale (the pipeline has cliffs a derivative cannot see).

---

### `data/cost_profiles/*.yaml`, `data/per_diem/*.yaml`, `data/union_rates/*.yaml`, `data/fx/*.yaml`

**Analog:** `data/crew_tiers.yaml` (full file read above) and `jurisdictions/us-ny.yaml` (RD-01 quoted-string convention, referenced throughout CONTEXT/RESEARCH but not re-read this pass since `data/crew_tiers.yaml` already demonstrates the identical header/body shape)

**Header pattern to copy exactly** — a `basis` field, a `provenance_note`, and an explicit statement of what this file is NOT (never `confidence`/`status`, reserved for `jurisdictions/*.yaml`):
```yaml
# One-paragraph comment: what this table is, why it lives in data/ not
# jurisdictions/, and the explicit "this file must never declare a
# `confidence` or `status` key" boundary.
basis: modelling_assumption   # or "sourced" per D-58's vocabulary
provenance_note: >
  ...
tiers:               # or whatever the table's top-level key is named
  <key>:
    <field>: "quoted-string-value"   # RD-01 — every numeric value quoted
```

**FX file shape (D-74's own stated field list):**
```yaml
base: "GBP"
quote: "USD"
rate: "1.27"
as_of_date: "2026-08-01"
source_url: "https://api.frankfurter.dev/..."
retrieved_at: "2026-08-26"
```

---

### `app/services/spec.py` (MODIFIED — D-71)

**Analog:** itself, full file read above

**What is being removed** — the module-level docstring's forbidding language and the constant it names:
```python
"""Route A business logic ...
This module must never import `engine.pipeline` or
`engine.qualifying_base`, and must never call `price_jurisdiction` or
`compute_qualifying_base` directly ... Route A returns no dollar figure
derived from the visitor's spec (D-36)."""
...
SPEND_NOT_DERIVED = (
    "Qualified spend is not derived from a described production in this phase. ..."
)
```
Both the docstring's forbidding claim and `SPEND_NOT_DERIVED` (and its field on `SpecResult`) are retired per D-71 — replaced by a real modelled-spend `Figure`, built via `engine.budget.build_canonical_budget` + `engine.cost_localizer` + `engine.pipeline.price_jurisdiction`. Retire explicitly (remove the constant, update its test coverage) — never leave it as unreachable dead code, per RESEARCH.md's State of the Art note.

**Existing dispatch shape to preserve unchanged** — the ordered-sequence handler pattern in `handle_spec_submission`:
```python
def handle_spec_submission(raw: SpecFormSubmission) -> SpecResult | RefusalResult:
    if raw.total_budget not in (None, ""):
        return RefusalResult(reason=REFUSAL_REASON, refused_field="total_budget")
    spec = ProductionSpec.model_validate(raw.model_dump(exclude={"total_budget"}))
    # ... crew_headcount resolution, city assessment loop, rule terms
```
D-71 changes what this function returns for a curated city (a real spend Figure instead of the `SPEND_NOT_DERIVED` string) — the D-35 budget-refusal-first ordering and the `RuleTerm`/`CityAssessment` shapes stay unchanged.

---

## Shared Patterns

### Provenance — `Figure` + `basis`
**Source:** `engine/figure.py:54-95` (existing), extended per D-58 (Pattern 1 above)
**Apply to:** Every new module that constructs a `Figure` — `budget.py`, `cost_localizer.py`, `seasonality.py`, `fx.py`, `landed_cost.py`, `gap.py`. Every cost-side `Figure` must set `basis` explicitly (never omit it, which defaults `None` and would be indistinguishable from an incentive-side Figure).

### Weakest-input-wins aggregation
**Source:** `engine/figure.py::combined_confidence` (lines 98-109), to be mirrored (not copied) by a new `combined_basis`
**Apply to:** `budget.py`, `landed_cost.py`, `ranker.py` — any module that builds a total Figure from multiple input Figures must call both `combined_confidence` (existing) and `combined_basis` (new) on the same `inputs` sequence, and must never let `combined_basis` default on an empty sequence (D-59's named landmine).

### Refuse rather than invent
**Source:** `engine.net_cash.transferable` (`engine/net_cash.py:154-186`)
**Apply to:** `fx.py` (missing FX pair, D-74), `ranker.py` (unranked city, D-56) — both raise/return-a-refusal-state rather than fabricate a midpoint or a `$0`.

### Single pinned rounding call site
**Source:** `engine/rounding.py::quantize_money` (full file read above)
**Apply to:** every cost-arithmetic module — `budget.py`, `cost_localizer.py`, `landed_cost.py`, `fx.py`. No new `.quantize()` call site anywhere on the cost side (D-78's own explicit requirement).

### Committed YAML, quoted-string values, `yaml.safe_load` only
**Source:** `engine/spec.py::resolve_crew_tier` (lines 158-176), `data/crew_tiers.yaml` header
**Apply to:** every new `data/*.yaml` file and its loader function — never `yaml.load` without `SafeLoader`, every numeric value a quoted string (RD-01).

### Module-anchored filesystem paths
**Source:** `engine/spec.py:62-63` (`CREW_TIERS_PATH`), `app/services/spec.py` docstring (`REPO_ROOT` convention)
**Apply to:** `engine/cost_profile.py`, `engine/fx.py`, `engine/seasonality.py`, and any new `app/services/_paths.py` additions — the systemd unit and pytest run from different working directories, so every new data-file path must be built from `Path(__file__).resolve().parents[N]`, never CWD-relative.

### CI-gate-as-pytest-assertion
**Source:** `tests/test_source_truth.py` (structural, non-judgment assertion over a data record) + `tests/test_app_spec_route.py:250-258` (the specific import-boundary assertion D-63 replaces)
**Apply to:** `tests/test_route_a_basis_walk.py` (D-63's basis-DAG walk) and the D-70 vocabulary grep — both are new pytest tests following this repo's established "honesty commitment becomes a CI gate, not a convention" pattern (also seen in `tests/mutation_targets.yaml` + its CI script for D-49).

### Fixture-driven test suites, sorted glob, fail-loud-on-empty
**Source:** `tests/test_engine_net_cash.py` header docstring (lines 1-12) naming the established discipline; `FIXTURE_DIR = "tests/fixtures/jurisdictions"` pattern
**Apply to:** every new `tests/test_engine_*.py` file that reads a fixture directory — `tests/fixtures/cost_profiles/*.yaml` should be loaded via the same sorted-glob + safe-loader + fail-loud-on-empty-glob discipline, never a single hardcoded filename.

## No Analog Found

None. Every file in the phase's file list has at least a role-match analog in the existing codebase (this phase's own RESEARCH.md states the design is explicitly "mirror four already-proven Phase 2/3 patterns," not new architecture). The weakest match is `engine/gap.py` (`GapDecomposer`), which has no direct component-diff precedent — closest available shape is `engine/pipeline.py`'s per-programme Figure composition plus `engine/net_cash.py`'s "make every deduction its own visible step" discipline; flagged for extra planner/executor attention but not blocking.

## Metadata

**Analog search scope:** `engine/`, `app/services/`, `app/routers/`, `data/`, `jurisdictions/`, `tests/`, `tests/fixtures/`
**Files scanned (read in full or targeted):** `engine/figure.py`, `engine/figure_serialize.py`, `engine/rounding.py`, `engine/qualifying_base.py`, `engine/net_cash.py`, `engine/pipeline.py`, `engine/spec.py`, `data/crew_tiers.yaml`, `app/services/spec.py`, `tests/mutation_targets.yaml`, `tests/test_engine_net_cash.py` (head), `tests/test_app_spec_route.py` (lines 230-270), `tests/test_source_truth.py` (head)
**Pattern extraction date:** 2026-08-26
</content>
