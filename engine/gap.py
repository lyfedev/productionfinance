"""Stage `[8]` of the pipeline: the component-by-component gap
decomposition (OUT-02, D-75).

`decompose_gap` takes two cities' already-aggregated `LandedCost` totals —
BOTH already expressed in the same `reporting_currency` via
`engine.landed_cost.aggregate(..., reporting_currency=...)`, which this
module asserts rather than re-derives — and produces one `Figure` per
matched cost-line label, plus a first-class `Currency` component when
either city required an FX conversion to reach `reporting_currency`
(D-75: "currency is a first-class component of the gap decomposition, not
a hidden conversion" — PROJECT.md itself names currency alongside labour,
housing, stages, equipment and travel as a landed-cost component).

**Design note on the per-label components.** Each per-label component
diffs the two cities' cost-line values AT FACE VALUE — i.e. before any FX
conversion was applied to either city (a "rate of one" comparison) — so
that the entire currency effect lands on the single `Currency` line rather
than being silently baked into every other row. This is what makes
`headline_gap.value == sum(component.value for component in components)`
an exact identity rather than an approximation: for a city with no
conversion, "face value" and "converted value" are the same number by
construction (see `_conversion_effect` below).

Components are matched **by label**, never by position — mirrors
`engine.net_cash._find_qualifying_base_figure`'s by-label lookup
discipline exactly. After plan 04-04, every committed cost profile prices
all ten `engine.landed_cost.COST_CATEGORIES`, so two committed cities'
`cost_total.inputs` trees carry the identical set of line labels; a label
present in only one city is therefore a real bug (a schema drift, a typo
in a department label) and raises rather than silently contributing zero.

JURISDICTION-AGNOSTIC by construction (JUR-05/D-53): every branch below
dispatches on `Figure.unit`/`Figure.label`/`LandedCost.fx_as_of_date` —
data already resolved by `engine.landed_cost.aggregate` — never a
hard-coded jurisdiction identifier string.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from engine.figure import Figure, combined_basis, combined_confidence
from engine.fx import rate_figure as fx_rate_figure
from engine.landed_cost import LandedCost
from engine.rounding import quantize_money

__all__ = ["GapDecomposition", "decompose_gap", "largest_component"]

CURRENCY_COMPONENT_LABEL = "Currency"


@dataclass(frozen=True)
class GapDecomposition:
    """The full component-by-component gap between two cities (OUT-02).

    `sign_convention` is stated ONCE here and repeated, verbatim, in every
    component's own derivation (so a reader who only sees one row still
    knows how to interpret its sign). `components` includes a zero-delta
    row for a label identical in both cities (never dropped — a dropped
    row is indistinguishable from an unpriced one) and a `Currency`
    component whenever either city required an FX conversion.
    """

    city_a_id: str
    city_b_id: str
    sign_convention: str
    components: tuple[Figure, ...]
    headline_gap: Figure


def largest_component(decomposition: GapDecomposition) -> Figure:
    """The component with the greatest absolute delta — a purely
    descriptive fact (no verb, no "responsible for", no "driven by"). Plan
    04-07's sensitivity output builds on top of this and must not inherit
    a prescriptive framing from here."""
    return max(decomposition.components, key=lambda component: abs(component.value))


def _money_lines_by_label(landed: LandedCost, reporting_currency: str) -> dict[str, Figure]:
    """The individual, already-converted cost-line Figures inside
    `landed.cost_total.inputs` — excluding the FX rate Figure `aggregate`
    attaches when a conversion applied (D-75): a rate Figure's `unit` is
    `"{quote} per {base}"`, which never equals a bare currency code, so
    filtering on `unit == reporting_currency` cleanly separates the two
    without any label-prefix guessing."""
    return {
        figure.label: figure
        for figure in landed.cost_total.inputs
        if figure.unit == reporting_currency
    }


def _face_value(figure: Figure, *, was_converted: bool) -> Decimal:
    """The cost-line's value AT FACE VALUE — before any FX conversion.
    `engine.landed_cost._convert_cost_lines` wraps every converted line as
    `Figure(..., inputs=(original,), ...)`, so the pre-conversion value is
    `figure.inputs[0].value` when this city underwent conversion, or
    `figure.value` itself when it did not (the two are numerically
    identical for a same-currency city, but only one code path is ever
    correct — the wrapping only happens when a conversion applied)."""
    if was_converted:
        return figure.inputs[0].value
    return figure.value


def _conversion_effect(landed: LandedCost, money_lines: list[Figure]) -> Decimal:
    """How much of this city's OWN cost total is attributable to the FX
    conversion — `converted total - the same figures summed at a rate of
    one`. Exactly `Decimal("0")` for a city that required no conversion
    (its face value and converted value are identical by construction),
    never approximated."""
    if landed.fx_as_of_date is None:
        return Decimal("0")
    converted_total = sum((figure.value for figure in money_lines), start=Decimal("0"))
    face_total = sum(
        (_face_value(figure, was_converted=True) for figure in money_lines), start=Decimal("0")
    )
    return converted_total - face_total


def _fold_reductions_into_targets(
    money_lines: dict[str, Figure], *, was_converted: bool
) -> tuple[dict[str, Decimal], dict[str, tuple[Figure, ...]]]:
    """Split `money_lines` (label -> possibly FX-wrapped Figure) into (1)
    face-value totals for every PRIMARY cost-line label, with any INC-10
    exemption reduction (D-76) that targets it already folded in, and (2)
    the top-level Figure(s) — the primary line plus any reduction(s)
    targeting it — that ride along in that label's `inputs`, so the
    click-through tree still reaches every reduction's own evidence.

    A reduction is identified STRUCTURALLY, never by sniffing its label
    text: `engine.exemptions.exemption_reductions` always emits a
    NEGATIVE value, and its pre-conversion Figure always carries the
    target cost line as its sole `inputs[0]` (`engine.cost_localizer
    .localize`'s post-loop exemption wiring). This is what lets two
    cities legitimately offer DIFFERENT exemption types — New York: sales
    tax on equipment; Los Angeles: hotel occupancy tax on housing
    (WINDOWS.md entries 15-16) — without a one-sided exemption LABEL ever
    being mistaken for a missing cost category (COST-06's ten categories
    are what must match; a stackable reduction is not itself one of
    them)."""
    face_figures = {
        label: (figure.inputs[0] if was_converted else figure)
        for label, figure in money_lines.items()
    }
    totals: dict[str, Decimal] = {
        label: figure.value for label, figure in face_figures.items() if figure.value >= 0
    }
    extra_inputs: dict[str, list[Figure]] = {label: [] for label in totals}
    for label, figure in face_figures.items():
        if figure.value >= 0:
            continue
        if not figure.inputs:
            raise ValueError(
                f"gap: cost line {label!r} carries a negative value with no target "
                "input recorded — only a D-76 exemption reduction is ever expected "
                "to be negative, and every one targets another cost line by "
                "construction (engine.cost_localizer.localize)"
            )
        target_label = figure.inputs[0].label
        if target_label not in totals:
            raise ValueError(
                f"gap: exemption reduction {label!r} targets {target_label!r}, which "
                "this city's own cost lines do not separately price"
            )
        totals[target_label] += figure.value
        extra_inputs[target_label].append(money_lines[label])

    inputs_by_label = {
        label: (money_lines[label], *extra_inputs[label]) for label in totals
    }
    return totals, inputs_by_label


def decompose_gap(
    city_a_id: str,
    city_a: LandedCost,
    city_b_id: str,
    city_b: LandedCost,
    *,
    reporting_currency: str,
) -> GapDecomposition:
    """Decompose the gap between `city_a` and `city_b` into one `Figure`
    per matched cost-line label, plus a `Currency` component when either
    city required an FX conversion to reach `reporting_currency`.

    Both `LandedCost` arguments MUST already have been produced by
    `engine.landed_cost.aggregate(..., reporting_currency=reporting_currency)`
    — this function asserts that precondition rather than re-deriving it,
    so the comparison is never silently made across two different
    currencies (D-74/D-75).
    """
    for city_id, landed in ((city_a_id, city_a), (city_b_id, city_b)):
        if landed.reporting_currency != reporting_currency:
            raise ValueError(
                f"decompose_gap: {city_id!r}'s LandedCost was aggregated with "
                f"reporting_currency={landed.reporting_currency!r}, not the requested "
                f"{reporting_currency!r} — both cities must be aggregated into the "
                "SAME reporting currency before their gap can be decomposed "
                "(D-74/D-75); a cross-currency comparison is never made implicitly"
            )

    sign_convention = (
        f"a positive component value means {city_a_id!r} costs more than "
        f"{city_b_id!r} for that component; a negative value means {city_b_id!r} "
        f"costs more — computed as {city_a_id!r}'s value minus {city_b_id!r}'s value, "
        "always in that order"
    )

    by_label_a = _money_lines_by_label(city_a, reporting_currency)
    by_label_b = _money_lines_by_label(city_b, reporting_currency)

    occurs_a = city_a.fx_as_of_date is not None
    occurs_b = city_b.fx_as_of_date is not None

    # Fold any INC-10 exemption reduction into the cost-line label it
    # targets BEFORE matching (D-76) — a stackable reduction's own label
    # is city-specific by design (New York's sales-tax exemption on
    # equipment; Los Angeles's hotel-occupancy exemption on housing), so
    # matching on the raw label set would raise on two cities that both
    # correctly price all ten COST_CATEGORIES. See
    # `_fold_reductions_into_targets`'s docstring for the full rationale.
    totals_a, inputs_a = _fold_reductions_into_targets(by_label_a, was_converted=occurs_a)
    totals_b, inputs_b = _fold_reductions_into_targets(by_label_b, was_converted=occurs_b)

    labels_a = set(totals_a)
    labels_b = set(totals_b)
    if labels_a != labels_b:
        only_in_a = sorted(labels_a - labels_b)
        only_in_b = sorted(labels_b - labels_a)
        raise ValueError(
            f"decompose_gap: {city_a_id!r} and {city_b_id!r} do not price the same "
            f"set of cost-line labels — present only in {city_a_id!r}: {only_in_a}; "
            f"present only in {city_b_id!r}: {only_in_b}. After plan 04-04 every "
            "committed cost profile prices all ten COST_CATEGORIES (with any "
            "stackable D-76 reduction already folded into the line it targets); "
            "a one-sided label here is a real schema drift, never a silent zero"
        )

    components: list[Figure] = []
    for label in sorted(labels_a):
        a_face = totals_a[label]
        b_face = totals_b[label]
        delta = quantize_money(a_face - b_face)
        a_related = inputs_a[label]
        b_related = inputs_b[label]

        currency_note = (
            "both cities' values above are AT FACE VALUE (before any FX "
            "conversion) — the separate 'Currency' component below carries the "
            "entire FX effect on its own line (D-75), so this row is never a "
            "hidden partial conversion"
            if (occurs_a or occurs_b)
            else "neither city required an FX conversion for this comparison"
        )
        reduction_note = (
            f"{label!r} carries {len(a_related) - 1 + len(b_related) - 1} stackable "
            "D-76 exemption reduction(s) already folded into the face value above "
            "— see this component's own `inputs` for each reduction's evidence"
            if (len(a_related) > 1 or len(b_related) > 1)
            else f"{label!r} carries no exemption reduction for either city"
        )

        components.append(
            Figure(
                value=delta,
                unit=reporting_currency,
                label=label,
                derivation=(
                    sign_convention,
                    f"{label!r}: {city_a_id!r} = {a_face} vs {city_b_id!r} = {b_face} "
                    f"-> delta = {delta} {reporting_currency}",
                    currency_note,
                    reduction_note,
                ),
                inputs=(*a_related, *b_related),
                source_url=None,
                date_checked=None,
                confidence=combined_confidence((*a_related, *b_related)),
                live_fetched_this_run=False,
                basis=combined_basis((*a_related, *b_related)),
            )
        )

    if occurs_a or occurs_b:
        effect_a = (
            _conversion_effect(city_a, list(by_label_a.values())) if occurs_a else Decimal("0")
        )
        effect_b = (
            _conversion_effect(city_b, list(by_label_b.values())) if occurs_b else Decimal("0")
        )
        currency_value = quantize_money(effect_a - effect_b)

        rate_figures: list[Figure] = []
        if occurs_a:
            rate_figures.append(fx_rate_figure(city_a.source_currency, reporting_currency))
        if occurs_b:
            rate_figures.append(fx_rate_figure(city_b.source_currency, reporting_currency))

        effect_lines = []
        if occurs_a:
            effect_lines.append(
                f"{city_a_id!r}: converting from {city_a.source_currency} to "
                f"{reporting_currency} moved its total by {effect_a} "
                f"{reporting_currency} relative to a rate of one"
            )
        if occurs_b:
            effect_lines.append(
                f"{city_b_id!r}: converting from {city_b.source_currency} to "
                f"{reporting_currency} moved its total by {effect_b} "
                f"{reporting_currency} relative to a rate of one"
            )

        single_rate = rate_figures[0] if len(rate_figures) == 1 else None
        components.append(
            Figure(
                value=currency_value,
                unit=reporting_currency,
                label=CURRENCY_COMPONENT_LABEL,
                derivation=(
                    sign_convention,
                    "how much of the headline gap is attributable to FX conversion "
                    "alone — computed as the difference between each converted "
                    "city's own conversion effect (its converted total minus the "
                    "same figures summed at a rate of one), an arithmetic fact "
                    "rather than a claim",
                    *effect_lines,
                    f"net currency contribution to the {city_a_id!r} minus "
                    f"{city_b_id!r} gap: {currency_value} {reporting_currency}",
                ),
                inputs=tuple(rate_figures),
                source_url=single_rate.source_url if single_rate is not None else None,
                date_checked=single_rate.date_checked if single_rate is not None else None,
                confidence=combined_confidence(rate_figures),
                live_fetched_this_run=False,
                basis=combined_basis(rate_figures),
            )
        )

    headline_value = city_a.cost_total.value - city_b.cost_total.value
    headline_gap = Figure(
        value=headline_value,
        unit=reporting_currency,
        label="Headline gap",
        derivation=(
            sign_convention,
            f"{city_a_id!r} cost total {city_a.cost_total.value} {reporting_currency} "
            f"minus {city_b_id!r} cost total {city_b.cost_total.value} "
            f"{reporting_currency} = {headline_value} {reporting_currency}",
            f"equals the exact sum of the {len(components)} component(s) below — "
            "asserted with equality, not a tolerance",
        ),
        inputs=tuple(components),
        source_url=None,
        date_checked=None,
        confidence=combined_confidence(components),
        live_fetched_this_run=False,
        basis=combined_basis(components),
    )

    return GapDecomposition(
        city_a_id=city_a_id,
        city_b_id=city_b_id,
        sign_convention=sign_convention,
        components=tuple(components),
        headline_gap=headline_gap,
    )
