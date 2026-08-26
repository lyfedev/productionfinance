"""Route A: budget refusal (D-35's two layers), per-city curated status
(D-40), New York's cited rule terms (D-37), and the not-yet-derived
statement (D-36).

Service-level coverage lands here first (Task 3); HTTP-level `TestClient`
coverage is added on top in Task 4, in this same file.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass

from pydantic import BaseModel

from app.services.city_lookup import resolve_city_to_jurisdiction
from app.services.spec import (
    REFUSAL_REASON,
    SPEND_NOT_DERIVED,
    RefusalResult,
    SpecFormSubmission,
    SpecResult,
    handle_spec_submission,
)


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
# D-36 — no money derived from the spec, ever
# ---------------------------------------------------------------------------


_FORBIDDEN_MONEY_KEYS = {
    "qualified_spend",
    "credit",
    "credit_amount",
    "gross_credit",
    "net_cash",
    "total_cost",
    "landed_cost",
}


def test_route_a_derives_no_money():
    raw = SpecFormSubmission(**_base_form_kwargs(candidate_cities=["New York, NY"]))
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)

    plain = _to_plain(result)
    all_keys: set[str] = set()
    _collect_keys(plain, all_keys)
    assert all_keys.isdisjoint(_FORBIDDEN_MONEY_KEYS)


def test_route_a_service_never_imports_the_pricing_path():
    import app.services.spec as spec_service

    module_names = {
        getattr(value, "__module__", None) for value in vars(spec_service).values()
    }
    assert "engine.pipeline" not in module_names
    assert "engine.qualifying_base" not in module_names

    from engine.pipeline import price_jurisdiction
    from engine.qualifying_base import compute_qualifying_base

    for value in vars(spec_service).values():
        assert value is not price_jurisdiction
        assert value is not compute_qualifying_base


def test_spend_not_derived_statement_present():
    raw = SpecFormSubmission(**_base_form_kwargs())
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)
    assert result.spend_not_derived == SPEND_NOT_DERIVED
