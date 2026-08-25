"""The single public entry point: `price_jurisdiction`.

Loops over every entry in `ruleset.programmes`, prices each independently
through base then credit then net cash, and returns a `PricedJurisdiction`
carrying the per-programme results plus a summed total. Summation is over
independent dollar outputs, never over rates. The loop is written for N
programmes from the outset even though NY and CT each declare exactly one —
plan 02-06 is where a jurisdiction genuinely declaring more than one
programme first exercises it, resolving `mutually_exclusive_with` (only one
of a mutually-exclusive pair contributes to the total; the other is still
priced and reported, never silently dropped) before summing.

Nothing in this module (or anywhere in `engine/`) is named for a
jurisdiction or branches on a jurisdiction identifier string (JUR-05).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from engine.credit import (
    Availability,
    Eligibility,
    assess_availability,
    assess_eligibility,
    compute_gross_credit,
)
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
    eligibility: Eligibility
    availability: Availability


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

    # Eligibility (does this production qualify?) and availability (does the
    # programme's annual allocation still have money left?) are computed
    # independently — INC-05 forbids collapsing them into one answer. An
    # ineligible production still gets a fully computed availability answer.
    eligibility = assess_eligibility(
        programme, qualifying_base, jurisdiction_status=jurisdiction.status
    )
    availability = assess_availability(gross_credit.value, annual_cap_remaining)

    return PricedProgramme(
        programme_id=programme.id,
        qualifying_base=qualifying_base,
        gross_credit=gross_credit,
        net_cash=net_cash,
        eligibility=eligibility,
        availability=availability,
    )


def _contribution_figure(priced_programme: PricedProgramme) -> Figure:
    """The single Figure a programme contributes to a jurisdiction total —
    `point` when the mechanism has one (refundable/rebate_grant/
    nonrefundable_credit), else `low` (transferable's declared-range floor,
    never a fabricated midpoint)."""
    return priced_programme.net_cash.point or priced_programme.net_cash.low


def _resolve_mutual_exclusivity(
    ruleset: JurisdictionRuleSet, priced_by_id: dict[str, PricedProgramme]
) -> tuple[set[str], list[str]]:
    """Resolve every declared `mutually_exclusive_with` edge before
    summation. Where two declared programmes name each other, only the
    LARGER contribution is taken; the smaller is excluded from the sum but
    stays fully priced and reported (`PricedJurisdiction.programmes` still
    carries it) — a producer needs to see what the alternative would have
    been, never a silently dropped figure.

    Returns (excluded_programme_ids, derivation_lines). A `pair` is
    deduplicated via `frozenset` so a symmetric declaration (both sides
    naming each other) is resolved exactly once."""
    programme_by_id = {programme.id: programme for programme in ruleset.programmes}
    currency = ruleset.jurisdiction.currency
    excluded_ids: set[str] = set()
    lines: list[str] = []
    resolved_pairs: set[frozenset[str]] = set()

    for programme in ruleset.programmes:
        for other_id in programme.mutually_exclusive_with:
            pair = frozenset({programme.id, other_id})
            if pair in resolved_pairs:
                continue
            resolved_pairs.add(pair)

            if other_id not in programme_by_id:
                raise ValueError(
                    f"programme {programme.id!r} declares mutually_exclusive_with "
                    f"{other_id!r}, which is not a declared programme id in this ruleset "
                    f"(declared ids: {sorted(programme_by_id)})"
                )

            this_value = _contribution_figure(priced_by_id[programme.id]).value
            other_value = _contribution_figure(priced_by_id[other_id]).value
            if this_value >= other_value:
                taken_id, taken_value = programme.id, this_value
                untaken_id, untaken_value = other_id, other_value
            else:
                taken_id, taken_value = other_id, other_value
                untaken_id, untaken_value = programme.id, this_value

            excluded_ids.add(untaken_id)
            lines.append(
                f"mutual exclusivity resolved between {programme.id!r} and {other_id!r}: "
                f"{taken_id!r} taken ({taken_value} {currency}), {untaken_id!r} not taken "
                f"({untaken_value} {currency}) — the untaken programme is still fully "
                "priced and reported, never silently dropped"
            )

    return excluded_ids, lines


def _grinding_clause_lines(ruleset: JurisdictionRuleSet, excluded_ids: set[str]) -> list[str]:
    """`jurisdictions/SCOPE-FREEZE.md` dimension 4 requires checking for a
    declared grinding/assistance-reduction clause between stacked programmes
    before summing. The schema has no field to express one (RD-05 does not
    add one), so every declared `stacks_with` pair that actually contributes
    to the sum emits a line stating the absence is recorded, not assumed."""
    lines: list[str] = []
    seen_pairs: set[frozenset[str]] = set()
    for programme in ruleset.programmes:
        if programme.id in excluded_ids:
            continue
        for other_id in programme.stacks_with:
            if other_id in excluded_ids:
                continue
            pair = frozenset({programme.id, other_id})
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            lines.append(
                "no grinding or assistance-reduction clause is declared between stacked "
                f"programmes {programme.id!r} and {other_id!r} (SCOPE-FREEZE.md dimension 4 "
                "— the absence is recorded, not assumed)"
            )
    return lines


def price_jurisdiction(
    ruleset: JurisdictionRuleSet,
    qualified_spend: Decimal,
    *,
    annual_cap_remaining_by_programme: dict[str, Decimal] | None = None,
) -> PricedJurisdiction:
    """Price every declared programme in `ruleset`, resolve mutual
    exclusivity, and return the summed total. Summation is over independent
    dollar outputs computed against each programme's own base — never over
    rates (A1.1). `PricedJurisdiction.programmes` carries every declared
    programme, in the order the rule file declares them, whether or not it
    contributes to the sum — grouping and ordering are read from the rule
    file, never reordered by this function."""
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
    priced_by_id = {pp.programme_id: pp for pp in priced}

    excluded_ids, exclusivity_lines = _resolve_mutual_exclusivity(ruleset, priced_by_id)
    grinding_lines = _grinding_clause_lines(ruleset, excluded_ids)

    contributing = [pp for pp in priced if pp.programme_id not in excluded_ids]
    total_value = Decimal("0")
    total_inputs: list[Figure] = []
    for priced_programme in priced:
        # ALL priced programmes' figures are carried as `inputs` — including
        # any excluded by mutual exclusivity — so a reader can see the
        # untaken alternative's figure even though it did not contribute to
        # `total_value`.
        total_inputs.append(_contribution_figure(priced_programme))
    for priced_programme in contributing:
        total_value += _contribution_figure(priced_programme).value
    total_value = quantize_money(total_value)

    derivation_lines: list[str] = [
        f"summed {len(contributing)} of {len(priced)} declared programme(s)' independent "
        "net-cash output(s) (never summed rates)",
    ]
    derivation_lines.extend(exclusivity_lines)
    if not exclusivity_lines:
        derivation_lines.append("no mutually-exclusive programme pairs are declared in this ruleset")
    derivation_lines.extend(grinding_lines)

    total_figure = Figure(
        value=total_value,
        unit=ruleset.jurisdiction.currency,
        label="Total landed net cash across all programmes",
        derivation=tuple(derivation_lines),
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
