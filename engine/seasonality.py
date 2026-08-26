"""Stage seasonality support: the derived shoot calendar (D-65) and
month-weighted per diem/housing (COST-04, COST-07, D-64).

Deliberately does NOT import from `engine.cost_localizer` even though that
module's `quarter_start_date` performs an identical quarter -> first-day
derivation: plan 04-03 Task 3 wires `engine/cost_localizer.py` to import
FROM this module (to price housing/per_diem for imported crew and cast),
and importing `cost_localizer.quarter_start_date` back here would create an
import cycle. The four-entry quarter -> month mapping is therefore
duplicated locally, matching the derivation `quarter_start_date` already
performs rather than inventing a new convention.

D-64 (load-bearing): seasonality rides ONLY on a published per-diem month
band — never a modelled multiplier applied to labour, stages or equipment.
A city whose committed per-diem snapshot carries no month band is
seasonality-absent, stated explicitly, never backfilled.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_CEILING, Decimal

from engine.figure import Figure
from engine.per_diem import PerDiemTable, lodging_for_month
from engine.rounding import quantize_money
from engine.spec import ProductionSpec

__all__ = [
    "SHOOT_DAYS_PER_WEEK",
    "SHOOT_DAYS_PER_WEEK_BASIS",
    "SHOOT_DAYS_PER_WEEK_NOTE",
    "MonthNights",
    "month_weighted_per_diem",
    "shoot_calendar",
]

_QUARTER_START_MONTH: dict[str, int] = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}

# D-65: a declared modelling assumption — no public source states a
# production's actual weekly shoot cadence. Named here, and by name in the
# assumptions this feature carries, so it is never mistaken for a sourced
# fact. Used ONLY to spread total shoot days into a calendar-night span for
# per-diem and housing pricing — never applied to labour, stages or
# equipment (D-64).
SHOOT_DAYS_PER_WEEK = Decimal("5")
SHOOT_DAYS_PER_WEEK_BASIS = "modelling_assumption"
SHOOT_DAYS_PER_WEEK_NOTE = (
    "SHOOT_DAYS_PER_WEEK = 5 days/week is a disclosed modelling assumption "
    "(no public source states a production's actual weekly shoot cadence); "
    "used only to convert total shoot days into a spread of calendar nights "
    "for per-diem and housing pricing, never applied to labour, stages or "
    "equipment (D-64)."
)


@dataclass(frozen=True)
class MonthNights:
    """One calendar month's night count within a derived shoot calendar."""

    year_month: str
    nights: int


def _shoot_calendar(
    spec: ProductionSpec, *, days_per_week: Decimal = SHOOT_DAYS_PER_WEEK
) -> tuple[MonthNights, ...]:
    """Spread `shoot_days_stage + shoot_days_location` from the first day
    of `spec.start_quarter` in `spec.start_year` across calendar months at
    `days_per_week` (D-65): the total shoot days imply a whole number of
    shoot WEEKS at that cadence, and a shoot week spans 7 calendar nights
    (a crew on location does not fly home for days off inside a
    multi-week shoot). A production with zero total shoot days derives an
    empty calendar — never a division-by-zero, never a fabricated night.

    Mirrors `engine.net_cash._arrival_timing`: a private helper returning a
    plain frozen dataclass tuple, called by the public `shoot_calendar`
    builder below, never left implicit.
    """
    total_shoot_days = Decimal(spec.shoot_days_stage) + Decimal(spec.shoot_days_location)
    if total_shoot_days <= 0:
        return ()

    weeks = (total_shoot_days / days_per_week).to_integral_value(rounding=ROUND_CEILING)
    total_nights = int(weeks) * 7
    start = date(spec.start_year, _QUARTER_START_MONTH[spec.start_quarter], 1)

    nights_by_month: dict[str, int] = {}
    order: list[str] = []
    for offset in range(total_nights):
        day = start + timedelta(days=offset)
        key = f"{day.year:04d}-{day.month:02d}"
        if key not in nights_by_month:
            nights_by_month[key] = 0
            order.append(key)
        nights_by_month[key] += 1

    return tuple(MonthNights(year_month=key, nights=nights_by_month[key]) for key in order)


