"""Stage `[6]` of the pipeline: `LandedCostAggregator`.

Sums a `LocalizedBudget`'s priced cost lines into one `cost_total`, then
combines it with a (possibly absent) net-cash incentive Figure into
`total_landed_cost`. Every category `COST_CATEGORIES` declares that this
city's profile does not price is a named entry in `not_priced` — NEVER a
`$0` line (D-60: an acknowledged gap is a declared exclusion, not a
fabricated zero). Mirrors `engine/pipeline.py:238-269`'s summation shape:
sum the values, quantize once, derive `confidence`/`basis` from the
combined inputs.

Plan 04-05 (COST-08, D-74/D-75) adds a declared `reporting_currency` to
`aggregate`. When it differs from the localized budget's own currency,
EVERY cost line is converted individually through `engine.fx.convert`
(one quantize per line, via that function's own pinned call) BEFORE
summation — the converted total is therefore the exact `Decimal` sum of
already-quantized converted lines, never a second quantize of the sum.
The FX rate itself is attached to `cost_total.inputs` as its own named
`engine.fx.rate_figure` component (D-75) — visible in the DAG, excluded
from the money sum, exactly the way `price_jurisdiction` carries a
non-contributing programme Figure in `inputs` while excluding it from
`total_value`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from engine.cost_localizer import LocalizedBudget
from engine.figure import Figure, combined_basis, combined_confidence
from engine.fx import convert as fx_convert
from engine.fx import rate_figure as fx_rate_figure
from engine.rounding import quantize_money

__all__ = [
    "COST_CATEGORIES",
    "PERMANENT_EXCLUSIONS",
    "LandedCost",
    "SeasonalityState",
    "aggregate",
    "compute_quarter_invariance",
]

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
class SeasonalityState:
    """Per-city seasonality disclosure (D-66): whether this city's
    committed per-diem snapshot carries a genuine month band, and the
    reason string either way — quoting the per-diem table's own
    `seasonality_note` when the state is `no_month_band`."""

    state: Literal["month_banded", "no_month_band"]
    reason: str


@dataclass(frozen=True)
class LandedCost:
    cost_total: Figure
    total_landed_cost: Figure
    not_priced: tuple[str, ...]
    permanent_exclusions: tuple[str, ...]
    # D-66: which Figure LABELS took a different value across the four
    # start-quarter re-runs, and which did not. Empty tuples (the default)
    # mean "not measured for this LandedCost" — never a claim that nothing
    # is quarter-variant. Populate via `compute_quarter_invariance` below.
    quarter_variant_lines: tuple[str, ...] = ()
    quarter_invariant_lines: tuple[str, ...] = ()
    seasonality_state: SeasonalityState | None = None
    # COST-08/D-74/D-75 (plan 04-05): the currency this total is reported
    # in, the localized budget's own (source) currency, and the FX
    # snapshot's `as_of_date` when a conversion was applied — `None` when
    # `reporting_currency` equalled the source currency (no conversion, no
    # snapshot consulted). A downstream renderer never has to infer any of
    # the three from the Figure tree.
    reporting_currency: str = ""
    source_currency: str = ""
    fx_as_of_date: date | None = None


def compute_quarter_invariance(
    runs: Mapping[str, tuple[Figure, ...]],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Compare N labelled re-runs (keyed by an arbitrary run identifier,
    e.g. a quarter name) and report which Figure LABELS took a different
    `value` in at least one run (`quarter_variant_lines`) versus which took
    the IDENTICAL value in every run that carries that label
    (`quarter_invariant_lines`).

    This is a genuine measurement over the supplied Figures — never a
    declared list of category names (D-66/D-67): mutate one input Figure's
    value and re-call this function, and the label's membership moves
    accordingly. A label present in only SOME runs is treated as variant
    (its presence itself differs across runs) rather than silently
    ignored — an incomplete run is evidence of a difference, not neutral
    information.

    Raises `ValueError` on an empty `runs` mapping — there is nothing to
    compare, and returning `((), ())` for "not measured" would be
    indistinguishable from "measured and found nothing variant."
    """
    if not runs:
        raise ValueError(
            "compute_quarter_invariance() received no runs to compare — supply at "
            "least one labelled re-run's Figures"
        )

    values_by_label: dict[str, set[Decimal]] = {}
    run_count_by_label: dict[str, int] = {}
    for figures in runs.values():
        for figure in figures:
            values_by_label.setdefault(figure.label, set()).add(figure.value)
            run_count_by_label[figure.label] = run_count_by_label.get(figure.label, 0) + 1

    total_runs = len(runs)
    variant: list[str] = []
    invariant: list[str] = []
    for label, values in values_by_label.items():
        if len(values) > 1 or run_count_by_label[label] != total_runs:
            variant.append(label)
        else:
            invariant.append(label)

    return tuple(sorted(variant)), tuple(sorted(invariant))


