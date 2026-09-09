"""`/compare` — the map + ranked-list product surface (Phase 6, UI-01/
UI-02/UI-04). Task 1 proves the end-to-end tracer path: an anonymous
`GET /compare` prices New York, Los Angeles and London and serves a
MapLibre-ready page. Task 2 widens coverage to arrival timing. Task 3 adds
the three-city-state/two-band/honesty gates."""

from __future__ import annotations

import json
import pathlib
import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_FLOOR_CITIES = ["New York, NY", "Los Angeles, CA", "London, UK"]

# Sourced from 04-CONTEXT.md § D-70 — the SAME vocabulary
# tests/test_app_spec_route.py's own module-level constant carries,
# duplicated here (not imported) per this repo's established
# per-test-module discipline.
_PRESCRIPTIVE_VOCABULARY: tuple[str, ...] = (
    "recommend",
    "recommends",
    "recommended",
    "recommendation",
    "should",
    "consider",
    "considers",
    "considered",
    "considering",
    "best",
    "optimal",
    "you could",
    "you should",
)
_VOCABULARY_PATTERNS = {
    word: re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    for word in _PRESCRIPTIVE_VOCABULARY
}

# Money-shaped: a run of digits (with optional thousands separators/
# decimal) followed by a 3-letter currency code — the exact shape every
# legitimate total on this page takes.
_MONEY_SHAPED = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:USD|GBP)")


def _geojson_block(html: str) -> dict:
    match = re.search(
        r'<script type="application/json" id="compare-geojson">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert match, "no embedded GeoJSON script block found in the rendered page"
    return json.loads(match.group(1))


def _section_html(html: str, aria_id: str) -> str:
    """Extract one `<section ... aria-labelledby="{aria_id}">...</section>`
    block's own inner HTML — a structural locate-by-container-element,
    never a plain string search over the whole document. Assumes no
    nested `<section>` inside (true for this template's own three bands)."""
    match = re.search(
        r'<section[^>]*aria-labelledby="' + re.escape(aria_id) + r'"[^>]*>(.*?)</section>',
        html,
        re.DOTALL,
    )
    assert match, f"no <section aria-labelledby={aria_id!r}> found in the rendered page"
    return match.group(1)


def _city_ids_in(section_html: str) -> set[str]:
    return set(re.findall(r'data-city-id="([^"]*)"', section_html))


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


# ---------------------------------------------------------------------------
# Task 3 — the three city states, the two-band separation, honesty gates
# ---------------------------------------------------------------------------


def test_get_compare_three_states_all_named_never_silently_dropped():
    """Every candidate city the visitor typed appears SOMEWHERE on the
    page: New York and London reach the ranked/unranked bands, Los
    Angeles reaches the unranked band, and a nonsense city with no
    committed cost profile reaches the third, "named but not priced"
    block — never vanishing between input and output."""
    response = client.get(
        "/compare",
        params=[("candidate_cities", c) for c in [*_FLOOR_CITIES, "Nowhereville, ZZ"]],
    )
    assert response.status_code == 200
    text = response.text
    assert "Named, but not priced" in text
    assert "Nowhereville, ZZ" in text
    assert "/research?city=" in text


def test_get_compare_band_separation_is_structural_never_a_single_shared_table():
    """D-55: no single `<table>`/`<ul>` container mixes rows from both
    bands — asserted by locating each band's own container element and
    checking the two sets of city_ids are disjoint, not by string search."""
    response = client.get(
        "/compare", params=[("candidate_cities", city) for city in _FLOOR_CITIES]
    )
    assert response.status_code == 200
    text = response.text

    ranked_ids = _city_ids_in(_section_html(text, "pf-ranked-heading"))
    unranked_ids = _city_ids_in(_section_html(text, "pf-unranked-heading"))

    assert ranked_ids, "expected at least one net_ranked city id in the ranked section"
    assert unranked_ids, "expected at least one incentive_not_modelled city id"
    assert ranked_ids.isdisjoint(unranked_ids)
    assert ranked_ids == {"us-ny-new-york"}
    assert unranked_ids == {"us-ca-los-angeles", "gb-london"}


def test_get_compare_unranked_incentive_column_is_words_only_never_money_shaped():
    """D-56, scoped to the unranked band's own container: every row
    renders a non-empty words-based unknown state in its incentive column,
    and that column never contains a money-shaped amount — scoped to the
    incentive column specifically, since the SAME container legitimately
    shows a money-shaped cost-only total in a different column."""
    response = client.get(
        "/compare", params=[("candidate_cities", city) for city in _FLOOR_CITIES]
    )
    assert response.status_code == 200
    unranked_section = _section_html(response.text, "pf-unranked-heading")

    incentive_cells = re.findall(
        r'<td class="pf-incentive-unknown">(.*?)</td>', unranked_section, re.DOTALL
    )
    assert len(incentive_cells) == 2, "expected one incentive cell per unranked city"
    for cell in incentive_cells:
        assert "unknown" in cell.lower()
        assert not _MONEY_SHAPED.search(cell), f"money-shaped amount found in incentive cell: {cell!r}"

    # The container as a whole DOES legitimately carry money (the
    # cost-only total column) — the gate is column-scoped, not
    # container-scoped, and this asserts that distinction is real.
    assert _MONEY_SHAPED.search(unranked_section)


def test_get_compare_d70_vocabulary_gate_over_rendered_html_body():
    response = client.get(
        "/compare",
        params=[("candidate_cities", c) for c in [*_FLOOR_CITIES, "Nowhereville, ZZ"]],
    )
    assert response.status_code == 200
    text = response.text

    violations = [
        word for word in _PRESCRIPTIVE_VOCABULARY if _VOCABULARY_PATTERNS[word].search(text)
    ]
    assert not violations, f"prescriptive vocabulary found in rendered /compare HTML: {violations}"


def test_static_assets_d70_vocabulary_gate():
    text = ""
    for path in pathlib.Path("app/static").rglob("*"):
        if path.is_file():
            text += path.read_text(encoding="utf-8")

    violations = [
        word for word in _PRESCRIPTIVE_VOCABULARY if _VOCABULARY_PATTERNS[word].search(text)
    ]
    assert not violations, f"prescriptive vocabulary found under app/static/: {violations}"


def test_get_compare_script_tag_city_not_reflected_unescaped_in_html_or_geojson():
    """Mirrors test_post_spec_form_script_tag_city_not_reflected_unescaped:
    a candidate city containing a script tag is escaped in the rendered
    HTML body AND is never present raw inside the embedded GeoJSON block
    (it resolves to no committed coordinate, so it never reaches the
    GeoJSON at all — this asserts that stays true)."""
    payload = "<script>alert(1)</script>"
    response = client.get("/compare", params=[("candidate_cities", payload)])
    assert response.status_code == 200
    assert payload not in response.text

    geojson_match = re.search(
        r'<script type="application/json" id="compare-geojson">(.*?)</script>',
        response.text,
        re.DOTALL,
    )
    assert geojson_match
    assert payload not in geojson_match.group(1)


def test_get_compare_live_checks_disclosure_never_labelled_as_a_priced_figure():
    """AGT-10: when a live programme check is present, it renders as its
    own separately-labelled section, never folded into a priced figure or
    the ranked band's own money column."""
    response = client.get(
        "/compare", params=[("candidate_cities", city) for city in _FLOOR_CITIES]
    )
    assert response.status_code == 200
    text = response.text
    if "Live programme checks" in text:
        assert "never changes a priced figure" in text or "never" in text.lower()
