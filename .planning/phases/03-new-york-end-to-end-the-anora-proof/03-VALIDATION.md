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

Populated at plan time. Task identifiers are `{plan}-T{n}`, numbering tasks in the order they appear
in each `03-0N-PLAN.md` `<tasks>` block. Every row below is claimed by at least one task.

| Req ID | Behavior | Threat Ref | Test Type | Automated Command | Claimed by | File Exists |
|--------|----------|------------|-----------|-------------------|------------|-------------|
| INP-01…INP-07 | `ProductionSpec` accepts every valid combination and rejects invalid ones: missing required field, both-or-neither of `crew_size`/`crew_tier`, imported > total, unknown extra field | T-03-02 (silent coercion) | unit + schema | `uv run pytest tests/test_engine_spec.py -x` | **03-02-T2** (field contract frozen by **03-02-T1**) | ❌ W0 |
| INP-08 | Two distinct layers: structurally, an extra field 422s; visibly, a non-empty **Total budget** field returns the friendly circularity explanation — not a generic validation error | T-03-02 | unit + integration | `uv run pytest tests/test_app_spec_route.py::test_budget_field_always_refused -x` | **03-02-T3** (service refusal + `extra="forbid"`), **03-02-T4** (the visible field and the on-screen message) | ❌ W0 |
| JUR-01 (success criterion 3) | Anora reproduces **$991,190** against **$3,964,760** of qualified spend, exact `Decimal` equality, through both the JSON route and the HTML route, with the NY ESD source link rendered beside the figure | T-03-01 (path traversal via `pair_id`) | golden-value + integration | `uv run pytest tests/test_app_validate_route.py::test_anora_reproduces_exactly_via_route -x` | **03-01-T2** (tracer: JSON + HTML routes, allowlist), **03-01-T3** (form selector path) | ❌ W0 |
| SHP-14 | Suite green unmutated; a non-zero count of NY exact-mode assertions is collected; red under a declared one-basis-point mutation of `us-ny.yaml`'s `base_rate`; red **for the right reason**; green again once restored | T-03-08, T-03-09 | CI job (bash + pytest), not itself a pytest test | `.github/scripts/mutation-check.sh` | **03-03-T1** (table + five-step script), **03-03-T2** (the blocking CI job) | ❌ W0 |
| (success criterion 1) | A full spec round-trips: submitted → echoed back normalized, including a `crew_tier` resolved to a headcount range | — | unit + integration | `uv run pytest tests/test_app_spec_route.py::test_spec_echoes_normalized_input -x` | **03-02-T3** (service echo + tier resolution), **03-02-T4** (form and result page) | ❌ W0 |
| (D-40, success criterion 1 adjacent) | An uncurated city name is accepted and marked `no curated model` — never rejected, never silently substituted, never offered a fuzzy suggestion | — | unit | `uv run pytest tests/test_app_spec_route.py::test_uncurated_city_never_suggested -x` | **03-02-T3** | ❌ W0 |
| (Phase 2 contract, non-regression) | `Figure` serialization crosses the HTTP boundary as `Decimal`→`str`, never `float` — the JSON response must not reintroduce Phase 2's precision bug | — | unit + property | `uv run pytest tests/test_app_validate_route.py -x` | **03-01-T2** | ❌ W0 |

*Status legend for the populated per-task table: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Task index

| Task ID | Plan | Task | Type |
|---------|------|------|------|
| 03-01-T1 | `03-01-PLAN.md` | Package legitimacy gate — jinja2 and python-multipart | `checkpoint:human-verify` (blocking-human) |
| 03-01-T2 | `03-01-PLAN.md` | End-to-end "Anora reproduces $991,190" — one path only | `tracer` (tdd) |
| 03-01-T3 | `03-01-PLAN.md` | The pair selector, the landing page, and the honest unselectable list | `auto` |
| 03-02-T1 | `03-02-PLAN.md` | Decision — freeze the `ProductionSpec` field contract (INP-01 "and scale") | `checkpoint:decision` (blocking) |
| 03-02-T2 | `03-02-PLAN.md` | `engine/spec.py` — the `ProductionSpec` contract and the crew-tier table | `auto` (tdd) |
| 03-02-T3 | `03-02-PLAN.md` | The Route A service — budget refusal, per-city status, and New York's rule terms | `auto` (tdd) |
| 03-02-T4 | `03-02-PLAN.md` | The spec form, the visible budget refusal on screen, and the result page | `auto` |
| 03-03-T1 | `03-03-PLAN.md` | The declared mutation table and the five-step non-vacuity gate | `auto` |
| 03-03-T2 | `03-03-PLAN.md` | Wire `mutation-check` into CI as a sixth blocking job | `auto` |

### Measured fact that changes the SHP-14 assertion