def _convert_cost_lines(
    cost_inputs: list[Figure], *, source_currency: str, target_currency: str
) -> tuple[list[Figure], Figure]:
    """Convert every Figure in `cost_inputs` from `source_currency` to
    `target_currency` individually through `engine.fx.convert` — ONE
    quantize per line (via `convert`'s own pinned call), never a second
    quantize applied to the eventual sum. Returns the converted lines
    (same order, same labels, so downstream lookups-by-label are
    unaffected) plus the FX rate as its own `Figure` (D-75) — a component,
    never a cost, and never included in the returned lines' values.

    A missing FX snapshot propagates `engine.fx.convert`'s own `ValueError`
    — the city reports a refusal with the stated reason rather than a
    total in the wrong currency or a total silently left unconverted."""
    converted_lines: list[Figure] = []
    for original in cost_inputs:
        converted = fx_convert(original.value, source_currency, target_currency)
        converted_lines.append(
            Figure(
                value=converted.value,
                unit=target_currency,
                label=original.label,
                derivation=(
                    f"{original.label!r}: {original.value} {source_currency} "
                    f"converted to {converted.value} {target_currency} via the "
                    f"committed {source_currency}->{target_currency} FX snapshot "
                    "(engine.fx.convert, one quantize applied to this line only)",
                    *converted.derivation,
                ),
                inputs=(original,),
                source_url=original.source_url,
                date_checked=original.date_checked,
                confidence=original.confidence,
                live_fetched_this_run=False,
                basis=original.basis,
                caveat=original.caveat,
            )
        )
    rate = fx_rate_figure(source_currency, target_currency)
    return converted_lines, rate


def aggregate(
    localized: LocalizedBudget,
    net_cash_figure: Figure | None = None,
    *,
    reporting_currency: str | None = None,
    quarter_variant_lines: tuple[str, ...] = (),
    quarter_invariant_lines: tuple[str, ...] = (),
    seasonality_state: SeasonalityState | None = None,
) -> LandedCost:
    """Sum every localized cost-line Figure into `cost_total`, then combine
    with `net_cash_figure` (a modelled incentive's net-cash Figure, when
    one was priced for this city) into `total_landed_cost`. When
    `net_cash_figure` is absent, `total_landed_cost` equals `cost_total`
    and says so — an unmodelled incentive is never treated as `$0`
    (D-56), it is simply not subtracted.

    `reporting_currency` (COST-08/D-74/D-75) defaults to `localized`'s own
    currency — a same-currency city (e.g. a USD city reported in USD)
    takes an UNCHANGED code path, byte-identical to plan 04-04's
    behaviour, and adds no FX line at all. When it genuinely differs, every
    cost line is converted individually (see `_convert_cost_lines`) before
    summation, and the FX rate is attached to `cost_total.inputs` as its
    own named component — visible, never a hidden multiplication."""
    cost_inputs = list(localized.lines)
    if not cost_inputs:
        raise ValueError(
            f"aggregate(): {localized.city_id!r}'s localized budget priced zero cost "
            "lines — a landed-cost total with no priced input would need a "
            "basis/confidence combination step to default to a fallback value, "
            "which combined_basis (D-59) refuses to do; commit at least one cost "
            "line to this city's profile before aggregating"
        )

    source_currency = localized.currency
    target_currency = reporting_currency or source_currency
    fx_line: Figure | None = None
    fx_as_of_date: date | None = None

    if target_currency != source_currency:
        cost_inputs, fx_line = _convert_cost_lines(
            cost_inputs, source_currency=source_currency, target_currency=target_currency
        )
        fx_as_of_date = fx_line.date_checked
        # Already-quantized converted lines summed directly — no second
        # quantize of the total (the plan's own explicit requirement).
        # Summing exact integer-valued Decimals cannot produce a
        # fractional residue, so this is not merely a style choice: it
        # keeps "the converted total is the exact sum of the converted
        # components" true by construction, never by coincidence.
        cost_total_value = sum((figure.value for figure in cost_inputs), start=Decimal("0"))
    else:
        cost_total_value = quantize_money(
            sum((figure.value for figure in cost_inputs), start=Decimal("0"))
        )

    basis_inputs = [*cost_inputs, fx_line] if fx_line is not None else cost_inputs
    cost_total_derivation: list[str] = [
        f"summed {len(cost_inputs)} localized cost line(s) for "
        f"{localized.city_id!r}: {cost_total_value} {target_currency}",
    ]
    if fx_line is not None:
        cost_total_derivation.append(
            f"reporting currency {target_currency!r} differs from this city's own "
            f"{source_currency!r} — every cost line above was converted "
            "individually before this sum (see each line's own derivation)"
        )
        cost_total_derivation.append(
            f"the FX rate itself ({fx_line.value} {fx_line.unit}) is carried in "
            "this total's inputs as its own named component (D-75) — it "
            "contributes NO money value of its own and is excluded from the sum "
            "above; it carries the rate, not a cost"
        )

    cost_total = Figure(
        value=cost_total_value,
        unit=target_currency,
        label="Total cost (pre-incentive)",
        derivation=tuple(cost_total_derivation),
        inputs=tuple(cost_inputs) + ((fx_line,) if fx_line is not None else ()),
        source_url=None,
        date_checked=None,
        confidence=combined_confidence(basis_inputs),
        live_fetched_this_run=False,
        basis=combined_basis(basis_inputs),
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
        quarter_variant_lines=quarter_variant_lines,
        quarter_invariant_lines=quarter_invariant_lines,
        seasonality_state=seasonality_state,
        reporting_currency=target_currency,
        source_currency=source_currency,
        fx_as_of_date=fx_as_of_date,
    )
