---
phase: 4
slug: cost-localization-landed-cost-outputs
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-26
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded by `/gsd-plan-phase 4` from `04-RESEARCH.md` § Validation Architecture.
> Task IDs are filled in by `/gsd-validate-phase` once PLAN.md files exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]`, `testpaths = ["tests"]` |
| **Quick run command** | `uv run pytest tests/<module-under-test>.py -q` |
| **Full suite command** | `uv run --frozen pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds (full suite; pure-Decimal engine, no network) |

---

## Sampling Rate

- **After every task commit:** Run the module's own test file — `uv run pytest tests/test_engine_<module>.py -q`
- **After every plan wave:** Run `uv run --frozen pytest tests/ -q` (the exact command already in the CI `tests` job)
- **Before `/gsd-verify-work`:** Full suite green, PLUS `tests/test_route_a_basis_walk.py` (D-63 basis gate) and `tests/test_golden_cost.py` (D-78 exact-total regression) both present and passing
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Task IDs are assigned by `/gsd-validate-phase` after plans exist. The requirement→test binding below is the contract each task must map onto.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | COST-01 | — | N/A | unit | `uv run pytest tests/test_engine_budget.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | COST-02 | — | N/A | unit | `uv run pytest tests/test_engine_cost_localizer.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | COST-03 | — | N/A | unit | `uv run pytest tests/test_engine_cost_localizer.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | COST-04 | — | Per-diem figure carries the D-61 ceiling caveat structurally, not as prose | unit | `uv run pytest tests/test_engine_seasonality.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | COST-05 | — | N/A | unit | `uv run pytest tests/test_engine_cost_localizer.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | COST-06 | — | Stage/equipment/permit/trucking lines never carry `basis: sourced` | unit | `uv run pytest tests/test_engine_cost_profile.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | COST-07 | — | N/A | integration | `uv run pytest tests/test_engine_seasonality.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | COST-08 | — | Missing FX pair raises rather than silently cross-rating | unit | `uv run pytest tests/test_engine_fx.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INC-10 | — | Tax exemptions reduce cost lines, never the credit figure | unit | `uv run pytest tests/test_engine_cost_localizer.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | OUT-01 | — | Unranked cities never render as `$0` | unit | `uv run pytest tests/test_engine_ranker.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | OUT-02 | — | N/A | integration (golden) | `uv run pytest tests/test_golden_cost.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | OUT-03 | — | No prescriptive vocabulary in sensitivity output (string-scan assertion) | unit + string-scan | `uv run pytest tests/test_engine_sensitivity.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | OUT-04 | — | N/A | unit | `uv run pytest tests/test_engine_landed_cost.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-63 (CI gate) | — | No `Figure` reachable from a Route A total carries `confidence: "validated"` | integration | `uv run pytest tests/test_route_a_basis_walk.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-72 (guard) | — | A validation-pair fixture is never routed through `BudgetModelBuilder` | integration | `uv run pytest tests/test_engine_against_validation_pairs.py -q` | ✅ extend existing | ⬜ pending |
| TBD | TBD | TBD | D-78 (golden) | — | N/A | golden/regression | `uv run pytest tests/test_golden_cost.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_engine_budget.py` — stubs for COST-01
- [ ] `tests/test_engine_cost_localizer.py` — stubs for COST-02, COST-03, COST-05, COST-06, INC-10
- [ ] `tests/test_engine_cost_profile.py` — schema-load test for `CityCostProfile`, mirroring the existing `engine/models.py::load_ruleset` test pattern
- [ ] `tests/test_engine_seasonality.py` — stubs for COST-04, COST-07, including the NY-seasonal / LA-flat per-diem branch
- [ ] `tests/test_engine_fx.py` — stubs for COST-08, including the missing-pair refusal path
- [ ] `tests/test_engine_landed_cost.py` — aggregation stage, OUT-04
- [ ] `tests/test_engine_ranker.py` — stubs for OUT-01, the two-band split, the never-`$0` guarantee
- [ ] `tests/test_engine_gap.py` — stubs for OUT-02, currency as its own gap component (D-75)
- [ ] `tests/test_engine_sensitivity.py` — stubs for OUT-03, including the vocabulary-grep assertion (D-70)
- [ ] `tests/test_golden_cost.py` — D-78 fixed-input exact-total regression test
- [ ] `tests/test_route_a_basis_walk.py` — D-63 CI gate, walking `figure_to_dict`'s recursive `inputs` output
- [ ] `tests/fixtures/cost_profiles/*.yaml` — synthetic cost profiles mirroring the existing `tests/fixtures/jurisdictions/synthetic-*.yaml` convention
- [ ] Framework install: none required — pytest 9.1.1 already installed and wired into CI

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sourced per-diem / union-rate dollar figures match the government or union primary document | COST-02, COST-03, COST-04 | Correctness of a committed YAML figure against an external published document cannot be asserted by the engine's own tests — the test can only prove the engine consumed the YAML faithfully | For each figure tagged `basis: sourced`, open its cited `source_url` and confirm the value and `date_checked` match. Any figure that cannot be confirmed must be downgraded from `sourced` before the phase is signed off. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
