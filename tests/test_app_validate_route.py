"""Route B — "Reproduce a disclosure" — end-to-end HTTP coverage (03-01).

Written RED-first (tdd="true", 03-01-PLAN.md Task 2): every test in this
module fails before `app/services/validate.py`, `app/routers/validate.py`,
`engine/figure_serialize.py` and the templates exist, then passes once they
land. The golden value — `Decimal("3964760")` qualified spend producing
`Decimal("991190")` gross credit for Anora — is not new logic; it is
`tests/test_engine_against_validation_pairs.py`'s already-proven sequence,
exposed through the HTTP boundary instead of a direct `price_jurisdiction`
call.
"""

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_anora_reproduces_exactly_via_route():
    response = client.get("/api/v1/validate/ny_anora")
    assert response.status_code == 200
    body = response.json()
    assert body["computed_credit"] == "991190"
    assert body["disclosed_credit"] == "991190"
    assert body["disclosed_qualified_spend"] == "3964760"
    assert body["verdict"] == "exact match"


def test_money_crosses_json_boundary_as_string_never_number():
    response = client.get("/api/v1/validate/ny_anora")
    assert response.status_code == 200
    # Parse the raw response text with the stdlib's own number-preserving
    # hook — if `computed_credit`/`disclosed_credit`/any figure `value` were
    # ever emitted as a bare JSON number, this parser would surface it as
    # a Python int/float instead of str.
    body = json.loads(response.text)

    assert isinstance(body["computed_credit"], str)
    assert isinstance(body["disclosed_credit"], str)
    assert isinstance(body["disclosed_qualified_spend"], str)

    def _walk(node: dict) -> None:
        assert isinstance(node["value"], str), f"Figure value not a string: {node!r}"
        for child in node["inputs"]:
            _walk(child)

    _walk(body["figure_tree"])


def test_figure_tree_serializes_recursively():
    response = client.get("/api/v1/validate/ny_anora")
    assert response.status_code == 200
    body = response.json()
    tree = body["figure_tree"]
    assert isinstance(tree["inputs"], list)
    assert len(tree["inputs"]) > 0

    required_keys = {
        "figure_id",
        "value",
        "unit",
        "label",
        "derivation",
        "source_url",
        "date_checked",
        "confidence",
        "live_fetched_this_run",
        "inputs",
    }

    def _walk(node: dict) -> None:
        assert required_keys.issubset(node.keys()), f"missing keys on node: {node!r}"
        for child in node["inputs"]:
            _walk(child)

    _walk(tree)


def test_unknown_pair_id_returns_404():
    response = client.get("/api/v1/validate/does-not-exist")
    assert response.status_code == 404


def test_traversal_shaped_pair_id_returns_404_and_reads_nothing():
    # Real slashes: httpx/Starlette path resolution never lets this reach
    # the {pair_id} handler as a literal traversal string, but the request
    # must never succeed (200) or crash the server (500) either way.
    response = client.get("/api/v1/validate/../../../../etc/passwd")
    assert response.status_code in (404, 400)

    # Percent-encoded slash: stays a single opaque path segment through
    # Starlette's router, decodes to a traversal-shaped string only inside
    # the handler — this is the case T-03-01's membership check must catch.
    response = client.get("/api/v1/validate/ny_anora%2F..%2F..%2Fetc%2Fpasswd")
    assert response.status_code == 404


def test_html_route_shows_both_figures_and_the_source_link():
    response = client.get("/validate/ny_anora")
    assert response.status_code == 200
    assert "991,190" in response.text
    assert "3,964,760" in response.text
    assert (
        'href="https://esd.ny.gov/sites/default/files/media/document/Q3-Film-Report-2025.pdf"'
        in response.text
    )


def test_bounded_pair_never_claims_exact_match():
    response = client.get("/api/v1/validate/ny_succession_s4")
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] != "exact match"
    assert "10" in body["verdict"]


def test_health_contract_unchanged():
    response = client.get("/health")
    assert response.status_code == 200
    assert set(response.json().keys()) == {"status", "version", "git_sha", "boot_time"}


def test_validate_form_lists_anora_and_names_unselectable_pairs_with_reasons():
    response = client.get("/validate")
    assert response.status_code == 200
    assert "Anora" in response.text
    assert "Don't Look Up" in response.text
    # ma_dont_look_up.yaml's own blocker text — proving the reason is shown
    # beside the unselectable pair, not silently omitted.
    assert "Qualifying spend is not publicly disclosed" in response.text


def test_post_validate_reproduces_anora_via_form():
    # This is the assertion that catches a missing form-parser dependency
    # (python-multipart) at request time, not only at import time.
    response = client.post("/validate", data={"pair_id": "ny_anora"})
    assert response.status_code == 200
    assert "991,190" in response.text


def test_post_validate_with_unselectable_pair_names_it_and_states_reason_not_500():
    response = client.post("/validate", data={"pair_id": "ct_christmas_always"})
    assert response.status_code != 500
    assert "ct_christmas_always" in response.text


def test_landing_page_shows_both_routes_and_health_link():
    response = client.get("/")
    assert response.status_code == 200
    assert "Price a production" in response.text
    assert "Reproduce a disclosure" in response.text
    assert "/health" in response.text
