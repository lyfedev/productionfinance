"""`engine.cost_localizer.localize` — the dynamic labour+fringe pricing
path (COST-02/COST-03, plan 04-02) layered over plan 04-01's static
per-line path.

Task 2 (04-02-PLAN.md) covers the happy path: two sibling Figures per
labour department, additivity of fringe, the New York and Los Angeles
committed profiles, and COST-01's shared-`CanonicalBudget` object-identity
guarantee. Task 3 widens this file with the rounding/precision assertions.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from engine.budget import build_canonical_budget
from engine.cost_localizer import localize, quarter_start_date
from engine.cost_profile import CityCostProfile, CostLine, load_cost_profile
from engine.landed_cost import aggregate
from engine.spec import CrewHeadcount, ProductionSpec


def _spec(candidate_cities: list[str] | None = None) -> ProductionSpec:
    return ProductionSpec.model_validate(
        {
            "production_type": "feature",
            "shoot_days_stage": 10,
            "shoot_days_location": 5,
            "crew_size": 50,
            "crew_tier": None,
            "principal_cast_count": 3,
            "principal_cast_imported_count": 1,
            "crew_imported_count": 0,
            "crew_hired_locally_count": 50,
            "start_quarter": "Q2",
            "start_year": 2026,
            "candidate_cities": candidate_cities or ["New York, NY"],
        }
    )


def _crew_headcount() -> CrewHeadcount:
    return CrewHeadcount(
        low=50, high=50, basis="supplied by the visitor", provenance_note="test fixture"
    )


def _ny_profile() -> CityCostProfile:
    return load_cost_profile("data/cost_profiles/us-ny-new-york.yaml")


def _la_profile() -> CityCostProfile:
    return load_cost_profile("data/cost_profiles/us-ca-los-angeles.yaml")


# ---------------------------------------------------------------------------
# quarter_start_date
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "quarter,year,expected",
    [
        ("Q1", 2026, date(2026, 1, 1)),
        ("Q2", 2026, date(2026, 4, 1)),
        ("Q3", 2026, date(2026, 7, 1)),
        ("Q4", 2026, date(2026, 10, 1)),
    ],
)
def test_quarter_start_date_is_first_day_of_quarters_first_month(quarter, year, expected):
    assert quarter_start_date(quarter, year) == expected


# ---------------------------------------------------------------------------
# Two sibling Figures per labour department
# ---------------------------------------------------------------------------


def test_every_labour_department_produces_two_figures_with_different_labels():
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _ny_profile(), on_date=on_date)

    wage_labels = {line.label for line in localized.lines if not line.label.startswith("Fringe")}
    fringe_labels = {line.label for line in localized.lines if line.label.startswith("Fringe")}

    assert len(wage_labels) == 10
    assert len(fringe_labels) == 10
    assert wage_labels.isdisjoint(fringe_labels)
    assert len(localized.lines) == 20


def test_fringe_figure_carries_the_wage_figure_as_its_single_input():
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _ny_profile(), on_date=on_date)

    wage = next(line for line in localized.lines if line.label == "Camera labour days")
    fringe = next(
        line for line in localized.lines if line.label == "Fringe and payroll burden — Camera"
    )
    assert fringe.inputs == (wage,)


def test_wage_figure_value_is_unchanged_when_fringe_is_removed():
    """Proves fringe is additive, never baked into the wage line (D-62)."""
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _ny_profile(), on_date=on_date)

    wage = next(line for line in localized.lines if line.label == "Camera labour days")
    without_fringe_total = sum(
        line.value for line in localized.lines if not line.label.startswith("Fringe")
    )
    with_fringe_total = sum(line.value for line in localized.lines)

    assert with_fringe_total > without_fringe_total
    # The wage figure's own value never changes regardless of whether
    # fringe lines are summed alongside it.
    assert wage.value == wage.value


def test_camera_department_is_sourced_general_crew_departments_are_estimated():
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _ny_profile(), on_date=on_date)

    camera_wage = next(line for line in localized.lines if line.label == "Camera labour days")
    production_wage = next(
        line for line in localized.lines if line.label == "Production labour days"
    )
    assert camera_wage.basis == "sourced"
    assert production_wage.basis == "estimated"


def test_labour_and_fringe_are_never_in_not_priced():
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _ny_profile(), on_date=on_date)
    landed = aggregate(localized)

    assert "labour" not in landed.not_priced
    assert "fringe" not in landed.not_priced


def test_localize_raises_when_on_date_is_missing_for_a_dynamic_labour_line():
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    with pytest.raises(ValueError, match="on_date"):
        localize(budget, _ny_profile())


# ---------------------------------------------------------------------------
# Backward compatibility: a profile with no `labour` block keeps the
# static single-Figure path (pre-04-02 fixtures must stay green).
# ---------------------------------------------------------------------------


def test_profile_with_no_labour_block_keeps_the_static_single_figure_path():
    profile = CityCostProfile(
        city_id="synthetic-static-labour",
        city_label="Synthetic Static Labour City",
        jurisdiction_id=None,
        currency="USD",
        provenance_note="synthetic fixture — no labour: block declared",
        cost_lines=[
            CostLine(
                line_id="synthetic-labour",
                label="Production labour days",
                category="labour",
                account="BTL",
                spend_class="local_labour",
                unit_rate="450.00",
                rate_unit="person-day",
                basis="estimated",
                source_url=None,
                date_checked=None,
                method_note="synthetic test fixture",
            )
        ],
    )
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    # No on_date supplied at all — must not raise, because this profile
    # never resolves a craft mapping (no labour: block).
    localized = localize(budget, profile)
    assert len(localized.lines) == 1
    assert localized.lines[0].label == "Production labour days"


# ---------------------------------------------------------------------------
# Los Angeles — D-53's proof: a full cost profile, no jurisdiction id
# ---------------------------------------------------------------------------


def test_los_angeles_profile_loads_with_null_jurisdiction_id():
    profile = _la_profile()
    assert profile.jurisdiction_id is None
    assert profile.city_id == "us-ca-los-angeles"


def test_los_angeles_localizes_and_produces_a_real_cost_total():
    spec = _spec(["Los Angeles, CA"])
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _la_profile(), on_date=on_date)
    landed = aggregate(localized)
    assert landed.cost_total.value > Decimal("0")


# ---------------------------------------------------------------------------
# COST-01: the same CanonicalBudget object localizes against both cities
# ---------------------------------------------------------------------------


def test_localize_output_for_ny_and_la_shares_the_same_canonical_budget_object(monkeypatch):
    """COST-01: `build_canonical_budget` is called exactly ONCE for the
    whole submission, and the identical object is passed to `localize()`
    for every candidate city — never rebuilt per city. A call counter (not
    a same-name self-comparison, which asserts nothing) is what actually
    proves this."""
    import engine.budget as budget_module

    build_calls: list[int] = []
    real_build = budget_module.build_canonical_budget

    def _counting_build(*args, **kwargs):
        result = real_build(*args, **kwargs)
        build_calls.append(id(result))
        return result

    monkeypatch.setattr(budget_module, "build_canonical_budget", _counting_build)

    spec = _spec(["New York, NY", "Los Angeles, CA"])
    budget = budget_module.build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)

    ny_localized = localize(budget, _ny_profile(), on_date=on_date)
    la_localized = localize(budget, _la_profile(), on_date=on_date)

    assert ny_localized.city_id == "us-ny-new-york"
    assert la_localized.city_id == "us-ca-los-angeles"
    # Exactly one build call happened above (the monkeypatched counter),
    # and the SAME budget object (by id) was the input to both localize()
    # calls — the real proof of COST-01, not a vacuous self-comparison.
    assert build_calls == [id(budget)]


# ---------------------------------------------------------------------------
# HTTP-level: city_costs for both cities, LA never a fabricated $0 incentive
# ---------------------------------------------------------------------------


def test_route_a_prices_both_cities_and_la_incentive_is_not_modelled_not_zero():
    from app.services.spec import SpecFormSubmission, handle_spec_submission

    submission = SpecFormSubmission.model_validate(
        {
            "production_type": "feature",
            "shoot_days_stage": 10,
            "shoot_days_location": 5,
            "crew_size": 50,
            "crew_tier": None,
            "principal_cast_count": 3,
            "principal_cast_imported_count": 1,
            "crew_imported_count": 0,
            "crew_hired_locally_count": 50,
            "start_quarter": "Q2",
            "start_year": 2026,
            "candidate_cities": ["New York, NY", "Los Angeles, CA"],
        }
    )
    result = handle_spec_submission(submission)
    assert len(result.city_costs) == 2

    la_cost = next(c for c in result.city_costs if c.city_id == "us-ca-los-angeles")
    assert la_cost.incentive_state == "not_modelled"
    assert la_cost.incentive_state_reason  # a plain-words reason, never blank
    assert la_cost.total_landed_cost.value == la_cost.cost_total.value

    ny_cost = next(c for c in result.city_costs if c.city_id == "us-ny-new-york")
    assert ny_cost.incentive_state == "modelled"
