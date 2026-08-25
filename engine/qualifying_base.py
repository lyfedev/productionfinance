"""Stage 3 of the pipeline: qualifying-base computation.

Dispatches on ``JurisdictionRuleSet.programmes[i].base_definition.type`` —
the ONLY jurisdiction-specific stage per ``.planning/research/ARCHITECTURE.md``
Q1, and even it reads *data* (the declared type string), never
per-jurisdiction Python.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from engine.figure import Confidence, Figure
from engine.models import Programme

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
    """

    total_spend: Decimal
    labour_spend: Decimal
    local_hires_spend: Decimal
    core_expenditure: Decimal

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


def _total_qualified_spend(
    programme: Programme,
    spend: SpendBreakdown,
    *,
    currency: str,
    source_url: str | None,
    date_checked: date | None,
    confidence: Confidence,
) -> Figure:
    core_expenditure = _core_expenditure_figure(
        spend,
        currency=currency,
        source_url=source_url,
        date_checked=date_checked,
        confidence=confidence,
    )

    figure = Figure(
        value=spend.total_spend,
        unit=currency,
        label="Qualifying base",
        derivation=(
            f"base type: total_qualified_spend — {programme.name} counts total "
            "qualified spend",
        ),
        inputs=(core_expenditure,),
        source_url=source_url,
        date_checked=date_checked,
        confidence=confidence,
        live_fetched_this_run=False,
    )

    return _apply_minimum_spend_check(programme, figure)


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

    `total_qualified_spend` is implemented. The other three declared types
    and the `custom` escape hatch raise `NotImplementedError` naming plan
    02-03, which implements them, rather than returning a wrong number.
    """
    base_type = programme.base_definition.type

    if base_type == "total_qualified_spend":
        return _total_qualified_spend(
            programme,
            spend,
            currency=currency,
            source_url=source_url,
            date_checked=date_checked,
            confidence=confidence,
        )

    if base_type in ("labour_only", "lesser_of_pct_core_or_actual_local", "local_hires_only"):
        raise NotImplementedError(
            f"base_definition.type {base_type!r} is implemented in plan 02-03"
        )

    # base_type == "custom" (the custom_handler_id escape hatch)
    raise NotImplementedError(
        "base_definition.type 'custom' (the custom_handler_id escape hatch) is "
        "implemented in plan 02-03"
    )
