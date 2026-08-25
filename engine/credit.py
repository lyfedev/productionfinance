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

from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import replace as _dataclass_replace
from datetime import date
from decimal import Decimal
from typing import Literal

from engine.figure import Figure
from engine.models import PerPersonCeiling, Programme, Tier
from engine.qualifying_base import CORE_EXPENDITURE_LABEL
from engine.rounding import quantize_money

__all__ = [
    "PerPersonCompensation",
    "blend_two_rates_by_ceiling",
    "compute_gross_credit",
    "lookup_flat_rate_by_band",
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
    raise ValueError(f"base {base} matches no declared tier band (declared bands: {tiers})")


def blend_two_rates_by_ceiling(
    base: Decimal,
    enhanced_threshold: Decimal,
    enhanced_rate: Decimal,
    standard_rate: Decimal,
    *,
    pct_cap: Decimal | None = None,
) -> Decimal:
    """`blended_by_ceiling_split`: UK-style. The first `enhanced_threshold`
    of `base` gets `enhanced_rate`; the remainder gets `standard_rate`.

    Split-then-cap ordering (recorded decision, `02-05-PLAN.md`): each slice
    is computed FIRST, then — if `pct_cap` is declared — EACH slice is
    capped to `pct_cap` of itself, and only then is each capped slice
    multiplied by its own rate. Both capped-and-rated amounts are SUMMED —
    genuinely different arithmetic from `lookup_flat_rate_by_band` above,
    never share a code path with it.

    Verified against the UK worked example (`feasibility-incentives.md`):
    base=18,000,000, enhanced_threshold=15,000,000, enhanced_rate=0.53,
    standard_rate=0.34, pct_cap=0.80 -> enhanced_slice=15,000,000, capped to
    12,000,000, x 0.53 = 6,360,000; standard_slice=3,000,000, capped to
    2,400,000, x 0.34 = 816,000; total **7,176,000** exactly.

    The WRONG, cap-before-split ordering — capping the whole base first
    (18,000,000 x 0.80 = 14,400,000, entirely below the 15,000,000 ceiling,
    so all of it takes the enhanced rate: 14,400,000 x 0.53 = **7,632,000**)
    — is a different function entirely and is never computed by this one.
    """
    enhanced_slice = min(base, enhanced_threshold)
    standard_slice = max(Decimal(0), base - enhanced_threshold)
    if pct_cap is not None:
        enhanced_slice = enhanced_slice * pct_cap
        standard_slice = standard_slice * pct_cap
    return enhanced_slice * enhanced_rate + standard_slice * standard_rate


@dataclass(frozen=True)
class PerPersonCompensation:
    """One named individual's compensation on a specific production —
    production-specific data, never rule-file data (a rule file declares
    the *ceiling*, not who was paid what). Passed into `compute_gross_credit`
    as an explicit parameter rather than threaded through the jurisdiction
    schema."""

    role: str
    amount: Decimal
    payment_route: Literal["w2", "loanout"]


def _w2_excess(compensation: Decimal, cap: Decimal) -> Decimal:
    """The comparison is strictly greater-than: compensation exactly at the
    cap has zero excess. Never negative — `max` floors it at Decimal('0')."""
    return max(Decimal("0"), compensation - cap)


def _select_loanout_rate(
    ceiling: PerPersonCeiling, production_date: date | None
) -> tuple[Decimal, str]:
    """Select the loan-out withholding rate in effect for `production_date`
    from the declared schedule — never a single scalar (SOURCE-TRUTH.md
    SRC-05's five-tier declining Georgia schedule is the concrete proof this
    must be a lookup-by-effective-date table). Falls back to the scalar
    `loanout_withholding_rate` only when no schedule is declared at all."""
    if ceiling.loanout_withholding_schedule:
        if production_date is None:
            raise ValueError(
                "a loanout_withholding_schedule is declared but no production_date "
                "was supplied to select a band from it"
            )
        for tier in ceiling.loanout_withholding_schedule:
            if tier.effective_from <= production_date and (
                tier.effective_to is None or production_date <= tier.effective_to
            ):
                band_desc = (
                    f"{tier.effective_from} through {tier.effective_to}"
                    if tier.effective_to is not None
                    else f"{tier.effective_from} onward"
                )
                return tier.loanout_withholding_rate, band_desc
        raise ValueError(
            f"production_date {production_date} matches no declared band in "
            f"loanout_withholding_schedule ({ceiling.loanout_withholding_schedule})"
        )
    if ceiling.loanout_withholding_rate is not None:
        return ceiling.loanout_withholding_rate, "single declared rate (no dated schedule)"
    raise ValueError(
        "loanout_exempt is true but neither loanout_withholding_rate nor "
        "loanout_withholding_schedule is declared on per_person_ceiling"
    )


def _record_loanout_withholding(
    ceiling: PerPersonCeiling,
    figure: Figure,
    comp: PerPersonCompensation,
    production_date: date | None,
) -> Figure:
    """Loan-out route, exempt from the per-person ceiling: the base is left
    untouched and a SEPARATE withholding-obligation Figure is attached to
    `figure.inputs` (never subtracted from the credit or from net cash — it
    is a liability on the loan-out entity, a different party)."""
    rate, band_desc = _select_loanout_rate(ceiling, production_date)
    withholding_value = comp.amount * rate

    # An unconfirmed schedule entry is still used, but every figure derived
    # from it — the withholding obligation itself, and the credit figure
    # this step returns — reports `researched` rather than `validated`
    # (the weaker-tier-always-wins convention `combined_confidence` already
    # establishes elsewhere in this codebase).
    confidence = "researched" if ceiling.loanout_withholding_confirmed is False else figure.confidence

    withholding_figure = Figure(
        value=withholding_value,
        unit=figure.unit,
        label=f"Loan-out withholding obligation — {comp.role}",
        derivation=(
            f"{comp.role}: loan-out payment {comp.amount} {figure.unit} x withholding "
            f"rate {rate} ({band_desc}) = {withholding_value} {figure.unit} — a liability "
            "on the loan-out entity, NOT subtracted from the credit or from net cash",
        ),
        inputs=(),
        source_url=figure.source_url,
        date_checked=figure.date_checked,
        confidence=confidence,
        live_fetched_this_run=False,
    )

    line = (
        f"{comp.role}: paid via loan-out, exempt from the per-person ceiling — full "
        f"{comp.amount} {figure.unit} qualifies for the base; a separate withholding "
        f"obligation of {withholding_value} {figure.unit} is recorded (see inputs), "
        "never subtracted from this credit"
    )
    stepped = figure.with_step(line)
    return _dataclass_replace(
        stepped,
        inputs=(*stepped.inputs, withholding_figure),
        confidence=confidence,
    )


def _apply_per_person_ceiling(
    programme: Programme,
    figure: Figure,
    per_person_compensations: Sequence[PerPersonCompensation],
    production_date: date | None,
) -> Figure:
    ceiling = programme.per_person_ceiling

    # The ceiling adjusts the BASE, not the output of the rate step — never
    # "simplify" this into a post-hoc clip on the credit dollar amount.
    # 02-RESEARCH.md Pitfall 4 verified by execution that applying the same
    # clip to the output instead of the base gives a different, wrong
    # number: a $2,000,000 W-2 lead against a $500,000 cap removes
    # $1,500,000 from the BASE before the rate multiplies it.
    if not ceiling.applies:
        line = "no per-person ceiling applies in this jurisdiction"
        if ceiling.note:
            line = f"{line} — {ceiling.note}"
        return figure.with_step(line)

    if not per_person_compensations:
        return figure.with_step(
            "a per-person ceiling applies in this jurisdiction, but no per-person "
            "compensation lines were supplied for this production — base unchanged"
        )

    for comp in per_person_compensations:
        if comp.payment_route == "loanout" and ceiling.loanout_exempt:
            figure = _record_loanout_withholding(ceiling, figure, comp, production_date)
            continue

        # W-2 route (and any non-exempt loan-out route, treated identically):
        # reduce the base by the excess over the declared cap. The
        # comparison is strictly greater-than — compensation exactly at the
        # cap has zero excess.
        cap = ceiling.w2_cap_amount
        if cap is None:
            figure = figure.with_step(
                f"{comp.role}: a per-person ceiling applies but no w2_cap_amount is "
                "declared for this programme — compensation qualifies in full"
            )
            continue

        excess = _w2_excess(comp.amount, cap.value)
        if excess > Decimal("0"):
            figure = figure.with_step(
                f"{comp.role}: W-2 compensation {comp.amount} {figure.unit} exceeds "
                f"the declared per-person cap of {cap.value} {cap.currency} by "
                f"{excess} {figure.unit} — base reduced by {excess}",
                value=figure.value - excess,
            )
        else:
            figure = figure.with_step(
                f"{comp.role}: W-2 compensation {comp.amount} {figure.unit} is at or "
                f"below the declared per-person cap of {cap.value} {cap.currency} — "
                "no reduction (comparison is strictly greater-than: compensation "
                "exactly at the cap has zero excess)"
            )

    return figure


def _apply_uplift_stacking(programme: Programme, figure: Figure) -> Figure:
    uplifts = programme.rate_structure.uplifts
    if uplifts:
        raise NotImplementedError(
            "uplift stacking (independent-dollar summation across "
            "programmes) is implemented in plan 02-06"
        )
    return figure.with_step("no uplift stacking rules are declared for this programme")


def _find_qualifying_base_input(figure: Figure) -> Figure | None:
    """The credit sequence's working `figure` carries the original
    `QualifyingBase` Figure as one of its `inputs` (set once, at
    construction, in `compute_gross_credit`) — found by label rather than by
    position, since a loan-out withholding obligation may also have been
    appended to `inputs` by the per-person-ceiling step above."""
    return next((inp for inp in figure.inputs if inp.label == "Qualifying base"), None)


def _find_core_expenditure_figure(figure: Figure) -> Figure | None:
    """Reach the un-capped `Core expenditure (pre-cap)` Figure through the
    `inputs` tuple of the `QualifyingBase` Figure — the edge every
    qualifying-base dispatch path preserves (plan 02-03)."""
    qualifying_base_figure = _find_qualifying_base_input(figure)
    if qualifying_base_figure is None:
        return None
    return next(
        (inp for inp in qualifying_base_figure.inputs if inp.label == CORE_EXPENDITURE_LABEL),
        None,
    )


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

    if rate_structure.type == "tiered_by_spend":
        if not rate_structure.tiers:
            raise ValueError(
                "rate_structure.type is 'tiered_by_spend' but no tiers are declared"
            )
        credit_value = lookup_flat_rate_by_band(figure.value, rate_structure.tiers)
        matched_tier = next(
            tier
            for tier in rate_structure.tiers
            if tier.threshold_low <= figure.value
            and (tier.threshold_high is None or figure.value < tier.threshold_high)
        )
        upper = matched_tier.threshold_high if matched_tier.threshold_high is not None else "∞"
        line = (
            "tiered_by_spend cliff lookup: the WHOLE base "
            f"{figure.value} {figure.unit} falls in the band "
            f"[{matched_tier.threshold_low}, {upper}) — takes the single rate "
            f"{matched_tier.rate}, never a marginal/blended calculation "
            f"(02-RESEARCH.md Pitfall 3) — gives {credit_value}"
        )
        if rate_structure.source_note:
            line = f"{line} — {rate_structure.source_note}"
        return figure.with_step(line, value=credit_value)

    if rate_structure.type == "blended_by_ceiling_split":
        ceiling_split = rate_structure.ceiling_split
        if (
            ceiling_split is None
            or ceiling_split.enhanced_threshold is None
            or ceiling_split.enhanced_rate is None
            or ceiling_split.standard_rate is None
        ):
            raise ValueError(
                "rate_structure.type is 'blended_by_ceiling_split' but ceiling_split "
                "is not fully declared (enhanced_threshold, enhanced_rate, standard_rate)"
            )
        core_expenditure_figure = _find_core_expenditure_figure(figure)
        if core_expenditure_figure is None:
            raise ValueError(
                f"blend_two_rates_by_ceiling requires the {CORE_EXPENDITURE_LABEL!r} "
                "inputs edge on the qualifying base, which is missing here — never "
                "fall back to the already-capped qualifying-base value, which is the "
                "wrong-ordering bug wearing a disguise"
            )

        core_expenditure = core_expenditure_figure.value
        enhanced_threshold = ceiling_split.enhanced_threshold.value
        enhanced_rate = ceiling_split.enhanced_rate
        standard_rate = ceiling_split.standard_rate
        pct_cap = programme.base_definition.pct_core_cap

        enhanced_slice = min(core_expenditure, enhanced_threshold)
        standard_slice = max(Decimal("0"), core_expenditure - enhanced_threshold)
        capped_enhanced_slice = enhanced_slice * pct_cap if pct_cap is not None else enhanced_slice
        capped_standard_slice = standard_slice * pct_cap if pct_cap is not None else standard_slice
        enhanced_amount = capped_enhanced_slice * enhanced_rate
        standard_amount = capped_standard_slice * standard_rate
        credit_value = enhanced_amount + standard_amount

        cap_desc = f"{pct_cap} of slice" if pct_cap is not None else "no percentage cap declared"
        # Both slices ALWAYS emit a derivation line, even when one is zero —
        # a wholly-enhanced production must still show the standard slice
        # was considered and came to nothing (never silent, PRV-03).
        figure = figure.with_step(
            "blended_by_ceiling_split enhanced slice: core expenditure "
            f"{core_expenditure} {figure.unit} split at enhanced_threshold "
            f"{enhanced_threshold} — enhanced slice {enhanced_slice}, capped "
            f"({cap_desc}) to {capped_enhanced_slice}, x rate {enhanced_rate} = "
            f"{enhanced_amount}"
        )
        line = (
            "blended_by_ceiling_split standard slice: remainder above "
            f"enhanced_threshold is {standard_slice}, capped ({cap_desc}) to "
            f"{capped_standard_slice}, x rate {standard_rate} = {standard_amount} — "
            f"total gross credit (enhanced + standard) = {credit_value}"
        )
        if rate_structure.source_note:
            line = f"{line} — {rate_structure.source_note}"
        return figure.with_step(line, value=credit_value)

    if rate_structure.type == "headcount_scaled":
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
    per_person_compensations: Sequence[PerPersonCompensation] = (),
    production_date: date | None = None,
    annual_cap_remaining: Decimal | None = None,
) -> Figure:
    """Run the five adjustment steps in exactly this order and never
    another: per-person ceiling, uplift stacking, tier or blend rate,
    per-project cap, annual programme cap.

    `per_person_compensations` and `production_date` are production-specific
    facts (who was paid what, on what date) — never rule-file data — so they
    are accepted as explicit keyword arguments rather than threaded through
    the jurisdiction schema. Both default to empty/`None`, which is exactly
    the case every jurisdiction with `per_person_ceiling.applies: false`
    (e.g. New York) exercises: the per-person-ceiling step's no-op branch
    never inspects them.

    `annual_cap_remaining` is accepted for the future live-consumption path
    (Phase 7); this plan does not yet consult it, since the annual cap step
    never changes `.value` (RD-04)."""
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

    figure = _apply_per_person_ceiling(
        programme, figure, per_person_compensations, production_date
    )
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
