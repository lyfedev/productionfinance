"""`CityGeo` — the committed cartographic reference table for map placement
(Phase 6, UI-02).

Mirrors `engine/cost_profile.py`'s discipline exactly: a local two-line
`StrictModel` (never imported from `engine.models` — a domain model should
not drag the whole rule-schema import graph in for one convention),
`CITY_GEO_PATH` module-anchored via `Path(__file__).resolve().parents[1]`
(never CWD-relative — `deploy/prodfin.service` sets
`WorkingDirectory=/opt/prodfin` on the host, and pytest runs from the repo
root), and a single `load_city_geo()` read path using `yaml.safe_load`
only.

A coordinate here is a display-layer convenience for MapLibre marker
placement — it is never a priced figure and never derived. A city with no
committed entry returns `None` from `geo_for_city_id` and is simply absent
from the map; it is never given a guessed coordinate.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

__all__ = ["CITY_GEO_PATH", "CityGeo", "StrictModel", "geo_for_city_id", "load_city_geo"]


class StrictModel(BaseModel):
    """Local mirror of `engine.cost_profile.StrictModel` (forbids
    unrecognised fields) — deliberately re-declared rather than imported,
    matching that module's own stated convention."""

    model_config = ConfigDict(extra="forbid")


# Module-anchored, never CWD-relative — matches `engine/cost_profile.py
# ::COST_PROFILES_DIR` exactly.
CITY_GEO_PATH = Path(__file__).resolve().parents[1] / "data" / "city_geo.yaml"


class CityGeo(StrictModel):
    """One committed cartographic reference row. `city_id` matches the
    corresponding `CityCostProfile.city_id` — this table is keyed to
    committed cost profiles, not to a visitor-supplied string."""

    city_id: str
    label: str
    latitude: str
    longitude: str
    source_url: str
    date_checked: str
    note: str


def load_city_geo(path: str | Path = CITY_GEO_PATH) -> dict[str, CityGeo]:
    """The single cartographic-reference read path. Parses with PyYAML's
    *safe* loader only (never `yaml.load`/`yaml.unsafe_load`), matching
    `engine/cost_profile.py::load_cost_profile`'s established convention.
    Returns every committed row, keyed by its own `city_id`."""
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return {city_id: CityGeo.model_validate(entry) for city_id, entry in raw["cities"].items()}


def geo_for_city_id(city_id: str, *, path: str | Path = CITY_GEO_PATH) -> CityGeo | None:
    """Resolve `city_id` (a committed `CityCostProfile.city_id`, never a
    visitor-supplied string interpolated into anything) to its committed
    coordinate, or `None` if no entry is committed for it — never a
    guessed or interpolated coordinate."""
    return load_city_geo(path).get(city_id)