`tests/fixtures/validation_pairs/` was read directly at plan time: **Anora is the only New York
pair with `assertion.mode: exact`.** `ny_succession_s4.yaml` is `bounded` with `tolerance_bps: 10`
(corrected in plan 02-01) and `ny_gilded_age_s2.yaml` is `bounded` with `tolerance_bps: 150`.
`03-RESEARCH.md` Pattern 4's illustrative step-2 check counts items matching a loose `-k "ny"`
filter, which would also count bounded-mode items that cannot anchor an exact-equality claim.
`03-03-T1` replaces it with two precise assertions: a count of **active, exact-mode, New York**
fixtures, and a `--collect-only` count against the declared `expected_red_test` node id
(`tests/test_engine_against_validation_pairs.py::test_anora_reproduces_exactly_through_price_jurisdiction`).

---

## Wave 0 Requirements

Every Wave 0 gap below is owned by a named task; none is left to be discovered at execution time.

- [ ] `engine/figure_serialize.py` — does not exist yet → **03-01-T2**
- [ ] `engine/spec.py` — does not exist yet → **03-02-T2**
- [ ] `app/services/__init__.py`, `app/services/validate.py`, `app/routers/__init__.py`,
      `app/routers/validate.py`, `app/templates/base.html`, `app/templates/validate_result.html`
      — none exist yet (only `app/main.py` exists, a single-file skeleton) → **03-01-T2**
- [ ] `app/templates/index.html`, `app/templates/validate_form.html` → **03-01-T3**
- [ ] `app/services/city_lookup.py`, `app/services/spec.py` → **03-02-T3**
- [ ] `app/routers/spec.py`, `app/templates/spec_form.html`, `app/templates/spec_result.html`
      → **03-02-T4**
- [ ] `data/crew_tiers.yaml` — new top-level directory and file → **03-02-T2**
- [ ] `.github/scripts/mutation-check.sh`, `tests/mutation_targets.yaml` — new → **03-03-T1**
- [ ] `tests/test_app_validate_route.py` — does not exist yet → **03-01-T2** (extended by 03-01-T3)
- [ ] `tests/test_engine_spec.py` — does not exist yet → **03-02-T2**
- [ ] `tests/test_app_spec_route.py` — does not exist yet → **03-02-T3** (extended by 03-02-T4)
- [ ] `jinja2`, `python-multipart` — not yet in `pyproject.toml` / `uv.lock` → **03-01-T2**, gated
      by **03-01-T1**. **`python-multipart` is required for any HTML `<form>` POST, not only file
      uploads** — Starlette's form parser raises at request time without it. Both packages returned
      `SUS` from the package-legitimacy gate on an `unknown-downloads` signal only; both repo URLs
      were confirmed against the Pallets and Kludex (current Starlette/FastAPI maintainer)
      organizations, so the `checkpoint:human-verify` at 03-01-T1 is a formality rather than an open
      question — but a `[SUS]` verdict is never auto-approvable, so it still blocks.

*No gap in shared test infrastructure: `testpaths = ["tests"]` already collects any new file under
`tests/`, and `.github/workflows/ci.yml`'s existing `tests` job already runs `pytest tests/`. Only the
new `mutation-check` job needs adding.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
`workflow.human_verify_mode` is `end-of-phase`, so each row below is carried as a
`<verify><human-check>` block on the owning task rather than as a mid-flight
`checkpoint:human-verify`; the verifier harvests them into `03-UAT.md` in one batch at end of phase.

| Behavior | Requirement | Carried by | Why Manual | Test Instructions |
|----------|-------------|------------|------------|-------------------|
| The hosted URL actually serves the Anora result to an anonymous visitor | Success criterion 3 / SHP-14 deploy path | **03-01-T3** `<human-check>` | The pytest suite exercises the app in-process via TestClient; "an anonymous visitor at the public URL sees it" is a property of the **deployment**, not of the runtime under test | From a logged-out browser (or `curl` with no cookies/headers) on a different network than the development machine, load `https://vockell.com/finance/`, follow "Reproduce a disclosure", submit with Anora selected, and confirm the page shows `$991,190` against `$3,964,760` with a working link to the NY ESD source document. Confirm every other path on the host is unchanged. |
| The budget refusal and the cited rule terms render for an anonymous visitor | INP-08 / D-37 | **03-02-T4** `<human-check>` | The readability of the refusal — "refused **with an explanation**" — is the requirement, and readability is not assertable by a status-code test | Load `https://vockell.com/finance/spec`, type a number into **Total budget**, submit, and confirm the circularity explanation is legible prose rather than a generic error. Clear it, resubmit, and confirm the echoed spec, New York's cited rule terms, an uncurated city with no suggested alternative, and the explicit not-yet-derived statement — with no spec-derived dollar figure anywhere. |
| The mutation gate is non-vacuous | SHP-14 | **03-03-T2** `<human-check>` | A CI job that always passes looks identical to one that works; only observing the deliberate red proves it | Run `.github/scripts/mutation-check.sh` locally and read the output, not just the exit code: confirm a non-zero NY exact-mode collected count, then that the mutated suite failed `test_anora_reproduces_exactly_through_price_jurisdiction` by name (right reason, not an unrelated collection error), then green after restore. Then open the GitHub Actions run and confirm `mutation-check (SHP-14)` is a sixth job whose log shows the deliberate red. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
