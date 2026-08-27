"""OUT-03 — `engine/sensitivity.py`'s declared step table, its real-pipeline
perturbation engine (D-67/D-68), cliff-crossing detection (D-69) and the
descriptive-language gate (D-70).

**D-70 non-vacuity proof (performed once, by hand, and reverted):** to
prove `test_d70_vocabulary_gate_is_non_vacuous_over_committed_cities_and_step_table`
is not vacuously green, `engine/sensitivity.py::_step_text` was temporarily
edited to append the phrase " — we recommend this" to every returned step
text, and this test was re-run in isolation. Observed result: RED, with
every one of the seven committed step rows' `step_text` correctly flagged,
e.g.:

    AssertionError: prescriptive vocabulary found in an emitted sensitivity
    string: [('recommend', '+1 stage shoot day — shoot_days_stage increased
    by 1 (10 -> 11); no other field adjusted — we recommend this'),
    ('recommend', "+1 crew member — crew_size increased by 1 (50 -> 51);
    the increment is applied to LOCALLY-HIRED crew (40 -> 41), not imported
    crew — this row's own declared choice — we recommend this"), ...] —
    D-70 forbids prescriptive vocabulary in any sensitivity output string

The edit was reverted immediately afterward (confirmed green again via a
full `tests/test_engine_sensitivity.py` re-run, 17 passed); the assertion
below is the permanent, always-green version guarding the reverted
(correct) code path.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import engine.sensitivity as sensitivity
from engine.budget import build_canonical_budget
from engine.cost_localizer import localize, quarter_start_date
from engine.cost_profile import COST_PROFILES_DIR, load_cost_profile
from engine.gap import decompose_gap
from engine.models import (
    Audit,
    BaseDefinition,
    Caps,
    EffectiveDates,
    Jurisdiction,
    JurisdictionRuleSet,
    PayoutLag,
    PerPersonCeiling,
    Programme,
    RateStructure,
    Source,
    Tier,
    Timing,
    TransferDiscount,
    Validation,
)
from engine.pipeline import price_jurisdiction
from engine.ranker import rank
from engine.sensitivity import (
    SENSITIVITY_STEPS_PATH,
    RegimeSignature,
    SensitivityStep,
    StepNotApplicable,
    load_sensitivity_steps,
    most_moving_row,
    sensitivity_rows,
)
from engine.spec import CrewHeadcount, ProductionSpec

_FIXTURE_COST_PROFILES_DIR = Path(__file__).resolve().parent / "fixtures" / "cost_profiles"


def _make_spec(**overrides: object) -> ProductionSpec:
    kwargs: dict[str, object] = {
        "production_type": "feature",
        "shoot_days_stage": 10,
        "shoot_days_location": 5,
        "crew_size": 50,
        "crew_tier": None,
        "principal_cast_count": 3,
        "principal_cast_imported_count": 1,
        "crew_imported_count": 10,
        "crew_hired_locally_count": 40,
        "start_quarter": "Q2",
        "start_year": 2026,
        "candidate_cities": ["placeholder"],
    }
    kwargs.update(overrides)
    return ProductionSpec.model_validate(kwargs)


def _write_steps_table(path: Path, rows: list[dict[str, str]]) -> None:
    lines = ["sensitivity_steps:"]
    for row in rows:
        lines.append(f"  - id: \"{row['id']}\"")
        lines.append(f"    spec_field: \"{row['spec_field']}\"")
        lines.append(f"    step: \"{row['step']}\"")
        lines.append(f"    unit_label: \"{row['unit_label']}\"")
        lines.append('    requirement: "OUT-03"')
        lines.append(f"    status: \"{row['status']}\"")
        lines.append("    why: \"test fixture row\"")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Task 1 — the declared step table and the perturbation engine
# ---------------------------------------------------------------------------


def test_committed_step_table_has_at_least_six_rows_with_required_fields():
    steps = load_sensitivity_steps()
    assert len(steps) >= 6
    for step in steps:
        assert isinstance(step, SensitivityStep)
        assert step.requirement == "OUT-03"
        assert step.status in ("active", "inactive")
        assert step.why.strip()


def test_committed_step_table_path_exists_and_is_module_anchored():
    assert SENSITIVITY_STEPS_PATH.exists()
    assert SENSITIVITY_STEPS_PATH.is_absolute()


def test_adding_an_inactive_row_changes_nothing(tmp_path, monkeypatch):
    steps_path = tmp_path / "sensitivity_steps.yaml"
    _write_steps_table(
        steps_path,
        [
            {
                "id": "stage-shoot-day",
                "spec_field": "shoot_days_stage",
                "step": "1",
                "unit_label": "stage shoot day",
                "status": "active",
            },
            {
                "id": "retired-row",
                "spec_field": "shoot_days_location",
                "step": "1",
                "unit_label": "location shoot day",
                "status": "inactive",
            },
        ],
    )
    monkeypatch.setattr(sensitivity, "SENSITIVITY_STEPS_PATH", steps_path)
    monkeypatch.setattr(sensitivity, "COST_PROFILES_DIR", _FIXTURE_COST_PROFILES_DIR)

    spec = _make_spec()
    rows = sensitivity_rows(spec, "synthetic-ranked", "synthetic-unranked", reporting_currency="USD")

    assert len(rows) == 1
    assert rows[0].spec_field == "shoot_days_stage"


def test_generic_step_application_needs_no_code_change_for_a_new_field(tmp_path, monkeypatch):
    """Proves the generic increment path: `start_year` is NOT one of the
    four disclosed special-case field names in `engine/sensitivity.py`,
    and is not coupled to any other field by a `ProductionSpec` validator
    (unlike `crew_imported_count`/`crew_hired_locally_count`, which are
    both tied to `crew_size`) — this row exercises the plain generic
    handler with zero code changes in that module."""
    steps_path = tmp_path / "sensitivity_steps.yaml"
    _write_steps_table(
        steps_path,
        [
            {
                "id": "new-generic-field",
                "spec_field": "start_year",
                "step": "1",
                "unit_label": "year",
                "status": "active",
            },
        ],
    )
    monkeypatch.setattr(sensitivity, "SENSITIVITY_STEPS_PATH", steps_path)
    monkeypatch.setattr(sensitivity, "COST_PROFILES_DIR", _FIXTURE_COST_PROFILES_DIR)

    spec = _make_spec()
    rows = sensitivity_rows(spec, "synthetic-ranked", "synthetic-unranked", reporting_currency="USD")

    assert len(rows) == 1
    assert rows[0].spec_field == "start_year"
    assert "start_year increased by 1" in rows[0].step_text


def test_an_unpriced_input_yields_zero_delta_with_a_non_empty_note(monkeypatch):
    """The committed `non-imported-principal-cast-member` row: total
    principal cast count feeds no cost line anywhere in the engine — only
    `principal_cast_imported_count` enters travel pricing."""
    monkeypatch.setattr(sensitivity, "COST_PROFILES_DIR", _FIXTURE_COST_PROFILES_DIR)
    spec = _make_spec()
    rows = sensitivity_rows(spec, "synthetic-ranked", "synthetic-unranked", reporting_currency="USD")

    row = next(r for r in rows if r.spec_field == "principal_cast_count")
    assert row.delta == Decimal("0")
    assert row.note
    assert "does not enter any priced line" in row.note


def test_a_row_that_genuinely_moves_the_gap_matches_an_independently_computed_value(monkeypatch):
    """Hand derivation (both fixture profiles price ONLY the "production"
    department, crew_share 0.10, at their own flat unit_rate):

    baseline: 50 * 0.10 * (10 + 5) = 75 person-days.
      city A (unit_rate 500.00): 75 x 500 = 37,500.
      city B (unit_rate  50.00): 75 x  50 =  3,750.
      baseline gap = 37,500 - 3,750 = 33,750.

    perturbed (+1 stage shoot day -> 16 total shoot days):
      75/15 x 16 = 80 person-days.
      city A: 80 x 500 = 40,000. city B: 80 x 50 = 4,000.
      perturbed gap = 40,000 - 4,000 = 36,000.

    delta = 36,000 - 33,750 = 2,250 -- computed independently of the
    engine, before this test was ever run against it.
    """
    monkeypatch.setattr(sensitivity, "COST_PROFILES_DIR", _FIXTURE_COST_PROFILES_DIR)
    spec = _make_spec()
    rows = sensitivity_rows(spec, "synthetic-ranked", "synthetic-unranked", reporting_currency="USD")

    row = next(r for r in rows if r.spec_field == "shoot_days_stage")
    assert row.baseline_gap == Decimal("33750")
    assert row.delta == Decimal("2250")
    assert row.direction == "widened"


def test_a_validator_violating_step_produces_a_row_with_a_reason_not_an_exception(monkeypatch):
    monkeypatch.setattr(sensitivity, "COST_PROFILES_DIR", _FIXTURE_COST_PROFILES_DIR)
    spec = _make_spec(crew_size=10, crew_imported_count=10, crew_hired_locally_count=0)

    rows = sensitivity_rows(spec, "synthetic-ranked", "synthetic-unranked", reporting_currency="USD")

    row = next(r for r in rows if r.spec_field == "crew_imported_count")
    assert row.delta == Decimal("0")
    assert row.note is not None
    assert "cannot be applied" in row.note


def test_rows_are_sorted_by_absolute_delta_descending(monkeypatch):
    monkeypatch.setattr(sensitivity, "COST_PROFILES_DIR", _FIXTURE_COST_PROFILES_DIR)
    spec = _make_spec()
    rows = sensitivity_rows(spec, "synthetic-ranked", "synthetic-unranked", reporting_currency="USD")

    deltas = [abs(row.delta) for row in rows]
    assert deltas == sorted(deltas, reverse=True)


def test_most_moving_row_returns_the_first_sorted_row(monkeypatch):
    monkeypatch.setattr(sensitivity, "COST_PROFILES_DIR", _FIXTURE_COST_PROFILES_DIR)
    spec = _make_spec()
    rows = sensitivity_rows(spec, "synthetic-ranked", "synthetic-unranked", reporting_currency="USD")

    assert most_moving_row(rows) is rows[0]


def test_most_moving_row_raises_on_empty_rows():
    try:
        most_moving_row(())
    except ValueError:
        pass
    else:
        raise AssertionError("expected most_moving_row(()) to raise ValueError")


_BANNED_SOURCE_PATTERN = re.compile(r"derivative|gradient|np\.|numpy")


def test_module_source_contains_no_derivative_or_gradient_terms():
    source = Path(sensitivity.__file__).read_text(encoding="utf-8")
    assert not _BANNED_SOURCE_PATTERN.search(source)


def test_no_hardcoded_jurisdiction_id_in_module_source():
    source = Path(sensitivity.__file__).read_text(encoding="utf-8")
    kept = "\n".join(line for line in source.splitlines() if not line.strip().startswith("#"))
    assert '"us-ny"' not in kept
    assert "'us-ny'" not in kept


# ---------------------------------------------------------------------------
# Task 2 — cliff-crossing detection and the descriptive-language gate
# ---------------------------------------------------------------------------


def test_crew_size_step_crossing_a_tier_boundary_names_both_tier_names(monkeypatch):
    """crew_size=60 sits exactly at the small/mid boundary (small: 30-60,
    mid: 60-120) -- `_infer_department_tier`'s tier-order scan returns
    "small" for 60 (checked first) and "mid" for 61. The +1 crew-size step
    crosses it."""
    monkeypatch.setattr(sensitivity, "COST_PROFILES_DIR", _FIXTURE_COST_PROFILES_DIR)
    spec = _make_spec(crew_size=60, crew_imported_count=10, crew_hired_locally_count=50)

    rows = sensitivity_rows(spec, "synthetic-ranked", "synthetic-unranked", reporting_currency="USD")
    row = next(r for r in rows if r.spec_field == "crew_size")

    assert row.cliff_crossings
    assert any("'small'" in c and "'mid'" in c for c in row.cliff_crossings)


def test_no_regime_change_produces_an_empty_cliff_crossings_tuple(monkeypatch):
    monkeypatch.setattr(sensitivity, "COST_PROFILES_DIR", _FIXTURE_COST_PROFILES_DIR)
    spec = _make_spec()
    rows = sensitivity_rows(spec, "synthetic-ranked", "synthetic-unranked", reporting_currency="USD")

    row = next(r for r in rows if r.spec_field == "shoot_days_location")
    assert row.cliff_crossings == ()


def _make_tiered_ruleset() -> JurisdictionRuleSet:
    """SYNTHETIC TEST FIXTURE — not a real jurisdiction, never committed
    to `jurisdictions/`. Two tiers crossing at spend=100,000, built
    directly as Pydantic objects (never a new committed YAML file) purely
    to prove `_regime_signature`/`_diff_regime_signatures` detect a
    tiered-rate-band crossing (D-69)."""
    jurisdiction = Jurisdiction(
        id="zz-sensitivity-test-tiered",
        name=(
            "SYNTHETIC TEST FIXTURE -- tiered band for cliff-crossing "
            "detection (never a real jurisdiction)"
        ),
        country_code="ZZ",
        level="national",
        parent_id=None,
        currency="USD",
        status="synthetic_fixture",
        effective_dates=EffectiveDates(
            rule_version_effective_from=date(2026, 1, 1),
            rule_version_effective_to=None,
            source_checked_date=date(2026, 8, 26),
        ),
        sources=[
            Source(
                url="https://example.invalid/synthetic-sensitivity-fixture",
                title=(
                    "Synthetic in-memory test fixture for "
                    "tests/test_engine_sensitivity.py -- not a real government source"
                ),
                accessed_date=date(2026, 8, 26),
                confidence="LOW",
            )
        ],
    )
    programme = Programme(
        id="zz-sensitivity-tiered-programme",
        name="Synthetic tiered-by-spend programme for cliff-crossing detection",
        mechanism="refundable",
        taxable=False,
        base_definition=BaseDefinition(type="total_qualified_spend"),
        per_person_ceiling=PerPersonCeiling(
            applies=False, note="not modelled by this synthetic fixture"
        ),
        rate_structure=RateStructure(
            type="tiered_by_spend",
            tiers=[
                Tier(threshold_low=Decimal("0"), threshold_high=Decimal("100000"), rate=Decimal("0.10")),
                Tier(threshold_low=Decimal("100000"), threshold_high=None, rate=Decimal("0.30")),
            ],
        ),
        minimum_spend=None,
        caps=Caps(),
        audit=Audit(mandatory=False, fee_schedule=[]),
        timing=Timing(
            terms_lock_at="application",
            payout_lag=PayoutLag(description="not modelled", typical_days=None, interest_paid=None),
        ),
        transfer_discount=TransferDiscount(applies=False),
        residency_rules=None,
        validation=Validation(validated=False),
    )
    return JurisdictionRuleSet(jurisdiction=jurisdiction, programmes=[programme])


def test_incentive_side_tiered_band_crossing_is_detected_via_synthetic_rule_file():
    ruleset = _make_tiered_ruleset()
    priced_low = price_jurisdiction(ruleset, Decimal("95000"), spend_confidence="researched")
    priced_high = price_jurisdiction(ruleset, Decimal("100000"), spend_confidence="researched")

    programme_low = priced_low.programmes[0].net_cash.point
    programme_high = priced_high.programmes[0].net_cash.point
    assert programme_low is not None and programme_high is not None

    spec = _make_spec()
    headcount = CrewHeadcount(
        low=50, high=50, basis="supplied by the visitor", provenance_note="test fixture"
    )
    budget = build_canonical_budget(spec, headcount)
    profile = load_cost_profile(_FIXTURE_COST_PROFILES_DIR / "synthetic-ranked.yaml")
    localized = localize(budget, profile)

    signature_low = sensitivity._regime_signature(spec, localized, (programme_low,))
    signature_high = sensitivity._regime_signature(spec, localized, (programme_high,))

    assert signature_low.rate_tier_band != signature_high.rate_tier_band

    crossings = sensitivity._diff_regime_signatures(
        signature_low, signature_high, city_id="synthetic-ranked"
    )
    assert any(
        "tiered-rate band" in crossing and "100000" in crossing for crossing in crossings
    )


def test_regime_signature_is_a_frozen_comparable_dataclass():
    a = RegimeSignature(
        crew_tier="small",
        rate_row_ids=(),
        per_diem_month_keys=(),
        minimum_spend_state=None,
        rate_tier_band=None,
        per_project_cap_state=None,
    )
    b = RegimeSignature(
        crew_tier="small",
        rate_row_ids=(),
        per_diem_month_keys=(),
        minimum_spend_state=None,
        rate_tier_band=None,
        per_project_cap_state=None,
    )
    assert a == b
    try:
        a.crew_tier = "mid"  # type: ignore[misc]
    except Exception:
        pass
    else:
        raise AssertionError("expected RegimeSignature to be frozen")


# ---------------------------------------------------------------------------
# D-70: the descriptive-language gate
# ---------------------------------------------------------------------------

# Sourced from 04-CONTEXT.md § D-70, plus the inherited-conventions phrasing
# ("you should", "consider", "recommend", "best", "optimal"). Defined ONCE
# here, matched case-insensitively on word boundaries so a substring inside
# an unrelated word never produces a false hit.
_PRESCRIPTIVE_VOCABULARY: tuple[str, ...] = (
    "recommend",
    "recommends",
    "recommended",
    "recommendation",
    "should",
    "consider",
    "considers",
    "considered",
    "considering",
    "best",
    "optimal",
    "you could",
    "you should",
)
_VOCABULARY_PATTERNS = {
    word: re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    for word in _PRESCRIPTIVE_VOCABULARY
}


def _collect_figure_lines(figure) -> set[str]:
    lines = set(figure.derivation)
    for child in figure.inputs:
        lines |= _collect_figure_lines(child)
    return lines


def _decompose_for(
    spec: ProductionSpec,
    profile_a,
    profile_b,
    ruleset_by_jurisdiction: dict,
    reporting_currency: str,
):
    headcount = sensitivity._resolve_crew_headcount(spec)
    budget = build_canonical_budget(spec, headcount)
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized_a = localize(budget, profile_a, on_date=on_date, spec=spec)
    localized_b = localize(budget, profile_b, on_date=on_date, spec=spec)
    ranked = rank(
        {profile_a.city_id: localized_a, profile_b.city_id: localized_b},
        ruleset_by_jurisdiction,
        reporting_currency=reporting_currency,
    )
    ranked_by_id = {city.city_id: city for city in ranked}
    return decompose_gap(
        profile_a.city_id,
        ranked_by_id[profile_a.city_id].landed_cost,
        profile_b.city_id,
        ranked_by_id[profile_b.city_id].landed_cost,
        reporting_currency=reporting_currency,
    )


def test_d70_vocabulary_gate_is_non_vacuous_over_committed_cities_and_step_table():
    """Scans every string `sensitivity_rows` emits (`step_text`,
    `direction`, `note`, `cliff_crossings`) PLUS every derivation line on
    every Figure the sensitivity path produces (the baseline and every
    active-step-perturbed New York vs Los Angeles gap decomposition),
    against the committed step table. See this module's own docstring for
    the recorded non-vacuity proof."""
    spec = _make_spec()
    city_a_id, city_b_id = "us-ny-new-york", "us-ca-los-angeles"
    reporting_currency = "USD"

    rows = sensitivity_rows(spec, city_a_id, city_b_id, reporting_currency=reporting_currency)

    collected: set[str] = set()
    for row in rows:
        collected.add(row.step_text)
        collected.add(row.direction)
        if row.note:
            collected.add(row.note)
        collected.update(row.cliff_crossings)

    profile_a = load_cost_profile(COST_PROFILES_DIR / f"{city_a_id}.yaml")
    profile_b = load_cost_profile(COST_PROFILES_DIR / f"{city_b_id}.yaml")
    ruleset_by_jurisdiction = sensitivity._load_jurisdiction_rulesets(profile_a, profile_b)

    baseline_decomposition = _decompose_for(
        spec, profile_a, profile_b, ruleset_by_jurisdiction, reporting_currency
    )
    collected |= _collect_figure_lines(baseline_decomposition.headline_gap)

    for step in load_sensitivity_steps():
        if step.status != "active":
            continue
        try:
            perturbed_spec, _note = sensitivity._apply_step(spec, step)
        except StepNotApplicable:
            continue
        decomposition = _decompose_for(
            perturbed_spec, profile_a, profile_b, ruleset_by_jurisdiction, reporting_currency
        )
        collected |= _collect_figure_lines(decomposition.headline_gap)

    assert collected, (
        "collected zero strings to scan -- the vocabulary gate would pass vacuously"
    )

    violations = [
        (word, text)
        for text in collected
        for word in _PRESCRIPTIVE_VOCABULARY
        if _VOCABULARY_PATTERNS[word].search(text)
    ]
    assert not violations, (
        f"prescriptive vocabulary found in an emitted sensitivity string: {violations} — "
        "D-70 forbids prescriptive vocabulary in any sensitivity output string"
    )
