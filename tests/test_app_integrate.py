"""The integration contract: the page shows what the API returns.

The failure this guards against is a demonstration page that formats its own
prettier version of the response. If the page and the endpoint can drift, the
page stops being evidence of anything.
"""

from __future__ import annotations

import html
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.integrate import PRESETS

client = TestClient(app)


def test_get_integrate_renders_for_an_anonymous_visitor() -> None:
    r = client.get("/integrate")
    assert r.status_code == 200
    assert "Integration contract" in r.text


def test_exact_match_preset_reproduces_the_published_government_figure() -> None:
    """Anora: ESD disclosed 991190 USD. The engine must return exactly that."""
    r = client.post("/api/v1/integrate", json=PRESETS["exact_match"]["request"])
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["programmes"][0]["gross_credit"]["value"] == "991190"


def test_refusal_preset_returns_cannot_be_computed_with_a_reason() -> None:
    """A refusal is part of the contract, not an error.

    Asserts the reason is non-empty: 'cannot be computed' with no explanation
    would be useless to an integrator.
    """
    r = client.post("/api/v1/integrate", json=PRESETS["refusal"]["request"])
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "cannot_be_computed"
    assert body["computed"] is None
    assert body["refusal_reason"], "a refusal must state why"


def test_a_refusal_never_reports_a_zero_credit() -> None:
    """A zero would assert the credit is worthless; the truth is it is unknown."""
    body = client.post("/api/v1/integrate", json=PRESETS["refusal"]["request"]).json()
    assert "0" != str(body.get("computed"))
    assert body.get("computed") is None


def test_unknown_jurisdiction_is_rejected_not_crashed() -> None:
    r = client.post(
        "/api/v1/integrate",
        json={"jurisdiction_id": "zz-nowhere", "qualified_spend": "1000"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


@pytest.mark.parametrize("bad", ["", "not-a-number", "-5"])
def test_unusable_spend_is_rejected_not_crashed(bad: str) -> None:
    r = client.post(
        "/api/v1/integrate", json={"jurisdiction_id": "us-ny", "qualified_spend": bad}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_the_response_carries_a_full_derivation_tree() -> None:
    """The derivation is the centrepiece — assert it has real depth."""
    body = client.post("/api/v1/integrate", json=PRESETS["exact_match"]["request"]).json()
    tree = body["programmes"][0]["gross_credit"]["derivation_tree"]
    assert tree["value"] == "991190"
    assert len(tree["derivation"]) >= 5, "a one-line derivation is not a derivation"


def test_the_page_shows_the_endpoint_response_verbatim() -> None:
    """The page must not format its own version of the payload.

    Without this, the page could show something the API never returns.
    """
    preset = PRESETS["exact_match"]["request"]
    api = client.post("/api/v1/integrate", json=preset).json()
    page = client.get(
        "/integrate?jurisdiction_id={jurisdiction_id}"
        "&qualified_spend={qualified_spend}&submitted=1".format(**preset)
    ).text
    assert json.dumps(api, indent=2)[:400] in html.unescape(page)


# ---------------------------------------------------------------------------
# The middle pane assembles as fields are filled (a stated UX requirement),
# and the page still works without JavaScript.
# ---------------------------------------------------------------------------


def test_the_request_pane_is_wired_for_live_assembly() -> None:
    """The form and request pane carry the ids the script binds to.

    Guards the wiring, not the browser behaviour: if a template edit drops
    either id the pane silently stops updating as fields are filled.
    """
    t = client.get("/integrate").text
    assert 'id="pf-int-form"' in t
    assert 'id="pf-int-request"' in t
    assert "integrate.js" in t


def test_presets_populate_the_inputs_rather_than_submitting() -> None:
    """Presets fill the fields so the request can be watched assembling.

    A preset that submits immediately skips the middle pane entirely, which
    is the thing the page exists to show.
    """
    t = client.get("/integrate").text
    assert t.count("data-preset") == 2, "one fill-button per preset"
    assert 'type="button"' in t, "a preset must not submit the form"


def test_the_page_works_without_javascript() -> None:
    """Progressive enhancement: the server renders the same JSON.

    The script reveals the payload earlier; it must not gate access to it.
    """
    t = client.get("/integrate?jurisdiction_id=us-ny&qualified_spend=3964760&submitted=1").text
    assert "991190" in t, "the response must be server-rendered"
    assert "<noscript>" in t, "presets need a no-JS path"
