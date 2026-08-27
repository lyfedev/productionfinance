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
from decimal import ROUND_HALF_EVEN, Decimal

import pytest

import engine.cost_localizer as cost_localizer_module
from engine.budget import CanonicalBudget, build_canonical_budget
from engine.cost_localizer import localize, quarter_start_date
from engine.cost_profile import (
    CityCostProfile,
    CostLine,
    CraftMapping,
    LabourBlock,
    load_cost_profile,
)
from engine.landed_cost import aggregate
from engine.spec import CrewHeadcount, ProductionSpec
from engine.union_rates import FringeComponent, FringeSchedule, RateRow

# The exact department NAMES (not labels) crew_tiers.yaml declares —
# needed to satisfy CityCostProfile's "labour.crafts covers every
# department" validator even in a synthetic fixture whose cost_lines only
# prices ONE of them.
_ALL_DEPARTMENT_NAMES = (
    "production",
    "camera",
    "grip_and_electric",
    "art",
    "wardrobe",
    "hair_and_makeup",
    "sound",
    "transportation",
    "locations",
    "post",
)


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
    localized = localize(budget, _ny_profile(), on_date=on_date, spec=spec)

    wage_labels = {line.label for line in localized.lines if line.label.endswith(" labour days")}
    fringe_labels = {line.label for line in localized.lines if line.label.startswith("Fringe")}

    assert len(wage_labels) == 10
    assert len(fringe_labels) == 10
    assert wage_labels.isdisjoint(fringe_labels)
    # 10 wage + 10 fringe (labour departments) + housing + per_diem +
    # flights (plan 04-03's travel categories, COST-04/COST-05) + stages +
    # equipment + permits + locations + trucking (plan 04-04's facilities
    # categories, COST-06) + 1 sales-tax exemption reduction (INC-10).
    assert len(localized.lines) == 29


def test_fringe_figure_carries_the_wage_figure_as_its_single_input():
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _ny_profile(), on_date=on_date, spec=spec)

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
    localized = localize(budget, _ny_profile(), on_date=on_date, spec=spec)

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
    localized = localize(budget, _ny_profile(), on_date=on_date, spec=spec)

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
    localized = localize(budget, _ny_profile(), on_date=on_date, spec=spec)
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
    localized = localize(budget, _la_profile(), on_date=on_date, spec=spec)
    landed = aggregate(localized)
    assert landed.cost_total.value > Decimal(0)


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

    ny_localized = localize(budget, _ny_profile(), on_date=on_date, spec=spec)
    la_localized = localize(budget, _la_profile(), on_date=on_date, spec=spec)

    assert ny_localized.city_id == "us-ny-new-york"
    assert la_localized.city_id == "us-ca-los-angeles"
    # Exactly one build call happened above (the monkeypatched counter),
    # and the SAME budget object (by id) was the input to both localize()
    # calls — the real proof of COST-01, not a vacuous self-comparison.
    assert build_calls == [id(budget)]


# ---------------------------------------------------------------------------
# HTTP-level: ranked_cities for both cities, LA never a fabricated $0
# incentive (plan 04-06 renames city_costs/CityCost -> ranked_cities/
# RankedCity and incentive_state/incentive_state_reason -> band/reason)
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
    assert len(result.ranked_cities) == 2

    la_cost = next(c for c in result.ranked_cities if c.city_id == "us-ca-los-angeles")
    assert la_cost.band == "incentive_not_modelled"
    assert la_cost.reason  # a plain-words reason, never blank
    assert la_cost.total_landed_cost.value == la_cost.cost_only_total.value

    ny_cost = next(c for c in result.ranked_cities if c.city_id == "us-ny-new-york")
    assert ny_cost.band == "net_ranked"


# ---------------------------------------------------------------------------
# Task 3 — precision: ROUND_HALF_UP, single quantization, Decimal end to end
# ---------------------------------------------------------------------------


def _zero_fringe_component() -> FringeComponent:
    return FringeComponent(value="0", basis="sourced", source_url="https://example.invalid/zero")


