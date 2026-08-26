"""Stage `[6]` of the pipeline: `LandedCostAggregator`.

Sums a `LocalizedBudget`'s priced cost lines into one `cost_total`, then
combines it with a (possibly absent) net-cash incentive Figure into
`total_landed_cost`. Every category `COST_CATEGORIES` declares that this
city's profile does not price is a named entry in `not_priced` — NEVER a
`$0` line (D-60: an acknowledged gap is a declared exclusion, not a
fabricated zero). Mirrors `engine/pipeline.py:238-269`'s summation shape:
sum the values, quantize once, derive `confidence`/`basis` from the
combined inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from engine.cost_localizer import LocalizedBudget
from engine.figure import Figure, combined_basis, combined_confidence
from engine.rounding import quantize_money

__all__ = ["COST_CATEGORIES", "PERMANENT_EXCLUSIONS", "LandedCost", "aggregate"]

# The canonical, closed cost-category vocabulary (mirrors
# `engine/cost_profile.py::CostCategory`'s Literal — that Literal is the
# schema-level closed set; this tuple is the runtime set `not_priced` is
# computed against). PROJECT.md names these components verbatim.
COST_CATEGORIES: tuple[str, ...] = (
    "labour",
    "fringe",
    "housing",
    "per_diem",
    "flights",
    "stages",
    "equipment",
    "permits",
    "locations",
    "trucking",
)

# D-60: acknowledged gaps this model deliberately does not price, ever,
# rendered as a declared exclusion list attached to every total — never a
# `$0` line item pretending the cost is zero.
PERMANENT_EXCLUSIONS: tuple[str, ...] = (
    "overtime",
    "turnaround penalties",
    "meal penalties",
    "kit fees",
    "non-union local differentials",
    "negotiated hotel rates",
)


@dataclass(frozen=True)
class LandedCost:
    cost_total: Figure
    total_landed_cost: Figure
    not_priced: tuple[str, ...]
    permanent_exclusions: tuple[str, ...]


def aggregate(localized: LocalizedBudget, net_cash_figure: Figure | None = None) -> LandedCost:
    """Sum every localized cost-line Figure into `cost_total`, then combine
    with `net_cash_figure` (a modelled incentive's net-cash Figure, when
    one was priced for this city) into `total_landed_cost`. When
    `net_cash_figure` is absent, `total_landed_cost` equals `cost_total`
    and says so — an unmodelled incentive is never treated as `$0`
    (D-56), it is simply not subtracted."""
    cost_inputs = list(localized.lines)
    if not cost_inputs:
        raise ValueError(
            f"aggregate(): {localized.city_id!r}'s localized budget priced zero cost "
            "lines — a landed-cost total with no priced input would need a "
            "basis/confidence combination step to default to a fallback value, "
            "which combined_basis (D-59) refuses to do; commit at least one cost "
            "line to this city's profile before aggregating"
        )
    cost_total_value = quantize_money(
        sum((figure.value for figure in cost_inputs), start=Decimal("0"))
    )

    cost_total = Figure(
        value=cost_total_value,
        unit=localized.currency,
        label="Total cost (pre-incentive)",
        derivation=(
            f"summed {len(cost_inputs)} localized cost line(s) for "
            f"{localized.city_id!r}: {cost_total_value} {localized.currency}",
        ),
        inputs=tuple(cost_inputs),
        source_url=None,
        date_checked=None,
        confidence=combined_confidence(cost_inputs),
        live_fetched_this_run=False,
        basis=combined_basis(cost_inputs),
    )

    not_priced = tuple(
        category for category in COST_CATEGORIES if category not in localized.categories_priced
    )

    total_inputs: list[Figure] = [cost_total]
    derivation_lines: list[str] = [
        f"cost total (pre-incentive): {cost_total.value} {cost_total.unit}",
        f"not priced by this city's profile: {', '.join(not_priced) if not_priced else 'none'}",
    ]

    if net_cash_figure is not None and net_cash_figure.unit == cost_total.unit:
        total_inputs.append(net_cash_figure)
        total_landed_value = quantize_money(cost_total.value - net_cash_figure.value)
        derivation_lines.append(
            f"less modelled net-cash incentive ({net_cash_figure.value} "
            f"{net_cash_figure.unit}) = {total_landed_value} {cost_total.unit}"
        )
    elif net_cash_figure is not None:
        total_inputs.append(net_cash_figure)
        total_landed_value = cost_total.value
        derivation_lines.append(
            f"incentive net-cash figure is denominated in {net_cash_figure.unit}, "
            f"not {cost_total.unit} — not netted against cost total without a dated "
            "FX conversion (Phase 4's currency component, D-74/D-75); total landed "
            "cost currently equals cost total alone"
        )
    else:
        total_landed_value = cost_total.value
        derivation_lines.append(
            "no incentive is modelled for this city — total landed cost equals "
            "cost total alone, never a fabricated $0 incentive (D-56)"
        )

    total_landed_cost = Figure(
        value=total_landed_value,
        unit=cost_total.unit,
        label="Total landed cost",
        derivation=tuple(derivation_lines),
        inputs=tuple(total_inputs),
        source_url=None,
        date_checked=None,
        confidence=combined_confidence(total_inputs),
        live_fetched_this_run=False,
        basis=combined_basis(total_inputs),
    )

    return LandedCost(
        cost_total=cost_total,
        total_landed_cost=total_landed_cost,
        not_priced=not_priced,
        permanent_exclusions=PERMANENT_EXCLUSIONS,
    )
