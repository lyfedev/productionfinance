---
phase: 2
slug: engine-spine-incentive-interpreter
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-25
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `02-RESEARCH.md` § Validation Architecture. Seeded at plan time; the
> Per-Task Verification Map is populated once PLAN.md task IDs exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 — already installed and green in this repo (Phase 1 shipped 35 passing tests) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` already present (pyproject.toml:20-21) |
| **Quick run command** | `uv run pytest tests/test_engine_*.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~5-10 seconds (pure `Decimal` arithmetic over YAML fixtures; no network, no host access) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_engine_*.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -q` — the full suite, including Phase 1's
  existing 35 tests. **Phase 2 must not regress them.**
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds
- **Per commit (CI, blocking):** Phase 1's `.github/workflows/ci.yml` already runs `pytest tests/`
  as a required status check — no CI change is needed for Phase 2's new test files, because
  `testpaths = ["tests"]` picks up any new file under `tests/` automatically.

---

## Per-Task Verification Map

Populated at plan time (2026-08-25). Every requirement-level row below is attached to at
least one plan task. Plan and task identifiers refer to `02-0N-PLAN.md` task numbers.

| Req ID | Plan / Task | Automated command |
|--------|-------------|-------------------|
| INC-01 | 02-01 T1 (tracer, `total_qualified_spend` end to end) · 02-03 T1 (all four types + escape hatch) | `uv run pytest tests/test_engine_qualifying_base.py::test_base_definition_types -x` |
| INC-02 | 02-05 T1 | `uv run pytest tests/test_engine_credit.py::test_per_person_ceiling_w2_vs_loanout -x` |
| INC-03 | 02-05 T2 (cliff vs blend dispatch) · 02-06 T1 (stacking, uplift order) | `uv run pytest tests/test_engine_credit.py::test_tier_dispatch_and_stacking -x` and `::test_stacking_prices_every_declared_programme -x` |
| INC-04 | 02-06 T2 | `uv run pytest tests/test_engine_credit.py::test_cap_boundaries -x` |
| INC-05 | 02-06 T2 | `uv run pytest tests/test_engine_credit.py::test_availability_separate_from_eligibility -x` |
| INC-06 | 02-01 T1 (`refundable` on the tracer path) · 02-04 T1 (remaining three + audit fee cliffs) | `uv run pytest tests/test_engine_net_cash.py::test_mechanism_conversions -x` |
| INC-07 | 02-04 T1 (corporation tax) · 02-04 T2 (UK golden value) | `uv run pytest tests/test_engine_net_cash.py::test_taxable_mechanism_uk_worked_example -x` |
| INC-08 | 02-04 T1 | `uv run pytest tests/test_engine_net_cash.py::test_arrival_timing_present -x` |
| INC-09 | 02-03 T2 | `uv run pytest tests/test_engine_qualifying_base.py::test_minimum_spend_cliff -x` |
| JUR-05 | 02-06 T3 | `uv run pytest tests/test_engine_jurisdiction_additivity.py -x` plus the recorded diff check |
| PRV-01 | 02-01 T1 (contract) · 02-02 T2 (property assertions) | `uv run pytest tests/test_engine_figure_provenance.py::test_every_figure_has_source_or_explicit_null -x` |
| PRV-02 | 02-01 T1 (closed enum) · 02-02 T2 (assertions) | `uv run pytest tests/test_engine_figure_provenance.py::test_confidence_is_closed_enum -x` |
| PRV-03 | 02-01 T1 (never-silent derivation) · 02-02 T2 (assertions) | `uv run pytest tests/test_engine_figure_provenance.py::test_derivation_never_empty_including_noops -x` |
| Rounding contract | 02-02 T1 | `uv run pytest tests/test_engine_rounding.py -x` |
| Decimal typing + fail-loud schema + 3 security gates | 02-02 T1 | `uv run pytest tests/test_engine_models.py -x` |
| D-02 interpreter proof (NY + CT) | 02-01 T1 (New York) · 02-05 T3 (Connecticut) | `uv run pytest tests/test_engine_against_validation_pairs.py -x` |
| Scope-freeze note | 02-01 T2 | `test -f jurisdictions/SCOPE-FREEZE.md` plus the human check in 02-06 T3 |

| Req ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|-------------------|-------------|
| INC-01 | Four base-definition types each compute a distinct qualifying base from the same input budget | unit | `uv run pytest tests/test_engine_qualifying_base.py::test_base_definition_types -x` | ❌ W0 |
| INC-02 | Per-person ceiling: W-2 capped at boundary−1/boundary/boundary+1; loan-out uncapped but withholding applied; verified against the GA worked example ($10M/$2M lead → $8.5M base → $2.55M credit) | unit + boundary | `uv run pytest tests/test_engine_credit.py::test_per_person_ceiling_w2_vs_loanout -x` | ❌ W0 |
| INC-03 | Tier/uplift ordering is read from data (swap declared order in a synthetic fixture, assert output changes); `tiered_by_spend` vs `blended_by_ceiling_split` produce different, individually-correct results; national+regional stacking sums independent dollar outputs, never percentages | unit + golden-value | `uv run pytest tests/test_engine_credit.py::test_tier_dispatch_and_stacking -x` | ❌ W0 |
| INC-04 | Per-project and annual caps clip at boundary−1/boundary/boundary+1 | boundary | `uv run pytest tests/test_engine_credit.py::test_cap_boundaries -x` | ❌ W0 |
| INC-05 | Eligible-but-cap-exhausted production reports `eligible=True, available=False` as two independent fields | unit | `uv run pytest tests/test_engine_credit.py::test_availability_separate_from_eligibility -x` | ❌ W0 |
| INC-06 | Each of 4 mechanisms (refundable / transferable / rebate_grant / nonrefundable_credit) nets audit fee correctly at fee-tier boundaries ($5M / $10M cliffs) | unit + boundary | `uv run pytest tests/test_engine_net_cash.py::test_mechanism_conversions -x` | ❌ W0 |
| INC-07 | Taxable mechanism nets corporation tax; golden-value regression against the £18M UK worked example (£7.176M gross → ~£5.38M net) | golden-value | `uv run pytest tests/test_engine_net_cash.py::test_taxable_mechanism_uk_worked_example -x` | ❌ W0 |
| INC-08 | `ArrivalTiming` present alongside `NetCash` for every mechanism; displayed, not discounted (per the stated scope cut) | unit | `uv run pytest tests/test_engine_net_cash.py::test_arrival_timing_present -x` | ❌ W0 |
| INC-09 | Minimum-spend cliff: threshold−$1 / threshold / threshold+$1 produce $0 / full-rate / full-rate, never a ramp | boundary | `uv run pytest tests/test_engine_qualifying_base.py::test_minimum_spend_cliff -x` | ❌ W0 |
| JUR-05 | A throwaway jurisdiction YAML is added with **zero diffs to any `engine/*.py` file** — verified structurally, not just by YAML validity | structural + unit | `uv run pytest tests/test_engine_jurisdiction_additivity.py -x` plus the documented check `git diff --name-only <fixture-commit> \| grep -c '^engine/'` == 0 | ❌ W0 |
| PRV-01 | Every `Figure` in a computed tree carries `source_url` and `date_checked`, or an explicit documented null | property | `uv run pytest tests/test_engine_figure_provenance.py::test_every_figure_has_source_or_explicit_null -x` | ❌ W0 |
| PRV-02 | `Figure.confidence` is always exactly `"validated"` or `"researched"` — no third value, no default | schema | `uv run pytest tests/test_engine_figure_provenance.py::test_confidence_is_closed_enum -x` | ❌ W0 |
| PRV-03 | Every adjustment step appends a non-empty derivation line, including no-op steps | property | `uv run pytest tests/test_engine_figure_provenance.py::test_derivation_never_empty_including_noops -x` | ❌ W0 |
| D-02 (interpreter proof) | NY rule file reproduces Anora ($991,190 **exact**), Gilded Age S2 (bounded, 150bps), and Succession S4 (**bounded, corrected at plan time — see the note below**); CT rule file reproduces Christmas Always ($1,159,502 exact) | golden-value, imports Phase 1's committed validation-pair fixtures | `uv run pytest tests/test_engine_against_validation_pairs.py -x` | ❌ W0 |

> **Correction, 2026-08-25 (plan time).** This row previously claimed Succession S4
> reproduces `$25,747,913` **exactly**. Checked against the committed fixture, that is
> false under a flat 25% New York model: `$102,920,384 × 0.25 = $25,730,096`, a residue of
> `$17,817` — an implied rate of 25.0173%, not 25.0000%. It is the same class of
> un-itemised uplift `ny_gilded_age_s2.yaml` already concedes, 75× smaller. Plan 02-01
> Task 1 resolves this visibly: either a newly cited modelled rule explains the residue and
> the fixture stays `exact`, or `ny_succession_s4.yaml`'s assertion is amended to `bounded`
> with `tolerance_bps` at most `10` and a written `variance_reason` stating the measured
> residue. Widening a tolerance without a written reason is forbidden by the plan's own
> prohibitions. **Anora remains the phase's one clean exact-mode New York anchor;
> Christmas Always is the second exact anchor, in Connecticut.**

*Status legend for the populated per-task table: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `engine/__init__.py`, `engine/models.py`, `engine/figure.py`, `engine/rounding.py`,
      `engine/qualifying_base.py`, `engine/credit.py`, `engine/net_cash.py`,
      `engine/handlers/__init__.py` — no engine code exists yet (confirmed: `find . -iname "*engine*"`
      returns only this phase's planning directory)
- [ ] `jurisdictions/us-ny.yaml`, `jurisdictions/us-ct.yaml` — real curated rule files, do not exist yet
- [ ] `tests/fixtures/jurisdictions/` — new directory for throwaway/synthetic fixtures used by the
      boundary tests and the JUR-05 additivity proof
- [ ] `tests/test_engine_*.py` — the 8 files named in the map above; none exist yet
- [ ] `pydantic` promoted to an explicit dependency line in `pyproject.toml` (currently transitive-only
      via FastAPI)

*No gap in shared test infrastructure or CI config: `testpaths = ["tests"]` already collects any new
file under `tests/`, and Phase 1's CI workflow already runs `pytest tests/` as a required job.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Zero engine-code diff when adding a jurisdiction | JUR-05 | The *automated* half (`test_engine_jurisdiction_additivity.py`) proves a new rule file prices correctly, but "no engine code changed" is a property of the **commit**, not of the runtime — a test cannot observe its own diff | After committing only the throwaway fixture jurisdiction YAML, run `git diff --name-only HEAD~1 HEAD \| grep '^engine/'` and confirm it returns nothing |
| Dated scope-freeze note exists and lists the fixed rule-dimension set | ROADMAP scope discipline | It is a written artifact/judgement, not a behavior | Confirm the note exists, is dated, and enumerates every modelled rule dimension; anything not on the list is out of scope for Phase 2 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
