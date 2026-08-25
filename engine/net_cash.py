"""Stage 5 of the pipeline: `NetCashConverter`.

Exactly four pure functions keyed by `mechanism` — never one function per
jurisdiction (ARCHITECTURE.md Anti-Pattern 1). Each deducts the audit fee
(cliff-tiered by spend threshold, GA-style — plan 02-04) then applies the
mechanism-specific conversion, and reports `ArrivalTiming` alongside the
resulting `NetCash` Figure.

Explicit invariant (`02-RESEARCH.md` A1.5): net cash output NEVER feeds back
into stage 3's qualifying-base input for the same production/jurisdiction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from engine.figure import Figure
from engine.models import AuditFeeTier, Programme
from engine.rounding import quantize_money

__all__ = [
    "ArrivalTiming",
    "NetCashResult",
    "convert_to_net_cash",
    "nonrefundable_credit",
    "rebate_grant",
    "refundable",
    "transferable",
]

# The label `compute_gross_credit` (engine/credit.py) gives the QualifyingBase
# Figure it always stores as one entry of `gross_credit.inputs`. Found by
# label, never by position — a loan-out withholding obligation may also have
# been appended to `inputs` by the per-person-ceiling step (engine/credit.py).
_QUALIFYING_BASE_LABEL = "Qualifying base"


@dataclass(frozen=True)
class ArrivalTiming:
    """When the cash is expected to arrive. Display only, never discounted
    to present value in Phase 2 (the explicit scope cut recorded in
    `jurisdictions/SCOPE-FREEZE.md` item 8)."""

    estimated_date: date | None
    typical_days: int | None
    reason: str


@dataclass(frozen=True)
class NetCashResult:
    """`low`/`high`/`point` are all equal for a mechanism with no rate
    range. For a mechanism whose conversion is a published range, `point`
    is `None` and the `high`/`low` Figures' derivation names both bounds
    and their source — a single midpoint must never be presented as a
    point estimate."""

    low: Figure
    high: Figure
    point: Figure | None
    arrival: ArrivalTiming


def _find_qualifying_base_figure(gross_credit: Figure) -> Figure:
    """Reach the `QualifyingBase` Figure `compute_gross_credit` always
    records as one entry of `gross_credit.inputs`, by label rather than
    position (mirrors `engine/credit.py::_find_qualifying_base_input`)."""
    for candidate in gross_credit.inputs:
        if candidate.label == _QUALIFYING_BASE_LABEL:
            return candidate
    raise ValueError(
        f"gross_credit Figure {gross_credit.label!r} carries no "
        f"{_QUALIFYING_BASE_LABEL!r} input — the audit fee cliff lookup needs "
        "the qualifying base value to select a spend band"
    )


def _select_audit_fee_tier(spend: Decimal, schedule: list[AuditFeeTier]) -> AuditFeeTier:
    """Cliff lookup, the same half-open-band shape as
    `engine/credit.py::lookup_flat_rate_by_band`: the band whose low
    threshold is at or below `spend` and whose high threshold is above it
    (or null). A spend exactly at a band's low threshold belongs to THAT
    band; a spend exactly at a band's high threshold belongs to the NEXT
    one. A spend matching no declared band raises — a schedule with a hole
    in it is a rule-file bug and must surface, never silently deduct
    nothing."""
    for tier in schedule:
        if tier.spend_threshold_low <= spend and (
            tier.spend_threshold_high is None or spend < tier.spend_threshold_high
        ):
            return tier
    raise ValueError(
        f"qualified spend {spend} matches no declared audit fee band "
        f"(declared bands: {schedule}) — a schedule with a hole in it must "
        "surface, never silently deduct nothing"
    )


def _deduct_audit_fee(programme: Programme, gross_credit: Figure) -> Figure:
    """An empty `fee_schedule` means no fee is modelled at all — deducts
    exactly `Decimal('0')` and says so. A non-empty schedule selects the
    band the qualifying base's spend falls into (cliff lookup) and deducts
    that band's declared `fee_primary`."""
    schedule = programme.audit.fee_schedule
    if not schedule:
        return gross_credit.with_step(
            "no audit fee schedule is declared for this programme — $0 deducted"
        )

    qualifying_base_figure = _find_qualifying_base_figure(gross_credit)
    spend = qualifying_base_figure.value
    tier = _select_audit_fee_tier(spend, schedule)
    fee = tier.fee_primary
    upper = tier.spend_threshold_high if tier.spend_threshold_high is not None else "∞"
    return gross_credit.with_step(
        f"audit fee: qualified spend {spend} {gross_credit.unit} falls in the "
        f"declared band [{tier.spend_threshold_low}, {upper}) — deducting the "
        f"declared fee of {fee} {gross_credit.unit}",
        value=gross_credit.value - fee,
    )


def refundable(programme: Programme, gross_credit: Figure) -> Figure:
    """Deduct the audit fee (an empty fee schedule deducts exactly $0); no
    further conversion for a refundable mechanism."""
    net = _deduct_audit_fee(programme, gross_credit)
    net = net.with_step(
        "refundable mechanism: net cash equals gross credit less audit fee, "
        "no further conversion"
    )
    quantized = quantize_money(net.value)
    return net.with_step(
        f"net cash quantized: {quantized} {net.unit}", value=quantized
    )


def rebate_grant(programme: Programme, gross_credit: Figure) -> Figure:
    """Same gross-less-audit-fee arithmetic as `refundable` — paid out as a
    cash rebate/grant rather than a tax refund, so the mechanism gets its
    own named function and its own derivation line, never a shared branch
    with `refundable` disguised as a distinction."""
    net = _deduct_audit_fee(programme, gross_credit)
    net = net.with_step(
        "rebate_grant mechanism: net cash equals gross credit less audit fee "
        "— paid as a cash rebate/grant, no further conversion"
    )
    quantized = quantize_money(net.value)
    return net.with_step(
        f"net cash quantized: {quantized} {net.unit}", value=quantized
    )