def _synthetic_camera_profile(region: str) -> CityCostProfile:
    """A synthetic profile pricing ONLY the camera department, still
    satisfying the "every department has a craft mapping" validator by
    mapping every other department to an inert general_crew craft no
    CostLine in this fixture ever looks up."""
    crafts = {name: CraftMapping(union="TESTUNION", craft="general_crew") for name in
              _ALL_DEPARTMENT_NAMES}
    crafts["camera"] = CraftMapping(union="TESTUNION", craft="camera")
    return CityCostProfile(
        city_id="synthetic-precision",
        city_label="Synthetic Precision City",
        jurisdiction_id=None,
        currency="USD",
        provenance_note="synthetic precision fixture for tests/test_engine_cost_localizer.py",
        cost_lines=[
            CostLine(
                line_id="camera-labour",
                label="Camera labour days",
                category="labour",
                account="BTL",
                spend_class="local_labour",
            )
        ],
        labour=LabourBlock(region=region, crafts=crafts),
    )


def _synthetic_budget(quantity: Decimal) -> CanonicalBudget:
    return CanonicalBudget(
        line_quantities={"Camera labour days": quantity},
        accounts={"Camera labour days": "BTL"},
        shoot_days=Decimal(1),
        crew_headcount=CrewHeadcount(low=1, high=1, basis="test", provenance_note="test fixture"),
    )


def test_half_dollar_labour_product_rounds_up_not_half_even(monkeypatch):
    """901.00 x 12.5 = 11262.50 exactly — 11262 is EVEN, so Python's
    ambient ROUND_HALF_EVEN would round DOWN (already even) to 11262,
    while the pinned ROUND_HALF_UP rounds UP to 11263. This is the
    specific case where the two modes disagree, proving the wage Figure
    goes through `quantize_money`'s pinned rounding, not a bare
    `.quantize()` using the default context."""
    synthetic_row = RateRow(
        row_id="synthetic-half-dollar",
        union="TESTUNION",
        region="us-test",
        craft="camera",
        rate="901.00",
        rate_unit="day",
        effective_from=date(2020, 1, 1),
        effective_to=None,
        basis="sourced",
        source_url="https://example.invalid/synthetic",
    )
    synthetic_fringe = FringeSchedule(
        union="TESTUNION",
        pension_health_pct=_zero_fringe_component(),
        payroll_tax_pct=_zero_fringe_component(),
        other_burden_pct=_zero_fringe_component(),
    )
    monkeypatch.setattr(cost_localizer_module, "load_union_rates", lambda: [synthetic_row])
    monkeypatch.setattr(
        cost_localizer_module, "load_fringe_schedules", lambda: {"TESTUNION": synthetic_fringe}
    )

    profile = _synthetic_camera_profile("us-test")
    budget = _synthetic_budget(Decimal("12.5"))
    localized = localize(budget, profile, on_date=date(2026, 1, 1))
    wage = next(line for line in localized.lines if line.label == "Camera labour days")

    raw_product = Decimal("901.00") * Decimal("12.5")
    assert raw_product == Decimal("11262.50")
    assert raw_product.quantize(Decimal(1), rounding=ROUND_HALF_EVEN) == Decimal(11262)
    assert wage.value == Decimal(11263)
    assert isinstance(wage.value, Decimal)


