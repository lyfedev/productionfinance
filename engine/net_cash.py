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
from datetime import date

from engine.figure import Figure
from engine.models import Programme

__all__ = [
    "ArrivalTiming",
    "NetCashResult",
    "convert_to_net_cash",
    "refundable",
    "transferable",
    "rebate_grant",
    "nonrefundable_credit",
]


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


def _deduct_audit_fee(programme: Programme, gross_credit: Figure) -> Figure:
    schedule = programme.audit.fee_schedule
    if not schedule:
        return gross_credit.with_step(
            "no audit fee schedule is declared for this programme — $0 deducted"
        )
    raise NotImplementedError(
        "audit fee tier lookup (cliff-tiered by spend threshold) is "
        "implemented in plan 02-04"
    )


def refundable(programme: Programme, gross_credit: Figure) -> Figure:
    """Deduct the audit fee (an empty fee schedule deducts exactly $0); no
    further conversion for a refundable mechanism."""
    net = _deduct_audit_fee(programme, gross_credit)
    return net.with_step(
        "refundable mechanism: net cash equals gross credit less audit fee, "
        "no further conversion"
    )


def transferable(programme: Programme, gross_credit: Figure) -> Figure:
    del programme, gross_credit
    raise NotImplementedError(
        "transferable mechanism (broker/transfer discount) is implemented in plan 02-04"
    )


def rebate_grant(programme: Programme, gross_credit: Figure) -> Figure:
    del programme, gross_credit
    raise NotImplementedError("rebate_grant mechanism is implemented in plan 02-04")


def nonrefundable_credit(programme: Programme, gross_credit: Figure) -> Figure:
    del programme, gross_credit
    raise NotImplementedError(
        "nonrefundable_credit mechanism (taxable, net of corporation tax) is "
        "implemented in plan 02-04"
    )


def _arrival_timing(programme: Programme) -> ArrivalTiming:
    lag = programme.timing.payout_lag
    if lag.typical_days is None:
        return ArrivalTiming(
            estimated_date=None,
            typical_days=None,
            reason=lag.description or "payout lag is not sourced for this jurisdiction",
        )
    # A confirmed typical_days value still does not synthesise a calendar
    # date here — composing typical_days against an actual application
    # date is a later plan's job (it needs a real anchor date this stage
    # does not receive). Never synthesise a date from an unsourced lag —
    # and never fabricate one for a sourced lag absent a real anchor.
    return ArrivalTiming(
        estimated_date=None,
        typical_days=lag.typical_days,
        reason=lag.description or "payout lag confirmed; anchor date not yet composed",
    )


def convert_to_net_cash(programme: Programme, gross_credit: Figure) -> NetCashResult:
    """Dispatch on `mechanism`. `refundable` is implemented; the other
    three mechanisms raise `NotImplementedError` naming plan 02-04."""
    mechanism = programme.mechanism

    if mechanism == "refundable":
        net_figure = refundable(programme, gross_credit)
    elif mechanism in ("transferable", "rebate_grant", "nonrefundable_credit"):
        raise NotImplementedError(
            f"mechanism {mechanism!r} is implemented in plan 02-04"
        )
    else:
        raise AssertionError(f"unreachable mechanism {mechanism!r} — closed enum")

    # For a mechanism with no rate range (refundable, the only one
    # implemented in this plan), low/high/point are all equal.
    return NetCashResult(
        low=net_figure,
        high=net_figure,
        point=net_figure,
        arrival=_arrival_timing(programme),
    )
