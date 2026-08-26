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
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from engine.spec import CrewHeadcount, ProductionSpec

__all__ = ["CanonicalBudget", "build_canonical_budget"]

# The tracer's single quantity line label. `engine/cost_localizer.py`'s
# `_find_line_by_label` looks this up by label, never by position, and the
# committed New York cost profile's one cost line declares the identical
# label so the two sides agree on the shared key.
CREW_LABOUR_DAYS_LABEL = "Crew labour days"

# BTL (below-the-line): crew labour is a below-the-line cost by standard
# film-production chart-of-accounts convention (OUT-04/D-77 — the tag is
# additive data; nothing in this phase groups or renders by it).
_CREW_LABOUR_ACCOUNT = "BTL"


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


def build_canonical_budget(spec: ProductionSpec, crew_headcount: CrewHeadcount) -> CanonicalBudget:
    """Build the single canonical budget for `spec`. Pure function of the
    spec and the already-resolved `crew_headcount` — takes NO city
    argument, which is COST-01 made structural: the caller builds this
    exactly once per submission and localizes it against every candidate
    city's cost profile in turn, never rebuilding it per city.

    The tracer (Phase 4 plan 04-01, Task 1) emits exactly one quantity
    line: crew labour days, computed as total shoot days (stage plus
    location) times the crew headcount's LOW bound. `CrewHeadcount` is a
    range, not a scalar, so using the low bound is a deliberate choice —
    named here, and again in the derivation line
    `engine/cost_localizer.py::localize` attaches to the resulting Figure,
    rather than silently picked without comment.
    """
    shoot_days = Decimal(spec.shoot_days_stage) + Decimal(spec.shoot_days_location)
    crew_labour_days = shoot_days * Decimal(crew_headcount.low)

    return CanonicalBudget(
        line_quantities={CREW_LABOUR_DAYS_LABEL: crew_labour_days},
        accounts={CREW_LABOUR_DAYS_LABEL: _CREW_LABOUR_ACCOUNT},
        shoot_days=shoot_days,
        crew_headcount=crew_headcount,
    )
