"""Stage `[2]` of the pipeline: `CityLocalizer` — price the ONE canonical
budget against ONE city's committed cost profile.

JURISDICTION-AGNOSTIC by ARCHITECTURE.md's own stage boundary (D-53,
04-CONTEXT.md): every dispatch below reads DATA declared on
`engine.cost_profile.CityCostProfile` / `CostLine` — never a hard-coded
jurisdiction identifier string. This module must contain no literal
two-letter-country/state jurisdiction-id substring anywhere in its own
source (JUR-05's additivity proof, `tests/test_engine_jurisdiction_additivity.py`,
scans the whole `engine/` tree for exactly this).

Plan 04-02 (COST-02/COST-03) widens the labour path: a `category:
"labour"` cost line whose department has a craft mapping on the profile's
`labour` block is priced dynamically — one dated union rate row selects
the wage, and the matching union's fringe schedule produces a SEPARATE,
sibling fringe Figure (D-62: fringe is never folded into the wage line).
A labour line with no craft mapping (or a profile with no `labour` block
at all) keeps plan 04-01's static per-line `unit_rate` path unchanged —
this is what keeps every pre-04-02 synthetic test fixture passing byte-
for-byte.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import yaml

from engine.budget import CREW_TIERS_PATH, CanonicalBudget
from engine.cost_profile import CityCostProfile, CostLine, CraftMapping
from engine.figure import Figure
from engine.per_diem import load_per_diem
from engine.qualifying_base import SpendBreakdown
from engine.rounding import quantize_money
from engine.seasonality import month_weighted_per_diem, shoot_calendar
from engine.spec import ProductionSpec
from engine.union_rates import (
    FringeSchedule,
    RateRow,
    load_fringe_schedules,
    load_union_rates,
    select_rate_row,
    weakest_basis,
)

__all__ = ["LocalizedBudget", "localize", "quarter_start_date"]

# Q1->Jan 1, Q2->Apr 1, Q3->Jul 1, Q4->Oct 1 — the first day of the
# quarter's first month, exactly as Task 2 specifies.
_QUARTER_START_MONTH: dict[str, int] = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}

# COST-04/COST-05 (plan 04-03): categories priced dynamically from imported
# headcount only, through the profile's `travel` block — never via the
# canonical budget's department quantities.
_TRAVEL_CATEGORIES = ("housing", "per_diem", "flights")


def quarter_start_date(start_quarter: str, start_year: int) -> date:
    """Derive the shoot's `on_date` from `ProductionSpec.start_quarter`
    plus `start_year` as the first day of the quarter's first month. Used
    by the caller (`app/services/spec.py`) to build the `on_date` passed
    into `localize()` — kept here, not duplicated at the call site, so the
    derivation is asserted in one place and disclosed identically in every
    labour Figure's derivation lines."""
    return date(start_year, _QUARTER_START_MONTH[start_quarter], 1)


@dataclass(frozen=True)
class LocalizedBudget:
    """One city's canonical budget, priced. `spend_breakdown` is derived
    from the priced lines' declared `spend_class` — this is how a
    localized budget answers "how much of this spend is local labour"
    from DATA rather than a jurisdiction branch (JUR-05)."""

    city_id: str
    jurisdiction_id: str | None
    currency: str
    lines: tuple[Figure, ...]
    spend_breakdown: SpendBreakdown
    categories_priced: frozenset[str]


def _find_line_by_label(lines: tuple[Figure, ...], label: str) -> Figure | None:
    """Lookup by label, never by position — mirrors
    `engine/net_cash.py::_find_qualifying_base_figure`'s by-label
    discipline."""
    for candidate in lines:
        if candidate.label == label:
            return candidate
    return None


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _department_name_by_label() -> dict[str, str]:
    """`data/crew_tiers.yaml` departments keyed by NAME (e.g. `"camera"`),
    but `CanonicalBudget.line_quantities` and `CostLine.label` are both
    keyed by that department's `label` (e.g. `"Camera labour days"`) — a
    profile's `labour.crafts` mapping is keyed by NAME (matching
    `engine.cost_profile.LabourBlock`'s own docstring), so this is the
    label -> name lookup that connects the two. Reads the same module-
    anchored `CREW_TIERS_PATH` `engine.budget.resolve_departments` reads,
    via `yaml.safe_load` only."""
    with open(CREW_TIERS_PATH, encoding="utf-8") as handle:
        table = yaml.safe_load(handle)
    return {entry["label"]: name for name, entry in table["departments"].items()}


