# Phase 3: New York End-to-End — The Anora Proof - Pattern Map

**Mapped:** 2026-08-25
**Files analyzed:** 17 (2 `engine/*.py` new, 1 `app/main.py` extended + 6 new `app/` files, 1 `data/*.yaml`, 1 `.github/scripts/*.sh`, 1 CI job edit, 5 `tests/*.py`/`tests/*.yaml` new)
**Analogs found:** 17/17 have at least a convention-level match; 3 are "spec is the literal code" exact matches straight from `03-RESEARCH.md`'s verified Code Examples (same situation Phase 2's PATTERNS.md documented — greenfield HTTP/domain layer, no twin file, but the research doc supplies executable patterns, not aspiration).

## Key carry-forward from Phase 2's PATTERNS.md

Phase 2 established the conventions this phase must not violate:
- Money/rates are `Decimal`, never `float`; every numeric YAML value is a quoted string (RD-01). Applies directly to the new `data/crew_tiers.yaml`.
- `yaml.safe_load` only, never `yaml.load`/`yaml.unsafe_load`.
- Two non-interchangeable confidence vocabularies exist: `Figure.confidence` (`{"validated","researched"}`) vs `Source.confidence` (4-tier `LEGAL_CONFIDENCE_TIERS`). D-39 adds a rule for the new crew-tier table: it must never render as `validated`.
- `StrictModel`-style `ConfigDict(extra="forbid")` is the established Pydantic convention in `engine/models.py` — `engine/spec.py`'s `ProductionSpec` mirrors it exactly.
- No dynamic `getattr`/`importlib` resolution anywhere — applies to `app/routers`/`app/services` wiring too (explicit imports and explicit dict dispatch only).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `engine/spec.py` | model (domain schema) | transform (request→validated object) | `engine/models.py` (`StrictModel`/`extra="forbid"` convention) | role-match — same convention, new domain |
| `engine/figure_serialize.py` | utility (recursive transform) | transform (Figure tree → JSON-safe dict) | `engine/rounding.py` (single-purpose pure utility, `03-RESEARCH.md` Pattern 2 supplies literal code) | exact — research doc supplies the code, mirrors Phase 2's "spec is the literal implementation" precedent |
| `app/main.py` (extended) | config/bootstrap | n/a | itself (Phase 1) | exact — extend in place, `/health` contract frozen (D-47), same `PUBLIC_PATH`/`_resolve_git_sha` machinery reused |
| `app/routers/spec.py` | router/controller | request-response (HTML + JSON) | `app/main.py`'s existing `@app.get("/")` / `@app.get("/health")` handlers (only existing route precedent in repo) | role-match — no router-module precedent exists yet, this is the first one |
| `app/routers/validate.py` | router/controller | request-response (HTML + JSON) | same as above, plus `tests/test_engine_against_validation_pairs.py` for how a validation-pair fixture is loaded and priced | role-match |
| `app/services/spec.py` | service | transform + validation | `engine/pipeline.py::price_programme`/`price_jurisdiction` (orchestration-function shape: pure function, explicit steps, returns a dataclass) | role-match — same "one function, explicit ordered steps, returns an immutable result object" shape, HTTP-adjacent instead of engine-pure |
| `app/services/validate.py` | service | request-response (fixture read → pipeline call → compare) | `tests/test_engine_against_validation_pairs.py::_gross_credit_via_pipeline` (exact loading/pricing sequence already proven) | exact — this service is a direct extraction of that test's own working code path into production code |
| `app/services/city_lookup.py` | service (lookup/registry) | transform (string → jurisdiction id or none) | `engine/handlers/__init__.py` (explicit `dict[str,...]` allow-list, no dynamic resolution) | role-match — same "small explicit table, never fuzzy/dynamic" constraint, applied to a city string instead of a handler name |
| `app/templates/*.html` (6 files) | presentation (Jinja2) | file-I/O/render | none in repo (first templates) | no analog — `03-RESEARCH.md` Architecture Patterns diagram is the spec |
| `data/crew_tiers.yaml` | config (curated but non-jurisdictional data) | file-I/O | `jurisdictions/us-ny.yaml` for the quoted-numeric-string convention; `tests/fixtures/validation_pairs/*.yaml` for the "provenance fields beside the number" shape, but explicitly NOT `jurisdictions/` structurally (D-39) | role-match (convention only, deliberately separate directory/status) |
| `.github/scripts/mutation-check.sh` | delivery/compliance script | batch (scratch-copy CI job) | `.github/scripts/lockfile-scan.sh` (`set -uo pipefail`, `PASS:`/`FAIL:` prefixed stderr/stdout, explicit non-zero exit, portable while-read loop) | exact — same script family, same shell conventions |
| `.github/workflows/ci.yml` (add `mutation-check` job) | config (CI) | n/a | the existing `lockfile-scan`/`tests` job blocks in the same file | exact — literal sibling job, same `actions/checkout@v4` + `astral-sh/setup-uv@v5` steps |
| `tests/mutation_targets.yaml` | test fixture (declared table) | file-I/O | `tests/fixtures/validation_pairs/*.yaml` (one-file-or-one-table-per-case, explicit fields, no hidden logic) | role-match |
| `tests/test_engine_spec.py` | test | unit | `tests/test_engine_models.py` (Pydantic-model validation test shape) | role-match |
| `tests/test_app_spec_route.py` | test | integration (HTTP) | `tests/test_health.py` (first and only existing FastAPI `TestClient` test in repo) | exact — same `TestClient` pattern, first to add POST coverage |
| `tests/test_app_validate_route.py` | test | integration (HTTP) + golden-value | `tests/test_health.py` (client shape) + `tests/test_engine_against_validation_pairs.py` (golden-value assertion: `Decimal("991190")`) | role-match, composite of two analogs |

