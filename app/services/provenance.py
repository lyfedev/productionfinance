"""UI-06/PRV-04 — the provenance rendering layer's own service module.

Holds no pricing logic (mirrors `app/routers/spec.py`'s established
no-business-logic contract). Every function here operates on `Figure`
objects the engine already produced — it never invents a source, a date,
or a rate. Its one job is to walk the REAL recursive `inputs` DAG (the
same DAG `tests/test_route_a_basis_walk.py`'s D-63 gate already proves is
free of fabricated `validated` claims) and turn it into two things a
template can render honestly:

1. `figure_provenance_state` — for `app/templates/_figure.html`, the
   single component every money figure in this surface renders through
   (UI-06). A figure with no reachable provenance is never a bare number
   — it renders an explicit statement naming what is missing.
2. `collect_rate_figures` / `build_rate_sheet` — for the consolidated
   printable assumptions panel (PRV-04), the deduplicated list of every
   atomic rate a comparison's totals were actually built from, derived
   from the Figure tree itself rather than a hand-maintained list that
   can drift out of sync with what the engine really used.

Two provenance axes are rendered here and are NEVER merged into one
badge (RD-02, `engine/figure.py`'s own docstring):
  - `Figure.confidence` (`validated` | `researched`) — has this figure
    been checked against a real government disclosure?
  - `Figure.basis` (`sourced` | `estimated` | `modelling_assumption` |
    `None`) — where did this number come from? `None` is the
    incentive-side's deliberate "this axis does not apply" state
    (`engine/figure.py`'s own docstring), never rendered as though it
    were a missing cost-side value.

D-59, restated for this module: a total's `basis` field is ALREADY the
weakest of its inputs — `engine.figure.combined_basis` computed that at
construction time, everywhere a cost-side total is built
(`engine/landed_cost.py::aggregate`). This module never recomputes
`basis` and never overrides what the engine already decided; it only
renders `figure.basis` verbatim. A total containing one
`modelling_assumption` leaf therefore reads `modelling_assumption` here
because it already does on the `Figure` itself — rendering the field
truthfully is what keeps the promise, not a second calculation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from engine.figure import Figure
from engine.ranker import RankedCity

__all__ = [
    "CityRateSheet",
    "FigureProvenanceState",
    "build_rate_sheet",
    "build_rate_sheets",
    "collect_distinct_figures",
    "collect_rate_figures",
    "figure_provenance_state",
]


@dataclass(frozen=True)
class FigureProvenanceState:
    """The verdict `_figure.html` renders for one `Figure`.

    `state` is one of three values, never collapsed to a boolean:
      - `"sourced"` — `figure.source_url` is set; a direct citation link
        is reachable.
      - `"computed"` — no direct `source_url` of its own, but
        `figure.inputs` is non-empty: this is an aggregate whose own
        provenance IS its input tree (each input carries its own
        provenance, reachable by expanding the derivation) — genuinely
        NOT a dead end, so this is never rendered as "unavailable".
      - `"unavailable"` — a LEAF figure (`figure.inputs` is empty) with
        no `source_url`: a genuine dead end, nothing further to expand
        into. `reason` names what is missing and why (a modelling
        assumption has no public source to cite at all; anything else
        missing a citation here is a real gap, named as one).
    """

    state: str
    reason: str | None


def figure_provenance_state(figure: Figure) -> FigureProvenanceState:
    """Classify `figure`'s reachable provenance (UI-06).

    Never returns `"unavailable"` for a figure that has a reachable path
    to sourced data through its own `inputs` — an aggregate total (e.g.
    `engine.landed_cost.aggregate`'s `cost_total`/`total_landed_cost`)
    deliberately carries `source_url=None` because ITS source is the
    disclosed sum of its inputs, not a single external document; treating
    that as "unavailable" would be dishonest in the other direction —
    claiming provenance is missing when it is, in fact, fully reachable
    one click away.
    """
    if figure.source_url:
        return FigureProvenanceState(state="sourced", reason=None)
    if figure.inputs:
        return FigureProvenanceState(state="computed", reason=None)
    if figure.basis == "modelling_assumption":
        return FigureProvenanceState(
            state="unavailable",
            reason=(
                "this is a modelling assumption (basis: modelling_assumption) — "
                "no public source exists for it; see the methodology page for "
                "what that means and why it is disclosed rather than hidden"
            ),
        )
    return FigureProvenanceState(
        state="unavailable",
        reason="no source citation was recorded for this figure",
    )


def collect_distinct_figures(roots: Sequence[Figure]) -> tuple[Figure, ...]:
    """Walk every root in `roots` recursively through `.inputs`,
    collecting every distinct node once, deduped by `figure_id`.

    Mirrors `tests/test_route_a_basis_walk.py`'s own established
    `_collect_tree` walk shape — this module is the one place that
    pattern moves from a test-only helper into product code, since the
    rendering layer needs the identical walk the D-63 CI gate already
    proves is honest.
    """
    seen: dict[str, Figure] = {}
    stack: list[Figure] = list(roots)
    while stack:
        figure = stack.pop()
        if figure.figure_id in seen:
            continue
        seen[figure.figure_id] = figure
        stack.extend(figure.inputs)
    return tuple(seen.values())


def _content_key(figure: Figure) -> tuple:
    return (
        figure.label,
        figure.source_url,
        figure.date_checked,
        str(figure.value),
        figure.unit,
        figure.basis,
        figure.confidence,
    )


def collect_rate_figures(roots: Sequence[Figure]) -> tuple[Figure, ...]:
    """Every LEAF figure (no further `.inputs`) reachable from `roots` —
    the atomic rates a total is built from, as distinct from a computed
    subtotal. This is the function PRV-04's assumptions panel derives its
    rate list from: it walks the REAL Figure tree the engine produced for
    this comparison, never a hand-maintained list that could drift out of
    sync with what the pipeline actually used.

    Deduplicated by CONTENT (label, source_url, date_checked, value,
    unit, basis, confidence), not by `figure_id` — two derivation
    branches that both consulted the identical published rate (e.g. the
    same per-diem row applied to housing and to M&IE) collapse to one
    row on a printable panel rather than repeating the same citation
    twice. Sorted by label then source_url for a stable, printable order.
    """
    distinct = collect_distinct_figures(roots)
    leaves = [figure for figure in distinct if not figure.inputs]

    seen_keys: set[tuple] = set()
    unique: list[Figure] = []
    for figure in leaves:
        key = _content_key(figure)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append(figure)

    return tuple(sorted(unique, key=lambda f: (f.label, f.source_url or "")))


@dataclass(frozen=True)
class CityRateSheet:
    """One city's row set for the consolidated assumptions panel
    (PRV-04). `rates` is derived from `city.total_landed_cost`'s own
    Figure tree (`collect_rate_figures`) — never hand-maintained.
    `not_priced`/`permanent_exclusions` are read straight off
    `city.landed_cost` (already computed by `engine.landed_cost
    .aggregate`, D-60) — never re-declared here, so this sheet cannot
    drift from what the engine actually excluded."""

    city_id: str
    total_landed_cost: Figure
    cost_only_total: Figure
    incentive_figure: Figure | None
    rates: tuple[Figure, ...]
    not_priced: tuple[str, ...]
    permanent_exclusions: tuple[str, ...]


def build_rate_sheet(city: RankedCity) -> CityRateSheet:
    """Build one city's `CityRateSheet` from a real `RankedCity` — the
    exact object `engine.ranker.rank` (by way of
    `app.services.compare.build_comparison`) already produced. Rates are
    collected from `total_landed_cost`'s tree, which already contains
    `cost_only_total`'s cost lines PLUS the incentive figure's own tree
    when one was priced (`engine.landed_cost.aggregate` nests both under
    `total_landed_cost.inputs`) — one walk covers both, never two
    separate walks that could disagree."""
    rates = collect_rate_figures([city.total_landed_cost])
    return CityRateSheet(
        city_id=city.city_id,
        total_landed_cost=city.total_landed_cost,
        cost_only_total=city.cost_only_total,
        incentive_figure=city.incentive_figure,
        rates=rates,
        not_priced=city.landed_cost.not_priced,
        permanent_exclusions=city.landed_cost.permanent_exclusions,
    )


def build_rate_sheets(cities: Sequence[RankedCity]) -> tuple[CityRateSheet, ...]:
    """One `CityRateSheet` per city in `cities`, in the SAME order the
    caller supplies (never re-sorted here — mirrors D-55's own
    ranked-band-then-unranked-band ordering when the caller passes
    `(*comparison.net_ranked, *comparison.incentive_not_modelled)`)."""
    return tuple(build_rate_sheet(city) for city in cities)
