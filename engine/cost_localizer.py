"""Stage `[2]` of the pipeline: `CityLocalizer` — price the ONE canonical
budget against ONE city's committed cost profile.

JURISDICTION-AGNOSTIC by ARCHITECTURE.md's own stage boundary (D-53,
04-CONTEXT.md): every dispatch below reads DATA declared on
`engine.cost_profile.CityCostProfile` / `CostLine` — never a hard-coded
jurisdiction identifier string. This module must contain no literal
two-letter-country/state jurisdiction-id substring anywhere in its own
source (JUR-05's additivity proof, `tests/test_engine_jurisdiction_additivity.py`,
scans the whole `engine/` tree for exactly this).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from engine.budget import CanonicalBudget
from engine.cost_profile import CityCostProfile, CostLine
from engine.figure import Figure
from engine.qualifying_base import SpendBreakdown
from engine.rounding import quantize_money

__all__ = ["LocalizedBudget", "localize"]


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


def _price_line(
    cost_line: CostLine, quantity: Decimal, budget: CanonicalBudget, profile: CityCostProfile
) -> Figure:
    """Price one declared `CostLine` against a `quantity` drawn from the
    canonical budget. Dispatches on nothing but `cost_line`'s own declared
    fields plus `profile.currency` (D-53/JUR-05)."""
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


def _derive_spend_breakdown(
    lines: tuple[Figure, ...], cost_line_by_label: dict[str, CostLine]
) -> SpendBreakdown:
    """Derive a `SpendBreakdown` from the priced lines' declared
    `spend_class` (JUR-05: from DATA, never a jurisdiction branch). A
    `local_labour` line contributes to both `labour_spend` and
    `local_hires_spend`; every priced line contributes to `total_spend`
    and, for this tracer, to `core_expenditure` (no exclusions are
    declared at the cost-localization layer)."""
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


def localize(budget: CanonicalBudget, profile: CityCostProfile) -> LocalizedBudget:
    """Price `budget` against `profile`. A profile cost line whose `label`
    has no matching entry in `budget.line_quantities` is skipped — it is
    not this budget's job to declare every possible cost line, and a
    profile is free to widen with lines a given budget shape does not
    (yet) supply quantities for."""
    cost_line_by_label = {cost_line.label: cost_line for cost_line in profile.cost_lines}

    lines: list[Figure] = []
    categories_priced: set[str] = set()
    for cost_line in profile.cost_lines:
        quantity = budget.line_quantities.get(cost_line.label)
        if quantity is None:
            continue
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