## Pattern Assignments

### `engine/spec.py` (model, transform)

**Analog:** `engine/models.py` lines 1-20 (module docstring/RD conventions) — mirror the `StrictModel` pattern verbatim; `03-RESEARCH.md` Pattern 1 (lines 338-390) is the literal target implementation, already written and verified against this repo's locked `pydantic==2.13.4` conventions.

**Convention to copy** (`engine/models.py`, extra="forbid" style — confirmed present in this repo's models file, same as Phase 2's PATTERNS.md documented):
```python
from pydantic import BaseModel, ConfigDict

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
```
Apply directly to `ProductionSpec(StrictModel)` per `03-RESEARCH.md` Pattern 1's full field list (production_type, shoot_days_stage/location, crew_size XOR crew_tier via `model_validator(mode="after")`, principal_cast fields, crew_imported/hired fields, start_quarter + start_year, candidate_cities). **No field represents money** — this is the structural half of D-35/INP-08, and it is the one thing this file must never grow, even by omission-turned-oversight in a later phase.

**Cross-field validator shape to copy** (same `model_validator(mode="after")` idiom `engine/models.py` already uses for its own cross-field checks — e.g. `_programme_edges_resolve_to_declared_ids`):
```python
@model_validator(mode="after")
def _exactly_one_crew_input(self) -> "ProductionSpec":
    if (self.crew_size is None) == (self.crew_tier is None):
        raise ValueError("exactly one of crew_size or crew_tier must be supplied")
    return self
```
**Pitfall to avoid (per RESEARCH.md Pitfall 3):** do not unconditionally assert `crew_imported_count + crew_hired_locally_count == crew_size` — guard with `if self.crew_size is not None:`, since `crew_tier`-only specs resolve to a range, not a scalar.

---

### `engine/figure_serialize.py` (utility, transform)