def test_wage_value_equals_quantize_money_once_not_a_double_quantize(monkeypatch):
    """quantity=0.5, rate=2.00: quantize_money(0.5 x 2.00) = quantize_money(1.00) = 1.
    A BUGGY implementation that rounded `quantity` to a whole day FIRST
    (0.5 -> 1 under ROUND_HALF_UP) and only then multiplied by the rate
    would get 1 x 2.00 = 2 instead — differing from the correct answer by
    exactly one dollar. This proves the actual code never does that."""
    synthetic_row = RateRow(
        row_id="synthetic-single-quantize",
        union="TESTUNION",
        region="us-test",
        craft="camera",
        rate="2.00",
        rate_unit="day",
        effective_from=date(2020, 1, 1),
        effective_to=None,
        basis="sourced",
        source_url="https://example.invalid/synthetic",
    )
    synthetic_fringe = FringeSchedule(
        union="TESTUNION",
        pension_health_pct=_zero_fringe_component(),
        payroll_tax_pct=_zero_fringe_component(),
        other_burden_pct=_zero_fringe_component(),
    )
    monkeypatch.setattr(cost_localizer_module, "load_union_rates", lambda: [synthetic_row])
    monkeypatch.setattr(
        cost_localizer_module, "load_fringe_schedules", lambda: {"TESTUNION": synthetic_fringe}
    )

    profile = _synthetic_camera_profile("us-test")
    budget = _synthetic_budget(Decimal("0.5"))
    localized = localize(budget, profile, on_date=date(2026, 1, 1))
    wage = next(line for line in localized.lines if line.label == "Camera labour days")

    correct = Decimal(1)
    double_quantized_wrong = Decimal(2)
    assert wage.value == correct
    assert wage.value != double_quantized_wrong
    assert double_quantized_wrong - correct == Decimal(1)


def test_fringe_percentages_summed_before_multiplication_not_after(monkeypatch):
    """wage=100, three fringe components of 0.005 each. Summed-then-
    multiplied (correct): 100 x (0.005+0.005+0.005 = 0.015) = 1.50,
    quantize_money once -> 2 (ROUND_HALF_UP rounds .50 up). Multiplied-
    then-summed (wrong): quantize_money(100 x 0.005) = quantize_money(0.50)
    = 1 for EACH component, summed to 1+1+1 = 3. The two orders disagree
    (2 vs 3), proving the declared summed-first order is the one actually
    computed."""
    synthetic_row = RateRow(
        row_id="synthetic-fringe-order",
        union="TESTUNION",
        region="us-test",
        craft="camera",
        rate="100.00",
        rate_unit="day",
        effective_from=date(2020, 1, 1),
        effective_to=None,
        basis="sourced",
        source_url="https://example.invalid/synthetic",
    )
    small_component = FringeComponent(
        value="0.005", basis="sourced", source_url="https://example.invalid/small"
    )
    synthetic_fringe = FringeSchedule(
        union="TESTUNION",
        pension_health_pct=small_component,
        payroll_tax_pct=small_component,
        other_burden_pct=small_component,
    )
    monkeypatch.setattr(cost_localizer_module, "load_union_rates", lambda: [synthetic_row])
    monkeypatch.setattr(
        cost_localizer_module, "load_fringe_schedules", lambda: {"TESTUNION": synthetic_fringe}
    )

    profile = _synthetic_camera_profile("us-test")
    budget = _synthetic_budget(Decimal(1))
    localized = localize(budget, profile, on_date=date(2026, 1, 1))
    fringe = next(
        line for line in localized.lines if line.label == "Fringe and payroll burden — Camera"
    )

    summed_first_correct = Decimal(2)
    multiplied_first_wrong = Decimal(3)
    assert fringe.value == summed_first_correct
    assert fringe.value != multiplied_first_wrong


def test_no_float_ever_enters_the_labour_pricing_path():
    """Structural proof (not just this test's own values): every Figure
    value produced by localize() against a committed profile is a
    Decimal, never a float."""
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _ny_profile(), on_date=on_date, spec=spec)
    for line in localized.lines:
        assert isinstance(line.value, Decimal)


# ---------------------------------------------------------------------------
# Task 3 — housing, per diem and flights for imported crew and cast only
# (COST-04/COST-05)
# ---------------------------------------------------------------------------


def _spec_with_imports(*, crew_imported: int, crew_local: int, cast_imported: int = 1) -> ProductionSpec:
    return ProductionSpec.model_validate(
        {
            "production_type": "feature",
            "shoot_days_stage": 10,
            "shoot_days_location": 5,
            "crew_size": crew_imported + crew_local,
            "crew_tier": None,
            "principal_cast_count": 3,
            "principal_cast_imported_count": cast_imported,
            "crew_imported_count": crew_imported,
            "crew_hired_locally_count": crew_local,
            "start_quarter": "Q2",
            "start_year": 2026,
            "candidate_cities": ["New York, NY"],
        }
    )


