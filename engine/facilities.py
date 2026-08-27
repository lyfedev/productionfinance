"""`FacilitiesTable` — the committed schema and pricing path for the five
never-sourced cost categories COST-06 names: stages, equipment, permits,
locations and trucking (04-CONTEXT.md D-53 cost side, 04-RESEARCH.md
Pitfall 4).

No standardized public rate card exists anywhere for any of these five
categories — this session confirmed it directly (04-RESEARCH.md Pitfall 4:
"a $19/hr Giggster listing next to a $3,500/shoot-day standing-set rate,
neither representative of what a real production actually negotiates").
Every committed entry is therefore `basis: "estimated"` (when a specific,
named public anchor is disclosed) or `basis: "modelling_assumption"`
(when none exists) — **never** `basis: "sourced"`, enforced structurally
below rather than by review discipline (COST-06, T-04-15).

`FACILITIES_PATH_BY_ID` is built by GLOBBING every committed YAML under
`FACILITIES_DIR` and reading each file's own declared `facilities_id` —
never a hard-coded Python dict literal naming a filename or an id. This
mirrors `engine.per_diem.PER_DIEM_PATH_BY_ID`'s exact convention (plan
04-03) for the identical reason: a committed facilities id embeds a
jurisdiction-shaped prefix by this project's own filename convention
(matching each committed city's own `city_id`), and writing that id as a
Python literal directly in this module's source would trip the JUR-05
substring scan a hard-coded dict would.

**Pricing treatment (research row A5).** A disclosed range (`rate_low`,
`rate_high`) is more honest than a single point estimate when the
underlying anchor figures are individual, wildly-variable marketing
listings with no standardization. This module applies the range at its
LOW BOUND uniformly across every facilities category in both committed
cities — never the midpoint — and states the disclosed upper bound in
every Figure's derivation. See 04-04-SUMMARY.md for the full stated
rationale for choosing the low bound over the midpoint.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from engine.figure import Basis, Figure
from engine.rounding import quantize_money
from engine.seasonality import SHOOT_DAYS_PER_WEEK

__all__ = [
    "FACILITIES_CATEGORIES",
    "FACILITIES_DIR",
    "FACILITIES_PATH_BY_ID",
    "FacilitiesEntry",
    "FacilitiesTable",
    "facilities_lines",
    "load_facilities",
]

# Module-anchored, never CWD-relative — matches `engine/cost_profile.py
# ::COST_PROFILES_DIR`, `engine/union_rates.py::UNION_RATES_DIR` and
# `engine/per_diem.py::PER_DIEM_DIR` (the systemd unit and pytest run from
# different working directories).
FACILITIES_DIR = Path(__file__).resolve().parents[1] / "data" / "facilities"

# The five never-sourced categories COST-06 names — a closed set, matching
# a subset of `engine.cost_profile.CostCategory`/`engine.landed_cost
# .COST_CATEGORIES`. Declaration order here also fixes the tuple order
# `facilities_lines` returns.
FACILITIES_CATEGORIES: tuple[str, ...] = (
    "stages",
    "equipment",
    "permits",
    "locations",
    "trucking",
)

_FACILITIES_LABEL: dict[str, str] = {
    "stages": "Stages",
    "equipment": "Equipment",
    "permits": "Permits",
    "locations": "Locations",
    "trucking": "Trucking",
}

# Which shoot-day count drives each category's quantity (Task 2,
# COST-06/D-53): stages price per STAGE shoot day; locations and permits
# price per LOCATION shoot day; equipment and trucking price per TOTAL
# shoot day. Declared as data here so `facilities_lines` reads it once
# rather than re-deriving the mapping inline.
_STAGE_DRIVEN = frozenset({"stages"})
_LOCATION_DRIVEN = frozenset({"locations", "permits"})
_TOTAL_DRIVEN = frozenset({"equipment", "trucking"})

RateUnit = Literal["shoot_day", "week", "flat"]


class StrictModel(BaseModel):
    """Local mirror of `engine.cost_profile.StrictModel` (forbids
    unrecognised fields). Deliberately not imported from that module — a
    domain model should not drag its import graph in for a two-line
    convention (matches every other module in this phase's own
    precedent)."""

    model_config = ConfigDict(extra="forbid")


class FacilitiesEntry(StrictModel):
    """One category's disclosed range for one city. `basis` is typed as
    the FULL three-value `Basis` (not a narrowed two-value Literal) so
    that a `basis: "sourced"` entry is caught by `_never_sourced` below
    with a message naming COST-06 explicitly — a narrowed Literal would
    only produce Pydantic's generic enum-mismatch message, losing the
    COST-06 citation the acceptance criteria require."""

    category: str
    rate_low: str
    rate_high: str
    rate_unit: RateUnit
    basis: Basis
    source_url: str | None = None
    date_checked: str | None = None
    anchor_note: str | None = None
    method_note: str

    @model_validator(mode="after")
    def _never_sourced(self) -> FacilitiesEntry:
        if self.basis == "sourced":
            raise ValueError(
                f"facilities entry {self.category!r}: basis 'sourced' is never legal "
                "here (COST-06) — no standardized public rate card exists for stages, "
                "equipment, permits, locations or trucking (04-RESEARCH.md Pitfall 4); "
                "use 'estimated' with a named anchor, or 'modelling_assumption' when "
                "none exists"
            )
        return self

    @model_validator(mode="after")
    def _method_note_is_non_empty(self) -> FacilitiesEntry:
        if not self.method_note.strip():
            raise ValueError(
                f"facilities entry {self.category!r}: method_note must be a non-empty "
                "string disclosing how the range was arrived at (PITFALLS E1/E5)"
            )
        return self

    @model_validator(mode="after")
    def _source_url_requires_anchor_note(self) -> FacilitiesEntry:
        if self.source_url and not self.anchor_note:
            raise ValueError(
                f"facilities entry {self.category!r}: a source_url requires a "
                "non-null anchor_note naming the specific public listing or "
                "published rate the range was drawn from"
            )
        return self


class FacilitiesTable(StrictModel):
    """One committed city's facilities reference table — exactly the five
    `FACILITIES_CATEGORIES`, never more, never fewer."""

    facilities_id: str
    city_label: str
    provenance_note: str
    entries: dict[str, FacilitiesEntry]

    @model_validator(mode="after")
    def _covers_exactly_the_five_categories(self) -> FacilitiesTable:
        missing = [c for c in FACILITIES_CATEGORIES if c not in self.entries]
        if missing:
            raise ValueError(
                f"facilities table {self.facilities_id!r} is missing entries for "
                f"{missing!r} — all five FACILITIES_CATEGORIES are required"
            )
        extra = [c for c in self.entries if c not in FACILITIES_CATEGORIES]
        if extra:
            raise ValueError(
                f"facilities table {self.facilities_id!r} declares unrecognised "
                f"categories {extra!r} — only {FACILITIES_CATEGORIES} are legal"
            )
        for key, entry in self.entries.items():
            if entry.category != key:
                raise ValueError(
                    f"facilities table {self.facilities_id!r}: entry keyed {key!r} "
                    f"declares category {entry.category!r} — the dict key and the "
                    "entry's own category field must match"
                )
        return self


def _discover_facilities_paths() -> dict[str, Path]:
    """Glob every committed facilities YAML under `FACILITIES_DIR` and
    read each file's own declared `facilities_id` — see module docstring
    for why this is a glob, not a hard-coded dict literal."""
    mapping: dict[str, Path] = {}
    for path in sorted(FACILITIES_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        facilities_id = raw.get("facilities_id") if raw else None
        if facilities_id:
            mapping[facilities_id] = path
    return mapping


FACILITIES_PATH_BY_ID: dict[str, Path] = _discover_facilities_paths()


def load_facilities(facilities_id: str) -> FacilitiesTable:
    """The single facilities-table read path. `facilities_id` is compared
    against `FACILITIES_PATH_BY_ID` by plain string equality — no
    normalization, no fuzzy matching. Parses with `yaml.safe_load` only."""
    path = FACILITIES_PATH_BY_ID.get(facilities_id)
    if path is None:
        raise ValueError(
            f"no committed facilities table declares facilities_id {facilities_id!r} "
            f"under {FACILITIES_DIR}"
        )
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return FacilitiesTable.model_validate(raw)


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _quantity_and_driver_note(
    category: str,
    rate_unit: RateUnit,
    *,
    shoot_days_stage: Decimal,
    shoot_days_location: Decimal,
    total_shoot_days: Decimal,
) -> tuple[Decimal, str]:
    """Resolve the driving day-count for `category` (Task 2's declared
    mapping), then convert it into the RATE's own unit. `rate_unit` never
    changes WHICH day-count drives a category — only how that day-count is
    expressed against the committed rate (a day count directly for
    `"shoot_day"`, a week count derived via the committed
    `SHOOT_DAYS_PER_WEEK` constant for `"week"`, or a single flat unit for
    `"flat"` regardless of duration)."""
    if category in _STAGE_DRIVEN:
        days, driver_note = shoot_days_stage, f"{shoot_days_stage} stage shoot day(s)"
    elif category in _LOCATION_DRIVEN:
        days, driver_note = (
            shoot_days_location,
            f"{shoot_days_location} location shoot day(s)",
        )
    elif category in _TOTAL_DRIVEN:
        days, driver_note = total_shoot_days, f"{total_shoot_days} total shoot day(s)"
    else:
        raise ValueError(f"facilities_lines: unrecognised category {category!r}")

    if rate_unit == "flat":
        return Decimal("1"), f"driven by {driver_note}, but priced as a single flat unit"
    if rate_unit == "week":
        weeks = days / Decimal(SHOOT_DAYS_PER_WEEK)
        return weeks, (
            f"driven by {driver_note}, converted to {weeks} week(s) at "
            f"{SHOOT_DAYS_PER_WEEK} shoot days per week (D-65's committed constant)"
        )
    return days, f"driven by {driver_note}"


def facilities_lines(
    table: FacilitiesTable,
    *,
    shoot_days_stage: Decimal,
    shoot_days_location: Decimal,
    total_shoot_days: Decimal,
    currency: str,
) -> tuple[Figure, ...]:
    """Price all five `FACILITIES_CATEGORIES` from `table`, in
    `FACILITIES_CATEGORIES` order. Every Figure is priced at the LOW BOUND
    of its declared `[rate_low, rate_high]` range (see module docstring),
    and every derivation states both bounds, which treatment was applied,
    and which shoot-day count drove the quantity."""
    figures: list[Figure] = []
    for category in FACILITIES_CATEGORIES:
        entry = table.entries[category]
        quantity, driver_note = _quantity_and_driver_note(
            category,
            entry.rate_unit,
            shoot_days_stage=shoot_days_stage,
            shoot_days_location=shoot_days_location,
            total_shoot_days=total_shoot_days,
        )
        rate_low = Decimal(entry.rate_low)
        rate_high = Decimal(entry.rate_high)
        value = quantize_money(quantity * rate_low)

        anchor_note = (
            f"anchor: {entry.anchor_note}"
            if entry.anchor_note
            else f"no public anchor — {entry.method_note}"
        )
        source_note = (
            f"source: {entry.source_url}"
            if entry.source_url
            else f"no source_url recorded — basis {entry.basis!r} (COST-06: never sourced)"
        )

        figure = Figure(
            value=value,
            unit=currency,
            label=_FACILITIES_LABEL[category],
            derivation=(
                f"{quantity} {entry.rate_unit}(s) x {rate_low} {currency} (LOW BOUND of "
                f"the disclosed [{rate_low}, {rate_high}] {currency} range) = {value} "
                f"{currency} — the low-bound treatment is applied uniformly across "
                "every facilities category in both committed cities; the disclosed "
                f"upper bound is {rate_high} {currency} (research row A5)",
                driver_note,
                anchor_note,
                source_note,
            ),
            inputs=(),
            source_url=entry.source_url,
            date_checked=_parse_date(entry.date_checked),
            confidence="researched",
            live_fetched_this_run=False,
            basis=entry.basis,
        )
        figures.append(figure)
    return tuple(figures)
