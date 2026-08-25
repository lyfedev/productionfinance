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
from engine.qualifying_base import CORE_EXPENDITURE_LABEL, EXCLUDED_LINE_ITEMS_TOTAL_LABEL
from engine.rounding import quantize_money

__all__ = [
    "Availability",
    "Eligibility",
    "PerPersonCompensation",
    "assess_availability",
    "assess_eligibility",
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


# `_apply_uplift_stacking` (within-programme, additive to the base rate) and
# multi-programme mutual-exclusivity/summation (engine/pipeline.py) are two
# different mechanisms, both named "stacking" in plain English — the
# scope-freeze note's dimension 4. This label marks a Figure carrying the
# total additive rate from this programme's own uplifts, attached to the
# credit-sequence figure's `inputs`, so `_apply_rate` (which runs after this
# step) can read it without `_apply_uplift_stacking` needing to widen
# `compute_gross_credit`'s call signature.
_UPLIFT_ADDITIONAL_RATE_LABEL = "Uplift stacking additional rate"


def _find_uplift_additional_rate(figure: Figure) -> Decimal:
    """Read the total additive rate `_apply_uplift_stacking` recorded, or
    `Decimal('0')` when no uplifts were declared (the common case — every
    existing rate-structure test with no uplifts continues to add exactly
    zero, unchanged)."""
    for inp in figure.inputs:
        if inp.label == _UPLIFT_ADDITIONAL_RATE_LABEL:
            return inp.value
    return Decimal("0")


def _apply_uplift_stacking(programme: Programme, figure: Figure) -> Figure:
    """Within one programme, uplifts are additive to that programme's own
    base rate, applied in the order the `uplifts` list declares them — the
    order is data, not a code branch (INC-03).

    `stackable` decides whether a given uplift may combine with uplifts
    already applied: a stackable uplift always adds its `additional_rate` to
    the running total; a non-stackable uplift only adds if nothing has been
    applied yet (it cannot combine with anything already taken). This makes
    the result order-dependent: swapping two non-stackable uplifts' declared
    order changes which one survives to contribute — `tests/test_engine_credit.py`
    proves this directly by reversing a fixture's declared `uplifts` list.

    `Programme.requires_separate_application` (a top-level field, distinct
    from `Uplift.requires_separate_application`) is recorded here too: the
    programme is still priced, but a derivation line names the requirement
    so it is never silently dropped when this programme's figure is later
    summed against others in `engine/pipeline.py`.
    """
    if programme.requires_separate_application:
        figure = figure.with_step(
            f"{programme.name}: requires_separate_application is true — this programme is "
            "still priced independently, but claiming it requires filing a separate "
            "application, not a shared one with any programme it stacks with"
        )

    uplifts = programme.rate_structure.uplifts
    if not uplifts:
        return figure.with_step("no uplift stacking rules are declared for this programme")

    applied_rate = Decimal("0")
    applied_any = False
    for uplift in uplifts:
        if uplift.stackable or not applied_any:
            applied_rate += uplift.additional_rate
            applied_any = True
            line = (
                f"uplift {uplift.id!r} ({uplift.name}): additional rate "
                f"{uplift.additional_rate} stacked onto the base rate — running "
                f"additional rate now {applied_rate} (stackable={uplift.stackable})"
            )
        else:
            line = (
                f"uplift {uplift.id!r} ({uplift.name}): stackable is false and an uplift "
                "was already applied earlier in the declared order — skipped, a "
                "non-stackable uplift cannot combine with uplifts already applied "
                "(order is read from data, not a code branch)"
            )
        if uplift.requires_separate_application:
            line = f"{line} — this uplift requires a separate application"
        figure = figure.with_step(line)

    marker = Figure(
        value=applied_rate,
        unit="rate",
        label=_UPLIFT_ADDITIONAL_RATE_LABEL,
        derivation=(
            f"total additional rate from this programme's stackable uplifts, applied in "
            f"declared order: {applied_rate}",
        ),
        inputs=(),
        source_url=figure.source_url,
        date_checked=figure.date_checked,
        confidence=figure.confidence,
        live_fetched_this_run=False,
    )
    return _dataclass_replace(figure, inputs=(*figure.inputs, marker))


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


def _find_excluded_line_items_total(figure: Figure) -> Decimal:
    """Reach the `Excluded line items total` Figure `engine/qualifying_base.py`
    always attaches to the Qualifying base Figure's `inputs` (CR-01, plan
    02-07), and return its value. Mirrors `_find_uplift_additional_rate`:
    returns `Decimal('0')` when the edge is absent — a directly-constructed
    test Figure with an empty `inputs` tuple (predating this plan) still
    works, since "the edge is missing" and "no exclusions declared" both
    correctly carry forward zero reduction."""
    qualifying_base_figure = _find_qualifying_base_input(figure)
    if qualifying_base_figure is None:
        return Decimal("0")
    marker = next(
        (
            inp
            for inp in qualifying_base_figure.inputs
            if inp.label == EXCLUDED_LINE_ITEMS_TOTAL_LABEL
        ),
        None,
    )
    return marker.value if marker is not None else Decimal("0")


def _apply_rate(programme: Programme, figure: Figure) -> Figure:
    rate_structure = programme.rate_structure

    if rate_structure.type == "flat":
        if rate_structure.base_rate is None:
            raise ValueError(
                "rate_structure.type is 'flat' but base_rate is not declared"
            )
        additional_rate = _find_uplift_additional_rate(figure)
        effective_rate = rate_structure.base_rate + additional_rate
        credit_value = figure.value * effective_rate
        line = f"flat rate {rate_structure.base_rate}"
        if additional_rate != Decimal("0"):
            line = (
                f"{line} + uplift stacking additional rate {additional_rate} = "
                f"{effective_rate}"
            )
        line = f"{line} applied to base {figure.value} {figure.unit}"
        if rate_structure.source_note:
            line = f"{line} — {rate_structure.source_note}"
        return figure.with_step(line, value=credit_value)

    if rate_structure.type == "tiered_by_spend":
        if not rate_structure.tiers:
            raise ValueError(
                "rate_structure.type is 'tiered_by_spend' but no tiers are declared"
            )
        raw_credit_value = lookup_flat_rate_by_band(figure.value, rate_structure.tiers)
        additional_rate = _find_uplift_additional_rate(figure)
        credit_value = raw_credit_value + figure.value * additional_rate
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
            f"(02-RESEARCH.md Pitfall 3) — gives {raw_credit_value}"
        )
        if additional_rate != Decimal("0"):
            line = (
                f"{line}; plus uplift stacking additional rate {additional_rate} x base "
                f"= {figure.value * additional_rate} — total {credit_value}"
            )
        if rate_structure.source_note:
            line = f"{line} — {rate_structure.source_note}"
        return figure.with_step(line, value=credit_value)

    if rate_structure.type == "blended_by_ceiling_split":
        # Uplift stacking's additive rate (_find_uplift_additional_rate) is
        # NOT consumed here: a ceiling-split blend already applies two
        # distinct rates to two distinct slices, and no requirement or
        # curated jurisdiction in this phase combines uplift stacking with
        # blended_by_ceiling_split — extending it speculatively (add to
        # both rates? one? a third slice?) would be an unverified guess,
        # exactly the kind of plausible-looking-but-invented behaviour this
        # engine exists to avoid. A future jurisdiction that needs this
        # combination requires a visible design decision, not a silent one.
        #
        # CR-01 (plan 02-07): this branch slices the EFFECTIVE core
        # expenditure — the raw core expenditure with every non-percentage-
        # cap reduction this same function already ran (minimum-spend,
        # excluded line items, the per-person ceiling) carried forward onto
        # it — never the raw core expenditure directly and never `.value` as
        # it stood before this step. The ONE thing this branch legitimately
        # does differently from every other rate branch is that it
        # re-derives the percentage cap per slice from core expenditure
        # rather than trusting it was already applied by
        # `base_definition.type` (SCOPE-FREEZE.md dimension 3's carve-out).
        # That carve-out covers the percentage cap and nothing else —
        # minimum-spend, excluded line items and the per-person ceiling are
        # never covered by it, and CR-01 is exactly what happens when the
        # carve-out is allowed to swallow them too.
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

        # A zero-or-below running base (a binding minimum-spend cliff, or a
        # per-person-ceiling reduction driving the base below zero — which
        # `_apply_per_person_ceiling` does not floor) short-circuits before
        # any slice is rated. This is what makes a binding cliff actually
        # reach the credit, rather than being discarded the way CR-01
        # discarded it.
        if figure.value <= Decimal("0"):
            return figure.with_step(
                "blended_by_ceiling_split: the running qualifying base is "
                f"{figure.value} {figure.unit} — zero or below after the declared "
                "adjustments (minimum-spend cliff and/or per-person ceiling) — no "
                "slice is rated, gross credit is 0",
                value=Decimal("0"),
            )

        # The total reduction this base has already taken that the
        # percentage cap did NOT cause: the excluded-line-items total
        # (engine/qualifying_base.py's always-attached marker) plus the
        # per-person ceiling's own reduction. The latter is exact because
        # `_apply_per_person_ceiling` is the only step between the Figure's
        # construction in `compute_gross_credit` and this branch that
        # changes `.value` — `_apply_uplift_stacking` provably does not (it
        # only ever appends a marker Figure to `inputs`); a future step
        # inserted between them must reckon with this invariant.
        qualifying_base_input = _find_qualifying_base_input(figure)
        assert qualifying_base_input is not None  # guaranteed by the guard clause above
        excluded_line_items_total = _find_excluded_line_items_total(figure)
        per_person_ceiling_reduction = max(
            Decimal("0"), qualifying_base_input.value - figure.value
        )
        total_reduction = max(
            Decimal("0"), excluded_line_items_total + per_person_ceiling_reduction
        )

        core_expenditure = core_expenditure_figure.value
        effective_core_expenditure = max(Decimal("0"), core_expenditure - total_reduction)
        enhanced_threshold = ceiling_split.enhanced_threshold.value
        enhanced_rate = ceiling_split.enhanced_rate
        standard_rate = ceiling_split.standard_rate
        pct_cap = programme.base_definition.pct_core_cap

        enhanced_slice = min(effective_core_expenditure, enhanced_threshold)
        standard_slice = max(Decimal("0"), effective_core_expenditure - enhanced_threshold)
        capped_enhanced_slice = enhanced_slice * pct_cap if pct_cap is not None else enhanced_slice
        capped_standard_slice = standard_slice * pct_cap if pct_cap is not None else standard_slice
        enhanced_amount = capped_enhanced_slice * enhanced_rate
        standard_amount = capped_standard_slice * standard_rate
        credit_value = enhanced_amount + standard_amount

        cap_desc = f"{pct_cap} of slice" if pct_cap is not None else "no percentage cap declared"
        # This line is emitted UNCONDITIONALLY, including when the total
        # reduction is zero — a zero reduction states so explicitly, so
        # silence is never mistaken for "not considered" (PRV-03).
        figure = figure.with_step(
            "blended_by_ceiling_split effective core expenditure: raw core "
            f"expenditure {core_expenditure} {figure.unit}, minus total reduction "
            f"{total_reduction} {figure.unit} (excluded line items "
            f"{excluded_line_items_total} + per-person ceiling {per_person_ceiling_reduction}, "
            "the only adjustments this branch's percentage-cap carve-out never covers) = "
            f"effective core expenditure {effective_core_expenditure} {figure.unit}"
        )
        # Both slices ALWAYS emit a derivation line, even when one is zero —
        # a wholly-enhanced production must still show the standard slice
        # was considered and came to nothing (never silent, PRV-03).
        figure = figure.with_step(
            "blended_by_ceiling_split enhanced slice: effective core expenditure "
            f"{effective_core_expenditure} {figure.unit} split at enhanced_threshold "
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
    """A per-project cap is a rule about what THIS project may be entitled
    to, so it clips the credit value: `min(credit, cap)`. The comparison is
    strictly greater-than — a credit exactly at the cap is not clipped
    (boundary test at cap-1/cap/cap+1). This is unlike the annual programme
    cap below (`_apply_annual_programme_cap`), which never touches `.value`
    at all (RD-04) — the two caps answer genuinely different questions."""
    cap = programme.caps.per_project_cap
    if cap is None:
        return figure.with_step("no per-project cap is declared for this programme")

    if figure.value > cap.value:
        clipped = cap.value
        line = (
            f"per-project cap of {cap.value} {cap.currency} applied — credit "
            f"{figure.value} {figure.unit} exceeds the cap and is clipped to {clipped}"
        )
        return figure.with_step(line, value=clipped)

    line = (
        f"per-project cap of {cap.value} {cap.currency} is declared but not binding "
        f"— credit {figure.value} {figure.unit} does not exceed it (comparison is "
        "strictly greater-than: a credit exactly at the cap is not clipped)"
    )
    return figure.with_step(line)


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

    consumption_check = programme.caps.cap_consumption_check
    check_desc = (
        f"declared consumption-check method: {consumption_check.method}"
        if consumption_check is not None
        else "no cap_consumption_check method is declared"
    )
    line = (
        f"annual programme cap of {cap.amount.value} {cap.amount.currency} "
        f"({cap.period}) declared — {check_desc} — cap existence recorded; the "
        "remaining-allocation figure (if supplied) feeds assess_availability, which "
        "is assessed separately (RD-04) and never reduces this gross credit value"
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

    `annual_cap_remaining` is accepted here for interface stability but is
    NOT consulted by this function — the annual-cap step never changes
    `.value` (RD-04). `assess_availability` below is where a caller's
    remaining-allocation figure is actually consumed; `engine/pipeline.py`
    calls it separately with the same value."""
    del annual_cap_remaining  # accepted for interface stability; consumed by assess_availability

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


@dataclass(frozen=True)
class Eligibility:
    """Whether a production QUALIFIES for a programme — answered completely
    independently of whether the programme's annual allocation still has
    money left in it (`Availability`, below). INC-05 forbids collapsing
    these into one boolean; they are two different questions with two
    different answers, computed here as two separate functions."""

    eligible: bool
    reasons: tuple[str, ...]


def assess_eligibility(
    programme: Programme,
    qualifying_base: Figure,
    *,
    jurisdiction_status: str,
) -> Eligibility:
    """Reasons cover: whether the minimum-spend threshold was met (read from
    `qualifying_base`'s own derivation — `_apply_minimum_spend_check` in
    `engine/qualifying_base.py` already records this unconditionally, so no
    new engine/qualifying_base.py change is needed here), whether the
    jurisdiction's programme is open (`jurisdiction_status !=
    'no_programme_found'`), and whether this programme declares a
    mutual-exclusivity relationship — its actual resolution (which of a
    mutually-exclusive pair is taken) happens at the jurisdiction level in
    `engine/pipeline.py`, not per-programme here, so this only names that it
    was considered.

    An ineligible production still gets a fully computed `Availability`
    answer elsewhere (`assess_availability`) — the two are never fused."""
    reasons: list[str] = []
    eligible = True

    if any(
        "is below the declared minimum-spend threshold" in line
        for line in qualifying_base.derivation
    ):
        eligible = False
        reasons.append(
            "qualifying spend is below the programme's declared minimum-spend threshold"
        )
    else:
        reasons.append("minimum-spend threshold met (or none declared for this programme)")

    if jurisdiction_status == "no_programme_found":
        eligible = False
        reasons.append(
            "jurisdiction.status is 'no_programme_found' — no active programme exists here"
        )
    else:
        reasons.append(f"jurisdiction status is {jurisdiction_status!r} — programme is open")

    if programme.mutually_exclusive_with:
        reasons.append(
            "declares mutually_exclusive_with "
            f"{programme.mutually_exclusive_with} — resolution (which programme is "
            "taken when both would contribute) happens at the jurisdiction level, "
            "in engine/pipeline.py, not here"
        )
    else:
        reasons.append("no mutually-exclusive programme is declared for this programme")

    return Eligibility(eligible=eligible, reasons=tuple(reasons))


@dataclass(frozen=True)
class Availability:
    """Whether the programme's annual allocation still has money left for
    THIS production's credit — a fact about the programme's remaining
    allocation, never about this project's entitlement (that is
    `Eligibility`, above, and the per-project cap in `_apply_per_project_cap`).

    Three-state, never a plain boolean: `available` is `True`/`False` only
    when a remaining-allocation figure was actually supplied; passing none
    yields `None` with a reason naming that consumption state was not
    fetched. Defaulting an unknown to `True` would be the single most
    misleading simplification available in this engine (the Czech Republic
    case in `feasibility-incentives.md`: terms stable, money exhausted
    mid-year — unrepresentable if availability is inferred from the rules
    rather than fetched)."""

    available: bool | None
    reason: str


def assess_availability(
    credit_value: Decimal,
    annual_cap_remaining: Decimal | None,
) -> Availability:
    """`annual_cap_remaining` is `None` whenever the caller has not fetched
    live consumption state for this run (Phase 7's `DataFreshnessGate` owns
    that fetch) — this function NEVER infers a value for it. Remaining
    allocation exactly equal to `credit_value` reports available; one
    dollar below reports unavailable, and no intermediate/partial-award
    state is modelled (`jurisdictions/SCOPE-FREEZE.md`, disclosed
    simplification, not a silent gap)."""
    if annual_cap_remaining is None:
        return Availability(
            available=None,
            reason=(
                "no remaining-allocation figure was supplied for this run — consumption "
                "state was not fetched (Phase 7's DataFreshnessGate owns fetching it); "
                "defaulting an unknown to available would be the single most misleading "
                "simplification available in this engine"
            ),
        )

    if annual_cap_remaining >= credit_value:
        return Availability(
            available=True,
            reason=(
                f"remaining allocation {annual_cap_remaining} is at or above the computed "
                f"credit {credit_value} — this production's credit fits within the "
                "programme's remaining annual allocation"
            ),
        )

    return Availability(
        available=False,
        reason=(
            f"remaining allocation {annual_cap_remaining} is below the computed credit "
            f"{credit_value} — the programme's annual allocation is exhausted for this "
            "production; partial allocation (splitting the award across periods) is "
            "deliberately not modelled in this phase, an explicit disclosed simplification "
            "(jurisdictions/SCOPE-FREEZE.md), never a silent gap"
        ),
    )
