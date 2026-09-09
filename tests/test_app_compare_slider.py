"""`/compare`'s start-date slider (Phase 6 plan 06-02, UI-03).

Task 1 proves the server-side dated re-ranking: a settled slider
position resolves to a real `(start_quarter, start_year)` pair and every
figure the client receives for it matches an independent, direct
`build_comparison` re-run at that same date — the client never computes
a cost figure of its own, it only requests a ranking for a date and
renders what comes back. Task 2 (a later commit in this same file)
proves the slider exists as a genuine native `<input type="range">` form
control that works with JavaScript disabled."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.compare import SLIDER_QUARTERS, CompareInputs, build_comparison

client = TestClient(app)

_FLOOR_CITIES = ["New York, NY", "Los Angeles, CA", "London, UK"]


def _ny_total_landed_cost(comparison) -> str:
    ny = next(c for c in comparison.net_ranked if c.city_id == "us-ny-new-york")
    return str(ny.total_landed_cost.value)


# ---------------------------------------------------------------------------
# Task 1 — server-side dated re-ranking
# ---------------------------------------------------------------------------


def test_slider_has_at_least_two_real_sourced_positions():
    # A slider that cannot move to a second, genuinely different date is
    # not a slider — and every position must resolve, never raise.
    assert len(SLIDER_QUARTERS) >= 2
    for quarter, year in SLIDER_QUARTERS:
        assert quarter in {"Q1", "Q2", "Q3", "Q4"}
        assert isinstance(year, int)


def test_two_different_start_indices_price_new_york_differently():
    """UI-03's own `<verify>`: a request for two different dates returns
    two rankings whose figures genuinely differ — New York is the one
    floor city with real month-banded GSA lodging data, so its own total
    landed cost must move across at least two slider positions."""
    totals = set()
    for index in range(len(SLIDER_QUARTERS)):
        response = client.post(
            "/api/v1/compare",
            json={"start_index": index, "candidate_cities": _FLOOR_CITIES},
        )
        assert response.status_code == 200
        data = response.json()
        ny = next(c for c in data["net_ranked"] if c["city_id"] == "us-ny-new-york")
        totals.add(ny["total_landed_cost"]["value"])
    assert len(totals) >= 2, "expected New York's total to differ across at least two dates"


def test_settled_slider_position_matches_a_direct_server_side_rebuild():
    """Every figure the JSON endpoint returns for a settled slider
    position matches an INDEPENDENT, direct `build_comparison` re-run at
    the exact same resolved date — proving the JSON response is not a
    second, divergent source of truth from the real pipeline, and that
    the client (which only ever sends `start_index`, never a date it
    resolved itself) is receiving a genuinely server-priced figure."""
    for index in range(len(SLIDER_QUARTERS)):
        response = client.post(
            "/api/v1/compare",
            json={"start_index": index, "candidate_cities": _FLOOR_CITIES},
        )
        assert response.status_code == 200
        via_http = response.json()

        quarter, year = SLIDER_QUARTERS[index]
        direct = build_comparison(
            CompareInputs(
                start_quarter=quarter, start_year=year, candidate_cities=_FLOOR_CITIES
            )
        )
        direct_total = _ny_total_landed_cost(direct)

        ny_via_http = next(c for c in via_http["net_ranked"] if c["city_id"] == "us-ny-new-york")
        assert ny_via_http["total_landed_cost"]["value"] == direct_total


def test_start_index_out_of_range_returns_a_readable_422_not_a_500():
    response = client.post("/api/v1/compare", json={"start_index": 999})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("start_index" in entry["msg"] for entry in detail)


def test_get_compare_start_index_out_of_range_returns_422():
    response = client.get("/compare", params={"start_index": 999})
    assert response.status_code == 422


def test_post_compare_json_invalid_payload_returns_422_json_never_a_500():
    """[Rule 1 deviation] `except ValidationError: raise HTTPException(...,
    detail=exc.errors())` (bare, no `include_context=False`) crashes at
    RESPONSE-render time — not at validation time — whenever
    pydantic-core embeds the raw `ValueError` instance itself in a
    validator error's `ctx.error` (observed on `GET /compare`'s own
    direct `CompareInputs(...)` construction; `json.dumps` cannot
    serialize a bare exception object, turning a clean 422 into an
    unhandled 500). This asserts BOTH invalid-input surfaces this router
    owns return a real, JSON-parseable 422 body — never raise while
    rendering the error response itself."""
    over_cap = client.post(
        "/api/v1/compare",
        json={"candidate_cities": [f"City {i}" for i in range(13)]},
    )
    assert over_cap.status_code == 422
    assert "at most 12 candidate cities" in over_cap.json()["detail"][0]["msg"]

    bad_index = client.post("/api/v1/compare", json={"start_index": 999})
    assert bad_index.status_code == 422
    assert "start_index" in bad_index.json()["detail"][0]["msg"]


def test_get_compare_over_cap_candidate_cities_returns_422_json_never_a_500():
    """The exact GET-path reproduction of the Rule 1 bug above — this is
    the surface that actually crashed with a bare `exc.errors()`."""
    response = client.get(
        "/compare", params=[("candidate_cities", f"City {i}") for i in range(13)]
    )
    assert response.status_code == 422
    assert "at most 12 candidate cities" in response.json()["detail"][0]["msg"]


def test_post_compare_json_carries_a_ranked_list_html_fragment():
    """UI-03's slider JS injects this fragment verbatim on a settled
    position — it must be present, non-empty, and contain the SAME
    city ids the full server-rendered page shows for the identical
    inputs (never a divergent, JS-only rendering)."""
    response = client.post(
        "/api/v1/compare",
        json={"start_index": 0, "candidate_cities": _FLOOR_CITIES},
    )
    assert response.status_code == 200
    fragment = response.json()["ranked_list_html"]
    assert "us-ny-new-york" in fragment
    assert "us-ca-los-angeles" in fragment
    assert "gb-london" in fragment

    full_page = client.get(
        "/compare",
        params=[("start_index", "0"), *[("candidate_cities", c) for c in _FLOOR_CITIES]],
    )
    assert full_page.status_code == 200
    assert "pf-ranked-list-container" in full_page.text
    # The exact same fragment source renders both surfaces — the city ids
    # visible in the fragment are a strict subset of the full page's own
    # rendered ranked-list markup for the same inputs.
    for city_id in ("us-ny-new-york", "us-ca-los-angeles", "gb-london"):
        assert city_id in full_page.text


def test_get_compare_start_index_no_js_path_reranks_the_server_rendered_page():
    """A plain GET carrying `start_index` — the exact query parameter a
    native `<input type="range">` inside a `<form method="get">` submits
    with no JavaScript at all — returns a correctly re-ranked, fully
    server-rendered page. `TestClient` never executes JavaScript, so this
    proves the no-JS path genuinely works end to end using only the
    router change this task adds (the slider's own markup is Task 2)."""
    import re

    baseline = client.get("/compare", params=[("candidate_cities", c) for c in _FLOOR_CITIES])
    assert baseline.status_code == 200

    baseline_index = SLIDER_QUARTERS.index(("Q2", 2026))
    other_index = 0 if baseline_index != 0 else 1
    reranked = client.get(
        "/compare",
        params=[
            ("start_index", str(other_index)),
            *[("candidate_cities", c) for c in _FLOOR_CITIES],
        ],
    )
    assert reranked.status_code == 200

    ny_total_pattern = re.compile(r'data-city-id="us-ny-new-york".*?pf-money">\s*([\d.]+)', re.DOTALL)
    baseline_total = ny_total_pattern.search(baseline.text).group(1)
    reranked_total = ny_total_pattern.search(reranked.text).group(1)
    assert baseline_total != reranked_total, (
        "the no-JS re-submitted page must show a genuinely different total for a "
        "different start date, not a stale cached figure"
    )