def transferable(programme: Programme, gross_credit: Figure) -> tuple[Figure, Figure]:
    """Convert a credit to cash at a broker discount. The declared range has
    a low and a high rate and there is no sourced point estimate, so the
    caller gets both bounds — never a midpoint presented as though it were
    sourced (the same class of error `accuracy_denominator_by_stage`,
    Phase 1, exists to prevent for a blended mean-error figure)."""
    discount = programme.transfer_discount
    if (
        not discount.applies
        or discount.typical_rate_low is None
        or discount.typical_rate_high is None
    ):
        raise ValueError(
            f"{programme.name}: mechanism is 'transferable' but transfer_discount "
            "does not fully declare applies=true, typical_rate_low and "
            "typical_rate_high"
        )

    after_fee = _deduct_audit_fee(programme, gross_credit)
    low_value = quantize_money(after_fee.value * discount.typical_rate_low)
    high_value = quantize_money(after_fee.value * discount.typical_rate_high)
    source = discount.source_note or "no source note declared for this discount range"
    line = (
        "transferable mechanism: gross credit less audit fee "
        f"({after_fee.value} {after_fee.unit}) converted to cash at a broker "
        f"discount range of {discount.typical_rate_low} (low) to "
        f"{discount.typical_rate_high} (high) — {source} — yields a range of "
        f"{low_value} to {high_value} {after_fee.unit}, no point estimate: a "
        "single midpoint would misrepresent a sourced range as a sourced figure"
    )
    low_figure = after_fee.with_step(line, value=low_value)
    high_figure = after_fee.with_step(line, value=high_value)
    return low_figure, high_figure


def nonrefundable_credit(programme: Programme, gross_credit: Figure) -> Figure:
    """The taxable path: deduct the audit fee, then deduct corporation tax
    at the programme's declared `corporation_tax_rate`. `taxable=True` with
    a null rate is rejected at schema-load time by
    `Programme._corporation_tax_rate_required_when_taxable` (RD-05 #3,
    `engine/models.py`) — never defaulted to zero tax here. A `taxable=False`
    programme routed through this mechanism emits a derivation line stating
    corporation tax does not apply, so a reader can tell the step was
    considered rather than skipped."""
    net = _deduct_audit_fee(programme, gross_credit)

    if programme.taxable:
        rate = programme.corporation_tax_rate
        assert rate is not None, (
            "Programme._corporation_tax_rate_required_when_taxable guarantees "
            "corporation_tax_rate is not None whenever taxable is True"
        )
        tax_amount = net.value * rate
        net = net.with_step(
            f"nonrefundable_credit mechanism: corporation tax at the declared "
            f"rate {rate} deducted from {net.value} {net.unit} — tax "
            f"{tax_amount} {net.unit}",
            value=net.value - tax_amount,
        )
    else:
        net = net.with_step(
            "nonrefundable_credit mechanism: taxable is false — corporation "
            "tax does not apply to this programme"
        )

    quantized = quantize_money(net.value)
    return net.with_step(
        f"net cash quantized: {quantized} {net.unit}", value=quantized
    )


def _arrival_timing(programme: Programme) -> ArrivalTiming:
    lag = programme.timing.payout_lag
    if lag.typical_days is None:
        return ArrivalTiming(
            estimated_date=None,
            typical_days=None,
            reason=lag.description or "payout lag is not sourced for this jurisdiction",
        )
    # A confirmed typical_days value composes an estimated calendar date by
    # adding the declared lag to today's run date. Never derive a date from
    # an UNSOURCED lag (the null branch above) — but a sourced lag is
    # displayed as an estimate, never discounted to present value
    # (jurisdictions/SCOPE-FREEZE.md item 8).
    estimated = datetime.now(tz=UTC).date() + timedelta(days=lag.typical_days)
    reason = (
        f"terms lock at {programme.timing.terms_lock_at}; payout lag of "
        f"{lag.typical_days} days"
        + (f" ({lag.description})" if lag.description else "")
        + f" applied to today's run date -> estimated arrival {estimated.isoformat()}"
    )
    return ArrivalTiming(
        estimated_date=estimated,
        typical_days=lag.typical_days,
        reason=reason,
    )


def convert_to_net_cash(programme: Programme, gross_credit: Figure) -> NetCashResult:
    """Dispatch on `mechanism`. All four mechanisms are implemented."""
    mechanism = programme.mechanism

    if mechanism == "refundable":
        net_figure = refundable(programme, gross_credit)
        return NetCashResult(
            low=net_figure, high=net_figure, point=net_figure,
            arrival=_arrival_timing(programme),
        )
    if mechanism == "rebate_grant":
        net_figure = rebate_grant(programme, gross_credit)
        return NetCashResult(
            low=net_figure, high=net_figure, point=net_figure,
            arrival=_arrival_timing(programme),
        )
    if mechanism == "nonrefundable_credit":
        net_figure = nonrefundable_credit(programme, gross_credit)
        return NetCashResult(
            low=net_figure, high=net_figure, point=net_figure,
            arrival=_arrival_timing(programme),
        )
    if mechanism == "transferable":
        low_figure, high_figure = transferable(programme, gross_credit)
        return NetCashResult(
            low=low_figure, high=high_figure, point=None,
            arrival=_arrival_timing(programme),
        )

    raise AssertionError(f"unreachable mechanism {mechanism!r} — closed enum")
