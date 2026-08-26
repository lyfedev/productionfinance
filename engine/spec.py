"""``ProductionSpec`` — the jurisdiction-agnostic input contract for Route A.

This is the durable artifact of Phase 3: Phases 4, 6, 7 and 9 all bind to
it (D-43). Decision Task 1 (03-02-PLAN.md, checkpoint) selected option A —
``production_type`` alone, with no separate numeric "scale" field. Adding a
scale-shaped field later is additive to this model; renaming or removing a
field once Phase 4 consumes it is a coordinated change across four phases.

Mirrors ``engine/models.py``'s ``StrictModel`` convention with a local
two-line base rather than importing it — that name is deliberately absent
from ``engine/models.py.__all__``, and a domain model should not drag the
whole rule schema's import graph in for one convention.

D-44: nothing in this module may import the web framework — ``engine/``
must stay importable by Phase 9's CLI entry point and by the JUR-05
additivity proof without a web stack.

No field on ``ProductionSpec`` represents a dollar amount, ever — this is
the structural half of D-35/INP-08, and the one invariant this file must
never grow, even by omission-turned-oversight in a later phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "CREW_TIERS_PATH",
    "CrewHeadcount",
    "CrewTier",
    "ProductionSpec",
    "StrictModel",
    "UnknownCrewTierError",
    "resolve_crew_tier",
]


class StrictModel(BaseModel):
    """Local mirror of ``engine.models.StrictModel`` (forbids unrecognised
    fields). Deliberately not imported from ``engine.models`` — that name
    is not exported there, and a domain model should not pull the whole
    rule schema module in just for this two-line convention."""

    model_config = ConfigDict(extra="forbid")


# INP-03
CrewTier = Literal["micro", "small", "mid", "large", "tentpole"]

# Module-anchored, never CWD-relative — the systemd unit and pytest run
# from different working directories (D-46-adjacent).
CREW_TIERS_PATH = Path(__file__).resolve().parents[1] / "data" / "crew_tiers.yaml"


class ProductionSpec(StrictModel):
    """The seven-dimension physical-input contract (INP-01...INP-07)."""

    # INP-01 — decision Task 1 option A: enum alone, no scale field.
    production_type: Literal["feature", "limited_series", "episodic"]

    # INP-02
    shoot_days_stage: int = Field(ge=0)
    shoot_days_location: int = Field(ge=0)

    # INP-03 — exactly one of the two must be supplied.
    crew_size: int | None = Field(default=None, ge=1)
    crew_tier: CrewTier | None = None

    # INP-04
    principal_cast_count: int = Field(ge=0)
    principal_cast_imported_count: int = Field(ge=0)

    # INP-05
    crew_imported_count: int = Field(ge=0)
    crew_hired_locally_count: int = Field(ge=0)

    # INP-06 — quarter AND year (D-41). 2036 is New York's own statutory
    # sunset year (SOURCE-TRUTH.md SRC-01), so the window is sane rather
    # than open-ended.
    start_quarter: Literal["Q1", "Q2", "Q3", "Q4"]
    start_year: int = Field(ge=2024, le=2036)

    # INP-07 — free text, never suggested or substituted (D-40).
    candidate_cities: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _exactly_one_crew_input(self) -> ProductionSpec:
        if (self.crew_size is None) == (self.crew_tier is None):
            raise ValueError(
                "exactly one of crew_size or crew_tier must be supplied — "
                "never both, never neither"
            )
        return self

    @model_validator(mode="after")
    def _imported_cast_within_total(self) -> ProductionSpec:
        if self.principal_cast_imported_count > self.principal_cast_count:
            raise ValueError(
                "principal_cast_imported_count cannot exceed principal_cast_count"
            )
        return self

    @model_validator(mode="after")
    def _crew_split_matches_explicit_crew_size(self) -> ProductionSpec:
        # Pitfall 3: guarded to the explicit-crew_size branch. A
        # crew_tier-only spec resolves to a RANGE (D-38), not a scalar, so
        # no exact-sum check applies when crew_size is None.
        if self.crew_size is not None:
            total = self.crew_imported_count + self.crew_hired_locally_count
            if total != self.crew_size:
                raise ValueError(
                    "crew_imported_count + crew_hired_locally_count "
                    f"({total}) must equal crew_size ({self.crew_size})"
                )
        return self

    @model_validator(mode="after")
    def _candidate_cities_are_non_blank(self) -> ProductionSpec:
        stripped = [city.strip() for city in self.candidate_cities]
        if any(not city for city in stripped):
            raise ValueError(
                "candidate_cities entries must not be empty or whitespace-only"
            )
        # Stripped of surrounding whitespace only — never deduplicated,
        # never reordered, interior characters never altered. The
        # visitor's list is echoed back as given.
        self.candidate_cities = stripped
        return self


@dataclass(frozen=True)
class CrewHeadcount:
    """A resolved crew headcount range, carrying the basis it came from."""

    low: int
    high: int
    basis: str
    provenance_note: str


class UnknownCrewTierError(KeyError):
    """Raised by ``resolve_crew_tier`` for a tier absent from
    ``data/crew_tiers.yaml`` — never falls back to a default range."""


def resolve_crew_tier(tier: CrewTier) -> CrewHeadcount:
    """Resolve ``tier`` to a headcount range via the committed table.

    Loads with ``yaml.safe_load`` only (never the unsafe/generic loader).
    A tier absent from the table raises ``UnknownCrewTierError`` naming
    the tier, rather than returning a default range.
    """
    with open(CREW_TIERS_PATH, encoding="utf-8") as handle:
        table = yaml.safe_load(handle)

    tiers = table["tiers"]
    if tier not in tiers:
        raise UnknownCrewTierError(f"Unknown crew tier: {tier!r}")

    entry = tiers[tier]
    return CrewHeadcount(
        low=int(entry["headcount_low"]),
        high=int(entry["headcount_high"]),
        basis=table["basis"],
        provenance_note=table["provenance_note"],
    )
