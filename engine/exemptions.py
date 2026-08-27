"""`ExemptionsTable` — sales-tax and hotel-occupancy exemptions as
stackable COST-side reductions (INC-10, D-76, 04-CONTEXT.md).

D-76's guarantee, structural: an exemption reduction Figure is appended to
`LocalizedBudget.lines` alongside every other cost line (wired in
`engine/cost_localizer.py::localize`) and therefore enters `cost_total`
through the SAME summation every other line uses. It is never passed to
`engine.pipeline.price_jurisdiction`, never constructed from (or attached
to) any Figure in that function's returned `PricedJurisdiction.total_net_cash`
DAG, and never nets against the incentive figure — the only route an
exemption Figure has into the priced total is the cost side.

`EXEMPTIONS_PATH_BY_ID` is built by GLOBBING every committed YAML under
`EXEMPTIONS_DIR` and reading each file's own declared `exemptions_id` —
never a hard-coded Python dict literal, for the identical JUR-05 reason
`engine.per_diem.PER_DIEM_PATH_BY_ID` and `engine.facilities
.FACILITIES_PATH_BY_ID` are glob-discovered rather than literal dicts (a
committed exemptions id embeds a jurisdiction-shaped prefix by this
project's own filename convention).

Matching an exemption to its target cost line is by `applies_to_category`
against `engine.cost_profile.CostCategory`'s closed vocabulary, via plain
string equality — never a positional index, never a substring match. A
category with no priced Figure (or more than one, an ambiguous match)
raises naming the exemption id rather than being silently dropped.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from engine.cost_profile import CostCategory
from engine.figure import Basis, Figure
from engine.rounding import quantize_money

__all__ = [
    "EXEMPTIONS_DIR",
    "EXEMPTIONS_PATH_BY_ID",
    "ExemptionEntry",
    "ExemptionsTable",
    "exemption_reductions",
    "load_exemptions",
]

# Module-anchored, never CWD-relative — matches every sibling reference-
# data module's own directory constant.
EXEMPTIONS_DIR = Path(__file__).resolve().parents[1] / "data" / "tax_exemptions"


class StrictModel(BaseModel):
    """Local mirror of `engine.cost_profile.StrictModel` (forbids
    unrecognised fields). Deliberately not imported from that module — a
    domain model should not drag its import graph in for a two-line
    convention (matches every other module in this phase's own
    precedent)."""

    model_config = ConfigDict(extra="forbid")


class ExemptionEntry(StrictModel):
    """One stackable cost-reduction exemption. `applies_to_category` is
    one of `engine.cost_profile.CostCategory`'s closed vocabulary — the
    SAME vocabulary a `CostLine.category` declares, so matching is a plain
    string-equality join, never a jurisdiction-id branch (JUR-05)."""

    exemption_id: str
    label: str
    applies_to_category: CostCategory
    kind: str
    rate: str
    basis: Basis
    source_url: str | None = None
    date_checked: str | None = None
    method_note: str
    eligibility_note: str

    @model_validator(mode="after")
    def _sourced_requires_source_url(self) -> ExemptionEntry:
        if self.basis == "sourced" and not self.source_url:
            raise ValueError(
                f"exemption {self.exemption_id!r}: basis 'sourced' requires a "
                "non-null source_url — an unsourced 'sourced' claim is the exact "
                "class of dishonesty D-58/D-59 exist to prevent"
            )
        return self

    @model_validator(mode="after")
    def _method_note_and_eligibility_note_non_empty(self) -> ExemptionEntry:
        if not self.method_note.strip():
            raise ValueError(
                f"exemption {self.exemption_id!r}: method_note must be a non-empty "
                "string disclosing the non-primary method used when basis is not "
                "'sourced' (PITFALLS E1/E5)"
            )
        if not self.eligibility_note.strip():
            raise ValueError(
                f"exemption {self.exemption_id!r}: eligibility_note must be a "
                "non-empty plain-words statement of who/what qualifies"
            )
        return self


class ExemptionsTable(StrictModel):
    """One committed city's exemptions table. An empty `exemptions` list is
    legal (a city offering no exemption simply has an empty table, or no
    `exemptions_id` declared on its `CityCostProfile` at all — never an
    entry with a zero rate)."""

    exemptions_id: str
    city_label: str
    provenance_note: str
    exemptions: list[ExemptionEntry]

    @model_validator(mode="after")
    def _unique_exemption_ids(self) -> ExemptionsTable:
        ids = [entry.exemption_id for entry in self.exemptions]
        if len(ids) != len(set(ids)):
            raise ValueError(
                f"exemptions table {self.exemptions_id!r} declares a duplicate "
                "exemption_id"
            )
        return self


def _discover_exemptions_paths() -> dict[str, Path]:
    """Glob every committed exemptions YAML under `EXEMPTIONS_DIR` and read
    each file's own declared `exemptions_id` — see module docstring for
    why this is a glob, not a hard-coded dict literal."""
    mapping: dict[str, Path] = {}
    for path in sorted(EXEMPTIONS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        exemptions_id = raw.get("exemptions_id") if raw else None
        if exemptions_id:
            mapping[exemptions_id] = path
    return mapping


EXEMPTIONS_PATH_BY_ID: dict[str, Path] = _discover_exemptions_paths()


def load_exemptions(exemptions_id: str) -> ExemptionsTable:
    """The single exemptions-table read path. `exemptions_id` is compared
    against `EXEMPTIONS_PATH_BY_ID` by plain string equality — no
    normalization, no fuzzy matching. Parses with `yaml.safe_load` only."""
    path = EXEMPTIONS_PATH_BY_ID.get(exemptions_id)
    if path is None:
        raise ValueError(
            f"no committed exemptions table declares exemptions_id {exemptions_id!r} "
            f"under {EXEMPTIONS_DIR}"
        )
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return ExemptionsTable.model_validate(raw)


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def exemption_reductions(
    table: ExemptionsTable,
    figures_by_category: dict[str, list[Figure]],
    currency: str,
) -> tuple[Figure, ...]:
    """Price every declared exemption in `table` as its own negative-value
    reduction Figure. `figures_by_category` maps a `CostCategory` string to
    every already-priced cost-line Figure declaring that category (built by
    the caller from the localized budget's declared `CostLine`s, matched by
    `Figure.label == CostLine.label`) — an exemption whose
    `applies_to_category` matches NO entry, or MORE than one (an ambiguous
    target), raises naming the exemption id rather than being silently
    dropped or guessed at.

    Each reduction's `value` is `-(matched_figure.value * rate)`, quantized
    once via `quantize_money`; `inputs` is exactly `(matched_figure,)` — the
    single target this reduction applies to, so a reader can walk from the
    reduction straight to the line it reduces. Multiple exemptions
    declared against the SAME category each apply independently to the
    matched figure's PRE-reduction value (never chained against a running
    total) — this is what makes them stackable rather than compounding.
    """
    reductions: list[Figure] = []
    for entry in table.exemptions:
        matches = figures_by_category.get(entry.applies_to_category, [])
        if not matches:
            raise ValueError(
                f"exemption {entry.exemption_id!r} declares applies_to_category "
                f"{entry.applies_to_category!r}, which matches no priced cost line "
                "in this localized budget — an exemption is never silently dropped"
            )
        if len(matches) > 1:
            raise ValueError(
                f"exemption {entry.exemption_id!r}'s applies_to_category "
                f"{entry.applies_to_category!r} matches {len(matches)} priced cost "
                "lines — ambiguous; exemption matching requires exactly one target"
            )
        target = matches[0]
        rate = Decimal(entry.rate)
        reduction_value = quantize_money(-(target.value * rate))

        source_note = (
            f"source: {entry.source_url}"
            if entry.source_url
            else f"no source_url recorded — basis {entry.basis!r}, method: "
            f"{entry.method_note}"
        )
        reduction = Figure(
            value=reduction_value,
            unit=currency,
            label=f"{entry.label} (reduces {target.label!r})",
            derivation=(
                f"{target.value} {currency} x -{rate} ({entry.kind} exemption rate) "
                f"= {reduction_value} {currency}, applied to the PRE-reduction value "
                f"of {target.label!r} — stackable: a second exemption on the same "
                "line applies independently to that same pre-reduction value, never "
                "chained against a running total",
                f"eligibility: {entry.eligibility_note}",
                source_note,
            ),
            inputs=(target,),
            source_url=entry.source_url,
            date_checked=_parse_date(entry.date_checked),
            confidence="researched",
            live_fetched_this_run=False,
            basis=entry.basis,
        )
        reductions.append(reduction)
    return tuple(reductions)
