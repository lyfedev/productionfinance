"""`engine.landed_cost.aggregate` — D-60's acknowledged-gaps list, and the
OUT-04 droppability proof: the chart-of-accounts `account` tag is a single
additive field nothing in this phase's aggregation reads, groups, subtotals
or renders by.
"""

from __future__ import annotations

import pytest

from decimal import Decimal

from engine.budget import build_canonical_budget
from engine.cost_localizer import localize, quarter_start_date
from engine.cost_profile import CityCostProfile, CostLine, load_cost_profile
from engine.landed_cost import COST_CATEGORIES, PERMANENT_EXCLUSIONS, aggregate
from engine.spec import CrewHeadcount, ProductionSpec


def _spec() -> ProductionSpec:
    return ProductionSpec.model_validate(
        {
            "production_type": "feature",
            "shoot_days_stage": 10,
            "shoot_days_location": 5,
            "crew_size": None,
            "crew_tier": "mid",
            "principal_cast_count": 3,
            "principal_cast_imported_count": 1,
            "crew_imported_count": 0,
            "crew_hired_locally_count": 0,
            "start_quarter": "Q2",
            "start_year": 2026,
            "candidate_cities": ["New York, NY"],
        }
    )


def _crew_headcount() -> CrewHeadcount:
    return CrewHeadcount(
        low=90, high=120, basis="modelling_assumption", provenance_note="test fixture"
    )


