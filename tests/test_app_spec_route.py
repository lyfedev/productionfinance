"""Route A: budget refusal (D-35's two layers), per-city curated status
(D-40), New York's cited rule terms (D-37), and — from Phase 4 — a real,
cited, basis-tagged dollar landed cost per candidate city (D-71).

Service-level coverage lands here first (Task 3); HTTP-level `TestClient`
coverage is added on top in Task 4, in this same file.
"""

from __future__ import annotations

import re
from dataclasses import fields, is_dataclass
from decimal import Decimal

from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import app
from app.services.city_lookup import resolve_city_to_jurisdiction
from app.services.spec import (
    REFUSAL_REASON,
    RefusalResult,
    SpecFormSubmission,
    SpecResult,
    handle_spec_submission,
)
from engine.figure_serialize import figure_to_dict

client = TestClient(app)


def test_ruleset_path_by_jurisdiction_is_shared_between_spec_and_validate():
    # Regression for WR-04: REPO_ROOT/RULESET_PATH_BY_JURISDICTION used to
    # be declared identically in both app/services/spec.py and
    # app/services/validate.py, with no test guarding the two dicts stayed
    # in sync. Both now import the same object from app/services/_paths.py
    # — asserting object identity (not just equal contents) is what
    # actually proves there is a single source of truth.
    from app.services.spec import RULESET_PATH_BY_JURISDICTION as spec_dict
    from app.services.validate import RULESET_PATH_BY_JURISDICTION as validate_dict

    assert spec_dict is validate_dict


def _base_form_kwargs(**overrides: object) -> dict:
    kwargs = {
        "production_type": "feature",
        "shoot_days_stage": 10,
        "shoot_days_location": 5,
        "crew_size": 50,
        "crew_tier": None,
        "principal_cast_count": 3,
        "principal_cast_imported_count": 1,
        "crew_imported_count": 10,
        "crew_hired_locally_count": 40,
        "start_quarter": "Q2",
        "start_year": 2026,
        "candidate_cities": ["New York, NY", "Reykjavik"],
        "total_budget": None,
    }
    kwargs.update(overrides)
    return kwargs


