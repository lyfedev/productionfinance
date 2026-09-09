"""app/services/export.py — UI-09: the self-contained export document.

Assembles a printable/downloadable snapshot of one comparison: the
two-band ranked list, the decomposed gap (or its refusal — D-55's
never-fabricated-number discipline), every figure's source and date, the
model-wide assumptions, and the D-60 acknowledged-gaps list. Holds no
pricing logic of its own — every dollar figure is read from the SAME
`app.services.compare.build_comparison` output every other surface
renders, via `app.services.provenance.build_rate_sheets` (the identical
derivation `/assumptions` already uses, `app/routers/methodology.py`).
This module's only job is assembling those pieces into one render-ready
`ExportDocument`.

UI-09's "complete without JavaScript" requirement is satisfied entirely
by generation: `build_export_document` and `export_document.html` do not
depend on anything happening in a browser — a recipient who opens the
rendered HTML with scripting disabled sees the identical page a producer
who forwarded it saw.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.services.compare import CompareInputs, Comparison, build_comparison
from app.services.provenance import CityRateSheet, build_rate_sheets
from engine.landed_cost import COST_CATEGORIES, PERMANENT_EXCLUSIONS

__all__ = ["ExportDocument", "build_export_document"]


@dataclass(frozen=True)
class ExportDocument:
    """The render-ready view model `export_document.html` renders.

    `comparison` carries the full two-band ranked list, the gap
    selection (a real decomposition or a stated refusal — never both),
    and every other field `/compare` itself renders. `rate_sheets` is
    the SAME per-city rate list `/assumptions` derives
    (`app.services.provenance.build_rate_sheets`), so this document's own
    per-figure sources/dates can never drift from what the comparison
    page shows for the identical comparison. `permanent_exclusions`/
    `cost_categories` are read from `engine.landed_cost` directly (D-60)
    — the acknowledged-gaps list travels with the document because it is
    read from the same place every other surface reads it, not
    hand-copied into this module."""

    comparison: Comparison
    rate_sheets: tuple[CityRateSheet, ...]
    permanent_exclusions: tuple[str, ...]
    cost_categories: tuple[str, ...]
    generated_at: str


def build_export_document(inputs: CompareInputs) -> ExportDocument:
    """Build one `ExportDocument` for `inputs` — the identical
    `Comparison` `/compare` renders (`app.services.compare
    .build_comparison`, unchanged), plus the assembled rate sheets and
    the model-wide acknowledged-gaps list. `generated_at` is stamped
    fresh on every call — an exported document states exactly when it
    was produced, never an ambient "as of now" the recipient has to
    infer."""
    comparison = build_comparison(inputs)
    rate_sheets = build_rate_sheets((*comparison.net_ranked, *comparison.incentive_not_modelled))
    return ExportDocument(
        comparison=comparison,
        rate_sheets=rate_sheets,
        permanent_exclusions=PERMANENT_EXCLUSIONS,
        cost_categories=COST_CATEGORIES,
        generated_at=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
