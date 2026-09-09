"""`/compare` — the map + ranked-list surface's own service layer (Phase 6,
UI-01/UI-02/UI-04).

Mirrors `app/routers/spec.py`'s established no-business-logic contract:
this module calls `app.services.spec.handle_spec_submission` and holds no
pricing logic of its own — every dollar figure a visitor reads still comes
from `engine.ranker.rank` by way of that one call. `CompareInputs` is the
query-string form of a comparison; `build_comparison` resolves it to a
render-ready `Comparison` view model; `to_geojson` turns the same ranked
cities into the `FeatureCollection` MapLibre renders.

D-55 discipline, restated for this surface: `Comparison.net_ranked` and
`Comparison.incentive_not_modelled` are two SEPARATE tuples, never one
list carrying a `band` flag a template has to filter on — a template that
forgot to check the flag would silently render an unranked city's
cost-only total inside the net-ranked band. The two are kept apart from
`SpecResult.ranked_cities` all the way to the Jinja context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.spec import SpecFormSubmission, SpecResult, handle_spec_submission
from engine.city_geo import geo_for_city_id
from engine.ranker import RankedCity
from engine.spec import CrewTier

__all__ = [
    "MAX_CANDIDATE_CITIES",
    "CompareInputs",
    "Comparison",
    "build_comparison",
    "to_geojson",
]

# T-06-05: a bound on the accepted candidate-city count — each city costs a
# real pipeline run (a canonical budget localization plus, for a
# rule-file-backed jurisdiction, a full price_jurisdiction call), so an
# unbounded list is a real denial-of-service surface, not a hypothetical
# one.
MAX_CANDIDATE_CITIES = 12

# UI-01/UI-02's default comparison: New York, Los Angeles and London — the
# same D-54 floor city set every other Phase 4/5 fixture and golden test
# prices against. A bare `GET /compare` (no query string at all) renders
# this real default comparison, never an error.
_DEFAULT_CANDIDATE_CITIES: tuple[str, ...] = ("New York, NY", "Los Angeles, CA", "London, UK")


class CompareInputs(BaseModel):
    """The query-string form of one comparison request. `extra="forbid"`
    plus sane defaults on every field (INP-01..INP-07's defaults for this
    surface specifically) so an anonymous `GET /compare` with no query
    string at all still prices a real default comparison — never a 422 for
    the bare case.

    `reporting_currency` is deliberately `Literal["USD"]` for this plan:
    `app.services.spec.REPORTING_CURRENCY` is still a fixed module
    constant (D-55/D-75) that this plan does not widen — the currency
    selector is a later plan's job (this phase's objective names it as a
    separate axis). The field is present now, and constrained to the one
    value the pipeline actually honours, rather than silently accepting
    and ignoring a value it cannot act on."""

    model_config = ConfigDict(extra="forbid")

    production_type: Literal["feature", "limited_series", "episodic"] = "feature"
    shoot_days_stage: int = Field(default=10, ge=0)
    shoot_days_location: int = Field(default=5, ge=0)
    crew_size: int | None = Field(default=50, ge=1)
    crew_tier: CrewTier | None = None
    principal_cast_count: int = Field(default=3, ge=0)
    principal_cast_imported_count: int = Field(default=1, ge=0)
    crew_imported_count: int = Field(default=10, ge=0)
    crew_hired_locally_count: int = Field(default=40, ge=0)
    start_quarter: Literal["Q1", "Q2", "Q3", "Q4"] = "Q2"
    start_year: int = Field(default=2026, ge=2024, le=2036)
    candidate_cities: list[str] = Field(
        default_factory=lambda: list(_DEFAULT_CANDIDATE_CITIES)
    )
    reporting_currency: Literal["USD"] = "USD"

    @model_validator(mode="after")
    def _candidate_city_count_within_bound(self) -> CompareInputs:
        # T-06-05: a readable 422 above the cap, never an unbounded pricing
        # run triggered from an anonymous, unauthenticated query string.
        if len(self.candidate_cities) > MAX_CANDIDATE_CITIES:
            raise ValueError(
                f"at most {MAX_CANDIDATE_CITIES} candidate cities may be compared per "
                f"request — {len(self.candidate_cities)} were submitted"
            )
        return self


@dataclass(frozen=True)
class Comparison:
    """The render-ready view model for `/compare`. `net_ranked` and
    `incentive_not_modelled` are `SpecResult.ranked_cities` split into the
    two D-55 bands (in `engine.ranker.rank`'s own order within each band —
    never re-sorted here). `geojson` is the exact `FeatureCollection`
    MapLibre renders — computed once, here, so the router and the JSON API
    both hand the browser the identical structure a visitor's HTML page
    already displayed as text."""

    inputs: CompareInputs
    spec_result: SpecResult
    net_ranked: tuple[RankedCity, ...]
    incentive_not_modelled: tuple[RankedCity, ...]
    geojson: dict


def build_comparison(inputs: CompareInputs) -> Comparison:
    """Resolve `inputs` to a `SpecResult` via the identical Route A
    pipeline `/spec` uses, then assemble the two-band, map-ready view
    model. Holds no pricing logic of its own (mirrors `app/routers/spec
    .py`'s own no-business-logic contract) — every dollar figure comes
    from `handle_spec_submission` unchanged."""
    raw = SpecFormSubmission(
        production_type=inputs.production_type,
        shoot_days_stage=inputs.shoot_days_stage,
        shoot_days_location=inputs.shoot_days_location,
        crew_size=inputs.crew_size,
        crew_tier=inputs.crew_tier,
        principal_cast_count=inputs.principal_cast_count,
        principal_cast_imported_count=inputs.principal_cast_imported_count,
        crew_imported_count=inputs.crew_imported_count,
        crew_hired_locally_count=inputs.crew_hired_locally_count,
        start_quarter=inputs.start_quarter,
        start_year=inputs.start_year,
        candidate_cities=inputs.candidate_cities,
        total_budget=None,
    )
    result = handle_spec_submission(raw)
    # `CompareInputs` never carries a `total_budget` field at all (a
    # stronger structural exclusion than `SpecFormSubmission`'s own named,
    # always-refused field) — D-35's refusal branch is therefore
    # unreachable through this surface.
    assert isinstance(result, SpecResult), (
        "handle_spec_submission returned a RefusalResult despite "
        "CompareInputs never supplying total_budget — unreachable"
    )

    net_ranked = tuple(c for c in result.ranked_cities if c.band == "net_ranked")
    incentive_not_modelled = tuple(
        c for c in result.ranked_cities if c.band == "incentive_not_modelled"
    )

    return Comparison(
        inputs=inputs,
        spec_result=result,
        net_ranked=net_ranked,
        incentive_not_modelled=incentive_not_modelled,
        geojson=to_geojson(result.ranked_cities, ()),
    )


def to_geojson(
    ranked_cities: tuple[RankedCity, ...], unpriced: tuple
) -> dict:
    """Build the GeoJSON `FeatureCollection` MapLibre renders. One feature
    per `ranked_cities` entry that resolves to a committed coordinate
    (`engine.city_geo.geo_for_city_id`) — a city with no committed
    coordinate is simply absent from the map, never given a guessed one.

    `unpriced` (a candidate city that resolved to no committed cost
    profile at all) never carries a coordinate by construction — accepted
    here only for signature symmetry with `build_comparison`'s own
    unpriced-city computation; it is never consulted, since an unpriced
    city can never reach this function with anything to plot.

    A feature's `properties` carries `city_id`, `label`, `band`,
    `total_text` (the exact `Decimal` string plus unit, for display) and
    `reason` (only for the `incentive_not_modelled` band). A `net_ranked`
    feature ALSO carries `total_value` — a bare float, a display-layer
    input to MapLibre's `interpolate` colour expression and nothing else;
    every figure a visitor reads still comes from `total_text`, never from
    this float. An `incentive_not_modelled` feature carries NO
    `total_value` property at all, so MapLibre cannot place it on the
    net-cost colour ramp even by accident (D-55)."""
    del unpriced  # never consulted — see docstring

    features: list[dict] = []
    for city in ranked_cities:
        geo = geo_for_city_id(city.city_id)
        if geo is None:
            continue

        properties: dict = {
            "city_id": city.city_id,
            "label": geo.label,
            "band": city.band,
            "total_text": f"{city.total_landed_cost.value} {city.total_landed_cost.unit}",
        }
        if city.band == "net_ranked":
            properties["total_value"] = float(city.total_landed_cost.value)
        else:
            properties["reason"] = city.reason

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(geo.longitude), float(geo.latitude)],
                },
                "properties": properties,
            }
        )

    return {"type": "FeatureCollection", "features": features}
