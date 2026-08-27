"""Stage `[1]` of the pipeline: `BudgetModelBuilder` — build the single,
jurisdiction-agnostic `CanonicalBudget` from a `ProductionSpec` (COST-01).

Mirrors `engine/qualifying_base.py`'s shape: a frozen dataclass carrying
the computed values, produced by a pure function that dispatches only on
the declared spec and `data/crew_tiers.yaml` fields — never on a city or
jurisdiction argument. The SAME `CanonicalBudget` instance is localized
against every candidate city's cost profile in turn
(`engine/cost_localizer.py::localize`); it must never be rebuilt per city,
or COST-01's "one budget, byte-identical regardless of which candidate
cities were named" promise is a lie rather than a structural fact.

D-38/OUT-04 (plan 04-01 Task 3): the budget decomposes crew labour into
one quantity line PER DEPARTMENT, each carrying its own ATL/BTL/POST
chart-of-accounts `account` tag (D-77) and its own `crew_share` of the
resolved headcount, read from `data/crew_tiers.yaml`'s `departments:`
block. This is a decomposition, not a new number: `CanonicalBudget`'s
total quantity across every department line equals exactly what the
tracer's single undivided line would have computed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

import yaml

from engine.spec import (
    CREW_TIERS_PATH,
    CrewHeadcount,
    CrewTier,
    ProductionSpec,
    UnknownCrewTierError,
)

__all__ = [
    "CREW_TIERS_PATH",
    "CanonicalBudget",
    "DepartmentShare",
    "build_canonical_budget",
    "resolve_departments",
]

# OUT-04/D-77: the closed chart-of-accounts tag vocabulary every department
# and every cost-profile line carries. Nothing in Phase 4 groups, subtotals
# or renders by this tag — that view is Phase 11's.
_LEGAL_ACCOUNTS = ("ATL", "BTL", "POST")

# Tier bracket lookup order for `_infer_department_tier` below — narrowest
# to widest, matching `data/crew_tiers.yaml::tiers`' own declaration order.
_TIER_ORDER: tuple[CrewTier, ...] = ("micro", "small", "mid", "large", "tentpole")


@dataclass(frozen=True)
class DepartmentShare:
    """One department's resolved share of a crew tier's headcount,
    carrying its OUT-04 account tag. `crew_share` is a fraction (e.g.
    `Decimal("0.15")`) of the tier's headcount, never a headcount itself."""

    name: str
    label: str
    account: str
    crew_share: Decimal


@dataclass(frozen=True)
class CanonicalBudget:
    """A single, jurisdiction-agnostic budget quantity table (COST-01).

    `line_quantities` and `accounts` are both keyed by the same line
    label — a `CostLine.label` in a `CityCostProfile` looks up its
    quantity here by that shared key
    (`engine/cost_localizer.py::_find_line_by_label`), never by position.
    """

    line_quantities: dict[str, Decimal]
    accounts: dict[str, str]
    shoot_days: Decimal
    crew_headcount: CrewHeadcount

    @property
    def total_quantity(self) -> Decimal:
        """The sum of every emitted quantity line. D-38's department split
        is a decomposition, never a new number — this must equal exactly
        what a single undivided crew-labour-days line would have computed
        (`tests/test_engine_budget.py` asserts this)."""
        return sum(self.line_quantities.values(), start=Decimal("0"))


