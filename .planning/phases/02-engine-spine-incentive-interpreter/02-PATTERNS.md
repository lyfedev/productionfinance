# Phase 2: Engine Spine & Incentive Interpreter - Pattern Map

**Mapped:** 2026-08-25
**Files analyzed:** 18 (8 `engine/*.py`, 2 `jurisdictions/*.yaml`, 4 synthetic fixture YAMLs, 8 `tests/test_engine_*.py` — some counted once where structurally identical)
**Analogs found:** Partial for all — this is greenfield code with **no direct structural predecessor** in the repo. Every analog below is a *convention* source (money/Decimal handling, YAML loading, provenance fields, fixture/test shape), not a twin file. 0/18 have a role+data-flow exact match; all 18 draw at least one concrete convention from an existing file.

## Key finding: no Money/Decimal helper class exists yet

RESEARCH.md's own "Code Examples" section and ARCHITECTURE.md's `Figure` dataclass are the **actual spec** for `engine/figure.py` and `engine/rounding.py` — copy those verbatim, they are not aspirational, they are executed-and-verified code from RESEARCH.md itself. Phase 1 never built the `.claude/CLAUDE.md`-mandated in-repo `Money` dataclass; it only established the *convention* that money fields are YAML strings parsed to `Decimal` at test time (see `tests/test_validation_pair_fixtures.py` `MONEY_FIELDS` loop, lines 120-137). There is nothing named `Money` anywhere in the codebase to import — Phase 2 is the first phase to actually construct the `decimal.Decimal`-based value handling CLAUDE.md mandates, via `Figure` (holds a bare `Decimal` in `.value`, not a `Money` wrapper). **Do not search for or invent an import from a nonexistent `app/money.py`.**

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `engine/__init__.py` | config/package-init | n/a | `app/__init__.py` | role-match (trivial: version/package marker only) |
| `engine/models.py` | model (schema) | transform (YAML→validated object) | `tests/test_validation_pair_fixtures.py` (validation *conventions*, not a Pydantic file) + ARCHITECTURE.md Q2 schema (spec) | partial — no existing Pydantic model file in repo at all; convention-only match |
| `engine/figure.py` | model (value object) | transform | ARCHITECTURE.md Q3 `Figure` dataclass (spec, reproduced verbatim in RESEARCH.md "Code Examples") | exact — RESEARCH.md supplies the literal code to use, not just a pattern to imitate |
| `engine/rounding.py` | utility | transform | RESEARCH.md "Code Examples" → Pinned rounding (spec, reproduced verbatim) | exact — same as above, literal code given |
| `engine/qualifying_base.py` | service (rule dispatch) | transform | none in repo; ARCHITECTURE.md Q1 stage 3 + Q2 `base_definition` schema is the spec | no analog — new domain logic |
| `engine/credit.py` | service (rule dispatch) | transform | RESEARCH.md "Code Examples" → `lookup_flat_rate_by_band` / `blend_two_rates_by_ceiling` (spec, reproduced verbatim) | exact for the two named functions; rest is new |
| `engine/net_cash.py` | service (rule dispatch) | transform | ARCHITECTURE.md Q1 stage 5 (4 mechanism functions) — spec only | no analog — new domain logic |
| `engine/handlers/__init__.py` | config (registry) | n/a | ARCHITECTURE.md Security Domain / Q2 escape-hatch description (spec: dict-literal allow-list, never `getattr`/`importlib`) | no analog — new, but the *constraint* (no dynamic resolution) is explicit and non-negotiable |
| `jurisdictions/us-ny.yaml` | config (curated data) | file-I/O | `sources/MANIFEST.yaml` (YAML data-with-provenance convention) + `tests/fixtures/validation_pairs/ny_anora.yaml` (money-as-string, source_url/date_checked convention) | role-match — same "provenance fields live beside the number" convention, different schema shape |
| `jurisdictions/us-ct.yaml` | config (curated data) | file-I/O | same as above, plus `ct_christmas_always.yaml` for the exact tiered-rate numbers to reproduce | role-match |
| `tests/fixtures/jurisdictions/*.yaml` (4 files) | test fixture | file-I/O | `tests/fixtures/validation_pairs/*.yaml` (fixture directory shape, "one file per case", synthetic naming) | role-match — same fixture-directory pattern, different domain schema |
| `tests/test_engine_models.py` | test | unit | `tests/test_validation_pair_fixtures.py` (parametrized `yaml.safe_load` + `pytest.mark.parametrize` over a sorted glob) | exact — same test-infrastructure convention |
| `tests/test_engine_rounding.py` | test | unit | RESEARCH.md Pitfall 2 (explicit constructed-boundary test requirement) | no direct analog file; requirement is explicit in RESEARCH.md itself |
| `tests/test_engine_qualifying_base.py` | test | unit + boundary | `tests/test_validation_pair_fixtures.py` structure (assert-per-field pattern) | role-match |
| `tests/test_engine_credit.py` | test | unit + boundary + golden-value | `tests/test_validation_pair_fixtures.py` structure | role-match |
| `tests/test_engine_net_cash.py` | test | unit + boundary + golden-value | `tests/test_validation_pair_fixtures.py` structure | role-match |
| `tests/test_engine_figure_provenance.py` | test | property | `tests/test_source_truth.py` (structural/property assertions over provenance-carrying records, not correctness assertions) | role-match — same "assert the record is structurally honest" spirit |
| `tests/test_engine_jurisdiction_additivity.py` | test | structural (git diff) | `tests/test_source_truth.py` (cross-file structural-consistency assertions, e.g. manifest vs. fixtures vs. archive) | role-match |
| `tests/test_engine_against_validation_pairs.py` | test | golden-value, imports existing fixtures | `tests/test_validation_pair_fixtures.py` (`accuracy_denominator_by_stage`, explicitly stated as importable by a later phase — this is that later phase) | exact — RESEARCH.md and the fixture test itself both name this exact reuse relationship |

