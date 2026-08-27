"""Free-text city -> cost-profile-stem resolution, explicit table only.

Copies `app/services/city_lookup.py`'s discipline exactly: `strip().casefold()`,
an explicit allow-list hit or a state-suffix fallback, no fuzzy match, no
edit distance, no substring scan, no "did you mean" anywhere in this
module. A visitor-supplied city string is NEVER interpolated into a
`Path` — only a stem drawn from `COST_PROFILE_BY_CITY` (or one of the
literal stems `resolve_city_to_profile_stem` returns for a state-suffix
match, each itself a member of that same committed set of stems) is ever
joined to `engine.cost_profile.COST_PROFILES_DIR` (T-04-01).

Plan 04-02 widens this table with Los Angeles (D-54) — this file is
jurisdiction-agnostic cost-profile lookup, unrelated to
`app/services/city_lookup.py`'s jurisdiction resolution (which stays
New-York-only until Phase 5 lands California's rule file, JUR-02). A city
resolving to a cost-profile stem here says nothing about whether an
incentive is modelled for it — see `app/services/spec.py`'s
`incentive_state` handling (D-56).

Plan 04-05 widens this table with London (D-54's third floor city, and
the first non-USD one) — the identical alias/state-suffix discipline
extended to a country suffix, since "London" alone is ambiguous with
London, Ontario or a US "London" (Kentucky, Ohio) in a way "New York" or
"Los Angeles" are not; the ", UK"/", United Kingdom"/", England" suffixes
resolve it unambiguously, mirroring the state-suffix pattern exactly.
"""

from __future__ import annotations

__all__ = ["COST_PROFILE_BY_CITY", "resolve_city_to_profile_stem"]

# Casefolded city string -> committed cost-profile stem (the filename,
# minus ".yaml", under data/cost_profiles/). Seeded with New York's aliases,
# matching app/services/city_lookup.py::CITY_ALIASES's New York entries;
# Los Angeles's aliases added by plan 04-02 (D-54).
COST_PROFILE_BY_CITY: dict[str, str] = {
    "new york": "us-ny-new-york",
    "new york city": "us-ny-new-york",
    "nyc": "us-ny-new-york",
    "manhattan": "us-ny-new-york",
    "brooklyn": "us-ny-new-york",
    "queens": "us-ny-new-york",
    "bronx": "us-ny-new-york",
    "the bronx": "us-ny-new-york",
    "staten island": "us-ny-new-york",
    "long island city": "us-ny-new-york",
    "astoria": "us-ny-new-york",
    "buffalo": "us-ny-new-york",
    "rochester": "us-ny-new-york",
    "albany": "us-ny-new-york",
    "syracuse": "us-ny-new-york",
    "yonkers": "us-ny-new-york",
    "los angeles": "us-ca-los-angeles",
    "la": "us-ca-los-angeles",
    "hollywood": "us-ca-los-angeles",
    "burbank": "us-ca-los-angeles",
    "culver city": "us-ca-los-angeles",
    "london": "gb-london",
    "greater london": "gb-london",
}

# Mirrors app/services/city_lookup.py::NY_STATE_SUFFIXES exactly — a
# ", NY"/", New York" suffix resolves to the same committed stem any of the
# aliases above resolve to, never a freshly-interpolated one. Los Angeles's
# ", CA"/", California" suffix mirrors the same pattern (D-54).
_NY_STATE_SUFFIXES: tuple[str, ...] = (", ny", ", new york")
_NY_STATE_SUFFIX_STEM = "us-ny-new-york"
_CA_STATE_SUFFIXES: tuple[str, ...] = (", ca", ", california")
_CA_STATE_SUFFIX_STEM = "us-ca-los-angeles"
# London's country-suffix analogue (D-54): "London" alone is ambiguous
# with London, Ontario or a US "London" in a way "New York"/"Los Angeles"
# are not, but a country-qualified string resolves unambiguously —
# mirrors the state-suffix pattern exactly, one committed stem, no
# fuzzy match.
_UK_STATE_SUFFIXES: tuple[str, ...] = (", uk", ", united kingdom", ", england")
_UK_STATE_SUFFIX_STEM = "gb-london"


def resolve_city_to_profile_stem(raw_city: str) -> str | None:
    """Resolve `raw_city` to a committed cost-profile stem, or `None` if no
    profile is committed for it. Normalizes with `strip().casefold()` and
    nothing else. Returns an alias-table hit if there is one; otherwise, if
    the normalized string ends with a New York, Los Angeles or UK country
    suffix, returns the matching stem; otherwise returns `None`. No further
    branch."""
    normalized = raw_city.strip().casefold()
    if normalized in COST_PROFILE_BY_CITY:
        return COST_PROFILE_BY_CITY[normalized]
    if normalized.endswith(_NY_STATE_SUFFIXES):
        return _NY_STATE_SUFFIX_STEM
    if normalized.endswith(_CA_STATE_SUFFIXES):
        return _CA_STATE_SUFFIX_STEM
    if normalized.endswith(_UK_STATE_SUFFIXES):
        return _UK_STATE_SUFFIX_STEM
    return None