def _price_line(
    cost_line: CostLine, quantity: Decimal, budget: CanonicalBudget, profile: CityCostProfile
) -> Figure:
    """Price one declared `CostLine` against a `quantity` drawn from the
    canonical budget, via the STATIC per-line `unit_rate` path. Dispatches
    on nothing but `cost_line`'s own declared fields plus `profile.currency`
    (D-53/JUR-05). Never called for a labour line with a craft mapping —
    see `_price_labour_department` for the dynamic path."""
    unit_rate = Decimal(cost_line.unit_rate)
    value = quantize_money(quantity * unit_rate)

    source_note = (
        f"source: {cost_line.source_url}"
        if cost_line.source_url
        else f"no source_url recorded — basis {cost_line.basis!r}, method: "
        f"{cost_line.method_note}"
    )
    headcount = budget.crew_headcount
    quantity_note = (
        f"quantity {quantity} {cost_line.rate_unit} uses the crew headcount's LOW "
        f"bound ({headcount.low} of a {headcount.low}-{headcount.high} range, "
        f"basis {headcount.basis!r}) — a deliberate choice, not the midpoint or "
        "high bound"
    )

    return Figure(
        value=value,
        unit=profile.currency,
        label=cost_line.label,
        derivation=(
            f"{quantity} {cost_line.rate_unit} x {unit_rate} {profile.currency} per "
            f"{cost_line.rate_unit} = {value} {profile.currency} ({source_note})",
            quantity_note,
        ),
        inputs=(),
        source_url=cost_line.source_url,
        date_checked=_parse_date(cost_line.date_checked),
        confidence="researched",
        live_fetched_this_run=False,
        basis=cost_line.basis,
    )


def _price_labour_department(
    cost_line: CostLine,
    quantity: Decimal,
    profile: CityCostProfile,
    craft_mapping: CraftMapping,
    on_date: date,
    rows: list[RateRow],
    fringe_schedules: dict[str, FringeSchedule],
) -> tuple[Figure, Figure]:
    """Price one labour-category department dynamically (COST-02/COST-03):
    select a dated union rate row for the wage, then emit a SEPARATE
    sibling fringe Figure from that union's fringe schedule (D-62 — never
    folded into the wage). `profile.labour` is guaranteed non-`None` by
    the caller (`localize()` only reaches here when a craft mapping was
    found, which itself requires `profile.labour` to exist)."""
    assert profile.labour is not None
    row = select_rate_row(
        rows, region=profile.labour.region, craft=craft_mapping.craft, on_date=on_date
    )
    rate = Decimal(row.rate)
    wage_value = quantize_money(quantity * rate)

    wage_source_note = (
        f"source: {row.source_url}"
        if row.source_url
        else f"no source_url recorded — basis {row.basis!r}, method: {row.method_note}"
    )
    local_note = f" Local {row.local}" if row.local else ""
    wage_figure = Figure(
        value=wage_value,
        unit=profile.currency,
        label=cost_line.label,
        derivation=(
            f"{quantity} {row.rate_unit}s x {rate} {profile.currency} per {row.rate_unit} "
            f"= {wage_value} {profile.currency} ({row.union}{local_note}, craft "
            f"{row.craft!r}, row {row.row_id!r}, effective_from {row.effective_from}, "
            f"{wage_source_note})",
            f"quantity {quantity} {row.rate_unit}s derives from the crew headcount's LOW "
            "bound times this department's crew_share times total shoot days "
            "(engine.budget.build_canonical_budget, D-38)",
            f"on_date {on_date} derived from ProductionSpec.start_quarter/start_year as "
            f"the first day of the quarter's first month — this is what selected rate "
            f"row {row.row_id!r} for region {profile.labour.region!r} craft "
            f"{craft_mapping.craft!r} rather than any other dated row",
        ),
        inputs=(),
        source_url=row.source_url,
        date_checked=_parse_date(row.date_checked),
        confidence="researched",
        live_fetched_this_run=False,
        basis=row.basis,
    )

    fringe_schedule = fringe_schedules.get(row.union)
    if fringe_schedule is None:
        raise ValueError(
            f"no fringe schedule declared for union {row.union!r} (rate row "
            f"{row.row_id!r}) — data/union_rates/fringe_schedules.yaml must carry an "
            "entry for every union a rate row declares"
        )
    pension = fringe_schedule.pension_health_pct
    payroll = fringe_schedule.payroll_tax_pct
    other = fringe_schedule.other_burden_pct
    pension_pct = Decimal(pension.value)
    payroll_pct = Decimal(payroll.value)
    other_pct = Decimal(other.value)
    summed_pct = pension_pct + payroll_pct + other_pct
    fringe_value = quantize_money(wage_value * summed_pct)

    department_label = cost_line.label.replace(" labour days", "").strip()
    fringe_basis = weakest_basis([pension.basis, payroll.basis, other.basis])

    def _component_note(name: str, component_value: Decimal, component) -> str:
        source_bit = f", {component.source_url}" if component.source_url else ""
        return f"{name}={component_value} (basis {component.basis!r}{source_bit})"

    fringe_figure = Figure(
        value=fringe_value,
        unit=profile.currency,
        label=f"Fringe and payroll burden — {department_label}",
        derivation=(
            f"{wage_value} {profile.currency} x ({pension_pct} + {payroll_pct} + "
            f"{other_pct} = {summed_pct}) = {fringe_value} {profile.currency} — "
            "the three percentages are summed in Decimal before the single "
            "multiplication (D-59/PITFALLS E1)",
            _component_note("pension_health_pct", pension_pct, pension),
            _component_note("payroll_tax_pct", payroll_pct, payroll),
            _component_note("other_burden_pct", other_pct, other),
            f"{row.union} fringe schedule — data/union_rates/fringe_schedules.yaml",
        ),
        inputs=(wage_figure,),
        source_url=None,
        date_checked=None,
        confidence="researched",
        live_fetched_this_run=False,
        basis=fringe_basis,
    )

    return wage_figure, fringe_figure


