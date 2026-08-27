"""`engine.gap.decompose_gap` — the component-by-component gap
decomposition (OUT-02, D-75).

Controlled synthetic profiles (mirroring `tests/test_engine_landed_cost
.py::_profile_with_account`'s convention — a local, in-Python
`CityCostProfile`, never a new fixture file for this task) prove the
by-label matching discipline, the zero-delta-is-emitted-not-dropped
guarantee, and the one-sided-label raise. The real committed profiles
(New York, Los Angeles, London) prove the exact-sum invariant for every
ordered pair and the currency component's presence/absence.
"""

from __future__ import annotations

import inspect
from decimal import Decimal

import pytest

from engine.budget import build_canonical_budget
from engine.cost_localizer import localize, quarter_start_date
from engine.cost_profile import CityCostProfile, CostLine, load_cost_profile
from engine.gap import decompose_gap, largest_component
from engine.landed_cost import LandedCost, aggregate
from engine.spec import CrewHeadcount, ProductionSpec

# ---------------------------------------------------------------------------
# Controlled synthetic profiles — by-label matching, zero deltas, one-sided
# labels.
# ---------------------------------------------------------------------------


def _shared_spec() -> ProductionSpec:
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
            "candidate_cities": ["Synthetic"],
        }
    )


def _shared_headcount() -> CrewHeadcount:
    return CrewHeadcount(
        low=100, high=100, basis="modelling_assumption", provenance_note="test fixture"
    )


def _cost_line(label: str, unit_rate: str) -> CostLine:
    return CostLine(
        line_id=f"synthetic-{label.lower().replace(' ', '-')}",
        label=label,
        category="equipment",
        account="BTL",
        spend_class="non_local",
        unit_rate=unit_rate,
        rate_unit="unit",
        basis="estimated",
        source_url=None,
        date_checked=None,
        method_note="synthetic fixture for tests/test_engine_gap.py",
    )


def _profile(city_id: str, cost_lines: list[CostLine]) -> CityCostProfile:
    return CityCostProfile(
        city_id=city_id,
        city_label=f"Synthetic {city_id}",
        jurisdiction_id=None,
        currency="USD",
        provenance_note="synthetic fixture for tests/test_engine_gap.py",
        cost_lines=cost_lines,
    )


def _landed_from_profile(profile: CityCostProfile) -> LandedCost:
    budget = build_canonical_budget(_shared_spec(), _shared_headcount())
    localized = localize(budget, profile)
    return aggregate(localized)


def _profile_a() -> CityCostProfile:
    return _profile(
        "synthetic-gap-a",
        [
            _cost_line("Production labour days", "100.00"),
            _cost_line("Camera labour days", "50.00"),
        ],
    )


def _profile_b() -> CityCostProfile:
    # "Production labour days" carries the SAME rate as profile_a — a
    # component identical in both cities, proving the zero-delta row is
    # emitted rather than dropped. "Camera labour days" differs.
    return _profile(
        "synthetic-gap-b",
        [
            _cost_line("Production labour days", "100.00"),
            _cost_line("Camera labour days", "80.00"),
        ],
    )


def _profile_c_mismatched_label() -> CityCostProfile:
    return _profile(
        "synthetic-gap-c",
        [
            _cost_line("Production labour days", "100.00"),
            _cost_line("Grip and electric labour days", "40.00"),
        ],
    )


def test_component_identical_in_both_cities_is_present_with_zero_delta():
    landed_a = _landed_from_profile(_profile_a())
    landed_b = _landed_from_profile(_profile_b())

    decomposition = decompose_gap(
        "gap-a", landed_a, "gap-b", landed_b, reporting_currency="USD"
    )

    by_label = {c.label: c for c in decomposition.components}
    assert "Production labour days" in by_label
    assert by_label["Production labour days"].value == Decimal("0")
    assert "Camera labour days" in by_label
    assert by_label["Camera labour days"].value != Decimal("0")


def test_components_sum_exactly_to_the_headline_gap():
    landed_a = _landed_from_profile(_profile_a())
    landed_b = _landed_from_profile(_profile_b())

    decomposition = decompose_gap(
        "gap-a", landed_a, "gap-b", landed_b, reporting_currency="USD"
    )

    total = sum((c.value for c in decomposition.components), start=Decimal("0"))
    assert total == decomposition.headline_gap.value


def test_gap_between_a_city_and_itself_is_all_zero():
    landed_a = _landed_from_profile(_profile_a())

    decomposition = decompose_gap(
        "solo", landed_a, "solo", landed_a, reporting_currency="USD"
    )

    assert decomposition.headline_gap.value == Decimal("0")
    for component in decomposition.components:
        assert component.value == Decimal("0")


def test_one_sided_label_raises_naming_the_label_and_both_city_ids():
    landed_a = _landed_from_profile(_profile_a())
    landed_c = _landed_from_profile(_profile_c_mismatched_label())

    with pytest.raises(ValueError) as exc_info:
        decompose_gap("gap-a", landed_a, "gap-c", landed_c, reporting_currency="USD")

    message = str(exc_info.value)
    assert "gap-a" in message
    assert "gap-c" in message
    assert "Camera labour days" in message
    assert "Grip and electric labour days" in message


