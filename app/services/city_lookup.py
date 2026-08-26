"""Free-text city -> jurisdiction resolution, explicit table only (D-40).

`resolve_city_to_jurisdiction`'s output is fully predictable from reading
`CITY_ALIASES` and `NY_STATE_SUFFIXES` alone — no fuzzy match, no edit
distance, no gazetteer, no "did you mean" anywhere in this module
(Pitfall 5). New York is this phase's only curated jurisdiction and
`jurisdictions/us-ny.yaml` is state-level, so any New York city name maps
to it.

Mirrors `engine/handlers/__init__.py`'s convention: a small, explicit,
committed `dict` allow-list, never dynamic resolution.
"""

from __future__ import annotations

__all__ = ["CITY_ALIASES", "NY_STATE_SUFFIXES", "resolve_city_to_jurisdiction"]

# Casefolded city string -> jurisdiction id. New York's best-known
# production locations only (A4: scoped narrow deliberately — see
# 03-RESEARCH.md Open Question 2 / Assumption A4).
CITY_ALIASES: dict[str, str] = {
    "new york": "us-ny",
    "new york city": "us-ny",
    "nyc": "us-ny",
    "manhattan": "us-ny",
    "brooklyn": "us-ny",
    "queens": "us-ny",
    "bronx": "us-ny",
    "the bronx": "us-ny",
    "staten island": "us-ny",
    "long island city": "us-ny",
    "astoria": "us-ny",
    "buffalo": "us-ny",
    "rochester": "us-ny",
    "albany": "us-ny",
    "syracuse": "us-ny",
    "yonkers": "us-ny",
}

NY_STATE_SUFFIXES: tuple[str, ...] = (", ny", ", new york")


def resolve_city_to_jurisdiction(raw_city: str) -> str | None:
    """Resolve `raw_city` to a jurisdiction id, or `None` if uncurated.

    Normalizes with `strip().casefold()` and nothing else — no Unicode
    normalization form, no byte- or grapheme-level comparison, and interior
    whitespace is never collapsed. Returns an alias-table hit if there is
    one; otherwise, if the normalized string ends with one of
    `NY_STATE_SUFFIXES`, returns `"us-ny"`; otherwise returns `None`. There
    is no third branch — no edit-distance call, no substring scan, no
    nearest-curated-jurisdiction fallback (D-40).
    """
    normalized = raw_city.strip().casefold()
    if normalized in CITY_ALIASES:
        return CITY_ALIASES[normalized]
    if normalized.endswith(NY_STATE_SUFFIXES):
        return "us-ny"
    return None
