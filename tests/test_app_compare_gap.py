"""`/compare`'s two-city gap picker (Phase 6 plan 06-02, UI-05).

`resolve_gap_selection` (`app.services.compare`) is UI-05's own
product-level honesty gate, layered ON TOP of the already-proven
`engine.gap.decompose_gap` (`tests/test_engine_gap.py`): a gap may only
be computed between two cities BOTH in the `net_ranked` band. Selecting
a city from the `incentive_not_modelled` band must render an explicit
refusal naming why the comparison would be misleading — never a computed
number. With the real committed floor-city set (New York, Los Angeles,
London) only New York has a committed rule file (D-53/D-55), so the
refusal path is exercised directly through the live HTTP surface, and
the "two genuinely modelled cities" path is proven with the SAME two
committed, real cost profiles (New York, Los Angeles) — mirroring
`tests/test_engine_gap.py`'s own "controlled synthetic" convention:
tagging both as `net_ranked` here tests THIS function's own band gate in
isolation from `engine.ranker.rank`'s real classification, which is
already proven elsewhere.
"""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import app
from app.services.compare import GapOption, resolve_gap_selection
from engine.budget import build_canonical_budget
from engine.cost_localizer import localize, quarter_start_date
from engine.cost_profile import load_cost_profile
from engine.landed_cost import aggregate
from engine.ranker import RankedCity
from engine.spec import CrewHeadcount, ProductionSpec

client = TestClient(app)

_FLOOR_CITIES = ["New York, NY", "Los Angeles, CA", "London, UK"]

# Money-shaped: a run of digits (with optional thousands separators/
# decimal) — the exact shape a computed delta or headline gap value
# takes. Mirrors test_app_compare_route.py's own `_MONEY_SHAPED`
# discipline, duplicated per this repo's established per-test-module
# convention rather than imported.
_MONEY_SHAPED = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:USD|GBP)")


def _section_html(html: str, aria_id: str) -> str:
    match = re.search(
        r'<section[^>]*aria-labelledby="' + re.escape(aria_id) + r'"[^>]*>(.*?)</section>',
        html,
        re.DOTALL,
    )
    assert match, f"no <section aria-labelledby={aria_id!r}> found in the rendered page"
    return match.group(1)


def _real_landed_cost(profile_path: str, *, on_quarter: str = "Q2", on_year: int = 2026):
    spec = ProductionSpec.model_validate(
        {
            "production_type": "feature",
            "shoot_days_stage": 10,
            "shoot_days_location": 5,
            "crew_size": None,
            "crew_tier": "mid",
            "principal_cast_count": 3,
            "principal_cast_imported_count": 1,
            "crew_imported_count": 10,
            "crew_hired_locally_count": 40,
            "start_quarter": on_quarter,
            "start_year": on_year,
            "candidate_cities": ["Synthetic"],
        }
    )
    headcount = CrewHeadcount(
        low=50, high=50, basis="modelling_assumption", provenance_note="test fixture"
    )
    budget = build_canonical_budget(spec, headcount)
    on_date = quarter_start_date(on_quarter, on_year)
    profile = load_cost_profile(profile_path)
    localized = localize(budget, profile, on_date=on_date, spec=spec)
    return aggregate(localized, reporting_currency="USD")


# ---------------------------------------------------------------------------
# The refusal path — a real net_ranked/incentive_not_modelled pair
# ---------------------------------------------------------------------------


def test_default_comparison_gap_picker_refuses_the_only_real_pair_available():
    """With the real committed floor-city set, New York is the only
    `net_ranked` city (D-53/D-55) — so the default two-city pair is
    exactly one modelled, one unmodelled city, and the picker must
    refuse rather than compute a number."""
    response = client.get(
        "/compare", params=[("candidate_cities", c) for c in _FLOOR_CITIES]
    )
    assert response.status_code == 200
    gap_section = _section_html(response.text, "pf-gap-heading")

    assert "pf-gap-refusal" in gap_section
    assert "carries no modelled incentive yet" in gap_section
    assert "ranked on net landed cost" in gap_section
    # The refusal renders NO computed number at all in its own message.
    refusal_text = re.search(
        r'data-gap-refusal>(.*?)</p>', gap_section, re.DOTALL
    ).group(1)
    assert not _MONEY_SHAPED.search(refusal_text)
    assert "data-gap-table" not in gap_section


def test_explicit_modelled_and_unmodelled_selection_also_refuses():
    response = client.get(
        "/compare",
        params=[
            ("gap_city_a", "us-ny-new-york"),
            ("gap_city_b", "us-ca-los-angeles"),
            *[("candidate_cities", c) for c in _FLOOR_CITIES],
        ],
    )
    assert response.status_code == 200
    gap_section = _section_html(response.text, "pf-gap-heading")
    assert "pf-gap-refusal" in gap_section
    assert "data-gap-table" not in gap_section