def test_every_component_derivation_names_the_sign_convention_and_both_values():
    landed_a = _landed_from_profile(_profile_a())
    landed_b = _landed_from_profile(_profile_b())

    decomposition = decompose_gap(
        "gap-a", landed_a, "gap-b", landed_b, reporting_currency="USD"
    )

    for component in decomposition.components:
        assert decomposition.sign_convention in component.derivation
        assert any("gap-a" in line and "gap-b" in line for line in component.derivation)


def test_no_currency_component_when_neither_city_was_converted():
    landed_a = _landed_from_profile(_profile_a())
    landed_b = _landed_from_profile(_profile_b())

    decomposition = decompose_gap(
        "gap-a", landed_a, "gap-b", landed_b, reporting_currency="USD"
    )

    labels = {c.label for c in decomposition.components}
    assert "Currency" not in labels


def test_reporting_currency_mismatch_raises():
    landed_a = _landed_from_profile(_profile_a())  # aggregated with default (USD)
    with pytest.raises(ValueError, match="reporting_currency"):
        decompose_gap("gap-a", landed_a, "gap-a-again", landed_a, reporting_currency="GBP")


def test_largest_component_returns_the_greatest_absolute_delta():
    landed_a = _landed_from_profile(_profile_a())
    landed_b = _landed_from_profile(_profile_b())

    decomposition = decompose_gap(
        "gap-a", landed_a, "gap-b", landed_b, reporting_currency="USD"
    )

    winner = largest_component(decomposition)
    assert winner.label == "Camera labour days"
    assert all(abs(winner.value) >= abs(c.value) for c in decomposition.components)


# ---------------------------------------------------------------------------
# The real committed profiles — exact-sum invariant for every ordered pair,
# and the currency component's presence/absence (D-75).
# ---------------------------------------------------------------------------


def _real_spec() -> ProductionSpec:
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
            "candidate_cities": ["placeholder"],
        }
    )


def _real_headcount() -> CrewHeadcount:
    return CrewHeadcount(
        low=50, high=50, basis="supplied by the visitor", provenance_note="test fixture"
    )


def _real_landed(profile_path: str) -> LandedCost:
    spec = _real_spec()
    headcount = _real_headcount()
    profile = load_cost_profile(profile_path)
    budget = build_canonical_budget(spec, headcount)
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    localized = localize(budget, profile, on_date=on_date, spec=spec)
    return aggregate(localized, reporting_currency="USD")


REAL_CITIES = {
    "us-ny-new-york": "data/cost_profiles/us-ny-new-york.yaml",
    "us-ca-los-angeles": "data/cost_profiles/us-ca-los-angeles.yaml",
    "gb-london": "data/cost_profiles/gb-london.yaml",
}


def _real_landed_by_city() -> dict[str, LandedCost]:
    return {city_id: _real_landed(path) for city_id, path in REAL_CITIES.items()}


def test_every_ordered_pair_among_the_three_committed_cities_sums_exactly():
    landed_by_city = _real_landed_by_city()
    city_ids = list(landed_by_city)

    for a_id in city_ids:
        for b_id in city_ids:
            if a_id == b_id:
                continue
            decomposition = decompose_gap(
                a_id,
                landed_by_city[a_id],
                b_id,
                landed_by_city[b_id],
                reporting_currency="USD",
            )
            total = sum((c.value for c in decomposition.components), start=Decimal("0"))
            assert total == decomposition.headline_gap.value, (a_id, b_id)


def test_london_pairs_carry_a_currency_component_ny_vs_la_does_not():
    landed_by_city = _real_landed_by_city()

    ny_vs_la = decompose_gap(
        "us-ny-new-york",
        landed_by_city["us-ny-new-york"],
        "us-ca-los-angeles",
        landed_by_city["us-ca-los-angeles"],
        reporting_currency="USD",
    )
    assert "Currency" not in {c.label for c in ny_vs_la.components}

    ny_vs_london = decompose_gap(
        "us-ny-new-york",
        landed_by_city["us-ny-new-york"],
        "gb-london",
        landed_by_city["gb-london"],
        reporting_currency="USD",
    )
    currency_components = [c for c in ny_vs_london.components if c.label == "Currency"]
    assert len(currency_components) == 1
    currency_component = currency_components[0]
    assert currency_component.date_checked is not None
    assert currency_component.source_url is not None

    la_vs_london = decompose_gap(
        "us-ca-los-angeles",
        landed_by_city["us-ca-los-angeles"],
        "gb-london",
        landed_by_city["gb-london"],
        reporting_currency="USD",
    )
    currency_components_la = [c for c in la_vs_london.components if c.label == "Currency"]
    assert len(currency_components_la) == 1


# ---------------------------------------------------------------------------
# JUR-05/D-53 — no jurisdiction identifier literal in this module's source
# ---------------------------------------------------------------------------


def test_no_jurisdiction_id_literal_in_gap_module():
    import engine.gap as gap_module

    source = inspect.getsource(gap_module)
    for literal in ('"us-ny"', '"us-ca"', '"gb-london"'):
        assert literal not in source
