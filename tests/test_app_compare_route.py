"""`/compare` — the map + ranked-list product surface (Phase 6, UI-01/
UI-02/UI-04). Task 1 proves the end-to-end tracer path: an anonymous
`GET /compare` prices New York, Los Angeles and London and serves a
MapLibre-ready page. Task 2 widens coverage to arrival timing. Task 3 adds
the three-city-state/two-band/honesty gates."""

from __future__ import annotations

import json
import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_FLOOR_CITIES = ["New York, NY", "Los Angeles, CA", "London, UK"]


def _geojson_block(html: str) -> dict:
    match = re.search(
        r'<script type="application/json" id="compare-geojson">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert match, "no embedded GeoJSON script block found in the rendered page"
    return json.loads(match.group(1))


# ---------------------------------------------------------------------------
# Task 1 — the end-to-end tracer
# ---------------------------------------------------------------------------


def test_get_compare_anonymous_no_auth_returns_200():
    # No cookie, no session, no header — a bare unauthenticated GET.
    response = client.get(
        "/compare", params=[("candidate_cities", city) for city in _FLOOR_CITIES]
    )
    assert response.status_code == 200
    assert "set-cookie" not in {k.lower() for k in response.headers}


def test_get_compare_prices_all_three_floor_cities_in_the_html_body():
    response = client.get(
        "/compare", params=[("candidate_cities", city) for city in _FLOOR_CITIES]
    )
    assert response.status_code == 200
    text = response.text
    # Every figure a visitor needs is server-rendered text before any
    # script runs (progressive enhancement, UI-02) — the city ids appear
    # in the ranked-list table bodies regardless of JavaScript.
    assert "us-ny-new-york" in text
    assert "us-ca-los-angeles" in text
    assert "gb-london" in text


def test_get_compare_carries_maplibre_and_openfreemap():
    response = client.get(
        "/compare", params=[("candidate_cities", city) for city in _FLOOR_CITIES]
    )
    assert response.status_code == 200
    text = response.text
    assert "maplibre" in text.lower()
    assert "tiles.openfreemap.org" in text


def test_get_compare_geojson_block_parses_and_splits_by_band():
    response = client.get(
        "/compare", params=[("candidate_cities", city) for city in _FLOOR_CITIES]
    )
    assert response.status_code == 200
    geojson = _geojson_block(response.text)
    assert geojson["type"] == "FeatureCollection"
    features = geojson["features"]
    assert features, "expected at least one GeoJSON feature for the floor cities"

    by_id = {feature["properties"]["city_id"]: feature for feature in features}
    assert "us-ny-new-york" in by_id

    for feature in features:
        props = feature["properties"]
        if props["band"] == "net_ranked":
            assert "total_value" in props
            assert isinstance(props["total_value"], (int, float))
        else:
            # D-55: an unranked feature never carries a ramp-eligible
            # numeric property at all — not zero, absent.
            assert "total_value" not in props
            assert props["reason"]


def test_get_compare_bare_request_renders_the_default_comparison():
    response = client.get("/compare")
    assert response.status_code == 200
    text = response.text
    assert "us-ny-new-york" in text


def test_get_compare_golden_new_york_matches_the_pinned_cost_only_total():
    # D-78 regression guard at the HTTP layer: /compare's default inputs
    # are the identical shape test_golden_cost.py's GOLDEN_SPEC pins.
    # New York is the net_ranked city, so its map `total_value` is net of
    # the modelled incentive — the pinned $758,427 is its COST-ONLY total,
    # which the ranked-list table (not the map) renders directly.
    response = client.get("/compare")
    assert response.status_code == 200
    text = response.text
    assert "758427 USD" in text