def _load_crew_tiers_table() -> dict:
    with open(CREW_TIERS_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _check_tier_boundaries_for_ambiguous_crew_share(table: dict) -> None:
    """WR-01 (04-REVIEW.md): `tiers:`'s brackets are inclusive-inclusive
    and touch at every boundary (e.g. `micro`'s `headcount_high` of 30
    equals `small`'s `headcount_low` of 30). `_infer_department_tier`
    resolves a boundary headcount to the narrower (lower) tier by
    iterating `_TIER_ORDER` narrowest-first — a deterministic but
    undocumented tie-break that is silently SAFE only as long as every
    department's `crew_share` is identical on both sides of the boundary.
    Mirrors `engine.union_rates._check_rate_rows_for_overlaps`'s
    "authoring error, never silently resolved by iteration order"
    discipline: raise loudly, at load time, the moment a future data edit
    differentiates a department's `crew_share` across a shared boundary,
    rather than let a real discontinuity resolve silently by declaration
    order."""
    tiers = table["tiers"]
    departments = table["departments"]
    bounds = {
        tier: (int(entry["headcount_low"]), int(entry["headcount_high"]))
        for tier, entry in tiers.items()
    }
    for lower_tier, upper_tier in pairwise(_TIER_ORDER):
        if lower_tier not in bounds or upper_tier not in bounds:
            # A synthetic/test table declaring only a subset of
            # `_TIER_ORDER`'s five tiers (e.g. this module's own
            # regression tests) has no boundary to check for the missing
            # tier(s) — never a `KeyError`.
            continue
        lower_high = bounds[lower_tier][1]
        upper_low = bounds[upper_tier][0]
        if lower_high != upper_low:
            continue
        for name, entry in departments.items():
            lower_share = entry["crew_share"][lower_tier]
            upper_share = entry["crew_share"][upper_tier]
            if lower_share != upper_share:
                raise ValueError(
                    f"crew_tiers.yaml: department {name!r} declares crew_share "
                    f"{lower_share!r} for tier {lower_tier!r} but {upper_share!r} "
                    f"for tier {upper_tier!r} — these tiers share boundary "
                    f"headcount {lower_high}, so a headcount of exactly "
                    f"{lower_high} would silently resolve to {lower_tier!r} by "
                    "_infer_department_tier's narrowest-first iteration order. "
                    "That is a real discontinuity now that the shares differ, "
                    "not a harmless tie-break — declare the brackets half-open "
                    "or otherwise resolve the ambiguity explicitly before "
                    "shipping differentiated shares across a shared boundary."
                )


def resolve_departments(tier: CrewTier) -> tuple[DepartmentShare, ...]:
    """Resolve `tier` to its department-ratio breakdown via the committed
    `data/crew_tiers.yaml::departments` table (D-38).

    Loads with `yaml.safe_load` only, from the same module-anchored
    `CREW_TIERS_PATH` `engine.spec.resolve_crew_tier` reads. A tier absent
    from any declared department's `crew_share` table raises
    `UnknownCrewTierError` — the identical contract `resolve_crew_tier`
    already holds — never a default department set. Also checks every
    pair of tiers sharing a boundary headcount for a differentiated
    `crew_share` (WR-01) — see
    `_check_tier_boundaries_for_ambiguous_crew_share`.
    """
    table = _load_crew_tiers_table()
    _check_tier_boundaries_for_ambiguous_crew_share(table)
    departments = table["departments"]

    shares: list[DepartmentShare] = []
    for name, entry in departments.items():
        account = entry["account"]
        if account not in _LEGAL_ACCOUNTS:
            raise ValueError(
                f"department {name!r} declares account {account!r}, not one of "
                f"{_LEGAL_ACCOUNTS}"
            )
        tier_shares = entry["crew_share"]
        if tier not in tier_shares:
            raise UnknownCrewTierError(f"Unknown crew tier: {tier!r}")
        shares.append(
            DepartmentShare(
                name=name,
                label=entry["label"],
                account=account,
                crew_share=Decimal(tier_shares[tier]),
            )
        )
    return tuple(shares)


def _tier_bounds() -> dict[str, tuple[int, int]]:
    table = _load_crew_tiers_table()
    return {
        tier: (int(entry["headcount_low"]), int(entry["headcount_high"]))
        for tier, entry in table["tiers"].items()
    }


def _infer_department_tier(spec: ProductionSpec, crew_headcount: CrewHeadcount) -> CrewTier:
    """Department ratios (D-38) are declared per crew TIER, but a visitor
    may supply an explicit `crew_size` instead of a tier (INP-03). When a
    tier was supplied, use it directly. When an explicit headcount was
    supplied instead, infer the tier whose committed `[low, high]` bracket
    contains it — or, for a headcount outside every declared bracket, the
    nearest bracket at the extremes. This is a disclosed,
    `modelling_assumption`-basis choice (recorded here, not a silent
    default), not a new headcount resolution: `crew_headcount` itself is
    unaffected."""
    if spec.crew_tier is not None:
        return spec.crew_tier

    bounds = _tier_bounds()
    headcount = crew_headcount.low
    for tier in _TIER_ORDER:
        low, high = bounds[tier]
        if low <= headcount <= high:
            return tier

    first_tier, last_tier = _TIER_ORDER[0], _TIER_ORDER[-1]
    if headcount < bounds[first_tier][0]:
        return first_tier
    return last_tier


def build_canonical_budget(spec: ProductionSpec, crew_headcount: CrewHeadcount) -> CanonicalBudget:
    """Build the single canonical budget for `spec`. Pure function of the
    spec and the already-resolved `crew_headcount` — takes NO city
    argument, which is COST-01 made structural: the caller builds this
    exactly once per submission and localizes it against every candidate
    city's cost profile in turn, never rebuilding it per city.

    D-38 (plan 04-01 Task 3): emits one quantity line PER DEPARTMENT,
    computed as (crew headcount's LOW bound x that department's
    `crew_share`) x total shoot days (stage plus location). Each line
    carries its department's `account` tag (OUT-04/D-77). `CrewHeadcount`
    is a range, not a scalar; using the low bound is the same deliberate
    choice plan 04-01's Task 1 tracer made, unchanged by this split.
    """
    shoot_days = Decimal(spec.shoot_days_stage) + Decimal(spec.shoot_days_location)
    tier = _infer_department_tier(spec, crew_headcount)
    departments = resolve_departments(tier)

    line_quantities: dict[str, Decimal] = {}
    accounts: dict[str, str] = {}
    for department in departments:
        department_headcount = Decimal(crew_headcount.low) * department.crew_share
        labour_days = department_headcount * shoot_days
        line_quantities[department.label] = labour_days
        accounts[department.label] = department.account

    return CanonicalBudget(
        line_quantities=line_quantities,
        accounts=accounts,
        shoot_days=shoot_days,
        crew_headcount=crew_headcount,
    )
