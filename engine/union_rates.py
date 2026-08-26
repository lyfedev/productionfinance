"""Dated union rate-card row selection and fringe schedule lookup
(COST-02/COST-03, D-53 cost side).

JURISDICTION-AGNOSTIC (JUR-05): `region` is a profile-declared data key (a
plain region-label string), matched by plain string equality only — this
module never branches on its value and contains no jurisdiction-id
literal of its own.

D-57: every row is read from a committed, dated, quoted-string YAML
snapshot under `data/union_rates/` via `yaml.safe_load` only — no runtime
network call, no new dependency.

WR-03 (mirroring `engine.credit._check_loanout_schedule_for_overlaps` and
`engine.credit._select_loanout_rate`): dated ranges are closed-closed
(`effective_from <= on_date <= effective_to`, with a null `effective_to`
meaning open-ended), overlapping bands for the same region+craft are a
rule-file authoring error caught at load time, and a date covered by no
row raises rather than falling back to the nearest or newest row.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

__all__ = [
    "FRINGE_SCHEDULES_PATH",
    "UNION_RATES_DIR",
    "FringeComponent",
    "FringeSchedule",
    "RateRow",
    "load_fringe_schedules",
    "load_union_rates",
    "select_rate_row",
    "weakest_basis",
]

# Module-anchored, never CWD-relative — matches `engine/cost_profile.py
# ::COST_PROFILES_DIR` and `engine/spec.py::CREW_TIERS_PATH` (the systemd
# unit and pytest run from different working directories).
UNION_RATES_DIR = Path(__file__).resolve().parents[1] / "data" / "union_rates"
FRINGE_SCHEDULES_PATH = UNION_RATES_DIR / "fringe_schedules.yaml"

Basis = Literal["sourced", "estimated", "modelling_assumption"]
RateUnit = Literal["day", "hour", "week"]

# Weakest-wins ordering, mirroring `engine.figure._BASIS_WEAKNESS_ORDER` —
# duplicated locally (not imported) so this module stays free to combine
# three fringe-component bases without constructing throwaway `Figure`
# instances just to call `combined_basis`.
_BASIS_WEAKNESS_ORDER: dict[str, int] = {
    "modelling_assumption": 0,
    "estimated": 1,
    "sourced": 2,
}


def weakest_basis(bases: list[Basis]) -> Basis:
    """The weakest of `bases`, mirroring `engine.figure.combined_basis`'s
    ordering. Raises on an empty list — never silently defaults (D-59's
    discipline applied here too)."""
    if not bases:
        raise ValueError("weakest_basis() received an empty list — nothing to combine")
    return min(bases, key=lambda basis: _BASIS_WEAKNESS_ORDER[basis])


class StrictModel(BaseModel):
    """Local mirror of `engine.cost_profile.StrictModel` (forbids
    unrecognised fields). Deliberately not imported from that module —
    a domain model should not drag in cost_profile's import graph for a
    two-line convention (matches `engine/spec.py`'s own precedent)."""

    model_config = ConfigDict(extra="forbid")


class RateRow(StrictModel):
    """One dated union rate-card row. `rate` is a quoted string (RD-01),
    parsed with `Decimal()` by the caller (`engine/cost_localizer.py`),
    never as a bare YAML-native float — Pydantic's default (non-strict)
    `str` validation already rejects an unquoted YAML number outright
    (it does not coerce int/float to str), so an authoring mistake here
    fails loudly at load time."""

    row_id: str
    union: str
    local: str | None = None
    region: str
    craft: str
    rate: str
    rate_unit: RateUnit
    effective_from: date
    effective_to: date | None = None
    basis: Basis
    source_url: str | None = None
    date_checked: str | None = None
    method_note: str | None = None

    @model_validator(mode="after")
    def _sourced_requires_source_url(self) -> RateRow:
        if self.basis == "sourced" and not self.source_url:
            raise ValueError(
                f"rate row {self.row_id!r}: basis 'sourced' requires a non-null "
                "source_url — an unsourced 'sourced' claim is the exact class of "
                "dishonesty D-58/D-59 exist to prevent"
            )
        return self

    @model_validator(mode="after")
    def _non_sourced_requires_method_note(self) -> RateRow:
        if self.basis != "sourced" and not self.method_note:
            raise ValueError(
                f"rate row {self.row_id!r}: basis {self.basis!r} requires a "
                "non-null method_note disclosing the non-primary method used "
                "(PITFALLS E1/E5)"
            )
        return self


class FringeComponent(StrictModel):
    """One percentage on a union's fringe schedule (pension_health,
    payroll_tax, other_burden) — EACH carries its OWN `basis`/`source_url`/
    `date_checked`/`method_note` (PITFALLS E1): a union document may source
    one percentage while another on the same union is still an industry
    estimate, and collapsing them to one shared basis would misrepresent
    the estimated one as sourced."""

    value: str
    basis: Basis
    source_url: str | None = None
    date_checked: str | None = None
    method_note: str | None = None

    @model_validator(mode="after")
    def _sourced_requires_source_url(self) -> FringeComponent:
        if self.basis == "sourced" and not self.source_url:
            raise ValueError("fringe component: basis 'sourced' requires a non-null source_url")
        return self

    @model_validator(mode="after")
    def _non_sourced_requires_method_note(self) -> FringeComponent:
        if self.basis != "sourced" and not self.method_note:
            raise ValueError(
                f"fringe component: basis {self.basis!r} requires a non-null method_note"
            )
        return self


class FringeSchedule(StrictModel):
    """One union's fringe schedule — three independently-sourced
    percentages, never one shared basis (see `FringeComponent`)."""

    union: str
    pension_health_pct: FringeComponent
    payroll_tax_pct: FringeComponent
    other_burden_pct: FringeComponent


def _bands_overlap(a: RateRow, b: RateRow) -> bool:
    """Standard closed-interval overlap test, mirroring
    `engine.credit._loanout_schedule_bands_overlap` exactly — a null
    `effective_to` is treated as unbounded."""
    a_starts_before_or_on_b_end = b.effective_to is None or a.effective_from <= b.effective_to
    b_starts_before_or_on_a_end = a.effective_to is None or b.effective_from <= a.effective_to
    return a_starts_before_or_on_b_end and b_starts_before_or_on_a_end


def _check_rate_rows_for_overlaps(rows: list[RateRow]) -> None:
    """WR-03: two rows declared for the SAME region+craft with overlapping
    dated ranges is a rule-file authoring error, not something resolved by
    declared list order — mirrors
    `engine.credit._check_loanout_schedule_for_overlaps` exactly. Rows for
    different regions or different crafts never collide with each other,
    however their dates overlap."""
    by_key: dict[tuple[str, str], list[RateRow]] = {}
    for row in rows:
        by_key.setdefault((row.region, row.craft), []).append(row)

    for (region, craft), group in by_key.items():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if _bands_overlap(a, b):
                    a_desc = f"{a.effective_from} through {a.effective_to or 'open-ended'}"
                    b_desc = f"{b.effective_from} through {b.effective_to or 'open-ended'}"
                    raise ValueError(
                        f"union_rates: region={region!r} craft={craft!r} declares two "
                        f"overlapping dated rows — {a.row_id!r} ({a_desc}) and "
                        f"{b.row_id!r} ({b_desc}) both cover at least one shared date. "
                        "A rate table covering the same date twice is an authoring "
                        "error; select_rate_row does not resolve it by declared list order."
                    )


def load_union_rates(paths: list[Path] | None = None) -> list[RateRow]:
    """Load every rate row across every `data/union_rates/*.yaml` file
    (default) or an explicit `paths` list (for tests), via `yaml.safe_load`
    only. `fringe_schedules.yaml` declares no `rows:` key and contributes
    nothing here — its `fringe_schedules:` key is read separately by
    `load_fringe_schedules`. Checks every region+craft group for
    overlapping dated ranges across ALL loaded files combined (a real
    authoring error could span two files, e.g. a future region-specific
    crew file accidentally re-declaring a craft `iatse.yaml` already
    covers)."""
    if paths is None:
        paths = sorted(UNION_RATES_DIR.glob("*.yaml"))

    rows: list[RateRow] = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        for row_data in raw.get("rows", []) or []:
            rows.append(RateRow.model_validate(row_data))

    _check_rate_rows_for_overlaps(rows)
    return rows


def load_fringe_schedules(path: Path | None = None) -> dict[str, FringeSchedule]:
    """Load `data/union_rates/fringe_schedules.yaml` into a `union ->
    FringeSchedule` mapping, via `yaml.safe_load` only."""
    if path is None:
        path = FRINGE_SCHEDULES_PATH
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return {
        entry["union"]: FringeSchedule.model_validate(entry)
        for entry in raw.get("fringe_schedules", []) or []
    }


def select_rate_row(rows: list[RateRow], *, region: str, craft: str, on_date: date) -> RateRow:
    """Select the row for `region`/`craft` whose closed-closed dated range
    covers `on_date` — plain string equality on `region`/`craft`, no
    normalization (JUR-05: `region` is profile-declared data, never
    branched on by value). No match raises `ValueError` naming region,
    craft and date — never falls back to the nearest row, never picks the
    newest."""
    for row in rows:
        if row.region != region or row.craft != craft:
            continue
        if row.effective_from <= on_date and (
            row.effective_to is None or on_date <= row.effective_to
        ):
            return row
    raise ValueError(
        f"no union rate row covers region={region!r} craft={craft!r} on {on_date} — "
        "no fallback to the nearest row or the newest row is performed"
    )
