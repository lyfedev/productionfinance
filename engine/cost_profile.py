"""`CityCostProfile` — the committed schema for one city's cost data.

D-53: a `CityCostProfile` is a genuinely different artifact from a
`JurisdictionRuleSet` — one prices union scale, per diem, housing, stages
and equipment; the other reproduces a government-issued incentive award.
Building this schema touches nothing in `engine/models.py` and needs no
`jurisdiction_id` to point at a real rule file (`jurisdiction_id` is
`None`-able for exactly this reason).

Mirrors `engine/spec.py`'s convention: a local two-line `StrictModel`
(``model_config = ConfigDict(extra="forbid")``), never imported from
`engine.models` — a domain model should not drag the whole rule schema's
import graph in for one two-line convention. `COST_PROFILES_DIR` is
module-anchored, matching `engine/spec.py::CREW_TIERS_PATH` — the systemd
unit and pytest run from different working directories.

Every numeric value in a committed cost-profile YAML file is a quoted
string (RD-01) — ``unit_rate`` is typed ``str`` here and parsed with
``Decimal()`` by the caller (`engine/cost_localizer.py`), never parsed as
a bare YAML-native float.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from engine.figure import Basis

__all__ = [
    "COST_PROFILES_DIR",
    "AccountTag",
    "CityCostProfile",
    "CostCategory",
    "CostLine",
    "SpendClass",
    "StrictModel",
    "load_cost_profile",
]


class StrictModel(BaseModel):
    """Local mirror of `engine.models.StrictModel` / `engine.spec.StrictModel`
    (forbids unrecognised fields). Deliberately not imported from either —
    that name is not exported from `engine.models.__all__`, and a domain
    model should not pull the whole rule schema module in for this
    two-line convention (matches `engine/spec.py`'s own precedent)."""

    model_config = ConfigDict(extra="forbid")


# Module-anchored, never CWD-relative — matches `engine/spec.py::CREW_TIERS_PATH`
# (the systemd unit and pytest run from different working directories).
COST_PROFILES_DIR = Path(__file__).resolve().parents[1] / "data" / "cost_profiles"

# The canonical cost-category vocabulary this project models (also declared
# in `engine/landed_cost.py::COST_CATEGORIES` — that tuple is the single
# source of truth for the *closed set*; this Literal must stay in sync with
# it, and both are exercised together by `tests/test_engine_cost_profile.py`
# and `tests/test_engine_landed_cost.py`).
CostCategory = Literal[
    "labour",
    "fringe",
    "housing",
    "per_diem",
    "flights",
    "stages",
    "equipment",
    "permits",
    "locations",
    "trucking",
]

# OUT-04/D-77: the chart-of-accounts tag every budget line and cost line
# carries at creation. Nothing in Phase 4 groups, subtotals or renders by
# this tag — that view is Phase 11's (D-77).
AccountTag = Literal["ATL", "BTL", "POST"]

# JUR-05: how a cost line's value is derived from the canonical budget's
# `SpendBreakdown` categories, declared as DATA on the profile line rather
# than a jurisdiction-id branch in code.
SpendClass = Literal["local_labour", "local_non_labour", "non_local"]


class CostLine(StrictModel):
    """One priced line in a `CityCostProfile`. `unit_rate` and `rate_unit`
    describe how a `CanonicalBudget` quantity becomes money; `basis` (D-58)
    and `method_note` carry the same honesty discipline an incentive-side
    Figure already carries."""

    line_id: str
    label: str
    category: CostCategory
    account: AccountTag
    spend_class: SpendClass
    unit_rate: str
    rate_unit: str
    basis: Basis
    source_url: str | None = None
    date_checked: str | None = None
    method_note: str | None = None

    @model_validator(mode="after")
    def _sourced_requires_source_url(self) -> CostLine:
        if self.basis == "sourced" and not self.source_url:
            raise ValueError(
                f"cost line {self.line_id!r}: basis 'sourced' requires a "
                "non-null source_url — an unsourced 'sourced' claim is the "
                "exact class of dishonesty D-58/D-59 exist to prevent"
            )
        return self

    @model_validator(mode="after")
    def _non_sourced_requires_method_note(self) -> CostLine:
        if self.basis != "sourced" and not self.method_note:
            raise ValueError(
                f"cost line {self.line_id!r}: basis {self.basis!r} requires "
                "a non-null method_note disclosing the non-primary method "
                "used (PITFALLS E1/E5)"
            )
        return self


class CityCostProfile(StrictModel):
    """A committed cost profile for one city (D-53). `jurisdiction_id` is
    `None`-able — a cost profile needs no rule file to exist."""

    city_id: str
    city_label: str
    jurisdiction_id: str | None = None
    currency: str
    provenance_note: str
    cost_lines: list[CostLine]


def load_cost_profile(path: str | Path) -> CityCostProfile:
    """The single cost-profile read path. Parses with PyYAML's *safe*
    loader only (never `yaml.load`/`yaml.unsafe_load`), matching
    `engine/models.py::load_ruleset` and `engine/spec.py::resolve_crew_tier`."""
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return CityCostProfile.model_validate(raw)
