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
from engine.spec import CREW_TIERS_PATH

__all__ = [
    "COST_PROFILES_DIR",
    "AccountTag",
    "CityCostProfile",
    "CostCategory",
    "CostLine",
    "CraftMapping",
    "LabourBlock",
    "SpendClass",
    "StrictModel",
    "TravelBlock",
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

# Categories priced dynamically (never via a static per-line unit_rate):
# "labour" through the profile's `labour` block (plan 04-02); "housing",
# "per_diem" and "flights" through the profile's `travel` block from
# imported headcount only (plan 04-03, COST-04/COST-05); "stages",
# "equipment", "permits", "locations" and "trucking" through the profile's
# `facilities_id`-selected table (plan 04-04, COST-06) — every facilities
# category is priced from the shoot calendar's day counts, never a static
# per-line rate that could silently drift out of sync with
# engine/facilities.py's committed range.
_DYNAMICALLY_PRICED_CATEGORIES = (
    "labour",
    "housing",
    "per_diem",
    "flights",
    "stages",
    "equipment",
    "permits",
    "locations",
    "trucking",
)


class CostLine(StrictModel):
    """One priced line in a `CityCostProfile`. `unit_rate` and `rate_unit`
    describe how a `CanonicalBudget` quantity becomes money; `basis` (D-58)
    and `method_note` carry the same honesty discipline an incentive-side
    Figure already carries.

    `unit_rate`/`rate_unit`/`basis` are optional for a `category: "labour"`
    line whose department is priced dynamically through the profile's
    `labour` block (`engine/cost_localizer.py::_price_labour_department`
    selects a dated union rate row instead) — plan 04-02 — and for a
    `category: "housing"`/`"per_diem"`/`"flights"` line priced dynamically
    through the profile's `travel` block from imported headcount — plan
    04-03 (COST-04/COST-05). Every other category still requires all three
    (the static per-line pricing path, unchanged since plan 04-01). A
    dynamically-priced-category line whose profile declares no matching
    block (`labour`/`travel`) still needs them — the static path is the
    fallback when no dynamic block is declared."""

    line_id: str
    label: str
    category: CostCategory
    account: AccountTag
    spend_class: SpendClass
    unit_rate: str | None = None
    rate_unit: str | None = None
    basis: Basis | None = None
    source_url: str | None = None
    date_checked: str | None = None
    method_note: str | None = None

    @model_validator(mode="after")
    def _non_dynamic_requires_static_pricing_fields(self) -> CostLine:
        if self.category not in _DYNAMICALLY_PRICED_CATEGORIES and (
            self.unit_rate is None or self.rate_unit is None or self.basis is None
        ):
            raise ValueError(
                f"cost line {self.line_id!r}: category {self.category!r} is priced by "
                "this profile's static unit_rate — unit_rate, rate_unit and basis are "
                "all required for any cost line outside "
                f"{_DYNAMICALLY_PRICED_CATEGORIES} (only those categories may omit "
                "them, when the profile declares a matching labour/travel block)"
            )
        return self

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
        if self.basis is not None and self.basis != "sourced" and not self.method_note:
            raise ValueError(
                f"cost line {self.line_id!r}: basis {self.basis!r} requires "
                "a non-null method_note disclosing the non-primary method "
                "used (PITFALLS E1/E5)"
            )
        return self


class CraftMapping(StrictModel):
    """One department's union+craft mapping (COST-02) — resolved through
    `engine.union_rates.select_rate_row(rows, region=profile.labour.region,
    craft=this.craft, on_date=...)`."""

    union: str
    craft: str


def _crew_tiers_department_names() -> list[str]:
    with open(CREW_TIERS_PATH, encoding="utf-8") as handle:
        table = yaml.safe_load(handle)
    return list(table["departments"].keys())


class LabourBlock(StrictModel):
    """A cost profile's labour-pricing declaration (COST-02/COST-03).
    `region` is the data key matched against `data/union_rates/*.yaml`
    rows' own `region` field (JUR-05: a profile-declared data key, never a
    jurisdiction id branched on in code). `crafts` maps a
    `data/crew_tiers.yaml` department NAME (not its `label`) to its craft
    mapping."""

    region: str
    crafts: dict[str, CraftMapping]


class TravelBlock(StrictModel):
    """A cost profile's travel-pricing declaration (COST-04/COST-05).
    `per_diem_id` selects a committed per-diem table via
    `engine.per_diem.load_per_diem` — declared DATA on the profile, never a
    visitor-supplied string (T-04-10). `flight_round_trip_rate` is a
    quoted-string per-imported-person round-trip airfare estimate.
    `housing_uplift_note` discloses explicitly whether housing is priced at
    anything beyond the per-diem table's lodging component — D-60's
    honesty discipline applied to a "we didn't model X" statement rather
    than leaving it implied."""

    per_diem_id: str
    flight_round_trip_rate: str
    basis: Basis
    source_url: str | None = None
    date_checked: str | None = None
    method_note: str | None = None
    housing_uplift_note: str

    @model_validator(mode="after")
    def _sourced_requires_source_url(self) -> TravelBlock:
        if self.basis == "sourced" and not self.source_url:
            raise ValueError(
                "travel block: basis 'sourced' requires a non-null source_url — an "
                "unsourced 'sourced' claim is the exact class of dishonesty D-58/D-59 "
                "exist to prevent"
            )
        return self

    @model_validator(mode="after")
    def _non_sourced_requires_method_note(self) -> TravelBlock:
        if self.basis != "sourced" and not self.method_note:
            raise ValueError(
                f"travel block: basis {self.basis!r} requires a non-null method_note "
                "disclosing the non-primary method used (PITFALLS E1/E5)"
            )
        return self


class CityCostProfile(StrictModel):
    """A committed cost profile for one city (D-53). `jurisdiction_id` is
    `None`-able — a cost profile needs no rule file to exist. `labour` and
    `travel` are `None`-able too — a synthetic test fixture with no
    dynamically-priced cost lines declares neither block (plan 04-01
    shape, still supported); a real committed profile with
    labour/housing/per_diem/flights-category lines should declare the
    matching block (the validators below only fire when the block IS
    declared, so they can never retroactively invalidate a fixture that
    predates these fields)."""

    city_id: str
    city_label: str
    jurisdiction_id: str | None = None
    currency: str
    provenance_note: str
    cost_lines: list[CostLine]
    labour: LabourBlock | None = None
    travel: TravelBlock | None = None
    # Plan 04-04 (COST-06): selects a committed `engine.facilities
    # .FacilitiesTable` for the stages/equipment/permits/locations/trucking
    # cost lines, priced dynamically from the shoot calendar's day counts —
    # `None`-able for the identical reason `labour`/`travel` are.
    facilities_id: str | None = None
    # Plan 04-04 (INC-10): selects a committed `engine.exemptions
    # .ExemptionsTable` of stackable cost-reduction Figures. `None`-able —
    # a city that offers no sales-tax or hotel-occupancy exemption simply
    # declares no `exemptions_id` (never an entry with a zero rate).
    exemptions_id: str | None = None

    @model_validator(mode="after")
    def _labour_covers_every_department_when_declared(self) -> CityCostProfile:
        if self.labour is None:
            return self
        departments = _crew_tiers_department_names()
        missing = [name for name in departments if name not in self.labour.crafts]
        if missing:
            raise ValueError(
                f"{self.city_id!r}: labour.crafts is missing a craft mapping for "
                f"department(s) {missing!r} — every data/crew_tiers.yaml department "
                "needs a craft mapping so it cannot silently price at zero"
            )
        return self


def load_cost_profile(path: str | Path) -> CityCostProfile:
    """The single cost-profile read path. Parses with PyYAML's *safe*
    loader only (never `yaml.load`/`yaml.unsafe_load`), matching
    `engine/models.py::load_ruleset` and `engine/spec.py::resolve_crew_tier`."""
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return CityCostProfile.model_validate(raw)
