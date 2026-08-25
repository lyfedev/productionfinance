---
phase: 3
slug: new-york-end-to-end-the-anora-proof
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-25
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `03-RESEARCH.md` § Validation Architecture. Seeded at plan time; the
> Per-Task Verification Map is populated once PLAN.md task IDs exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 — already installed and green (Phases 1 and 2 shipped a passing suite) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` already present |
| **Quick run command** | `uv run pytest tests/test_engine_spec.py tests/test_app_spec_route.py tests/test_app_validate_route.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~10-20 seconds (adds an in-process ASGI TestClient layer over Phase 2's pure-`Decimal` suite; no network, no host access) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_engine_spec.py tests/test_app_spec_route.py tests/test_app_validate_route.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -q` — the full suite, including Phase 1's and
  Phase 2's existing tests. **Phase 3 must not regress them.**
- **Before `/gsd-verify-work`:** Full suite green, **plus** a run of `.github/scripts/mutation-check.sh`
  proving the SHP-14 gate is non-vacuous (red under a declared mutation, red for the right reason,
  green again once restored).
- **Max feedback latency:** 20 seconds
- **Per commit (CI, blocking):** Phase 1's `.github/workflows/ci.yml` already runs `pytest tests/` as a
  required status check, and `testpaths = ["tests"]` collects any new file automatically — so no CI
  change is needed for the new test files. Only the new `mutation-check` job must be added (D-52).

---

## Per-Task Verification Map

Populated at plan time once `03-0N-PLAN.md` task identifiers exist. The requirement-level rows below
are the contract each plan task must attach to; every row must be claimed by at least one task.

| Req ID | Behavior | Threat Ref | Test Type | Automated Command | File Exists |
|--------|----------|------------|-----------|-------------------|-------------|
| INP-01…INP-07 | `ProductionSpec` accepts every valid combination and rejects invalid ones: missing required field, both-or-neither of `crew_size`/`crew_tier`, imported > total, unknown extra field | T-03-02 (silent coercion) | unit + schema | `uv run pytest tests/test_engine_spec.py -x` | ❌ W0 |
| INP-08 | Two distinct layers: structurally, an extra field 422s; visibly, a non-empty **Total budget** field returns the friendly circularity explanation — not a generic validation error | T-03-02 | unit + integration | `uv run pytest tests/test_app_spec_route.py::test_budget_field_always_refused -x` | ❌ W0 |
| JUR-01 (success criterion 3) | Anora reproduces **$991,190** against **$3,964,760** of qualified spend, exact `Decimal` equality, through both the JSON route and the HTML route, with the NY ESD source link rendered beside the figure | T-03-01 (path traversal via `pair_id`) | golden-value + integration | `uv run pytest tests/test_app_validate_route.py::test_anora_reproduces_exactly_via_route -x` | ❌ W0 |
| SHP-14 | Suite green unmutated; a non-zero count of NY exact-mode assertions is collected; red under a declared one-basis-point mutation of `us-ny.yaml`'s `base_rate`; red **for the right reason**; green again once restored | — | CI job (bash + pytest), not itself a pytest test | `.github/scripts/mutation-check.sh` | ❌ W0 |
| (success criterion 1) | A full spec round-trips: submitted → echoed back normalized, including a `crew_tier` resolved to a headcount range | — | unit + integration | `uv run pytest tests/test_app_spec_route.py::test_spec_echoes_normalized_input -x` | ❌ W0 |
| (D-40, success criterion 1 adjacent) | An uncurated city name is accepted and marked `no curated model` — never rejected, never silently substituted, never offered a fuzzy suggestion | — | unit | `uv run pytest tests/test_app_spec_route.py::test_uncurated_city_never_suggested -x` | ❌ W0 |
| (Phase 2 contract, non-regression) | `Figure` serialization crosses the HTTP boundary as `Decimal`→`str`, never `float` — the JSON response must not reintroduce Phase 2's precision bug | — | unit + property | `uv run pytest tests/test_app_validate_route.py -x` | ❌ W0 |

*Status legend for the populated per-task table: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `engine/spec.py`, `engine/figure_serialize.py` — do not exist yet
- [ ] `app/routers/spec.py`, `app/routers/validate.py`, `app/services/spec.py`,
      `app/services/validate.py`, `app/services/city_lookup.py`, `app/templates/*.html` — none exist
      yet (only `app/main.py` exists, a single-file skeleton)
- [ ] `data/crew_tiers.yaml` — new top-level directory and file
- [ ] `.github/scripts/mutation-check.sh`, `tests/mutation_targets.yaml` — new
- [ ] `tests/test_engine_spec.py`, `tests/test_app_spec_route.py`, `tests/test_app_validate_route.py`
      — none exist yet
- [ ] `jinja2`, `python-multipart` — not yet in `pyproject.toml` / `uv.lock`. **`python-multipart` is
      required for any HTML `<form>` POST, not only file uploads** — Starlette's form parser raises at
      request time without it. Both packages returned `SUS` from the package-legitimacy gate on an
      `unknown-downloads` signal only; both repo URLs were confirmed against the Pallets and Kludex
      (current Starlette/FastAPI maintainer) organizations, so a `checkpoint:human-verify` here is a
      formality rather than an open question.

*No gap in shared test infrastructure: `testpaths = ["tests"]` already collects any new file under
`tests/`, and `.github/workflows/ci.yml`'s existing `tests` job already runs `pytest tests/`. Only the
new `mutation-check` job needs adding.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The hosted URL actually serves the Anora result to an anonymous visitor | Success criterion 3 / SHP-14 deploy path | The pytest suite exercises the app in-process via TestClient; "an anonymous visitor at the public URL sees it" is a property of the **deployment**, not of the runtime under test | From a logged-out browser (or `curl` with no cookies/headers), load the public subdomain, submit the spec form naming New York, and confirm the page shows `$991,190` against `$3,964,760` with a working link to the NY ESD source document |
| The mutation gate is non-vacuous | SHP-14 | A CI job that always passes looks identical to one that works; only observing the deliberate red proves it | Run `.github/scripts/mutation-check.sh` locally, confirm it exits non-zero under the declared mutation, read the failure output to confirm it names the NY exact-mode assertion (right reason, not an unrelated collection error), then confirm it exits zero once `us-ny.yaml` is restored |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