def _profile_with_account(account: str) -> CityCostProfile:
    return CityCostProfile(
        city_id="synthetic-landed-cost",
        city_label="Synthetic Landed Cost City",
        jurisdiction_id=None,
        currency="USD",
        provenance_note="synthetic fixture for tests/test_engine_landed_cost.py",
        cost_lines=[
            CostLine(
                line_id="synthetic-labour",
                label="Production labour days",
                category="labour",
                account=account,
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


def test_not_priced_names_every_unpriced_category_never_a_zero_line():
    budget = build_canonical_budget(_spec(), _crew_headcount())
    localized = localize(budget, _profile_with_account("BTL"))
    landed = aggregate(localized)

    assert "labour" not in landed.not_priced
    for category in COST_CATEGORIES:
        if category != "labour":
            assert category in landed.not_priced
    assert landed.permanent_exclusions == PERMANENT_EXCLUSIONS


def test_aggregate_raises_rather_than_default_a_basis_or_confidence_on_zero_lines():
    """D-59: an empty cost-line input list has no basis to combine — this
    must raise, never silently default to a fallback tier."""
    empty_profile = CityCostProfile(
        city_id="synthetic-empty",
        city_label="Synthetic Empty City",
        jurisdiction_id=None,
        currency="USD",
        provenance_note="synthetic fixture with zero cost lines",
        cost_lines=[],
    )
    budget = build_canonical_budget(_spec(), _crew_headcount())
    localized = localize(budget, empty_profile)
    with pytest.raises(ValueError):
        aggregate(localized)


# ---------------------------------------------------------------------------
# OUT-04 — the account tag is additive and droppable
# ---------------------------------------------------------------------------


def test_aggregate_output_is_byte_identical_regardless_of_account_tag_value():
    """OUT-04/D-77: the `account` tag is a single additive field nothing in
    Phase 4's aggregation reads. Two otherwise-identical profiles that
    differ ONLY in their cost lines' `account` value must produce
    byte-identical `aggregate()` output — proving the tag can be dropped
    (or changed) without unpicking the rest of the aggregation."""
    budget = build_canonical_budget(_spec(), _crew_headcount())

    landed_btl = aggregate(localize(budget, _profile_with_account("BTL")))
    landed_post = aggregate(localize(budget, _profile_with_account("POST")))

    assert landed_btl.cost_total.value == landed_post.cost_total.value
    assert landed_btl.total_landed_cost.value == landed_post.total_landed_cost.value
    assert landed_btl.not_priced == landed_post.not_priced
    assert landed_btl.permanent_exclusions == landed_post.permanent_exclusions
    assert landed_btl.cost_total.basis == landed_post.cost_total.basis
    assert landed_btl.cost_total.confidence == landed_post.cost_total.confidence


def test_landed_cost_module_never_groups_or_subtotals_by_account():
    """OUT-04 (D-77): the rendered chart-of-accounts breakdown is Phase
    11's, not Phase 4's. `engine/landed_cost.py`'s own source must never
    reference an `account` field — a future contributor adding an
    account-keyed subtotal here would be building the view a full phase
    early."""
    import inspect

    import engine.landed_cost as landed_cost_module

    source = inspect.getsource(landed_cost_module)
    assert "account" not in source.lower()


# ---------------------------------------------------------------------------
# COST-08/D-74/D-75 (plan 04-05) — per-component FX conversion into a
# comparable reporting currency.
# ---------------------------------------------------------------------------


def _imported_spec(candidate_cities: list[str]) -> ProductionSpec:
    return ProductionSpec.model_validate(
        {
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
            "candidate_cities": candidate_cities,
        }
    )


def _imported_crew_headcount() -> CrewHeadcount:
    return CrewHeadcount(
        low=50, high=50, basis="supplied by the visitor", provenance_note="test fixture"
    )


def _ny_profile() -> CityCostProfile:
    return load_cost_profile("data/cost_profiles/us-ny-new-york.yaml")


def _london_profile() -> CityCostProfile:
    return load_cost_profile("data/cost_profiles/gb-london.yaml")


def test_default_reporting_currency_is_the_localized_budgets_own_currency():
    spec = _imported_spec(["London, UK"])
    budget = build_canonical_budget(spec, _imported_crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _london_profile(), on_date=on_date, spec=spec)

    landed = aggregate(localized)

    assert landed.cost_total.unit == "GBP"
    assert landed.reporting_currency == "GBP"
    assert landed.source_currency == "GBP"
    assert landed.fx_as_of_date is None


def test_london_converted_total_equals_exact_sum_of_converted_components():
    spec = _imported_spec(["London, UK"])
    budget = build_canonical_budget(spec, _imported_crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _london_profile(), on_date=on_date, spec=spec)

    landed = aggregate(localized, reporting_currency="USD")

    money_lines = [f for f in landed.cost_total.inputs if f.unit == "USD"]
    assert len(money_lines) == len(localized.lines)
    assert landed.cost_total.value == sum((f.value for f in money_lines), start=Decimal("0"))
    assert landed.cost_total.unit == "USD"
    assert landed.reporting_currency == "USD"
    assert landed.source_currency == "GBP"
    assert landed.fx_as_of_date is not None


def test_fx_rate_figure_is_present_in_inputs_and_contributes_zero_to_the_sum():
    spec = _imported_spec(["London, UK"])
    budget = build_canonical_budget(spec, _imported_crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _london_profile(), on_date=on_date, spec=spec)

    landed = aggregate(localized, reporting_currency="USD")

    fx_lines = [f for f in landed.cost_total.inputs if f.label == "FX rate GBP->USD"]
    assert len(fx_lines) == 1
    fx_line = fx_lines[0]
    assert fx_line.value == Decimal("1.363")

    money_lines = [f for f in landed.cost_total.inputs if f is not fx_line]
    assert landed.cost_total.value == sum((f.value for f in money_lines), start=Decimal("0"))
    # Adding the rate's own numeric value to the money sum would NOT equal
    # the reported total — proving the rate figure is excluded from the
    # sum, not merely present alongside it by coincidence.
    assert landed.cost_total.value != landed.cost_total.value + fx_line.value
    assert any("excluded from the sum" in line for line in landed.cost_total.derivation)


def test_usd_city_reporting_in_usd_adds_no_fx_line_and_is_byte_identical():
    spec = _imported_spec(["New York, NY"])
    budget = build_canonical_budget(spec, _imported_crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _ny_profile(), on_date=on_date, spec=spec)

    landed_default = aggregate(localized)
    landed_explicit = aggregate(localized, reporting_currency="USD")

    assert landed_default.cost_total.value == landed_explicit.cost_total.value
    assert landed_default.cost_total.inputs == landed_explicit.cost_total.inputs
    assert landed_default.cost_total.derivation == landed_explicit.cost_total.derivation
    assert not any("FX rate" in f.label for f in landed_explicit.cost_total.inputs)
    assert landed_explicit.fx_as_of_date is None


def test_missing_fx_snapshot_raises_rather_than_returning_an_unconverted_total():
    spec = _imported_spec(["London, UK"])
    budget = build_canonical_budget(spec, _imported_crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _london_profile(), on_date=on_date, spec=spec)

    # No committed gbp-eur.yaml snapshot exists — the city must report a
    # refusal, never a total silently left in GBP or wrongly labelled EUR.
    with pytest.raises(ValueError, match="GBP"):
        aggregate(localized, reporting_currency="EUR")


def test_landed_cost_records_reporting_source_currency_and_fx_date():
    spec = _imported_spec(["London, UK"])
    budget = build_canonical_budget(spec, _imported_crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, _london_profile(), on_date=on_date, spec=spec)

    landed = aggregate(localized, reporting_currency="USD")

    assert landed.reporting_currency == "USD"
    assert landed.source_currency == "GBP"
    assert landed.fx_as_of_date is not None
    assert landed.fx_as_of_date.isoformat() == "2026-08-26"