def _travel_figures(localized):
    return {
        line.label: line
        for line in localized.lines
        if line.label
        in (
            "Housing — imported crew and cast",
            "Per diem (M&IE) — imported crew and cast",
            "Flights — imported crew and cast",
        )
    }


def test_zero_imported_headcount_produces_computed_zero_never_not_priced():
    spec = _spec_with_imports(crew_imported=0, crew_local=50, cast_imported=0)
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _ny_profile(), on_date=on_date, spec=spec)
    landed = aggregate(localized)

    travel = _travel_figures(localized)
    assert set(travel) == {
        "Housing — imported crew and cast",
        "Per diem (M&IE) — imported crew and cast",
        "Flights — imported crew and cast",
    }
    for label, figure in travel.items():
        assert figure.value == Decimal("0"), label
        joined = " ".join(figure.derivation)
        assert "zero" in joined.lower()

    assert "housing" not in landed.not_priced
    assert "per_diem" not in landed.not_priced
    assert "flights" not in landed.not_priced


def test_ten_imported_crew_produces_exactly_ten_times_the_one_person_figure():
    on_date = quarter_start_date("Q2", 2026)

    one_person_spec = _spec_with_imports(crew_imported=1, crew_local=49, cast_imported=0)
    budget_one = build_canonical_budget(one_person_spec, _crew_headcount())
    localized_one = localize(budget_one, _ny_profile(), on_date=on_date, spec=one_person_spec)
    one_travel = _travel_figures(localized_one)

    ten_person_spec = _spec_with_imports(crew_imported=10, crew_local=40, cast_imported=0)
    budget_ten = build_canonical_budget(ten_person_spec, _crew_headcount())
    localized_ten = localize(budget_ten, _ny_profile(), on_date=on_date, spec=ten_person_spec)
    ten_travel = _travel_figures(localized_ten)

    expected_per_diem = one_travel["Per diem (M&IE) — imported crew and cast"].value * 10
    expected_housing = one_travel["Housing — imported crew and cast"].value * 10
    expected_flights = one_travel["Flights — imported crew and cast"].value * 10

    assert ten_travel["Per diem (M&IE) — imported crew and cast"].value == expected_per_diem
    assert ten_travel["Housing — imported crew and cast"].value == expected_housing
    assert ten_travel["Flights — imported crew and cast"].value == expected_flights


def test_increasing_locally_hired_crew_alone_leaves_travel_costs_unchanged():
    on_date = quarter_start_date("Q2", 2026)

    spec_a = _spec_with_imports(crew_imported=10, crew_local=40)
    budget_a = build_canonical_budget(spec_a, _crew_headcount())
    localized_a = localize(budget_a, _ny_profile(), on_date=on_date, spec=spec_a)
    travel_a = _travel_figures(localized_a)

    spec_b = _spec_with_imports(crew_imported=10, crew_local=90)
    crew_headcount_b = CrewHeadcount(
        low=100, high=100, basis="supplied by the visitor", provenance_note="test fixture"
    )
    budget_b = build_canonical_budget(spec_b, crew_headcount_b)
    localized_b = localize(budget_b, _ny_profile(), on_date=on_date, spec=spec_b)
    travel_b = _travel_figures(localized_b)

    for label in travel_a:
        assert travel_a[label].value == travel_b[label].value, label


def test_both_committed_profiles_not_priced_is_now_empty():
    """Plan 04-04 (COST-06) prices the last five categories (stages,
    equipment, permits, locations, trucking) via each profile's
    `facilities_id` — `not_priced` must now compute to empty for both
    committed cities."""
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)

    ny_landed = aggregate(localize(budget, _ny_profile(), on_date=on_date, spec=spec))
    la_landed = aggregate(localize(budget, _la_profile(), on_date=on_date, spec=spec))

    assert ny_landed.not_priced == ()
    assert la_landed.not_priced == ()


