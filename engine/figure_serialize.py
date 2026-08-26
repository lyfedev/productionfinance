"""Recursive `Figure` -> JSON-safe dict conversion.

Reproduced from `03-RESEARCH.md` Pattern 2 (Code Examples), matching this
plan's `03-PATTERNS.md` file classification (an exact match, same as Phase
2's `engine/rounding.py`-style single-purpose pure utility).

D-44: this module imports only from `engine.figure` and the standard
library — nothing here (or anywhere in `engine/`) may import the web
framework. D-45: `inputs` recurses over every child in full, no depth cap,
no summarization — the derivation tree is the product's provenance claim
and a flattened/truncated tree silently deletes the evidence.

`figure_to_dict` must be the only path a `Figure` takes to a JSON response.
Never call `dataclasses.asdict(figure)` directly and return it — `Decimal`
and `date` fields are not JSON-native and crash the default JSON encoder
with a 500 at encode time, not a 422 (Pitfall 4).
"""

from __future__ import annotations

from engine.figure import Figure

__all__ = ["figure_to_dict"]


def figure_to_dict(figure: Figure) -> dict:
    """Convert `figure` and its full recursive `inputs` tree to a
    JSON-safe dict. `value` is converted with `str(...)` so Decimal
    precision survives the JSON boundary intact — a numeric conversion
    here would reintroduce Phase 2's own precision bug."""
    return {
        "figure_id": figure.figure_id,
        "value": str(figure.value),
        "unit": figure.unit,
        "label": figure.label,
        "derivation": list(figure.derivation),
        "source_url": figure.source_url,
        "date_checked": figure.date_checked.isoformat() if figure.date_checked else None,
        "confidence": figure.confidence,
        "live_fetched_this_run": figure.live_fetched_this_run,
        "inputs": [figure_to_dict(child) for child in figure.inputs],
    }