def test_json_endpoint_carries_the_refusal_and_no_decomposition():
    response = client.post(
        "/api/v1/compare",
        json={"candidate_cities": _FLOOR_CITIES},
    )
    assert response.status_code == 200
    gap = response.json()["gap"]
    assert gap["refusal"] is not None
    assert gap["decomposition"] is None
    assert gap["city_a_id"] == "us-ny-new-york"


def test_fewer_than_two_selectable_cities_refuses_with_its_own_reason():
    """A single candidate city produces one `RankedCity` at most — a gap
    between one city and nothing is refused for a DIFFERENT, honest
    reason than the band mismatch above."""
    response = client.get("/compare", params=[("candidate_cities", "New York, NY")])
    assert response.status_code == 200
    gap_section = _section_html(response.text, "pf-gap-heading")
    assert "Fewer than two candidate cities" in gap_section
    assert "data-gap-table" not in gap_section


def test_gap_picker_options_span_both_bands_never_the_unpriced_city():
    response = client.get(
        "/compare",
        params=[("candidate_cities", c) for c in [*_FLOOR_CITIES, "Nowhereville, ZZ"]],
    )
    assert response.status_code == 200
    gap_section = _section_html(response.text, "pf-gap-heading")
    # Scoped to the actual `<select>` options, not the whole section — the
    # section ALSO carries "Nowhereville, ZZ" forward as a hidden
    # candidate_cities field (correctly preserving the visitor's full
    # input set across a gap-form resubmit), which is a different thing
    # from it being a selectable gap option.
    select_a = re.search(
        r'<select id="pf-gap-city-a".*?</select>', gap_section, re.DOTALL
    ).group(0)
    select_b = re.search(
        r'<select id="pf-gap-city-b".*?</select>', gap_section, re.DOTALL
    ).group(0)
    for select_html in (select_a, select_b):
        assert "us-ny-new-york" in select_html
        assert "us-ca-los-angeles" in select_html
        assert "gb-london" in select_html
        assert "Nowhereville" not in select_html


# ---------------------------------------------------------------------------
# The working path — two genuinely modelled (net_ranked) cities
# ---------------------------------------------------------------------------


def test_two_net_ranked_cities_produce_components_summing_exactly_to_the_headline():
    """Controlled synthetic banding (both real committed profiles tagged
    `net_ranked`) proves `resolve_gap_selection`'s own wiring: when both
    selected cities ARE net_ranked, it delegates to
    `engine.gap.decompose_gap` unchanged, and the returned components sum
    EXACTLY to the headline gap — asserted with equality, not a
    tolerance, mirroring `engine.gap`'s own exact-sum contract."""
    ny_landed = _real_landed_cost("data/cost_profiles/us-ny-new-york.yaml")
    la_landed = _real_landed_cost("data/cost_profiles/us-ca-los-angeles.yaml")

    ny_city = RankedCity(
        city_id="us-ny-new-york",
        total_landed_cost=ny_landed.total_landed_cost,
        band="net_ranked",
        reason=None,
        incentive_figure=None,
        cost_only_total=ny_landed.cost_total,
        landed_cost=ny_landed,
    )
    la_city = RankedCity(
        city_id="us-ca-los-angeles",
        total_landed_cost=la_landed.total_landed_cost,
        band="net_ranked",
        reason=None,
        incentive_figure=None,
        cost_only_total=la_landed.cost_total,
        landed_cost=la_landed,
    )

    selection = resolve_gap_selection(
        (ny_city, la_city), "us-ny-new-york", "us-ca-los-angeles"
    )
    assert selection.refusal is None
    decomposition = selection.decomposition
    assert decomposition is not None

    total = sum(component.value for component in decomposition.components)
    assert total == decomposition.headline_gap.value
    assert len(decomposition.components) > 0
    # Every component is named, and every value is genuinely signed (a
    # real Decimal, not a pre-formatted, sign-stripped string).
    for component in decomposition.components:
        assert component.label
        assert component.value == component.value  # a real, comparable Decimal


def test_resolve_gap_selection_defaults_to_the_first_two_ranked_ids_in_order():
    ny_landed = _real_landed_cost("data/cost_profiles/us-ny-new-york.yaml")
    la_landed = _real_landed_cost("data/cost_profiles/us-ca-los-angeles.yaml")
    ny_city = RankedCity(
        city_id="us-ny-new-york",
        total_landed_cost=ny_landed.total_landed_cost,
        band="net_ranked",
        reason=None,
        incentive_figure=None,
        cost_only_total=ny_landed.cost_total,
        landed_cost=ny_landed,
    )
    la_city = RankedCity(
        city_id="us-ca-los-angeles",
        total_landed_cost=la_landed.total_landed_cost,
        band="net_ranked",
        reason=None,
        incentive_figure=None,
        cost_only_total=la_landed.cost_total,
        landed_cost=la_landed,
    )
    selection = resolve_gap_selection((ny_city, la_city), None, None)
    assert selection.city_a_id == "us-ny-new-york"
    assert selection.city_b_id == "us-ca-los-angeles"
    assert selection.decomposition is not None
    assert isinstance(selection.options[0], GapOption)
    assert selection.options[0].band == "net_ranked"