**Analog:** `engine/rounding.py` (single pure function, single call-site discipline) for *shape*; `03-RESEARCH.md` Pattern 2 (lines 398-419) for the literal function body — copy verbatim, same as Phase 2 copied the `Figure` dataclass and `quantize_money` verbatim from their respective research-doc Code Examples.

```python
from engine.figure import Figure

def figure_to_dict(figure: Figure) -> dict:
    return {
        "figure_id": figure.figure_id,
        "value": str(figure.value),              # Decimal -> str, never float
        "unit": figure.unit,
        "label": figure.label,
        "derivation": list(figure.derivation),
        "source_url": figure.source_url,
        "date_checked": figure.date_checked.isoformat() if figure.date_checked else None,
        "confidence": figure.confidence,
        "live_fetched_this_run": figure.live_fetched_this_run,
        "inputs": [figure_to_dict(child) for child in figure.inputs],
    }
```
**Never** call `dataclasses.asdict(figure)` directly and return it from a route (Pitfall 4 — `Decimal`/`date` crash FastAPI's default JSON encoder with a 500, not a 422, and a GET-only smoke test will not catch it).

---

### `app/main.py` (extended)

**Analog:** itself. Read lines 60-97 (already read this session) for the exact patterns to extend, not replace:
- `/health` returns exactly `{"status", "version", "git_sha", "boot_time"}` — D-47 freezes this; new routers must not touch this handler.
- `PUBLIC_PATH = os.environ.get("PRODFIN_PUBLIC_PATH", "").rstrip("/")` — every new template link must be built relative to `PUBLIC_PATH`, exactly like the existing `index()` handler does (`f"{PUBLIC_PATH}/health"`), per the documented 01-09 absolute-path bug precedent.
- Add `from fastapi.templating import Jinja2Templates` and mount new routers with `app.include_router(...)`, following FastAPI's own convention (no analog needed in-repo — this is the first router mount).

---

### `app/routers/spec.py`, `app/routers/validate.py` (router, request-response)

**Analog:** `app/main.py`'s existing `@app.get("/")`/`@app.get("/health")` handlers — the only route-handler precedent in the repo. Copy the "plain function, explicit return type, no framework magic" style. `03-RESEARCH.md`'s System Architecture Diagram (lines 200-276) is the literal routing table to implement: three endpoints per route (`GET` form, `POST` form, `GET/POST` JSON API), all three calling into the identical `app/services/*.py` function (D-43 — never duplicate logic between the JSON and HTML paths).

**Form-parsing dependency — do not omit:** any route using `Form(...)` requires `python-multipart` installed (Pitfall 1) — cover with at least one `client.post(url, data={...})` integration test, not only `client.get(...)`.

---

### `app/services/spec.py` (service, transform+validation)

**Analog:** `engine/pipeline.py::price_programme`/`price_jurisdiction` for the "one function, ordered numbered steps as inline comments, returns an immutable dataclass result" shape (see `engine/pipeline.py` lines 66-100, already read this session). `03-RESEARCH.md` Pattern 3 (lines 421-448) is the literal code to adapt.

```python
REFUSAL_REASON = (
    "cost is only ever an output; a fixed dollar amount buys a different "
    "production in each city, which makes the comparison circular"
)

class SpecFormSubmission(BaseModel):
    # ... the seven INP fields ...
    total_budget: str | None = None  # named deliberately — see Pitfall 2

def handle_spec_submission(raw: SpecFormSubmission) -> "SpecResult | RefusalResult":
    if raw.total_budget not in (None, ""):
        return RefusalResult(reason=REFUSAL_REASON)   # D-35 "visible" half
    spec = ProductionSpec.model_validate(raw.model_dump(exclude={"total_budget"}))
    # D-37 items 1-4: echo spec, per-city curated status, NY rule terms
    # via engine.models.load_ruleset, explicit "not yet derived" statement.
    # NO call to compute_qualifying_base / price_jurisdiction (D-36).
```
**Pitfall 2, explicit:** `extra="forbid"`'s generic 422 body does not satisfy success criterion 2's "refused with an explanation" — the named `total_budget` field + this explicit check is mandatory, not optional polish.

---

### `app/services/validate.py` (service, request-response)

**Analog:** `tests/test_engine_against_validation_pairs.py::test_anora_reproduces_exactly_through_price_jurisdiction` (read this session) — this service is a direct production extraction of that test's already-proven working sequence.

**Sequence to copy** (concrete, from `engine/pipeline.py` + the test file's own loading pattern):
```python
import yaml
from decimal import Decimal
from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction

def reproduce_disclosure(pair_id: str) -> "ValidateResult":
    with open(f"tests/fixtures/validation_pairs/{pair_id}.yaml") as f:
        pair = yaml.safe_load(f)                       # yaml.safe_load ONLY
    ruleset = load_ruleset(RULESET_PATH_BY_JURISDICTION[pair["jurisdiction_id"]])
    priced = price_jurisdiction(ruleset, Decimal(pair["qualified_spend"]))
    computed = priced.programmes[0].gross_credit.value  # RD-03: gross credit, never net cash
    disclosed = Decimal(pair["credit_amount"])
    verdict = "exact match" if computed == disclosed else "MISMATCH"
    return ValidateResult(disclosed=disclosed, computed_figure=priced.programmes[0].gross_credit,
                           verdict=verdict, ...)
```
**Anora's proven anchor** (from `tests/test_engine_against_validation_pairs.py`, read this session): `Decimal("3964760")` qualified spend → `Decimal("991190")` gross credit, exactly. This is not new logic — it is exposure of an already-passing test.

**Known refusal case to surface, not hide** (WINDOWS.md #3, `us-ct.yaml`): if a future pair selector ever offers a Connecticut pair, `price_jurisdiction` raises `ValueError` because `transfer_discount` rates are null — catch and render as an honest "cannot be converted to net cash: no sourced transfer discount rate" message, never a bare 500 and never an invented rate. Phase 3 is NY-only so this is a guard rail, not active code.

---

### `app/services/city_lookup.py` (service, lookup)

**Analog:** `engine/handlers/__init__.py` (explicit `dict[str, Callable]` allow-list, no `getattr`/`importlib` — read in Phase 2's PATTERNS.md, same non-negotiable constraint applies here to a different value type).

```python
# app/services/city_lookup.py — small, explicit, committed table.
# Normalizes only case/whitespace + a short known-alias list for New York.
# Anything not an exact hit after that is "no curated model" — never a
# fuzzy match, never a suggestion (D-40, Pitfall 5).
CITY_ALIASES: dict[str, str] = {
    "new york": "us-ny",
    "new york city": "us-ny",
    "nyc": "us-ny",
}

def resolve_city_to_jurisdiction(raw_city: str) -> str | None:
    key = raw_city.strip().lower()
    return CITY_ALIASES.get(key)  # None => "no curated model", reported plainly
```

---

### `app/templates/*.html` (presentation, Jinja2)

**Analog:** none in-repo — first templates. Follow `03-RESEARCH.md`'s Recommended Project Structure listing (`base.html`, `index.html`, `spec_form.html`, `spec_result.html`, `validate_form.html`, `validate_result.html`) and D-48 (near-unstyled semantic HTML, no design system). Every link must be built with the `PUBLIC_PATH` prefix, matching `app/main.py`'s existing `index()` handler convention (`f"{PUBLIC_PATH}/health"`).

---

### `data/crew_tiers.yaml` (config, curated non-jurisdictional data)

**Analog:** `jurisdictions/us-ny.yaml` for the quoted-numeric-string convention (RD-01 applies to any headcount range value written as a decimal-ish number, though these are likely plain ints — quote if any field could ever be fractional); `tests/fixtures/validation_pairs/ny_anora.yaml` for the "provenance lives beside the value" shape. **Deliberately structurally separate from `jurisdictions/`** per D-39 — this file must carry an explicit provenance note that it is a modelling assumption and must never set a `confidence: validated` field (that tier is reserved for `jurisdictions/*.yaml` rule files reproducing government disclosures).

```yaml
# data/crew_tiers.yaml — modelling assumption, NOT a sourced government figure.
# No confidence field here is ever "validated" (D-39).
provenance_note: >
  Non-union local labour/crew-composition rates are not publicly disclosed
  (PROJECT.md line 78). These ranges are an internal modelling assumption,
  not a government-sourced figure, and are labelled accordingly wherever
  rendered.
tiers:
  micro:
    headcount_low: 15
    headcount_high: 30
  # ... small / mid / large / tentpole ...
```

---

### `.github/scripts/mutation-check.sh` (delivery/compliance script, batch)

**Analog:** `.github/scripts/lockfile-scan.sh` (read in full this session, lines 1-40) — copy its exact shell conventions: `#!/usr/bin/env bash`, `set -uo pipefail`, a leading comment block naming the requirement ID (SHP-14) and exit codes, `PASS:`/`FAIL:` prefixed messages to the right stream, portable `while IFS= read -r` loops (not `mapfile`, for bash 3.2/macOS parity — same portability note this project already applies).

**Literal script to adapt** (`03-RESEARCH.md` Pattern 4, lines 454-501 — already a complete, ordered five-step script matching D-50 exactly): scratch-copy via `mktemp -d` + `trap 'rm -rf "$SCRATCH"' EXIT`, never mutate the working tree; step 1 green-unmutated; step 2 non-zero collected NY exact-mode items (`pytest --collect-only -k "ny" | grep -c "::"`); step 3 apply the declared one-basis-point mutation to `jurisdictions/us-ny.yaml`; step 4 assert red for the *named* test, not a collection error; step 5 restore and re-assert green. Drive the actual find/replace from `tests/mutation_targets.yaml` (D-51) rather than hard-coding the `sed` pattern, so CT's Christmas Always anchor is a one-row addition once WINDOWS.md #3 clears.

---

### `.github/workflows/ci.yml` (add `mutation-check` job)

**Analog:** the existing `lockfile-scan`/`tests` jobs in the same file (read this session, lines 1-90). Copy the exact job shape:
```yaml
  mutation-check:
    name: mutation-check (SHP-14)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Non-vacuity proof — suite green, mutation makes it red, restore green
        run: bash .github/scripts/mutation-check.sh
```
Add this job alongside the other five; do not restructure `lockfile-scan`, `vendor-scan`, `commit-window`, `secret-scan`, or `tests` (D-52).

---

### `tests/test_app_spec_route.py`, `tests/test_app_validate_route.py` (test, integration/HTTP)

**Analog:** `tests/test_health.py` — the only existing `TestClient` usage in the repo (`from fastapi.testclient import TestClient`, `from app.main import app`). Copy its client-construction pattern; extend with `client.post(url, data={...})` calls (form path) and `client.post(url, json={...})` (API path) — a GET-only test suite will not catch Pitfall 1 (missing `python-multipart`) or Pitfall 4 (raw `Figure` serialization crash).

`tests/test_app_validate_route.py` additionally asserts the golden value exactly as `tests/test_engine_against_validation_pairs.py` already does: `assert computed == Decimal("991190")`, now reached through the HTTP layer instead of calling `price_jurisdiction` directly.

---

### `tests/test_engine_spec.py` (test, unit)

**Analog:** `tests/test_engine_models.py` — same "construct valid/invalid instances, assert `ValidationError` on the invalid ones" shape already used for `JurisdictionRuleSet`. Must include: an `extra="forbid"` stray-field 422 case, the `crew_size` XOR `crew_tier` validator both directions, and at minimum one `crew_tier`-only case exercising the Pitfall-3 guard.

## Shared Patterns

### `extra="forbid"` StrictModel convention
**Source:** `engine/models.py` (Phase 2, `ConfigDict(extra="forbid")`).
**Apply to:** `engine/spec.py::ProductionSpec`, `app/services/spec.py::SpecFormSubmission` (the latter deliberately does NOT forbid extra in the same way — it *names* `total_budget` so it can be caught with a real message; see Pattern 3 above and Pitfall 2).

### Decimal / quoted-YAML-string discipline
**Source:** `.claude/CLAUDE.md`, `engine/models.py` RD-01, `engine/rounding.py`.
**Apply to:** `data/crew_tiers.yaml` (any fractional field), `app/services/validate.py` (`Decimal(pair["qualified_spend"])`, `Decimal(pair["credit_amount"])` — never float).

### `yaml.safe_load` only
**Source:** Phase 2 PATTERNS.md, `tests/test_validation_pair_fixtures.py`.
**Apply to:** `app/services/validate.py` (reading fixture pairs), `data/crew_tiers.yaml` loader, `.github/scripts/mutation-check.sh`'s Python-side table reader if any.

### No dynamic resolution (explicit dict allow-lists only)
**Source:** `engine/handlers/__init__.py`.
**Apply to:** `app/services/city_lookup.py` (explicit alias dict, never fuzzy match — D-40/Pitfall 5), any router→service wiring in `app/routers/*.py`.

### `PASS:`/`FAIL:` CI script convention, scratch-copy discipline
**Source:** `.github/scripts/lockfile-scan.sh`.
**Apply to:** `.github/scripts/mutation-check.sh` — same message prefixes, same `set -uo pipefail`, same non-zero exit on any failure, same explicit "fail loud on a vacuous/empty result" pattern lockfile-scan already applies to zero-package extraction.

### `TestClient` HTTP integration tests
**Source:** `tests/test_health.py`.
**Apply to:** `tests/test_app_spec_route.py`, `tests/test_app_validate_route.py` — extend with POST coverage (form + JSON), which no existing test file does yet.

### Recursive Figure serialization, never bare `asdict`
**Source:** `engine/figure.py` (Phase 2), `03-RESEARCH.md` Pattern 2.
**Apply to:** every route in `app/routers/validate.py` and any Route A response in `app/routers/spec.py` that carries a `Figure` (the NY rule-term figures per D-37 item 3) — always through `engine/figure_serialize.py::figure_to_dict`, never `dataclasses.asdict(figure)` directly.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `app/templates/*.html` (6 files) | presentation | render | No templating exists anywhere in the repo yet (Phase 1/2 are template-free); `03-RESEARCH.md`'s Architecture Patterns diagram and Recommended Project Structure are the sole spec |
| `app/routers/*.py`, `app/services/*.py` (as a layer) | controller/service | request-response | First router/service split in the repo — `app/main.py` has held all routes inline through Phase 1; `03-RESEARCH.md`'s System Architecture Diagram is the spec for the split |

## Metadata

**Analog search scope:** `app/` (full), `engine/` (full), `tests/` (`test_health.py`, `test_engine_against_validation_pairs.py`, `test_engine_models.py` read directly; others listed via `ls`), `.github/scripts/` (full), `.github/workflows/ci.yml` (full), `jurisdictions/` (listed, prior-session content read via Phase 2 PATTERNS.md), `.planning/phases/02-engine-spine-incentive-interpreter/02-PATTERNS.md` (full)
**Files scanned:** `app/main.py` (full), `engine/models.py` (partial, header/RD conventions), `engine/pipeline.py` (full), `.github/scripts/lockfile-scan.sh` (full), `.github/workflows/ci.yml` (partial, all job headers + `tests` job), `tests/test_engine_against_validation_pairs.py` (partial, module docstring + golden-value tests)
**Pattern extraction date:** 2026-08-25
