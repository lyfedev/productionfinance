"""The single public entry point: `price_jurisdiction`.

Loops over every entry in `ruleset.programmes`, prices each independently
through base then credit then net cash, and returns a `PricedJurisdiction`
carrying the per-programme results plus a summed total. Summation is over
independent dollar outputs, never over rates. The loop is written for N
programmes from the outset even though every jurisdiction this plan builds
declares exactly one.

Nothing in this module (or anywhere in `engine/`) is named for a
jurisdiction or branches on a jurisdiction identifier string (JUR-05).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from engine.credit import compute_gross_credit
from engine.figure import Figure, combined_confidence
from engine.models import Jurisdiction, JurisdictionRuleSet, Programme
from engine.net_cash import NetCashResult, convert_to_net_cash
from engine.qualifying_base import SpendBreakdown, compute_qualifying_base
from engine.rounding import quantize_money

__all__ = ["PricedProgramme", "PricedJurisdiction", "price_programme", "price_jurisdiction"]


@dataclass(frozen=True)
class PricedProgramme:
    programme_id: str
    qualifying_base: Figure
    gross_credit: Figure
    net_cash: NetCashResult


@dataclass(frozen=True)
class PricedJurisdiction:
    jurisdiction_id: str
    programmes: tuple[PricedProgramme, ...]
    total_net_cash: Figure


def _primary_source_provenance(jurisdiction: Jurisdiction) -> tuple[str | None, str | None]:
    """Returns (source_url, date_checked-as-Source.accessed_date) from the
    jurisdiction's first cited source, or (None, None) if it cites none.

    Q2's schema places `sources` at the jurisdiction level (not per
    programme); a curated jurisdiction like New York cites this list once
    for the whole rule file, so its first entry stands in for "this
    programme's sources[0]" in a single-source-list rule file."""
    if not jurisdiction.sources:
        return None, None
    primary = jurisdiction.sources[0]
    return primary.url, primary.accessed_date


def price_programme(
    jurisdiction: Jurisdiction,
    programme: Programme,
    qualified_spend: Decimal,
    *,
    annual_cap_remaining: Decimal | None = None,
) -> PricedProgramme:
    """Price one programme through base -> credit -> net cash."""
    confidence = "validated" if jurisdiction.status == "curated_validated" else "researched"
    source_url, date_checked = _primary_source_provenance(jurisdiction)

    spend = SpendBreakdown.from_total(qualified_spend)
    qualifying_base = compute_qualifying_base(
        programme,
        spend,
        currency=jurisdiction.currency,
        source_url=source_url,
        date_checked=date_checked,
        confidence=confidence,
    )
    gross_credit = compute_gross_credit(
        programme, qualifying_base, annual_cap_remaining=annual_cap_remaining
    )
    net_cash = convert_to_net_cash(programme, gross_credit)

    return PricedProgramme(
        programme_id=programme.id,
        qualifying_base=qualifying_base,
        gross_credit=gross_credit,
        net_cash=net_cash,
    )


def price_jurisdiction(
    ruleset: JurisdictionRuleSet,
    qualified_spend: Decimal,
    *,
    annual_cap_remaining_by_programme: dict[str, Decimal] | None = None,
) -> PricedJurisdiction:
    """Price every declared programme in `ruleset` and return the summed
    total. Summation is over independent dollar outputs computed against
    each programme's own base — never over rates (A1.1)."""
    remaining_by_programme = annual_cap_remaining_by_programme or {}

    priced: list[PricedProgramme] = [
        price_programme(
            ruleset.jurisdiction,
            programme,
            qualified_spend,
            annual_cap_remaining=remaining_by_programme.get(programme.id),
        )
        for programme in ruleset.programmes
    ]

    total_value = Decimal("0")
    total_inputs: list[Figure] = []
    for priced_programme in priced:
        contribution_figure = priced_programme.net_cash.point or priced_programme.net_cash.low
        total_value += contribution_figure.value
        total_inputs.append(contribution_figure)
    total_value = quantize_money(total_value)

    total_figure = Figure(
        value=total_value,
        unit=ruleset.jurisdiction.currency,
        label="Total landed net cash across all programmes",
        derivation=(
            f"summed {len(priced)} independent programme net-cash output(s) "
            "(never summed rates)",
        ),
        inputs=tuple(total_inputs),
        source_url=None,
        date_checked=None,
        confidence=combined_confidence(total_inputs),
        live_fetched_this_run=False,
    )

    return PricedJurisdiction(
        jurisdiction_id=ruleset.jurisdiction.id,
        programmes=tuple(priced),
        total_net_cash=total_figure,
    )