def _price_travel_categories(
    profile: CityCostProfile, spec: ProductionSpec
) -> dict[str, Figure]:
    """Price housing, per diem and flights (COST-04/COST-05) from imported
    headcount ONLY — locally-hired crew and local cast generate zero of
    each, and the derivation says so by name (COST-05's entire content).
    `profile.travel` is guaranteed non-`None` by the caller (`localize()`
    only reaches here when a housing/per_diem/flights cost line was found
    alongside a declared `travel` block)."""
    assert profile.travel is not None
    imported_headcount = spec.crew_imported_count + spec.principal_cast_imported_count

    table = load_per_diem(profile.travel.per_diem_id)
    calendar = shoot_calendar(spec)
    housing_figure, per_diem_figure = month_weighted_per_diem(
        table, calendar, imported_headcount, currency=profile.currency
    )
    housing_figure = housing_figure.with_step(
        f"housing uplift: {profile.travel.housing_uplift_note}"
    )

    if imported_headcount == 0:
        headcount_note = (
            f"imported crew count ({spec.crew_imported_count}) and imported "
            f"principal cast count ({spec.principal_cast_imported_count}) were both "
            "zero for this submission — this is a COMPUTED zero, not an unpriced "
            "category (COST-05)"
        )
    else:
        headcount_note = (
            f"priced for {imported_headcount} imported person(s) "
            f"({spec.crew_imported_count} imported crew + "
            f"{spec.principal_cast_imported_count} imported principal cast); "
            f"locally-hired crew ({spec.crew_hired_locally_count}) and local cast "
            "generate zero housing, per diem and flight cost (COST-05)"
        )
    housing_figure = housing_figure.with_step(headcount_note)
    per_diem_figure = per_diem_figure.with_step(headcount_note)

    flight_rate = Decimal(profile.travel.flight_round_trip_rate)
    flights_value = quantize_money(Decimal(imported_headcount) * flight_rate)
    flight_source_note = (
        f"source: {profile.travel.source_url}"
        if profile.travel.source_url
        else f"no source_url recorded — basis {profile.travel.basis!r}, method: "
        f"{profile.travel.method_note}"
    )
    flights_figure = Figure(
        value=flights_value,
        unit=profile.currency,
        label="Flights — imported crew and cast",
        derivation=(
            f"{imported_headcount} imported person(s) x {flight_rate} "
            f"{profile.currency} round-trip = {flights_value} {profile.currency} "
            f"({flight_source_note})",
            headcount_note,
        ),
        inputs=(),
        source_url=profile.travel.source_url,
        date_checked=_parse_date(profile.travel.date_checked),
        confidence="researched",
        live_fetched_this_run=False,
        basis=profile.travel.basis,
    )

    return {
        "housing": housing_figure,
        "per_diem": per_diem_figure,
        "flights": flights_figure,
    }


def _derive_spend_breakdown(
    lines: tuple[Figure, ...], cost_line_by_label: dict[str, CostLine]
) -> SpendBreakdown:
    """Derive a `SpendBreakdown` from the priced lines' declared
    `spend_class` (JUR-05: from DATA, never a jurisdiction branch). A
    `local_labour` line contributes to both `labour_spend` and
    `local_hires_spend`; every priced line contributes to `total_spend`
    and, for this tracer, to `core_expenditure` (no exclusions are
    declared at the cost-localization layer). A fringe Figure (no
    `CostLine` of its own — see `localize()`) is looked up via the SAME
    originating wage `CostLine`'s `spend_class`, so payroll burden on
    local labour counts as local labour spend too."""
    total = Decimal("0")
    labour = Decimal("0")
    local_hires = Decimal("0")
    for figure in lines:
        total += figure.value
        cost_line = cost_line_by_label.get(figure.label)
        if cost_line is not None and cost_line.spend_class == "local_labour":
            labour += figure.value
            local_hires += figure.value
    return SpendBreakdown(
        total_spend=total,
        labour_spend=labour,
        local_hires_spend=local_hires,
        core_expenditure=total,
    )


