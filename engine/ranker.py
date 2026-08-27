"""Stage `[7]` of the pipeline: the two-band ranked list (OUT-01, D-55).

`rank()` is the machinery behind PROJECT.md's whole thesis — that a
producer's headline ranking inverts once net cash applies. Every candidate
city is fully priced (`engine.landed_cost.aggregate`); only a city whose
jurisdiction genuinely has a committed rule file AND whose net cash
converts successfully enters the `net_ranked` band, sorted on NET landed
cost. Every other city sits in a separate `incentive_not_modelled` band,
carrying its COST-ONLY total — never a fabricated `$0` incentive (D-56,
load-bearing and rejected explicitly, `.planning/phases/
04-cost-localization-landed-cost-outputs/04-CONTEXT.md`). The two bands
are sorted independently and concatenated — ranked band first, unranked
band second — NEVER interleaved as though the two totals were comparable
(D-55).

Mirrors `engine/pipeline.py`'s per-item loop and summation shape combined
with `engine.net_cash.transferable`'s refuse-rather-than-invent branch: a
city whose rule file exists but whose net cash cannot be computed (the
shape Connecticut's open transfer-discount gap takes, `.planning/
WINDOWS.md` entry 3) falls into the unranked band carrying the underlying
refusal message verbatim, rather than raising out of `rank`.

JURISDICTION-AGNOSTIC by construction (JUR-05/D-53): every dispatch below
reads `LocalizedBudget.jurisdiction_id` (data already resolved by
`engine.cost_localizer.localize`) and looks it up in a caller-supplied
mapping — never a hard-coded jurisdiction identifier string anywhere in
this module's own source.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from engine.cost_localizer import LocalizedBudget
from engine.figure import Figure
from engine.landed_cost import aggregate
from engine.models import JurisdictionRuleSet
from engine.pipeline import price_jurisdiction

__all__ = ["RankedCity", "rank"]

Band = Literal["net_ranked", "incentive_not_modelled"]


@dataclass(frozen=True)
class RankedCity:
    """One city's place in the two-band ranked list (D-55).

    `reason` is populated ONLY for the `incentive_not_modelled` band — it
    is `None` for a `net_ranked` city, never an empty string (an empty-
    but-present reason would be indistinguishable from a dropped one,
    mirroring `Figure.caveat`'s own non-empty-or-None contract).
    `incentive_figure` is the priced net-cash Figure for a `net_ranked`
    city, `None` for an unranked one. `cost_only_total` is ALWAYS
    populated (both bands) — the pre-incentive cost total, so a renderer
    can show "what net cash bought" for a ranked city without a second
    lookup.
    """

    city_id: str
    total_landed_cost: Figure
    band: Band
    reason: str | None
    incentive_figure: Figure | None
    cost_only_total: Figure


def _no_rule_file_reason(jurisdiction_id: str | None) -> str:
    if jurisdiction_id is None:
        return (
            "no curated or live-researched rule file exists for this city's "
            "jurisdiction yet — this city's cost profile declares no jurisdiction_id "
            "at all"
        )
    return (
        f"no curated or live-researched rule file exists for jurisdiction "
        f"{jurisdiction_id!r} yet"
    )


def _cannot_convert_reason(jurisdiction_id: str, error: Exception) -> str:
    # WINDOWS.md entry 3's exact shape: a rule file exists, but a mechanism
    # (e.g. transferable at an unsourced discount rate) refuses to convert
    # to net cash. The underlying refusal message is carried VERBATIM —
    # never paraphrased or summarized away.
    return (
        f"a rule file exists for jurisdiction {jurisdiction_id!r} but its net cash "
        f"cannot be computed: {error}"
    )


def rank(
    localized_by_city: Mapping[str, LocalizedBudget],
    ruleset_by_jurisdiction: Mapping[str, JurisdictionRuleSet],
) -> tuple[RankedCity, ...]:
    """Price every city in `localized_by_city` and place it in the
    `net_ranked` or `incentive_not_modelled` band.

    A city enters `net_ranked` only when BOTH hold: (1) its
    `jurisdiction_id` is a key in `ruleset_by_jurisdiction`, and (2)
    `engine.pipeline.price_jurisdiction` prices that ruleset against this
    city's modelled spend without raising. Every other city enters
    `incentive_not_modelled` with `total_landed_cost` equal to its
    COST-ONLY total (`engine.landed_cost.aggregate` called with no
    net-cash figure) — never `$0`, never cost minus an assumed-zero
    incentive (D-56).

    Each band is sorted independently, ascending by `total_landed_cost
    .value`; the return value is the ranked band followed by the unranked
    band, concatenated — never interleaved, never a single merged sort
    (D-55).
    """
    ranked: list[RankedCity] = []
    unranked: list[RankedCity] = []

    for city_id, localized in localized_by_city.items():
        jurisdiction_id = localized.jurisdiction_id
        ruleset = ruleset_by_jurisdiction.get(jurisdiction_id) if jurisdiction_id else None

        if ruleset is None:
            landed = aggregate(localized)
            unranked.append(
                RankedCity(
                    city_id=city_id,
                    total_landed_cost=landed.total_landed_cost,
                    band="incentive_not_modelled",
                    reason=_no_rule_file_reason(jurisdiction_id),
                    incentive_figure=None,
                    cost_only_total=landed.cost_total,
                )
            )
            continue

        try:
            priced = price_jurisdiction(
                ruleset,
                localized.spend_breakdown.total_spend,
                spend_breakdown=localized.spend_breakdown,
                # D-63/D-71: this qualified spend is MODELLED from a
                # described production, never reproduced against a real
                # government disclosure — it must never be able to reach
                # "validated" (see engine/pipeline.py::price_programme).
                spend_confidence="researched",
            )
        except ValueError as error:
            landed = aggregate(localized)
            unranked.append(
                RankedCity(
                    city_id=city_id,
                    total_landed_cost=landed.total_landed_cost,
                    band="incentive_not_modelled",
                    reason=_cannot_convert_reason(jurisdiction_id, error),
                    incentive_figure=None,
                    cost_only_total=landed.cost_total,
                )
            )
            continue

        net_cash_figure = priced.total_net_cash
        landed = aggregate(localized, net_cash_figure)
        ranked.append(
            RankedCity(
                city_id=city_id,
                total_landed_cost=landed.total_landed_cost,
                band="net_ranked",
                reason=None,
                incentive_figure=net_cash_figure,
                cost_only_total=landed.cost_total,
            )
        )

    ranked_sorted = tuple(sorted(ranked, key=lambda city: city.total_landed_cost.value))
    unranked_sorted = tuple(sorted(unranked, key=lambda city: city.total_landed_cost.value))
    return ranked_sorted + unranked_sorted