## Pattern Assignments

### `engine/models.py` (model, transform)

**Analog:** No existing Pydantic file in this repo — the schema is fully specified in `.planning/research/ARCHITECTURE.md` Q2 and corrected by `02-RESEARCH.md` Finding 1. Treat `02-RESEARCH.md` "Pattern 1: Decimal-safe rule-file loading" as the literal code pattern.

**Decimal-typing pattern** (`02-RESEARCH.md` lines 227-243, verified against this repo's locked `pydantic==2.13.4`):
```python
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

**Conflict flag (CRITICAL — read before writing this file):** `.planning/research/ARCHITECTURE.md` Q2's literal schema types every rate/threshold field `float`. `02-RESEARCH.md` explicitly supersedes this ("State of the Art" table, lines 427-433) and mandates `Decimal` for every such field, plus quoting every numeric rule-file value as a YAML string. This is not a style choice — RESEARCH.md verified by direct execution that `float` + naive `Decimal()` conversion corrupts rates like `0.263`/`0.30`/`0.35`. **Use `Decimal`, never `float`, for every money/rate/threshold field in `engine/models.py`, even though ARCHITECTURE.md's schema listing literally says `float` in several places** (`base_rate: float`, `additional_rate: float`, `pct_core_cap: float`, etc.). The planner should write this as an explicit deviation-from-ARCHITECTURE.md task note, not silently diverge.

**Closed-enum pattern (from existing test convention, `tests/test_validation_pair_fixtures.py` lines 54-56):**
```python
LEGAL_DISCLOSURE_STAGES = {"issued", "allocated", "estimated"}
LEGAL_STATUSES = {"active", "blocked"}
LEGAL_ASSERTION_MODES = {"exact", "bounded"}
```
Mirror this shape as Pydantic `Literal[...]` types on `mechanism`, `base_definition.type`, `rate_structure.type`, `status` — fail loud (raise) rather than default, per Security Domain V5.

---

### `engine/figure.py` (model, transform)

**Analog:** `02-RESEARCH.md` "Code Examples" → The Figure value object — this is a verbatim reproduction of `.planning/research/ARCHITECTURE.md` Q3, marked "the schema Phase 2 must implement, not a new proposal." Copy directly:
```python
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

**Provenance field-name reuse:** `source_url` and `date_checked` are the exact field names already used in `tests/fixtures/validation_pairs/*.yaml` (e.g. `ny_anora.yaml` lines 15, 19) — Phase 2 reuses these names verbatim rather than minting `citation_url`/`checked_on` or similar. `confidence` as a closed `validated`/`researched` enum is new to this phase (Phase 1's fixtures use a different closed vocabulary, `LEGAL_CONFIDENCE_TIERS = {"LOW", "MEDIUM", "MEDIUM-HIGH", "HIGH"}` in `tests/test_source_truth.py` line 36) — **these are two distinct, non-interchangeable confidence vocabularies** (see Shared Patterns below).

---

### `engine/rounding.py` (utility, transform)

**Analog:** `02-RESEARCH.md` "Code Examples" → Pinned rounding (Finding 2), verbatim:
```python
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
No analog needed elsewhere in the repo — nothing currently rounds money (Phase 1's fixture tests only parse `Decimal(raw)`, never quantize).

---

### `engine/credit.py` (service, transform)

**Analog:** `02-RESEARCH.md` "Code Examples" → Cliff vs. blended rate dispatch (Finding 3), verbatim:
```python
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
**Critical: never merge these two functions into one branch** — RESEARCH.md Pitfall 3 verified this produces a ~$175,000 error against the CT disclosed figure if conflated. Same file also needs the ordered `CreditCalculator` sequence (per_person_ceiling → uplift_stacking → tier/rate → per_project_cap → annual_programme_cap); ARCHITECTURE.md Q1 stage 4 (lines 105-113) is the spec; the GA worked example ($10M spend, $2M W-2 lead → $8.5M ceiling-adjusted base × 30% = $2.55M) is the regression anchor for Pitfall 4 (ceiling applies to base, before rate).

**Never-silent-derivation pattern** (ARCHITECTURE.md Q3, reproduced in `02-RESEARCH.md` Pattern 2):
```python
if programme.per_person_ceiling.applies:
    figure = figure.with_step(f"per-person ceiling applied: ${ceiling_amount} cap on {role}")
else:
    figure = figure.with_step("no per-person ceiling applies in this jurisdiction")
```
Apply this unconditionally at every one of the 5 `CreditCalculator` steps.

---

### `engine/qualifying_base.py`, `engine/net_cash.py` (service, transform)

**Analog:** No code analog anywhere in the repo — these are new domain logic with the schema fully specified in ARCHITECTURE.md Q1 (stages 3 and 5) and Q2 (`base_definition`, `mechanism`/`taxable`/`audit`/`transfer_discount` fields). No pattern to extract from existing files beyond the Decimal/rounding/Figure conventions above, which apply uniformly. `net_cash.py` needs exactly 4 pure functions keyed by `mechanism` (`refundable`, `transferable`, `rebate_grant`, `nonrefundable_credit`) — never one function per jurisdiction (Anti-Pattern 1).

---

### `engine/handlers/__init__.py` (config, registry)

**Analog:** No code analog. The constraint is explicit and non-negotiable: **a plain `dict[str, Callable]` literal, never `getattr`/`importlib.import_module` resolving a string from rule-file content** — Security Domain V4/threat-pattern table in `02-RESEARCH.md` lines 519, 529. This is forward-looking hardening: Phase 2's own rule files are human-written, but the same registry will later receive references from Phase 7's LLM-extracted YAML, so the closed allow-list must be established now.

---

### `jurisdictions/us-ny.yaml`, `jurisdictions/us-ct.yaml` (config, file-I/O)

**Analog:** `sources/MANIFEST.yaml` for the "every field traceable to a citation" convention, and `tests/fixtures/validation_pairs/ny_anora.yaml` / `ct_christmas_always.yaml` for the exact provenance field names (`source_url`, `date_checked`) and the money-as-quoted-string convention.

**Imports/loading pattern to reuse** (`tests/test_validation_pair_fixtures.py` lines 61-63, `yaml.safe_load` only):
```python
def _load(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)
```
Never `yaml.load()`/`yaml.unsafe_load()` — already Phase 1 convention, `02-RESEARCH.md` Security Domain V5 makes this an explicit control.

**Money-as-string convention to extend to rates** (`tests/test_validation_pair_fixtures.py` `MONEY_FIELDS` check, lines 130-137 — the same discipline `02-RESEARCH.md` Finding 1 extends to rate/threshold fields):
```python
for field in MONEY_FIELDS:
    raw = data.get(field)
    ...
    assert isinstance(raw, str), (
        f"{path}: money field '{field}' must be a YAML string "
        f"(never a float), got {type(raw).__name__}: {raw!r}"
    )
```
Concretely: `jurisdictions/us-ct.yaml`'s `rate_structure.tiers` must be written `{threshold_low: "100000", ..., rate: "0.30"}`, quoted, exactly as `02-RESEARCH.md`'s own excerpt shows (line 240-242) — do not follow ARCHITECTURE.md Q2's unquoted schema listing literally.

**Exact figures these two rule files must reproduce** (D-05 anchors, already committed and readable):
- NY: Anora `$3,964,760 qualified_spend → $991,190 credit_amount` (exact, flat 25%) — `tests/fixtures/validation_pairs/ny_anora.yaml`
- NY: Succession S4, Gilded Age S2 (bounded, 150bps) — same directory
- CT: Christmas Always `$3,865,005 → $1,159,502` (exact, `tiered_by_spend` cliff lookup, NOT marginal) — `tests/fixtures/validation_pairs/ct_christmas_always.yaml`

---

### `tests/fixtures/jurisdictions/*.yaml` (test fixture, file-I/O)

**Analog:** `tests/fixtures/validation_pairs/` directory shape — one file per case, descriptive snake_case filename, kept structurally separate from the production data directory (`jurisdictions/` vs `sources/` split mirrors `tests/fixtures/jurisdictions/` vs `jurisdictions/`). Reuse the sorted-glob parametrization convention:
```python
FIXTURE_DIR = "tests/fixtures/validation_pairs"
FIXTURE_PATHS = sorted(glob(f"{FIXTURE_DIR}/*.yaml"))
if not FIXTURE_PATHS:
    raise RuntimeError(...)  # never a vacuous green (T-01-15)
```
Apply the same "fail loud, not vacuous-green" guard to any new fixture-driven test over `tests/fixtures/jurisdictions/`.

---

### `tests/test_engine_*.py` (8 files) (test, unit/boundary/golden-value/property)

**Analog:** `tests/test_validation_pair_fixtures.py` (parametrized-fixture + explicit-expected-value pattern) is the primary structural analog for all 8; `tests/test_source_truth.py` (structural/cross-file consistency assertions) is the secondary analog specifically for `test_engine_figure_provenance.py` and `test_engine_jurisdiction_additivity.py`, since those two test *shape/structure* rather than *arithmetic correctness*.

**`tests/test_engine_against_validation_pairs.py` specifically:** RESEARCH.md and the existing fixture file both name this exact reuse relationship — `tests/test_validation_pair_fixtures.py`'s `accuracy_denominator_by_stage()` function (lines 279-301) is explicitly documented as "Importable by Phase 5's Job 1 mismatch taxonomy via `from tests.test_validation_pair_fixtures import accuracy_denominator_by_stage`" — Phase 2's golden-value test against the existing fixtures should import fixture data the same way `test_validation_pair_fixtures.py` loads it (`yaml.safe_load`, sorted glob), not re-implement fixture loading.

**pytest config already covers new files** — no `pyproject.toml` change needed beyond adding `pydantic` as an explicit dependency; `testpaths = ["tests"]` (pyproject.toml line 20) already picks up `tests/test_engine_*.py`.

---

## Shared Patterns

### Money/Decimal handling
**Source:** `.claude/CLAUDE.md` (mandate: stdlib `decimal.Decimal` + in-repo dataclass, `py-moneyed` forbidden) + `02-RESEARCH.md` Finding 1 (verified execution) + `tests/test_validation_pair_fixtures.py` `MONEY_FIELDS` convention (lines 58, 120-137).
**Apply to:** `engine/models.py` (every rate/money/threshold field `Decimal`, never `float`), `jurisdictions/*.yaml` and `tests/fixtures/jurisdictions/*.yaml` (every such value quoted as a YAML string), `engine/rounding.py` (single quantize call site).
**Note:** No `Money` dataclass exists yet in this repo despite CLAUDE.md naming one — `Figure.value: Decimal` (bare) is what Phase 2 actually builds; do not invent an import from a nonexistent module.

### YAML loading
**Source:** `tests/test_validation_pair_fixtures.py` lines 61-63, `tests/test_source_truth.py`.
**Apply to:** Any code in `engine/` or test file that reads `jurisdictions/*.yaml` or `tests/fixtures/jurisdictions/*.yaml`.
```python
def _load(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)
```
Never `yaml.load()`/`yaml.unsafe_load()`.

### Provenance fields
**Source:** `tests/fixtures/validation_pairs/ny_anora.yaml` (`source_url`, `date_checked` field names) + ARCHITECTURE.md Q3 `Figure` dataclass (`confidence: Literal["validated", "researched"]`).
**Apply to:** `engine/figure.py`, every jurisdiction YAML's `sources[]` entries.
**Conflict flag:** two non-interchangeable confidence vocabularies exist in this repo already — do not conflate them:
- `tests/test_source_truth.py` line 36: `LEGAL_CONFIDENCE_TIERS = {"LOW", "MEDIUM", "MEDIUM-HIGH", "HIGH"}` — used for source-document reliability in `SOURCE-TRUTH.md`/`MANIFEST.yaml`.
- `Figure.confidence` (this phase, per ARCHITECTURE.md Q3 and PRV-02): closed to exactly `{"validated", "researched"}` — a different axis (was this figure checked against a real disclosure, or only researched/estimated). `02-RESEARCH.md` PRV-02 test map explicitly requires this be a closed 2-value enum, not the 4-value source-reliability tier. The planner should make sure `test_engine_figure_provenance.py::test_confidence_is_closed_enum` asserts against `{"validated","researched"}`, not accidentally against the `SOURCE-TRUTH.md` 4-tier vocabulary.

### Fixture/test conventions
**Source:** `tests/test_validation_pair_fixtures.py` (whole file — parametrize over sorted glob, explicit `REQUIRED_FIELDS` set, fail-loud-on-empty-glob guard, `Decimal(raw)` money-field parse-check).
**Apply to:** All 8 `tests/test_engine_*.py` files; `tests/fixtures/jurisdictions/` directory structure.

## No Analog Found

Files with no close structural match anywhere in the repo (planner should rely on `02-RESEARCH.md`'s Code Examples / ARCHITECTURE.md's schema directly, since those sections were written specifically to serve as this phase's implementation spec):

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `engine/qualifying_base.py` | service | transform | No qualifying-base computation exists anywhere pre-Phase-2; ARCHITECTURE.md Q1 stage 3 is the sole spec |
| `engine/net_cash.py` | service | transform | No net-cash-mechanism code exists pre-Phase-2; ARCHITECTURE.md Q1 stage 5 is the sole spec |
| `engine/handlers/__init__.py` | config | n/a | No handler-registry pattern exists elsewhere in the repo; Security Domain constraint (explicit dict allow-list, no dynamic import) is the only guidance, and it is a hard requirement not a style choice |

## Metadata

**Analog search scope:** `app/`, `sources/`, `tests/` (all files), `pyproject.toml`, `.planning/phases/01-*/`, `.planning/research/ARCHITECTURE.md`, `02-RESEARCH.md`
**Files scanned:** `app/main.py`, `app/__init__.py`, `pyproject.toml`, `sources/MANIFEST.yaml`, `tests/test_validation_pair_fixtures.py` (full), `tests/test_source_truth.py` (partial, structure confirmed), `tests/fixtures/validation_pairs/ny_anora.yaml`, `tests/fixtures/validation_pairs/ct_christmas_always.yaml`, `02-RESEARCH.md` (full), `.planning/research/ARCHITECTURE.md` (full)
**Pattern extraction date:** 2026-08-25
