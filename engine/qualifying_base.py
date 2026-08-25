"""Stage 3 of the pipeline: qualifying-base computation.

Dispatches on ``JurisdictionRuleSet.programmes[i].base_definition.type`` —
the ONLY jurisdiction-specific stage per ``.planning/research/ARCHITECTURE.md``
Q1, and even it reads *data* (the declared type string), never
per-jurisdiction Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from engine.figure import Confidence, Figure
from engine.handlers import resolve_handler
from engine.models import BaseDefinition, Programme

__all__ = ["SpendBreakdown", "compute_qualifying_base", "CORE_EXPENDITURE_LABEL"]

# Every qualifying-base handler records the un-capped core expenditure on
# its returned Figure as an entry in `inputs` whose label is exactly this
# string. Plan 02-05's two-rate ceiling split reads this edge, because a
# ceiling split operates on core expenditure *before* any percentage cap
# applies — establishing the edge here (rather than in a later plan) is
# what lets the expansion plans run in parallel.
CORE_EXPENDITURE_LABEL = "Core expenditure (pre-cap)"


@dataclass(frozen=True)
class SpendBreakdown:
    """A localized budget's spend, broken out by the categories the four
    base-definition types read from.

    D-02 interpreter-only boundary: Phase 4 owns cost localisation. Phase 2
    (this engine) never derives a SpendBreakdown itself — it either receives
    one already broken out, or (the tracer's path, ``from_total``) is fed a
    single disclosed qualified-spend figure directly.

    ``line_items`` is a named-component-to-Decimal mapping that
    ``base_definition.excluded_line_items`` (a list of names declared in a
    rule file) subtracts from a computed base. It defaults to empty — most
    programmes declare no excluded line items and never read it.
    """

    total_spend: Decimal
    labour_spend: Decimal
    local_hires_spend: Decimal
    core_expenditure: Decimal
    line_items: dict[str, Decimal] = field(default_factory=dict)

    @classmethod
    def from_total(cls, total: Decimal) -> "SpendBreakdown":
        """Build a SpendBreakdown from a single total when only a total is
        known. This is the D-02 interpreter-only boundary in code: the
        tracer feeds a disclosed qualified-spend figure straight in, with no
        cost-localisation pipeline upstream of it yet."""
        return cls(
            total_spend=total,
            labour_spend=total,
            local_hires_spend=total,
            core_expenditure=total,
        )


def _core_expenditure_figure(
    spend: SpendBreakdown,
    *,
    currency: str,
    source_url: str | None,
    date_checked: date | None,
    confidence: Confidence,
) -> Figure:
    return Figure(
        value=spend.core_expenditure,
        unit=currency,
        label=CORE_EXPENDITURE_LABEL,
        derivation=("core expenditure recorded before any percentage cap applies",),
        inputs=(),
        source_url=source_url,
        date_checked=date_checked,
        confidence=confidence,
        live_fetched_this_run=False,
    )


def _apply_minimum_spend_check(programme: Programme, figure: Figure) -> Figure:
    """A hard step function (INC-09) — never interpolated.

    When `minimum_spend` is declared and the spend is below it, the base is
    `Decimal("0")` with a derivation line saying so. When it is not
    declared, the step still emits a line saying no minimum-spend threshold
    is declared, so silence is never mistaken for "not considered" (PRV-03).
    """
    minimum = programme.minimum_spend
    if minimum is None:
        return figure.with_step("no minimum-spend threshold is declared for this programme")

    if figure.value < minimum.value:
        return figure.with_step(
            f"spend {figure.value} {figure.unit} is below the declared minimum-spend "
            f"threshold of {minimum.value} {minimum.currency} — qualifying base is "
            "$0 (step function, never interpolated)",
            value=Decimal("0"),
        )

    return figure.with_step(
        f"spend {figure.value} {figure.unit} meets the declared minimum-spend "
        f"threshold of {minimum.value} {minimum.currency}"
    )


def _apply_excluded_line_items(
    base_definition: BaseDefinition, spend: SpendBreakdown, figure: Figure
) -> Figure:
    """Subtract every named component in ``excluded_line_items``, in the
    order the rule file declares them.

    Subtraction of a set of disjoint components is order-independent by
    arithmetic — the result is identical regardless of declaration order,
    which ``tests/test_engine_qualifying_base.py`` asserts directly rather
    than assuming. A name not present in ``spend.line_items`` raises
    ``KeyError`` rather than silently treating it as zero.
    """
    for item_name in base_definition.excluded_line_items:
        try:
            item_value = spend.line_items[item_name]
        except KeyError as exc:
            raise KeyError(
                f"base_definition.excluded_line_items names {item_name!r}, which "
                "SpendBreakdown.line_items does not carry a value for"
            ) from exc
        figure = figure.with_step(
            f"excluded line item {item_name!r}: subtracting {item_value} {figure.unit} "
            "(declared in base_definition.excluded_line_items)",
            value=figure.value - item_value,
        )
    return figure


def _lesser_of_pct_core_or_actual_local(
    programme: Programme, spend: SpendBreakdown
) -> tuple[Decimal, str]:
    """UK-style lesser-of formula: the smaller of a declared percentage of
    core expenditure, or actual local core expenditure.

    Per the D-02 interpreter-only boundary, no cost-localisation pipeline
    exists yet — every dollar of ``SpendBreakdown.core_expenditure`` is
    treated as the "actual local core expenditure" candidate at this stage.
    When the two candidates are exactly equal, the value is returned once
    (never summed/doubled) and the derivation says so explicitly, so an
    equal-value tie is visibly handled rather than accidentally correct.
    """
    pct_cap = programme.base_definition.pct_core_cap
    if pct_cap is None:
        raise ValueError(
            f"{programme.name}: base_definition.type is "
            "'lesser_of_pct_core_or_actual_local' but pct_core_cap is not declared"
        )

    pct_candidate = spend.core_expenditure * pct_cap
    actual_candidate = spend.core_expenditure

    if pct_candidate == actual_candidate:
        return pct_candidate, (
            "base type: lesser_of_pct_core_or_actual_local — "
            f"{programme.name}: {pct_cap} of core expenditure ({pct_candidate}) and "
            f"actual local core expenditure ({actual_candidate}) were equal; "
            "returning that value once, never doubled"
        )
    if pct_candidate < actual_candidate:
        return pct_candidate, (
            "base type: lesser_of_pct_core_or_actual_local — "
            f"{programme.name}: {pct_cap} of core expenditure ({pct_candidate}) is "
            f"the lesser candidate, below actual local core expenditure "
            f"({actual_candidate})"
        )
    return actual_candidate, (
        "base type: lesser_of_pct_core_or_actual_local — "
        f"{programme.name}: actual local core expenditure ({actual_candidate}) is "
        f"the lesser candidate, below {pct_cap} of core expenditure ({pct_candidate})"
    )


def _custom(programme: Programme, spend: SpendBreakdown) -> tuple[Decimal, str]:
    """The ``custom`` escape hatch: resolve ``custom_handler_id`` against the
    closed ``HANDLER_REGISTRY`` and call it. An identifier absent from the
    registry raises ``KeyError`` naming it — never a silent fallback to
    ``total_qualified_spend`` or any other default base."""
    handler_id = programme.base_definition.custom_handler_id
    if handler_id is None:
        raise ValueError(
            f"{programme.name}: base_definition.type is 'custom' but "
            "custom_handler_id is not declared"
        )
    handler = resolve_handler(handler_id)
    raw_value = handler(programme, spend)
    return raw_value, (
        f"base type: custom — {programme.name} uses custom_handler_id "
        f"{handler_id!r} (HANDLER_REGISTRY) -> {raw_value}"
    )


def _raw_base(programme: Programme, spend: SpendBreakdown) -> tuple[Decimal, str]:
    """Compute the raw (pre-excluded-items, pre-minimum-spend) base value and
    its derivation line, dispatching on ``base_definition.type``.

    Every branch reads only declared data — never a jurisdiction identifier
    string (JUR-05)."""
    base_type = programme.base_definition.type

    if base_type == "total_qualified_spend":
        return spend.total_spend, (
            f"base type: total_qualified_spend — {programme.name} counts total "
            "qualified spend"
        )
    if base_type == "labour_only":
        return spend.labour_spend, (
            f"base type: labour_only — {programme.name} counts labour spend only"
        )
    if base_type == "local_hires_only":
        return spend.local_hires_spend, (
            f"base type: local_hires_only — {programme.name} counts spend paid to "
            "locally-hired personnel only"
        )
    if base_type == "lesser_of_pct_core_or_actual_local":
        return _lesser_of_pct_core_or_actual_local(programme, spend)
    if base_type == "custom":
        return _custom(programme, spend)

    # Every other value is excluded by BaseDefinition.type's closed Literal
    # at Pydantic validation time (T-02-02) — this branch is unreachable.
    raise AssertionError(f"unreachable base_definition.type {base_type!r}")


def compute_qualifying_base(
    programme: Programme,
    spend: SpendBreakdown,
    *,
    currency: str = "USD",
    source_url: str | None = None,
    date_checked: date | None = None,
    confidence: Confidence = "validated",
) -> Figure:
    """Dispatch on `base_definition.type` and return a `QualifyingBase` Figure.

    All four declarative types plus the `custom` escape hatch are
    implemented. Every returned Figure carries the un-capped core
    expenditure as an `inputs` entry labelled `CORE_EXPENDITURE_LABEL`,
    has `excluded_line_items` subtracted in declaration order, and is then
    passed through the minimum-spend cliff.
    """
    core_expenditure = _core_expenditure_figure(
        spend,
        currency=currency,
        source_url=source_url,
        date_checked=date_checked,
        confidence=confidence,
    )

    raw_value, derivation_line = _raw_base(programme, spend)

    figure = Figure(
        value=raw_value,
        unit=currency,
        label="Qualifying base",
        derivation=(derivation_line,),
        inputs=(core_expenditure,),
        source_url=source_url,
        date_checked=date_checked,
        confidence=confidence,
        live_fetched_this_run=False,
    )

    figure = _apply_excluded_line_items(programme.base_definition, spend, figure)

    # The minimum-spend cliff is evaluated against the *qualifying base*
    # produced by the dispatch above (net of excluded_line_items), never
    # against spend.total_spend / the raw input total. A jurisdiction whose
    # base definition is labour-only asks whether the qualifying labour
    # cleared the bar, not whether the production's total budget did — the
    # same class of ordering hazard as applying a per-person ceiling to the
    # output instead of the base (02-RESEARCH.md Pitfall 4).
    return _apply_minimum_spend_check(programme, figure)