def _to_plain(obj: object) -> object:
    """Recursively convert dataclasses / pydantic models / tuples into
    plain dicts/lists so a test can walk the whole result for forbidden
    key names, independent of how the service happens to structure it."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _to_plain(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, (list, tuple)):
        return [_to_plain(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _to_plain(value) for key, value in obj.items()}
    return obj


def _collect_keys(node: object, collected: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            collected.add(key)
            _collect_keys(value, collected)
    elif isinstance(node, list):
        for item in node:
            _collect_keys(item, collected)


# ---------------------------------------------------------------------------
# D-35 — the visible budget refusal
# ---------------------------------------------------------------------------


def test_budget_field_always_refused():
    raw = SpecFormSubmission(**_base_form_kwargs(total_budget="1000000"))
    result = handle_spec_submission(raw)
    assert isinstance(result, RefusalResult)
    assert result.reason == REFUSAL_REASON


def test_empty_budget_field_is_not_a_refusal():
    for empty_value in (None, ""):
        raw = SpecFormSubmission(**_base_form_kwargs(total_budget=empty_value))
        result = handle_spec_submission(raw)
        assert isinstance(result, SpecResult)


# ---------------------------------------------------------------------------
# D-40 — uncurated cities are accepted and reported, never suggested
# ---------------------------------------------------------------------------


def test_uncurated_city_never_suggested():
    raw = SpecFormSubmission(**_base_form_kwargs(candidate_cities=["Reykjavik"]))
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)
    assessment = result.city_assessments[0]
    assert assessment.jurisdiction_id is None
    assert "no curated model" in assessment.status.lower()

    plain = _to_plain(result)
    all_keys: set[str] = set()
    _collect_keys(plain, all_keys)
    for forbidden in ("suggestion", "alternative", "nearest_match", "did_you_mean"):
        assert forbidden not in all_keys


def test_new_york_aliases_resolve():
    for name in (
        "New York",
        "new york city",
        "NYC",
        "Brooklyn",
        "  Buffalo  ",
        "Albany, NY",
        "Rochester, New York",
    ):
        assert resolve_city_to_jurisdiction(name) == "us-ny", name


def test_city_matching_is_strip_and_casefold_only():
    assert resolve_city_to_jurisdiction("NEW YORK") == "us-ny"
    assert resolve_city_to_jurisdiction("New  York") is None


# ---------------------------------------------------------------------------
# Echo + crew resolution
# ---------------------------------------------------------------------------


def test_spec_echoes_normalized_input():
    raw = SpecFormSubmission(**_base_form_kwargs())
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)
    assert result.spec.start_quarter == "Q2"
    assert result.spec.candidate_cities == ["New York, NY", "Reykjavik"]
    assert result.spec.crew_size == 50


def test_spec_echoes_tier_only_submission_with_resolved_headcount():
    raw = SpecFormSubmission(
        **_base_form_kwargs(
            crew_size=None,
            crew_tier="mid",
            crew_imported_count=0,
            crew_hired_locally_count=0,
        )
    )
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)
    assert result.spec.crew_tier == "mid"
    assert result.crew_headcount.low <= result.crew_headcount.high
    assert result.crew_headcount.basis == "modelling_assumption"
    assert result.crew_headcount.provenance_note.strip() != ""


# ---------------------------------------------------------------------------
# D-37 item 3 — New York's rule terms, cited
# ---------------------------------------------------------------------------


def test_new_york_rule_terms_carry_citations():
    raw = SpecFormSubmission(**_base_form_kwargs(candidate_cities=["New York, NY"]))
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)

    labels = {term.label for term in result.rule_terms}
    for expected_fragment in (
        "rate",
        "mechanism",
        "minimum spend",
        "per-project",
        "annual",
        "audit",
        "payout",
    ):
        assert any(expected_fragment in label.lower() for label in labels), expected_fragment

    for term in result.rule_terms:
        assert term.source_url, term.label
        assert term.date_checked is not None, term.label
        assert term.confidence, term.label

    assert any(
        "no " in term.value_text.lower() or "not " in term.value_text.lower()
        for term in result.rule_terms
    )


def test_no_rule_terms_when_no_ny_city_named():
    raw = SpecFormSubmission(**_base_form_kwargs(candidate_cities=["Reykjavik"]))
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)
    assert result.rule_terms == ()


# ---------------------------------------------------------------------------
# D-71 — Route A now DOES derive money, and every figure it derives is
# fully cited (basis, source_url, date_checked, confidence) — never a bare
# number. This is the deliberate reversal of Phase 3's D-36 guard.
# ---------------------------------------------------------------------------


def _walk_figure_dicts(node: object) -> list[dict]:
    """Collect every Figure-shaped dict reachable from `node`'s full JSON
    tree (a Figure dict is identified structurally: it carries both
    `figure_id` and `confidence` keys, matching `figure_to_dict`'s exact
    output shape) — including the recursive `inputs` children."""
    found: list[dict] = []
    if isinstance(node, dict):
        if "figure_id" in node and "confidence" in node:
            found.append(node)
            for child in node.get("inputs", []):
                found.extend(_walk_figure_dicts(child))
        else:
            for value in node.values():
                found.extend(_walk_figure_dicts(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_walk_figure_dicts(item))
    return found


def test_route_a_derives_money_as_fully_cited_figures_only():
    """Route A now legitimately derives money (D-71). The forbidden-key
    assertion Phase 3 wrote is replaced by the honest successor: every
    money value it derives must be a `Figure` dict — never a bare number —
    and every such Figure carries `basis`, `source_url`, `date_checked` and
    `confidence` keys (D-58/PRV-01/PRV-02)."""
    raw = SpecFormSubmission(**_base_form_kwargs(candidate_cities=["New York, NY"]))
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)
    assert result.city_costs, "expected at least one CityCost for a New York candidate"

    figure_dicts: list[dict] = []
    for cost in result.city_costs:
        figure_dicts.extend(_walk_figure_dicts(figure_to_dict(cost.cost_total)))
        figure_dicts.extend(_walk_figure_dicts(figure_to_dict(cost.total_landed_cost)))
    assert len(figure_dicts) > 1, "expected more than one Figure node in the response tree"

    for figure_dict in figure_dicts:
        for required_key in ("basis", "source_url", "date_checked", "confidence"):
            assert required_key in figure_dict, (figure_dict["label"], required_key)


def test_route_a_service_reaches_the_pricing_path():
    """D-71 deliberately REVERSES Phase 3's D-36 import-boundary guard:
    `app.services.spec` now DOES reach `engine.pipeline` for any candidate
    city with both a committed cost profile and a committed rule file.
    D-63's basis-walk gate (the full, non-vacuous version lives in
    `tests/test_route_a_basis_walk.py`) is what replaces the deleted guard
    as the real honesty check — this test proves the reversal is real by
    asserting the module actually imports `price_jurisdiction`, and proves
    the replacement gate holds by walking this call's own output tree for
    a `confidence: "validated"` node."""
    import app.services.spec as spec_service
    from engine.pipeline import price_jurisdiction

    assert spec_service.price_jurisdiction is price_jurisdiction

    raw = SpecFormSubmission(**_base_form_kwargs(candidate_cities=["New York, NY"]))
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)
    assert result.city_costs

    figure_dicts: list[dict] = []
    for cost in result.city_costs:
        figure_dicts.extend(_walk_figure_dicts(figure_to_dict(cost.total_landed_cost)))
    assert len(figure_dicts) > 5, "expected a non-trivial Figure tree, not a flattened one"
    for figure_dict in figure_dicts:
        assert figure_dict["confidence"] != "validated", figure_dict["label"]


def test_route_a_spend_origin_states_it_is_modelled_not_disclosed():
    """D-73/D-32: the only thing distinguishing Route A from Route B now
    that both return a credit figure is where the qualified spend came
    from — and the page must make that visible next to the number."""
    raw = SpecFormSubmission(**_base_form_kwargs(candidate_cities=["New York, NY"]))
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)
    lowered = result.spend_origin.lower()
    assert "modelled" in lowered
    assert "not" in lowered and "disclosed" in lowered


# ---------------------------------------------------------------------------
# Task 4 — HTTP-level coverage (GET/POST /spec, POST /api/v1/spec, GET /)
# ---------------------------------------------------------------------------


def _valid_form_data(**overrides: str) -> dict[str, str]:
    data = {
        "production_type": "feature",
        "shoot_days_stage": "10",
        "shoot_days_location": "5",
        "crew_size": "50",
        "crew_tier": "",
        "principal_cast_count": "3",
        "principal_cast_imported_count": "1",
        "crew_imported_count": "10",
        "crew_hired_locally_count": "40",
        "start_quarter": "Q2",
        "start_year": "2026",
        "candidate_cities": "New York, NY\nReykjavik",
        "total_budget": "",
    }
    data.update(overrides)
    return data


def _valid_json_body(**overrides: object) -> dict:
    body = {
        "production_type": "feature",
        "shoot_days_stage": 10,
        "shoot_days_location": 5,
        "crew_size": 50,
        "crew_tier": None,
        "principal_cast_count": 3,
        "principal_cast_imported_count": 1,
        "crew_imported_count": 10,
        "crew_hired_locally_count": 40,
        "start_quarter": "Q2",
        "start_year": 2026,
        "candidate_cities": ["New York, NY"],
        "total_budget": None,
    }
    body.update(overrides)
    return body


def test_get_spec_form_returns_200_with_budget_label():
    response = client.get("/spec")
    assert response.status_code == 200
    assert "Total budget" in response.text


def test_post_spec_form_valid_returns_200_and_echoes_spec():
    response = client.post("/spec", data=_valid_form_data())
    assert response.status_code == 200
    assert "Q2" in response.text
    assert "New York, NY" in response.text
    assert "Reykjavik" in response.text


def test_post_spec_form_with_budget_shows_refusal_reason():
    response = client.post("/spec", data=_valid_form_data(total_budget="1000000"))
    assert response.status_code != 500
    assert "makes the comparison circular" in response.text


def test_post_spec_form_non_numeric_crew_size_never_500s():
    # Regression for CR-01: crew_size was converted with a bare int(crew_size)
    # as an inline argument expression to SpecFormSubmission(...), which
    # raised an uncaught ValueError before the surrounding
    # `except ValidationError` block could catch it, escaping as an
    # unhandled 500. Every field must fail readably, never with a bare
    # framework error page.
    response = client.post(
        "/spec", data=_valid_form_data(crew_size="not-a-number")
    )
    assert response.status_code == 422
    assert response.status_code != 500
    assert "not-a-number" in response.text


def test_post_api_v1_spec_extra_field_returns_422():
    body = _valid_json_body()
    body["unexpected_field"] = "nope"
    response = client.post("/api/v1/spec", json=body)
    assert response.status_code == 422


def test_post_api_v1_spec_uncurated_city_returns_200_marked_no_curated_model():
    response = client.post(
        "/api/v1/spec", json=_valid_json_body(candidate_cities=["Reykjavik"])
    )
    assert response.status_code == 200
    body = response.json()
    assessment = body["city_assessments"][0]
    assert assessment["jurisdiction_id"] is None
    assert "no curated model" in assessment["status"].lower()


def test_post_spec_form_script_tag_city_not_reflected_unescaped():
    response = client.post(
        "/spec", data=_valid_form_data(candidate_cities="<script>alert(1)</script>")
    )
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text


def test_index_route_a_link_resolves_to_200():
    response = client.get("/")
    assert response.status_code == 200

    hrefs = re.findall(r'href="([^"]+)"', response.text)
    spec_hrefs = [href for href in hrefs if href.endswith("/spec")]
    assert spec_hrefs, f"no anchor with an href ending in /spec found: {hrefs}"

    spec_link_response = client.get(spec_hrefs[0])
    assert spec_link_response.status_code == 200


# ---------------------------------------------------------------------------
# D-71 — the JSON contract: real dollars, cited, basis-tagged, over HTTP
# ---------------------------------------------------------------------------


def test_post_api_v1_spec_new_york_candidate_returns_real_landed_cost():
    response = client.post(
        "/api/v1/spec", json=_valid_json_body(candidate_cities=["New York, NY"])
    )
    assert response.status_code == 200
    body = response.json()

    assert "spend_not_derived" not in body
    assert body["city_costs"], "expected a city_costs entry for a New York candidate"

    city_cost = body["city_costs"][0]
    total_landed_cost = city_cost["total_landed_cost"]
    value = Decimal(total_landed_cost["value"])
    assert value != Decimal("0")
    assert total_landed_cost["basis"] is not None

    # D-60: an unpriced category is a named entry in `not_priced`, never a
    # fabricated $0 line item.
    assert set(city_cost["not_priced"]).issubset(
        {
            "labour",
            "fringe",
            "housing",
            "per_diem",
            "flights",
            "stages",
            "equipment",
            "permits",
            "locations",
            "trucking",
        }
    )
    assert "labour" not in city_cost["not_priced"], "the tracer's one line prices labour"

    assert "modelled" in body["spend_origin"].lower()
    assert "disclosed" in body["spend_origin"].lower()

    # Every cost-side Figure (the D-58 basis axis's own subject matter)
    # carries a non-null basis, and the cost total's basis is the weakest
    # among its cost-line inputs — never a fallback default (D-59). Plan
    # 04-04 adds the five facilities categories at basis
    # "modelling_assumption" — the weakest tier present, so the combined
    # cost total now reports that tier (previously "estimated", before
    # facilities landed).
    cost_side_nodes = _walk_figure_dicts(city_cost["cost_total"])
    assert len(cost_side_nodes) > 1
    assert all(node["basis"] is not None for node in cost_side_nodes)
    assert city_cost["cost_total"]["basis"] == "modelling_assumption"


def test_no_spend_not_derived_symbol_anywhere_in_app_or_engine():
    import subprocess

    result = subprocess.run(
        ["grep", "-rn", "SPEND_NOT_DERIVED", "app/", "engine/"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.stdout == "", result.stdout
