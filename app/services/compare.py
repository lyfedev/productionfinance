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
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.spec import (
    REPORTING_CURRENCY,
    LiveProgrammeCheck,
    SpecFormSubmission,
    SpecResult,
    handle_spec_submission,
)
from engine.city_geo import geo_for_city_id
from engine.city_profile_lookup import resolve_city_to_profile_stem
from engine.cost_localizer import quarter_start_date
from engine.gap import GapDecomposition, decompose_gap
from engine.ranker import RankedCity
from engine.spec import CrewTier

if TYPE_CHECKING:
    from app.services.live_fx import FxResolution

__all__ = [
    "MAX_CANDIDATE_CITIES",
    "SLIDER_QUARTERS",
    "CompareInputs",
    "Comparison",
    "GapOption",
    "GapSelection",
    "UnpricedCity",
    "build_comparison",
    "resolve_gap_selection",
    "resolve_start_index",
    "slider_options",
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

# UI-03: the fixed sequence of quarters the start-date slider ranges over.
# Bounded to the exact months `data/per_diem/gsa/us-ny-new-york-county.yaml`
# `lodging_by_month` actually publishes (2025-10 through 2026-09) — every
# slider position is therefore priced against a genuinely sourced monthly
# rate, never a fallback past the published range and never an invented
# day-level granularity the engine does not have (`engine.cost_localizer
# .localize` and `engine.seasonality.shoot_calendar` both resolve a shoot's
# start date from `ProductionSpec.start_quarter`/`start_year` — quarter is
# the engine's real resolution, and the slider is honest about that rather
# than pretending a finer one).
#
# Three consecutive quarters, not four: `data/union_rates/iatse.yaml`'s
# `iatse-l600-camera-us-ny-2025` row (the ONLY committed us-ny camera row)
# carries `effective_to: "2026-08-01"` and states explicitly that no
# 2026-2027 successor row is committed yet (WINDOWS.md) — "a shoot date
# after 2026-08-01 in New York correctly raises rather than falling back
# to this expired row." `engine.sensitivity.sensitivity_rows`' own
# "start_quarter advanced by one" mutation row re-prices the NEXT quarter
# forward to measure that step, uncaught — so Q3 2026 (a real, per-diem-
# covered quarter on its own) would advance to Q4 2026 and crash every
# request that landed on it. Excluding it here is a scope decision, not a
# silent workaround: the fix belongs to `data/union_rates/iatse.yaml` (a
# curated rate table outside this plan's `files_modified`), not to this
# slider. Three quarters still spans a real, disclosed seasonal swing in
# New York's own lodging ceiling: Q4 2025 (peak, $342), Q1 2026
# (off-peak, $179), Q2 2026 (mid, $281 — also `CompareInputs`' own
# default start date, index 2, and the last quarter whose own
# "advanced by one" sensitivity row stays inside the covered range).
SLIDER_QUARTERS: tuple[tuple[str, int], ...] = (
    ("Q4", 2025),
    ("Q1", 2026),
    ("Q2", 2026),
    ("Q3", 2026),
)


def slider_options() -> tuple[dict, ...]:
    """One entry per slider position — index, quarter, year, and the real
    calendar date (`quarter_start_date`, the first day of that quarter)
    the slider's own tick labels read. A date lookup over a fixed,
    committed sequence, never a computed cost figure — the honesty
    boundary UI-03 draws around this page's own script."""
    return tuple(
        {
            "index": i,
            "start_quarter": quarter,
            "start_year": year,
            "label": f"{quarter} {year}",
            "date": quarter_start_date(quarter, year).isoformat(),
        }
        for i, (quarter, year) in enumerate(SLIDER_QUARTERS)
    )


def resolve_start_index(index: int) -> tuple[str, int]:
    """Resolve a slider position to its `(start_quarter, start_year)`
    pair. Raises `ValueError` for an out-of-range index — surfaced by
    `CompareInputs`' own validator as a readable 422, never silently
    clamped to the nearest valid position."""
    if not 0 <= index < len(SLIDER_QUARTERS):
        raise ValueError(
            f"start_index must be between 0 and {len(SLIDER_QUARTERS) - 1} — "
            f"{index} is out of range"
        )
    return SLIDER_QUARTERS[index]


def _current_slider_index(start_quarter: str, start_year: int) -> int | None:
    """The slider position matching `start_quarter`/`start_year`, or
    `None` when the resolved date falls outside the slider's own fixed
    range (e.g. a caller of `POST /api/v1/compare` naming a quarter no
    slider position represents) — the template renders a stated default
    position in that case rather than guessing one."""
    try:
        return SLIDER_QUARTERS.index((start_quarter, start_year))
    except ValueError:
        return None


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
    # UI-03: the start-date slider's own position. When supplied, this
    # OVERRIDES `start_quarter`/`start_year` above (resolved via
    # `resolve_start_index`) — a caller MAY still post `start_quarter`/
    # `start_year` directly instead (the JSON contract this field widens,
    # never narrows), but the two are never both honoured independently.
    start_index: int | None = Field(default=None, ge=0)
    candidate_cities: list[str] = Field(
        default_factory=lambda: list(_DEFAULT_CANDIDATE_CITIES)
    )
    reporting_currency: Literal["USD"] = "USD"
    # UI-11 (plan 06-04): a PURE display-layer choice — never fed into
    # pricing (`build_comparison` never reads it), never widening
    # `reporting_currency` above (that stays the engine-level constant
    # 06-01 deliberately left alone). Bounded to
    # `engine.fx.SUPPORTED_CURRENCY_CODES` — the only pairs a committed
    # fallback snapshot could ever exist for
    # (`app.services.currency_display.DISPLAY_CURRENCIES` re-exports the
    # same tuple, single source of truth). Carried on `CompareInputs`
    # (rather than as a router-only parameter) so it round-trips through
    # a permalink (plan 06-04's own UI-08) and survives the settled-
    # slider's JS-collected POST body the same way `reporting_currency`
    # already does, with zero changes to `app/static/compare.js` (a
    # hidden field carries it; `compare.js`'s own `FormData` collection
    # is already generic over whatever fields a form declares).
    display_currency: Literal["USD", "GBP"] = "USD"
    # UI-05: the two-city gap picker's own selection. `None` (the default)
    # resolves to the first two selectable cities in rank order — see
    # `resolve_gap_selection`. An unrecognised id is never a 422 here; it
    # falls back to that same default rather than adding a new failure
    # mode to a form field a visitor can only set by picking from a
    # server-rendered `<select>` in the first place.
    gap_city_a: str | None = None
    gap_city_b: str | None = None

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

    @model_validator(mode="after")
    def _resolve_start_index(self) -> CompareInputs:
        # UI-03: a settled slider position resolves to the exact same
        # (start_quarter, start_year) pair a direct query-string request
        # would use — one code path, never a parallel date-to-quarter
        # mapping duplicated between this validator and the template.
        if self.start_index is not None:
            quarter, year = resolve_start_index(self.start_index)
            self.start_quarter = quarter
            self.start_year = year
        return self


@dataclass(frozen=True)
class UnpricedCity:
    """A candidate city named by the visitor that resolved to no committed
    cost profile at all — the third explicit page state (never silently
    dropped between input and output). `name` is the visitor's own typed
    string, echoed back exactly as `spec_result.html` already does for the
    uncurated-jurisdiction case."""

    name: str
    reason: str


@dataclass(frozen=True)
class GapOption:
    """One selectable city in the UI-05 two-city gap picker. Carried
    separately from `RankedCity` so a template can render every
    selectable option's display label and band without reaching back
    into `engine.city_geo` itself."""

    city_id: str
    label: str
    band: Literal["net_ranked", "incentive_not_modelled"]


@dataclass(frozen=True)
class GapSelection:
    """UI-05's own product-level gate, layered ON TOP of
    `engine.gap.decompose_gap` — that function has no opinion about D-55
    bands at all (it only requires a matching `reporting_currency` and an
    identical cost-line label set); the refusal here is a policy THIS
    surface imposes, because its city picker lets a visitor choose ANY
    two cities, including a mismatched pair `decompose_gap` never sees a
    reason to refuse on its own.

    `decomposition` and `refusal` are mutually exclusive — exactly one is
    non-`None`. `refusal` is populated (never a computed number) whenever
    fewer than two cities are selectable at all, OR either selected city
    sits in the `incentive_not_modelled` band: comparing a net total to a
    gross one is exactly the misleading arithmetic this product exists to
    refuse to produce."""

    options: tuple[GapOption, ...]
    city_a_id: str | None
    city_b_id: str | None
    decomposition: GapDecomposition | None
    refusal: str | None


def _gap_option_label(city_id: str) -> str:
    """The gap picker's own display label for `city_id` — the committed
    `CityGeo.label` when one exists, or `city_id` itself as a fallback
    (never reached for a `RankedCity`, whose `city_id` is always a
    committed `CityCostProfile.city_id` and therefore always resolves —
    kept only so this function has no partial branch)."""
    geo = geo_for_city_id(city_id)
    return geo.label if geo is not None else city_id


_FEWER_THAN_TWO_REASON = (
    "Fewer than two candidate cities produced a total at all — select at "
    "least two cities with a committed cost profile before a gap can be "
    "shown."
)


def resolve_gap_selection(
    ranked_cities: tuple[RankedCity, ...],
    requested_a: str | None,
    requested_b: str | None,
) -> GapSelection:
    """Resolve the visitor's two-city selection (or the rank-order
    default when either id is unrecognised) to a `GapSelection`. Every
    city in `ranked_cities` (both D-55 bands — `unpriced_cities` never
    reach here, since they carry no `LandedCost` to gap at all) is a
    selectable option. Delegates the actual arithmetic to
    `engine.gap.decompose_gap` unchanged — this function's own job is
    entirely the band-honesty gate and the default-pair resolution."""
    options = tuple(
        GapOption(
            city_id=city.city_id,
            label=_gap_option_label(city.city_id),
            band=city.band,
        )
        for city in ranked_cities
    )
    by_id = {city.city_id: city for city in ranked_cities}
    selectable_ids = tuple(city.city_id for city in ranked_cities)

    if len(selectable_ids) < 2:
        return GapSelection(
            options=options,
            city_a_id=selectable_ids[0] if selectable_ids else None,
            city_b_id=None,
            decomposition=None,
            refusal=_FEWER_THAN_TWO_REASON,
        )

    city_a_id = requested_a if requested_a in by_id else selectable_ids[0]
    city_b_id = (
        requested_b
        if (requested_b in by_id and requested_b != city_a_id)
        else next((cid for cid in selectable_ids if cid != city_a_id), None)
    )
    if city_b_id is None:
        return GapSelection(
            options=options,
            city_a_id=city_a_id,
            city_b_id=None,
            decomposition=None,
            refusal=_FEWER_THAN_TWO_REASON,
        )

    city_a = by_id[city_a_id]
    city_b = by_id[city_b_id]
    if city_a.band != "net_ranked" or city_b.band != "net_ranked":
        unmodelled = [c.city_id for c in (city_a, city_b) if c.band != "net_ranked"]
        refusal = (
            f"{' and '.join(unmodelled)} carries no modelled incentive yet — its "
            "total is cost-only, while a net_ranked city's total is net of a "
            "modelled incentive. Subtracting one from the other would compare a "
            "gross total to a net one, exactly the misleading arithmetic this "
            "product exists to refuse to produce. Both selected cities must be "
            "ranked on net landed cost before a gap is shown."
        )
        return GapSelection(
            options=options,
            city_a_id=city_a_id,
            city_b_id=city_b_id,
            decomposition=None,
            refusal=refusal,
        )

    decomposition = decompose_gap(
        city_a_id,
        city_a.landed_cost,
        city_b_id,
        city_b.landed_cost,
        reporting_currency=REPORTING_CURRENCY,
    )
    return GapSelection(
        options=options,
        city_a_id=city_a_id,
        city_b_id=city_b_id,
        decomposition=decomposition,
        refusal=None,
    )


@dataclass(frozen=True)
class Comparison:
    """The render-ready view model for `/compare`. `net_ranked` and
    `incentive_not_modelled` are `SpecResult.ranked_cities` split into the
    two D-55 bands (in `engine.ranker.rank`'s own order within each band —
    never re-sorted here). `unpriced_cities` is the third explicit page
    state (UI-01's "never silently dropped" contract). `geojson` is the
    exact `FeatureCollection` MapLibre renders — computed once, here, so
    the router and the JSON API both hand the browser the identical
    structure a visitor's HTML page already displayed as text.
    `fx_resolutions`/`live_programme_checks` are carried straight through
    from `SpecResult` (AGT-10) — this plan renders them as their own
    labelled disclosures; a later plan (06-05) reuses them unchanged.

    `gap_selection` (UI-05) is the two-city gap picker's resolved state —
    see `resolve_gap_selection`. `slider_options`/`slider_current_index`
    (UI-03) are the start-date slider's own fixed tick sequence and the
    position matching `inputs.start_quarter`/`start_year`, `None` when
    that pair falls outside the slider's own range."""

    inputs: CompareInputs
    spec_result: SpecResult
    net_ranked: tuple[RankedCity, ...]
    incentive_not_modelled: tuple[RankedCity, ...]
    unpriced_cities: tuple[UnpricedCity, ...]
    geojson: dict
    fx_resolutions: tuple[FxResolution, ...]
    live_programme_checks: tuple[LiveProgrammeCheck, ...]
    gap_selection: GapSelection
    slider_options: tuple[dict, ...]
    slider_current_index: int | None


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
    unpriced_cities = _unpriced_cities(result)
    gap_selection = resolve_gap_selection(
        result.ranked_cities, inputs.gap_city_a, inputs.gap_city_b
    )

    return Comparison(
        inputs=inputs,
        spec_result=result,
        net_ranked=net_ranked,
        incentive_not_modelled=incentive_not_modelled,
        unpriced_cities=unpriced_cities,
        geojson=to_geojson(result.ranked_cities, unpriced_cities),
        fx_resolutions=result.fx_resolutions,
        live_programme_checks=result.live_programme_checks,
        gap_selection=gap_selection,
        slider_options=slider_options(),
        slider_current_index=_current_slider_index(inputs.start_quarter, inputs.start_year),
    )


def _unpriced_cities(result: SpecResult) -> tuple[UnpricedCity, ...]:
    """The third explicit page state: every candidate city the visitor
    named that resolved to no committed cost profile at all — a city
    absent from `result.ranked_cities`. Computed by set difference between
    `result.city_assessments` (every candidate the visitor typed) and the
    `city_id`s `engine.ranker.rank` actually priced — resolving each
    assessment's name through the SAME pure, allow-list-only
    `resolve_city_to_profile_stem` lookup `app.services.spec` already used
    to build `result.ranked_cities` in the first place (never a second
    pricing run, never `load_cost_profile`/`localize` called again)."""
    priced_city_ids = {city.city_id for city in result.ranked_cities}
    unpriced: list[UnpricedCity] = []
    for assessment in result.city_assessments:
        stem = resolve_city_to_profile_stem(assessment.name)
        if stem is not None and stem in priced_city_ids:
            continue
        unpriced.append(
            UnpricedCity(
                name=assessment.name,
                reason=(
                    f"No committed cost profile exists for {assessment.name!r} yet — "
                    "it was never priced, and is named here rather than dropped."
                ),
            )
        )
    return tuple(unpriced)


def to_geojson(
    ranked_cities: tuple[RankedCity, ...], unpriced: tuple[UnpricedCity, ...]
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