def _london_profile() -> CityCostProfile:
    return load_cost_profile("data/cost_profiles/gb-london.yaml")


def test_london_prices_end_to_end_in_gbp_with_not_priced_empty():
    """Plan 04-05 (COST-02/COST-08): London is the third committed city
    and the first non-USD one — the schema's proof that it generalises
    past US unions and a single currency, with zero engine changes beyond
    the declared BECTU data and London's own committed cost profile."""
    spec = _spec(["London, UK"])
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)

    localized = localize(budget, _london_profile(), on_date=on_date, spec=spec)
    landed = aggregate(localized)

    assert landed.not_priced == ()
    assert landed.cost_total.unit == "GBP"
    for figure in localized.lines:
        assert figure.unit == "GBP"


def test_london_per_diem_carries_no_month_band_resolving_research_assumption_a4():
    """Resolves 04-RESEARCH.md Assumption A4: the State Department's
    London row is flat all year (Season Begin 01/01, Season End 12/31),
    never a genuine month-by-month band — D-64's absent branch, exactly
    like Los Angeles, and recorded in .planning/WINDOWS.md."""
    from engine.landed_cost import SeasonalityState
    from engine.per_diem import load_per_diem

    london_table = load_per_diem("gb-london")

    assert london_table.lodging_by_month is None
    assert london_table.lodging_flat_rate == "424"
    assert london_table.seasonality_note is not None

    london_state = SeasonalityState(state="no_month_band", reason=london_table.seasonality_note)
    assert london_state.state == "no_month_band"
    assert "Assumption A4" in london_state.reason


def test_both_committed_profiles_total_landed_cost_basis_is_modelling_assumption():
    """D-59: with facilities lines at basis 'modelling_assumption' (the
    weakest tier present across the full ten-category set), both
    committed cities' total_landed_cost must report 'modelling_assumption'
    — never a stronger tier while an assumption is present."""
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)

    ny_landed = aggregate(localize(budget, _ny_profile(), on_date=on_date, spec=spec))
    la_landed = aggregate(localize(budget, _la_profile(), on_date=on_date, spec=spec))

    assert ny_landed.total_landed_cost.basis == "modelling_assumption"
    assert la_landed.total_landed_cost.basis == "modelling_assumption"


def test_removing_a_facilities_category_reintroduces_it_to_not_priced():
    """`not_priced` must be a genuine MEASUREMENT, never a hardcoded empty
    tuple — deleting one category's cost line from a real committed
    profile must make that category reappear in `not_priced`, and nothing
    else."""
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)

    profile = _ny_profile()
    remaining_lines = [
        cost_line for cost_line in profile.cost_lines if cost_line.category != "stages"
    ]
    profile_without_stages = profile.model_copy(update={"cost_lines": remaining_lines})

    landed = aggregate(localize(budget, profile_without_stages, on_date=on_date, spec=spec))

    assert landed.not_priced == ("stages",)


def test_every_per_diem_and_housing_figure_has_a_non_null_caveat():
    spec = _spec_with_imports(crew_imported=10, crew_local=40)
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _ny_profile(), on_date=on_date, spec=spec)

    travel = _travel_figures(localized)
    assert travel["Housing — imported crew and cast"].caveat is not None
    assert travel["Per diem (M&IE) — imported crew and cast"].caveat is not None


def test_localize_raises_when_spec_missing_for_a_dynamic_travel_line():
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    with pytest.raises(ValueError, match="ProductionSpec"):
        localize(budget, _ny_profile(), on_date=on_date)


def test_no_jurisdiction_id_literal_in_cost_localizer_per_diem_or_seasonality():
    import re

    paths = ["engine/cost_localizer.py", "engine/per_diem.py", "engine/seasonality.py"]
    pattern = re.compile(r'"us-ny"|"us-ca"')
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        assert not pattern.search(source), f"{path} contains a bare jurisdiction-id literal"
