"""`PerDiemTable` — the committed schema for one GSA/State-Dept per-diem
snapshot, and its single read path (COST-04, D-61, D-64).

`PER_DIEM_PATH_BY_ID` is built by GLOBBING every committed YAML under
`PER_DIEM_DIR` and reading each file's OWN declared `per_diem_id` — never a
hard-coded Python dict literal naming a filename or an id. Two independent
reasons: (1) it mirrors `engine.union_rates.load_union_rates`'s existing
glob-and-read convention exactly rather than inventing a second one; (2) a
committed per-diem id embeds a jurisdiction-shaped prefix by the project's
own filename convention, and writing that id as a Python literal directly
in this module's source would trip the JUR-05 substring scan the same way
an early draft of `engine/union_rates.py`'s docstring did in plan 04-02 —
glob discovery avoids the collision structurally rather than requiring a
scan exception.

T-04-10: `PER_DIEM_PATH_BY_ID` is computed once, at import time, from files
already committed to the repo — a visitor-supplied string is looked up
against this table by plain equality and never joined to a path directly.

`lodging_for_month` is the D-64 fallback made structural: a table declares
EITHER `lodging_by_month` (a genuine month-banded snapshot) OR
`lodging_flat_rate` (a genuine absence of seasonal signal) — never both,
never neither, and a month absent from a band map is a raise, never a
nearest-neighbour guess.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

__all__ = [
    "PER_DIEM_DIR",
    "PER_DIEM_PATH_BY_ID",
    "PerDiemTable",
    "load_per_diem",
    "lodging_for_month",
]

# Module-anchored, never CWD-relative — matches `engine/cost_profile.py
# ::COST_PROFILES_DIR` and `engine/union_rates.py::UNION_RATES_DIR` (the
# systemd unit and pytest run from different working directories).
PER_DIEM_DIR = Path(__file__).resolve().parents[1] / "data" / "per_diem"

Basis = Literal["sourced", "estimated", "modelling_assumption"]


class StrictModel(BaseModel):
    """Local mirror of `engine.cost_profile.StrictModel` (forbids
    unrecognised fields). Deliberately not imported from that module — a
    domain model should not drag its import graph in for a two-line
    convention (matches every other module in this phase's own precedent)."""

    model_config = ConfigDict(extra="forbid")


class PerDiemTable(StrictModel):
    """One committed per-diem snapshot. Exactly one of `lodging_by_month`
    (a genuine month-banded rate) or `lodging_flat_rate` (a genuine
    year-round rate, D-64's stated fallback) must be declared — declaring
    neither or both is a data-authoring error, caught here rather than at
    price time."""

    per_diem_id: str
    fiscal_year: str
    county: str
    source_url: str
    retrieved_at: str
    mie_daily: str
    basis: Basis
    lodging_by_month: dict[str, str] | None = None
    lodging_flat_rate: str | None = None
    method_note: str | None = None
    # D-61: the reimbursement-ceiling disclaimer, structural on the table so
    # it can be copied onto every Figure this table produces.
    ceiling_caveat: str
    # D-64: required only for a flat-rate table — the stated reason
    # seasonality is genuinely absent, not merely unresearched.
    seasonality_note: str | None = None

    @model_validator(mode="after")
    def _exactly_one_lodging_shape(self) -> PerDiemTable:
        has_month_band = self.lodging_by_month is not None
        has_flat_rate = self.lodging_flat_rate is not None
        if has_month_band == has_flat_rate:
            raise ValueError(
                f"per-diem table {self.per_diem_id!r} must declare exactly one of "
                "lodging_by_month or lodging_flat_rate — never neither, never both"
            )
        return self

    @model_validator(mode="after")
    def _ceiling_caveat_is_non_empty(self) -> PerDiemTable:
        if not self.ceiling_caveat.strip():
            raise ValueError(
                f"per-diem table {self.per_diem_id!r}: ceiling_caveat must be a "
                "non-empty string (D-61) — no per-diem figure is presented without it"
            )
        return self

    @model_validator(mode="after")
    def _sourced_requires_source_url(self) -> PerDiemTable:
        if self.basis == "sourced" and not self.source_url:
            raise ValueError(
                f"per-diem table {self.per_diem_id!r}: basis 'sourced' requires a "
                "non-null source_url — an unsourced 'sourced' claim is the exact "
                "class of dishonesty D-58/D-59 exist to prevent"
            )
        return self

    @model_validator(mode="after")
    def _non_sourced_requires_method_note(self) -> PerDiemTable:
        if self.basis != "sourced" and not self.method_note:
            raise ValueError(
                f"per-diem table {self.per_diem_id!r}: basis {self.basis!r} requires "
                "a non-null method_note disclosing the non-primary method used "
                "(PITFALLS E1/E5)"
            )
        return self


def _discover_per_diem_paths() -> dict[str, Path]:
    """Glob every committed per-diem YAML under `PER_DIEM_DIR` and read
    each file's own declared `per_diem_id` — see module docstring for why
    this is a glob, not a hard-coded dict literal."""
    mapping: dict[str, Path] = {}
    for path in sorted(PER_DIEM_DIR.rglob("*.yaml")):
        with open(path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        per_diem_id = raw.get("per_diem_id") if raw else None
        if per_diem_id:
            mapping[per_diem_id] = path
    return mapping


PER_DIEM_PATH_BY_ID: dict[str, Path] = _discover_per_diem_paths()


def load_per_diem(per_diem_id: str) -> PerDiemTable:
    """The single per-diem read path. `per_diem_id` is compared against
    `PER_DIEM_PATH_BY_ID` by plain string equality — no normalization, no
    case folding, no fuzzy matching. A visitor-supplied string never
    reaches this function; the id always comes from a committed
    `CityCostProfile.travel.per_diem_id` field (T-04-10). Parses with
    `yaml.safe_load` only."""
    path = PER_DIEM_PATH_BY_ID.get(per_diem_id)
    if path is None:
        raise ValueError(
            f"no committed per-diem table declares per_diem_id {per_diem_id!r} under "
            f"{PER_DIEM_DIR} — a visitor string never reaches this loader"
        )
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return PerDiemTable.model_validate(raw)


def lodging_for_month(table: PerDiemTable, year_month: str) -> Decimal:
    """The month's lodging rate when `table` carries a genuine month band,
    or the flat rate when it does not (D-64). A `year_month` absent from a
    declared band map raises — never a fallback to a neighbouring month,
    never an interpolation."""
    if table.lodging_by_month is not None:
        if year_month not in table.lodging_by_month:
            raise ValueError(
                f"per-diem table {table.per_diem_id!r} has no lodging_by_month entry "
                f"for {year_month!r} — no fallback to a neighbouring month is "
                "performed (D-64)"
            )
        return Decimal(table.lodging_by_month[year_month])
    assert table.lodging_flat_rate is not None
    return Decimal(table.lodging_flat_rate)
