"""UI-11 — chosen-currency display with dual disclosure (Phase 6, plan
06-04). A visitor picks a DISPLAY currency; this module decides what to
show on screen, never what to price.

Pure display layer, structurally separate from the pricing pipeline:
`engine.landed_cost.aggregate` -> `engine.fx.convert` remain the ONLY
path that produces `RankedCity.total_landed_cost`/`cost_only_total`/
`incentive_figure` — this module never mutates a `Figure`, never calls
`engine.fx.convert`, and its output never feeds back into
`app.services.compare.build_comparison`. Golden totals (D-78) are
therefore unaffected by anything in this file, by construction.

UI-11's own honesty requirements, enforced structurally, across TWO
distinct mechanisms this module provides:

**1. The chosen-currency conversion** (`DualCurrencyDisplay`/
`build_city_displays`/`display_figure`) — a visitor's own display-
currency PICK, applied forward from whatever currency a total is
CURRENTLY expressed in (`engine.landed_cost.aggregate`'s own
`reporting_currency`, USD today, D-55/D-75) to their chosen one:
  - The figure's own value/unit is ALWAYS shown; a converted figure is
    added ALONGSIDE it, never in its place (`original_value`/
    `original_unit` are always populated; `converted_value` is additive).
  - A converted figure is visibly marked as converted and carries its
    own FX rate, that rate's date, and whether the rate was live or the
    D-89 committed-snapshot fallback (`rate_origin`).
  - The rate itself is never invented. Every conversion goes through
    `app.services.cache_policy.resolve_fx` — the single sanctioned
    live-or-disclosed-fallback entry point `app/services/spec.py`
    already uses for its own AGT-10 FX disclosures, mirrored here rather
    than re-implemented. A pair with no live result AND no committed
    fallback snapshot (`engine.fx`'s own D-74 refusal, raised as
    `ValueError`) surfaces as an explicit `conversion_refusal` — never a
    guessed number.
  One `resolve_fx` call per DISTINCT source currency per request, never
  one per figure: several figures sharing a currency (e.g. every New
  York total) reuse the SAME resolved rate.

**2. The original-currency disclosure** (`OriginalCurrencyFigure`/
`build_original_currency_figures`/`reconstruct_source_currency_total`)
— the UNCONDITIONAL case the plan's own must-haves name explicitly ("a
US state's credit is denominated in USD and a UK figure in GBP"):
`engine.landed_cost.aggregate` converts EVERY cost line into
`reporting_currency` before a `RankedCity`'s totals are even built, so a
city whose OWN priced currency (`LandedCost.source_currency`, e.g. GBP
for London) differs from `reporting_currency` (USD) never carries its
TRUE original-currency total as its own `Figure` object at all — only
the converted USD total. This mechanism reconstructs that true original
figure from data the engine ALREADY disclosed (never re-derived, never
touching `engine/`): `RankedCity.cost_only_total` is, by
`engine.landed_cost.aggregate`'s own construction, ALWAYS a pure sum of
its cost lines — never netted against an incentive — so a ONE-LEVEL walk
over its OWN `.inputs` (deliberately NOT the recursive, deduplicating
walk `app.services.provenance.collect_rate_figures` performs — see
`reconstruct_source_currency_total`'s own docstring for why deduping
leaves would silently undercount a genuine reconstruction sum), summing
each converted line's single pre-conversion `.inputs[0]` value
(`engine.landed_cost._convert_cost_lines`'s own documented structure),
reconstructs the exact original total — shown ALWAYS, independent of
any visitor display-currency choice,
because the honesty gap it closes ("what did the government actually
publish, in its own currency") exists regardless of what a visitor
happens to have selected. `RankedCity.total_landed_cost` reuses the SAME
reconstruction ONLY when `incentive_figure is None` (provably no
netting occurred, so `total_landed_cost` equals `cost_only_total`
exactly) — this module refuses to guess at a netted total's
pre-conversion value rather than risk a silently wrong reconstruction;
that combination (a netted incentive on a non-reporting-currency city)
never arises against the currently committed floor-city set, where the
one city needing reconstruction (London) has no modelled incentive.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from engine.figure import Figure
from engine.fx import SUPPORTED_CURRENCY_CODES
from engine.ranker import RankedCity
from engine.rounding import quantize_money

if TYPE_CHECKING:
    from app.services.live_fx import FxResolution

__all__ = [
    "DISPLAY_CURRENCIES",
    "DualCurrencyDisplay",
    "OriginalCurrencyFigure",
    "build_city_displays",
    "build_original_currency_figures",
    "display_figure",
    "reconstruct_source_currency_total",
]

# Bounded to the exact pairs a committed fallback snapshot could ever
# exist for (`engine.fx.SUPPORTED_CURRENCY_CODES`, re-exported here as
# the single source of truth) — a display currency this module could
# never actually convert to/from is never offered to a visitor at all.
DISPLAY_CURRENCIES: tuple[str, ...] = SUPPORTED_CURRENCY_CODES


@dataclass(frozen=True)
class DualCurrencyDisplay:
    """One figure's dual-currency display state. `original_value`/
    `original_unit` are the figure's OWN value/unit, unchanged — always
    rendered. `converted_value` is `None` whenever no conversion is
    needed (the figure's own unit already IS `display_currency`) OR a
    conversion was attempted and refused (see `conversion_refusal`) —
    NEVER a guessed number in either case."""

    figure_id: str
    original_value: Decimal
    original_unit: str
    display_currency: str
    converted_value: Decimal | None
    rate: Decimal | None
    rate_origin: str | None
    rate_date: str | None
    disclosure: str | None
    conversion_refusal: str | None


def _resolve_rates(
    source_currencies: Sequence[str], display_currency: str, on_date: date
) -> dict[str, FxResolution | ValueError]:
    """One `resolve_fx` call per DISTINCT source currency that differs
    from `display_currency`. A currency pair with no live result and no
    committed fallback (`engine.fx`'s D-74 refusal, raised as
    `ValueError` all the way up through `app.services.live_fx
    .resolve_fx`) is caught HERE and stored as the exception itself —
    never lets one unconvertible figure crash the whole comparison
    render; `display_figure` turns a stored exception into an explicit
    `conversion_refusal` instead."""
    from app.services.cache_policy import resolve_fx

    resolved: dict[str, FxResolution | ValueError] = {}
    for base in sorted({currency for currency in source_currencies if currency != display_currency}):
        try:
            resolved[base] = resolve_fx(base, display_currency, on_date)
        except ValueError as exc:
            resolved[base] = exc
    return resolved


def display_figure(
    figure: Figure,
    display_currency: str,
    rate_or_error: FxResolution | ValueError | None,
) -> DualCurrencyDisplay:
    """Build one figure's `DualCurrencyDisplay` from an ALREADY-resolved
    rate (or refusal) for `figure.unit` -> `display_currency`. Never
    resolves a rate itself — see `_resolve_rates`/`build_city_displays`
    for why: one resolution per distinct currency per request, not one
    per figure."""
    if figure.unit == display_currency or rate_or_error is None:
        return DualCurrencyDisplay(
            figure_id=figure.figure_id,
            original_value=figure.value,
            original_unit=figure.unit,
            display_currency=display_currency,
            converted_value=None,
            rate=None,
            rate_origin=None,
            rate_date=None,
            disclosure=None,
            conversion_refusal=None,
        )

    if isinstance(rate_or_error, ValueError):
        return DualCurrencyDisplay(
            figure_id=figure.figure_id,
            original_value=figure.value,
            original_unit=figure.unit,
            display_currency=display_currency,
            converted_value=None,
            rate=None,
            rate_origin=None,
            rate_date=None,
            disclosure=None,
            conversion_refusal=str(rate_or_error),
        )

    resolution = rate_or_error
    converted_value = quantize_money(figure.value * resolution.rate)
    return DualCurrencyDisplay(
        figure_id=figure.figure_id,
        original_value=figure.value,
        original_unit=figure.unit,
        display_currency=display_currency,
        converted_value=converted_value,
        rate=resolution.rate,
        rate_origin=resolution.origin,
        rate_date=resolution.fetched_at or resolution.snapshot_date,
        disclosure=resolution.disclosure,
        conversion_refusal=None,
    )


def build_city_displays(
    cities: Sequence[RankedCity], display_currency: str, *, on_date: date
) -> dict[str, DualCurrencyDisplay]:
    """One `DualCurrencyDisplay` per money `Figure` a ranked-list row
    shows (`total_landed_cost`, `cost_only_total`, and `incentive_figure`
    when present), keyed by `Figure.figure_id` — a template looks its own
    figure up by `figure.figure_id` rather than this module re-deriving
    which row a `Figure` belongs to."""
    figures: list[Figure] = []
    for city in cities:
        figures.append(city.total_landed_cost)
        figures.append(city.cost_only_total)
        if city.incentive_figure is not None:
            figures.append(city.incentive_figure)

    rates = _resolve_rates([figure.unit for figure in figures], display_currency, on_date)
    return {
        figure.figure_id: display_figure(figure, display_currency, rates.get(figure.unit))
        for figure in figures
    }


@dataclass(frozen=True)
class OriginalCurrencyFigure:
    """UI-11's unconditional case: `source_value`/`source_currency` is
    the TRUE pre-conversion total for a `RankedCity` whose own priced
    currency differs from `reporting_currency` — reconstructed from the
    engine's own disclosed `Figure` tree (see module docstring,
    mechanism 2). Shown ALWAYS alongside the reporting-currency figure,
    independent of any visitor display-currency choice."""

    source_currency: str
    source_value: Decimal


def reconstruct_source_currency_total(cost_only_total: Figure, source_currency: str) -> Decimal | None:
    """Reconstruct the TRUE pre-conversion total, in `source_currency`,
    from `cost_only_total`'s own disclosed `Figure` tree — a ONE-LEVEL
    walk over `cost_only_total.inputs`, deliberately NOT a recursive,
    deduplicating walk (`app.services.provenance.collect_rate_figures`
    is the wrong tool here: it dedupes LEAVES by content for a PRINTABLE
    rate list, which silently undercounts a genuine reconstruction sum
    whenever the identical underlying rate object legitimately
    contributes to more than one cost line — this function summed every
    OCCURRENCE, matching what the engine actually added).

    This mirrors `engine.landed_cost._convert_cost_lines`'s own exact,
    documented structure: when a conversion occurred, EVERY entry in
    `cost_only_total.inputs` is either one of the converted cost lines —
    each carrying exactly ONE input, the untouched pre-conversion
    original, still denominated in `source_currency` — or the trailing
    FX-rate component itself (a genuine leaf with ZERO inputs, therefore
    never matching the one-input pattern below and excluded by
    construction, not by a currency-code guess). Summing each matching
    entry's single input's `.value` reproduces the engine's own
    documented invariant verbatim: 'the converted total is the exact sum
    of the converted components.'

    Returns `None` when no entry matches this pattern at all
    (`cost_only_total`'s own unit already IS `source_currency` — nothing
    was converted, so there is no separate original figure to show)."""
    original_values = [
        entry.inputs[0].value
        for entry in cost_only_total.inputs
        if len(entry.inputs) == 1 and entry.inputs[0].unit == source_currency
    ]
    if not original_values:
        return None
    return sum(original_values, start=Decimal(0))


def build_original_currency_figures(
    cities: Sequence[RankedCity],
) -> dict[str, OriginalCurrencyFigure]:
    """For every city whose OWN priced currency
    (`landed_cost.source_currency`) differs from the reporting currency
    its totals are expressed in (`landed_cost.reporting_currency`),
    attach the reconstructed original to BOTH `cost_only_total` (always
    safe — a pure sum by construction) and `total_landed_cost` (ONLY
    when `incentive_figure is None`, i.e. provably no netting occurred —
    see module docstring for why a netted total is never reconstructed
    here). Keyed by `figure_id`, mirroring `build_city_displays`."""
    result: dict[str, OriginalCurrencyFigure] = {}
    for city in cities:
        source = city.landed_cost.source_currency
        target = city.landed_cost.reporting_currency
        if not source or not target or source == target:
            continue
        reconstructed = reconstruct_source_currency_total(city.cost_only_total, source)
        if reconstructed is None:
            continue
        original = OriginalCurrencyFigure(source_currency=source, source_value=reconstructed)
        result[city.cost_only_total.figure_id] = original
        if city.incentive_figure is None:
            result[city.total_landed_cost.figure_id] = original
    return result