def localize(
    budget: CanonicalBudget,
    profile: CityCostProfile,
    *,
    on_date: date | None = None,
    spec: ProductionSpec | None = None,
) -> LocalizedBudget:
    """Price `budget` against `profile`. A profile cost line whose `label`
    has no matching entry in `budget.line_quantities` is skipped — it is
    not this budget's job to declare every possible cost line, and a
    profile is free to widen with lines a given budget shape does not
    (yet) supply quantities for. This skip does NOT apply to a
    `housing`/`per_diem`/`flights` cost line priced through `profile.travel`
    — those are priced from imported headcount, never from a budget
    quantity (see below).

    A `category: "labour"` cost line whose department has a craft mapping
    on `profile.labour` is priced dynamically (COST-02/COST-03): TWO
    sibling Figures are emitted (wage, fringe) instead of one, and
    `on_date` is REQUIRED in that case — omitting it while any candidate
    department resolves to a craft mapping raises `ValueError` rather than
    silently falling back to the static path. A profile with no `labour`
    block, or a labour line whose department has no craft mapping, is
    unaffected by `on_date` and keeps plan 04-01's single-Figure static
    path — this is what keeps every pre-04-02 synthetic fixture green.

    A `category: "housing"`/`"per_diem"`/`"flights"` cost line is priced
    dynamically (COST-04/COST-05) ONLY when `profile.travel` is also
    declared — `spec` is REQUIRED in that case (imported headcount and the
    shoot calendar both come from it). A profile with no `travel` block
    keeps such a line on the static per-line path unaffected by `spec`,
    exactly mirroring the labour/`on_date` relationship above."""
    cost_line_by_label = {cost_line.label: cost_line for cost_line in profile.cost_lines}
    department_name_by_label = _department_name_by_label()

    rows: list[RateRow] | None = None
    fringe_schedules: dict[str, FringeSchedule] | None = None
    travel_figures: dict[str, Figure] | None = None

    lines: list[Figure] = []
    categories_priced: set[str] = set()
    for cost_line in profile.cost_lines:
        if cost_line.category in _TRAVEL_CATEGORIES and profile.travel is not None:
            if travel_figures is None:
                if spec is None:
                    raise ValueError(
                        f"localize(): {profile.city_id!r}'s cost line "
                        f"{cost_line.label!r} (category {cost_line.category!r}) is "
                        "priced via profile.travel from imported headcount, but no "
                        "ProductionSpec was supplied"
                    )
                travel_figures = _price_travel_categories(profile, spec)
            figure = travel_figures[cost_line.category]
            lines.append(figure)
            cost_line_by_label[figure.label] = cost_line
            categories_priced.add(cost_line.category)
            continue

        quantity = budget.line_quantities.get(cost_line.label)
        if quantity is None:
            continue

        craft_mapping: CraftMapping | None = None
        if cost_line.category == "labour" and profile.labour is not None:
            department_name = department_name_by_label.get(cost_line.label)
            if department_name is not None:
                craft_mapping = profile.labour.crafts.get(department_name)

        if craft_mapping is not None:
            if on_date is None:
                raise ValueError(
                    f"localize(): {profile.city_id!r}'s cost line {cost_line.label!r} "
                    "is priced via a dated union rate row (a craft mapping is "
                    "declared on profile.labour), but no on_date was supplied"
                )
            if rows is None:
                rows = load_union_rates()
                fringe_schedules = load_fringe_schedules()
            wage_figure, fringe_figure = _price_labour_department(
                cost_line, quantity, profile, craft_mapping, on_date, rows, fringe_schedules
            )
            lines.append(wage_figure)
            lines.append(fringe_figure)
            # The fringe Figure has no CostLine of its own — attribute it
            # to the same wage CostLine's spend_class so payroll burden on
            # local labour is counted as local labour spend too.
            cost_line_by_label[fringe_figure.label] = cost_line
            categories_priced.add("labour")
            categories_priced.add("fringe")
        else:
            lines.append(_price_line(cost_line, quantity, budget, profile))
            categories_priced.add(cost_line.category)

    spend_breakdown = _derive_spend_breakdown(tuple(lines), cost_line_by_label)

    return LocalizedBudget(
        city_id=profile.city_id,
        jurisdiction_id=profile.jurisdiction_id,
        currency=profile.currency,
        lines=tuple(lines),
        spend_breakdown=spend_breakdown,
        categories_priced=frozenset(categories_priced),
    )