def shoot_calendar(
    spec: ProductionSpec, *, days_per_week: Decimal = SHOOT_DAYS_PER_WEEK
) -> tuple[MonthNights, ...]:
    """Public entry point over `_shoot_calendar` — see its docstring for
    the derivation. `days_per_week` is exposed so a caller can prove
    `quarter_invariant_lines`-style measurements are genuine (re-run at a
    different declared rate and see the calendar change), never to accept
    a visitor-supplied cadence."""
    return _shoot_calendar(spec, days_per_week=days_per_week)


def month_weighted_per_diem(
    table: PerDiemTable,
    calendar: tuple[MonthNights, ...],
    headcount: int,
    *,
    currency: str = "USD",
) -> tuple[Figure, Figure]:
    """Price housing (lodging) and per diem (M&IE) for `headcount` people
    across `calendar`'s nights, month by month, as TWO SIBLING Figures
    (D-62's discipline extended to travel costs — never folded into one
    number, since `housing` and `per_diem` are separate `COST_CATEGORIES`).
    Both figures carry `table`'s `basis` and `ceiling_caveat` (D-61) and a
    derivation line per calendar month naming its nights and rate, so the
    seasonal swing is auditable line by line.

    D-64's explicit-absence branch: when `table` has no `lodging_by_month`,
    both figures additionally carry ONE derivation line stating explicitly
    that no month-banded data exists for this city and quoting the table's
    `seasonality_note` — never interpolated, never borrowed from another
    city's pattern.
    """
    mie = Decimal(table.mie_daily)
    housing_total = Decimal("0")
    per_diem_total = Decimal("0")
    housing_lines: list[str] = []
    per_diem_lines: list[str] = []

    if not calendar:
        housing_lines.append("zero calendar nights derived for this shoot — no housing cost")
        per_diem_lines.append("zero calendar nights derived for this shoot — no per-diem cost")

    for month in calendar:
        lodging_rate = lodging_for_month(table, month.year_month)
        housing_value = Decimal(headcount) * Decimal(month.nights) * lodging_rate
        per_diem_value = Decimal(headcount) * Decimal(month.nights) * mie
        housing_total += housing_value
        per_diem_total += per_diem_value
        housing_lines.append(
            f"{month.year_month}: {month.nights} night(s) x {headcount} imported "
            f"person(s) x {lodging_rate} {currency} lodging = {housing_value} {currency}"
        )
        per_diem_lines.append(
            f"{month.year_month}: {month.nights} night(s) x {headcount} imported "
            f"person(s) x {mie} {currency} M&IE = {per_diem_value} {currency}"
        )

    if table.lodging_by_month is None:
        absence_line = (
            f"no month-banded per-diem data exists for {table.per_diem_id!r} — "
            "seasonality is absent rather than backfilled with a multiplier "
            f"(D-64): {table.seasonality_note}"
        )
        housing_lines.append(absence_line)
        per_diem_lines.append(absence_line)
    else:
        band_line = (
            f"{table.per_diem_id!r} carries a genuine month-banded lodging rate "
            f"(source: {table.source_url})"
        )
        housing_lines.append(band_line)
        per_diem_lines.append(band_line)

    housing_figure = Figure(
        value=quantize_money(housing_total),
        unit=currency,
        label="Housing — imported crew and cast",
        derivation=tuple(housing_lines),
        inputs=(),
        source_url=table.source_url,
        date_checked=None,
        confidence="researched",
        live_fetched_this_run=False,
        basis=table.basis,
        caveat=table.ceiling_caveat,
    )
    per_diem_figure = Figure(
        value=quantize_money(per_diem_total),
        unit=currency,
        label="Per diem (M&IE) — imported crew and cast",
        derivation=tuple(per_diem_lines),
        inputs=(),
        source_url=table.source_url,
        date_checked=None,
        confidence="researched",
        live_fetched_this_run=False,
        basis=table.basis,
        caveat=table.ceiling_caveat,
    )
    return housing_figure, per_diem_figure
