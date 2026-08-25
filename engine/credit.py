"""Stage 4 of the pipeline: the ordered, data-declared `CreditCalculator`
adjustment sequence.

Five steps, in exactly this order and never another: per-person ceiling,
uplift stacking, tier or blend rate, per-project cap, annual programme cap.
Every step appends a derivation line unconditionally, including when it does
nothing — a no-op emits a line stating that no such rule is declared for
this programme, so silence is never mistaken for "not considered" (PRV-03).
Two adjacent no-op steps emit two distinct lines and are never collapsed.
"""

from __future__ import annotations

from decimal import Decimal

from engine.figure import Figure
from engine.models import Programme, Tier
from engine.rounding import quantize_money

__all__ = [
    "compute_gross_credit",
    "lookup_flat_rate_by_band",
    "blend_two_rates_by_ceiling",
]


def lookup_flat_rate_by_band(base: Decimal, tiers: list[Tier]) -> Decimal:
    """`tiered_by_spend`: the WHOLE base gets ONE rate, selected by which
    band `base` falls into. Verified (`02-RESEARCH.md` Finding 3) against
    Connecticut's Christmas Always: $3,865,005 (falls in the >$1,000,000
    band) x 0.30 = $1,159,501.50, quantized -> $1,159,502, exact match to
    the disclosed figure. This is a lookup, NOT a marginal/blended
    calculation — never share a code path with `blend_two_rates_by_ceiling`
    below (Pitfall 3: conflating the two produced a ~$175,000 error against
    the disclosed CT figure when verified this session)."""
    for tier in tiers:
        if tier.threshold_low <= base and (
            tier.threshold_high is None or base < tier.threshold_high
        ):
            return base * tier.rate
    raise ValueError(f"base {base} matches no declared tier band")


def blend_two_rates_by_ceiling(
    base: Decimal,
    enhanced_threshold: Decimal,
    enhanced_rate: Decimal,
    standard_rate: Decimal,
) -> Decimal:
    """`blended_by_ceiling_split`: UK-style. The first `enhanced_threshold`
    of base gets `enhanced_rate`; the remainder gets `standard_rate`. Both
    slices are computed and SUMMED — genuinely different from the lookup
    above, never share a code path with it."""
    enhanced_slice = min(base, enhanced_threshold)
    standard_slice = max(Decimal(0), base - enhanced_threshold)
    return enhanced_slice * enhanced_rate + standard_slice * standard_rate


def _apply_per_person_ceiling(programme: Programme, figure: Figure) -> Figure:
    ceiling = programme.per_person_ceiling
    if ceiling.applies:
        raise NotImplementedError(
            "per-person ceiling application (W-2 cap / loan-out withholding "
            "schedule) is implemented in plan 02-05"
        )
    line = "no per-person ceiling applies in this jurisdiction"
    if ceiling.note:
        line = f"{line} — {ceiling.note}"
    return figure.with_step(line)


def _apply_uplift_stacking(programme: Programme, figure: Figure) -> Figure:
    uplifts = programme.rate_structure.uplifts
    if uplifts:
        raise NotImplementedError(
            "uplift stacking (independent-dollar summation across "
            "programmes) is implemented in plan 02-06"
        )
    return figure.with_step("no uplift stacking rules are declared for this programme")


def _apply_rate(programme: Programme, figure: Figure) -> Figure:
    rate_structure = programme.rate_structure

    if rate_structure.type == "flat":
        if rate_structure.base_rate is None:
            raise ValueError(
                "rate_structure.type is 'flat' but base_rate is not declared"
            )
        credit_value = figure.value * rate_structure.base_rate
        line = (
            f"flat rate {rate_structure.base_rate} applied to base "
            f"{figure.value} {figure.unit}"
        )
        if rate_structure.source_note:
            line = f"{line} — {rate_structure.source_note}"
        return figure.with_step(line, value=credit_value)

    if rate_structure.type in (
        "tiered_by_spend",
        "blended_by_ceiling_split",
        "headcount_scaled",
    ):
        raise NotImplementedError(
            f"rate_structure.type {rate_structure.type!r} is implemented in plan 02-05"
        )

    raise AssertionError(
        f"unreachable rate_structure.type {rate_structure.type!r} — closed enum"
    )


def _apply_per_project_cap(programme: Programme, figure: Figure) -> Figure:
    cap = programme.caps.per_project_cap
    if cap is None:
        return figure.with_step("no per-project cap is declared for this programme")
    raise NotImplementedError("per-project cap clipping is implemented in plan 02-06")


def _apply_annual_programme_cap(programme: Programme, figure: Figure) -> Figure:
    # RD-04: an annual programme cap never reduces gross credit. It is a
    # fact about the programme's remaining allocation, not this project's
    # entitlement — cap EXISTENCE is rule data (recorded here); cap
    # CONSUMPTION and the resulting availability answer are Phase 7's
    # DataFreshnessGate / plan 02-06's assess_availability, an entirely
    # separate determination. This step always records the cap's existence
    # (or absence) and never changes `.value`.
    #
    # 02-RESEARCH.md Open Question 1 (recorded here, not resolved): does
    # every curated/future jurisdiction truly apply caps as one global
    # post-hoc clip on the final credit, or do some (e.g. New Mexico's
    # per-component dollar caps) need caps applied to sub-components of the
    # credit before they are summed? NY and CT (this phase's two build
    # targets) are both consistent with a single global cap; a future
    # jurisdiction that needs per-component caps would require a visible
    # reinterpretation here, not a silent one.
    cap = programme.caps.annual_programme_cap
    if cap is None or cap.amount is None:
        return figure.with_step("no annual programme cap is declared for this programme")

    line = (
        f"annual programme cap of {cap.amount.value} {cap.amount.currency} "
        f"({cap.period}) declared — cap existence recorded; availability is "
        "assessed separately (RD-04) and never reduces this gross credit value"
    )
    return figure.with_step(line)


def compute_gross_credit(
    programme: Programme,
    qualifying_base: Figure,
    *,
    annual_cap_remaining: Decimal | None = None,
) -> Figure:
    """Run the five adjustment steps in exactly this order and never
    another: per-person ceiling, uplift stacking, tier or blend rate,
    per-project cap, annual programme cap. `annual_cap_remaining` is
    accepted for the future live-consumption path (Phase 7); this plan does
    not yet consult it, since the annual cap step never changes `.value`
    (RD-04)."""
    del annual_cap_remaining  # accepted for interface stability; unused until 02-06/Phase 7

    figure = Figure(
        value=qualifying_base.value,
        unit=qualifying_base.unit,
        label="Gross credit",
        derivation=(
            f"starting base: {qualifying_base.value} {qualifying_base.unit} "
            f"(from {qualifying_base.label})",
        ),
        inputs=(qualifying_base,),
        source_url=qualifying_base.source_url,
        date_checked=qualifying_base.date_checked,
        confidence=qualifying_base.confidence,
        live_fetched_this_run=False,
    )

    figure = _apply_per_person_ceiling(programme, figure)
    figure = _apply_uplift_stacking(programme, figure)
    figure = _apply_rate(programme, figure)
    figure = _apply_per_project_cap(programme, figure)
    figure = _apply_annual_programme_cap(programme, figure)

    # Quantise to whole dollars through quantize_money at the single point
    # a computed credit becomes a reportable figure.
    quantized = quantize_money(figure.value)
    return figure.with_step(
        f"gross credit quantized to whole dollars: {quantized}", value=quantized
    )
