"""`engine.landed_cost.aggregate` — D-60's acknowledged-gaps list, and the
OUT-04 droppability proof: the chart-of-accounts `account` tag is a single
additive field nothing in this phase's aggregation reads, groups, subtotals
or renders by.
"""

from __future__ import annotations

import pytest

from engine.budget import build_canonical_budget
from engine.cost_localizer import localize
from engine.cost_profile import CityCostProfile, CostLine
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
