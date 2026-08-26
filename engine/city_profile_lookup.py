"""Free-text city -> cost-profile-stem resolution, explicit table only.

Copies `app/services/city_lookup.py`'s discipline exactly: `strip().casefold()`,
an explicit allow-list hit or a state-suffix fallback, no fuzzy match, no
edit distance, no substring scan, no "did you mean" anywhere in this
module. A visitor-supplied city string is NEVER interpolated into a
`Path` — only a stem drawn from `COST_PROFILE_BY_CITY` (or the single
literal `resolve_city_to_profile_stem` returns for a state-suffix match,
itself a member of that same committed set of stems) is ever joined to
`engine.cost_profile.COST_PROFILES_DIR` (T-04-01).
"""

from __future__ import annotations

__all__ = ["COST_PROFILE_BY_CITY", "resolve_city_to_profile_stem"]

# Casefolded city string -> committed cost-profile stem (the filename,
# minus ".yaml", under data/cost_profiles/). Seeded with New York's aliases,
# matching app/services/city_lookup.py::CITY_ALIASES's New York entries.
COST_PROFILE_BY_CITY: dict[str, str] = {
    "new york": "new-york",
    "new york city": "new-york",
    "nyc": "new-york",
    "manhattan": "new-york",
    "brooklyn": "new-york",
    "queens": "new-york",
    "bronx": "new-york",
    "the bronx": "new-york",
    "staten island": "new-york",
    "long island city": "new-york",
    "astoria": "new-york",
    "buffalo": "new-york",
    "rochester": "new-york",
    "albany": "new-york",
    "syracuse": "new-york",
    "yonkers": "new-york",
}

# Mirrors app/services/city_lookup.py::NY_STATE_SUFFIXES exactly — a
# ", NY"/", New York" suffix resolves to the same committed stem any of the
# aliases above resolve to, never a freshly-interpolated one.
_NY_STATE_SUFFIXES: tuple[str, ...] = (", ny", ", new york")
_NY_STATE_SUFFIX_STEM = "new-york"


def resolve_city_to_profile_stem(raw_city: str) -> str | None:
    """Resolve `raw_city` to a committed cost-profile stem, or `None` if no
    profile is committed for it. Normalizes with `strip().casefold()` and
    nothing else. Returns an alias-table hit if there is one; otherwise, if
    the normalized string ends with a New York state suffix, returns the
    same New York stem; otherwise returns `None`. No third branch."""
    normalized = raw_city.strip().casefold()
    if normalized in COST_PROFILE_BY_CITY:
        return COST_PROFILE_BY_CITY[normalized]
    if normalized.endswith(_NY_STATE_SUFFIXES):
        return _NY_STATE_SUFFIX_STEM
    return None
