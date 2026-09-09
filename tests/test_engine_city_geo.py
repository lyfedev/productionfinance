"""`engine.city_geo` — the committed cartographic reference table (Phase 6,
UI-02). Covers the loader round-trip, the never-a-guessed-coordinate
contract for an unknown city, and the extra-fields-raise discipline every
`StrictModel` in this codebase carries."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from engine.city_geo import CITY_GEO_PATH, CityGeo, geo_for_city_id, load_city_geo

_COMMITTED_CITY_IDS = ("us-ny-new-york", "us-ca-los-angeles", "gb-london")


def test_load_city_geo_round_trips_every_committed_city():
    table = load_city_geo()
    assert set(table) == set(_COMMITTED_CITY_IDS)
    for city_id, entry in table.items():
        assert isinstance(entry, CityGeo)
        assert entry.city_id == city_id
        assert entry.label
        assert entry.source_url.startswith("https://")
        assert entry.note.strip()
        # Latitude/longitude are quoted YAML strings (RD-01) that parse as
        # real floats — never bare YAML-native numerics.
        float(entry.latitude)
        float(entry.longitude)


@pytest.mark.parametrize("city_id", _COMMITTED_CITY_IDS)
def test_geo_for_city_id_returns_the_committed_entry(city_id: str):
    entry = geo_for_city_id(city_id)
    assert entry is not None
    assert entry.city_id == city_id


def test_geo_for_city_id_returns_none_for_an_unknown_city():
    # Never a guessed or interpolated coordinate — an uncommitted city is
    # simply absent.
    assert geo_for_city_id("zz-nowhere") is None
    assert geo_for_city_id("<script>alert(1)</script>") is None


def test_load_city_geo_rejects_extra_fields(tmp_path: Path):
    raw = yaml.safe_load(CITY_GEO_PATH.read_text(encoding="utf-8"))
    raw["cities"]["us-ny-new-york"]["unexpected_field"] = "boom"
    bad_path = tmp_path / "city_geo.yaml"
    bad_path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_city_geo(bad_path)


def test_load_city_geo_uses_safe_load_only():
    # Mirrors engine/cost_profile.py's own source-inspection discipline:
    # asserts the read path never reaches for the unsafe/generic loader.
    # Scoped to load_city_geo's own function body, not the module's
    # docstring (which names the forbidden alternatives in prose).
    import inspect

    from engine.city_geo import load_city_geo

    body = inspect.getsource(load_city_geo)
    assert "yaml.safe_load" in body
    assert "yaml.load(" not in body
    assert "yaml.unsafe_load(" not in body
