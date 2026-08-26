"""Route A — "Price a production". All three routes call the identical
`app.services.spec.handle_spec_submission` (D-43); this module holds no
business logic of its own."""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.services.spec import (
    CityAssessment,
    CityCost,
    RefusalResult,
    RuleTerm,
    SpecFormSubmission,
    SpecResult,
    handle_spec_submission,
)
from engine.figure_serialize import figure_to_dict

__all__ = ["router"]

router = APIRouter()

# The candidate-cities textarea accepts one city per line. Split on
# newline ONLY — a comma is legitimate *within* a single city name (e.g.
# "Albany, NY", "Rochester, New York" — exactly the trailing-suffix format
# resolve_city_to_jurisdiction expects), so splitting on comma too would
# tear one city name into two entries. Only the empty string produced by a
# trailing newline is dropped here; a genuinely blank line the visitor
# left deliberately (e.g. "   ") is left for ProductionSpec's own
# validator to reject with a real message.
def _split_cities(raw: str) -> list[str]:
    return [part for part in raw.split("\n") if part != ""]


def _rule_term_to_json(term: RuleTerm) -> dict:
    return {
        "label": term.label,
        "value_text": term.value_text,
        "basis": term.basis,
        "source_url": term.source_url,
        "source_title": term.source_title,
        "date_checked": term.date_checked.isoformat() if term.date_checked else None,
        "confidence": term.confidence,
    }


def _city_assessment_to_json(assessment: CityAssessment) -> dict:
    return {
        "name": assessment.name,
        "jurisdiction_id": assessment.jurisdiction_id,
        "status": assessment.status,
    }


def _city_cost_to_json(cost: CityCost) -> dict:
    # `figure_to_dict` is the only path a Figure takes to JSON (Pitfall 4)
    # — never `dataclasses.asdict`, which would crash on the Decimal/date
    # fields Figure carries.
    return {
        "city_id": cost.city_id,
        "cost_total": figure_to_dict(cost.cost_total),
        "total_landed_cost": figure_to_dict(cost.total_landed_cost),
        "not_priced": list(cost.not_priced),
        "permanent_exclusions": list(cost.permanent_exclusions),
        "incentive_state": cost.incentive_state,
        "incentive_state_reason": cost.incentive_state_reason,
    }


def _spec_result_to_json(result: SpecResult) -> dict:
    # Every value converted to a JSON-native type before returning — the
    # result carries no bare Decimal, but rule-term `date_checked` values
    # are not JSON-native and would crash the default encoder with a 500
    # at encode time rather than a 422 if returned raw (Pitfall 4).
    return {
        "spec": result.spec.model_dump(),
        "crew_headcount": {
            "low": result.crew_headcount.low,
            "high": result.crew_headcount.high,
            "basis": result.crew_headcount.basis,
            "provenance_note": result.crew_headcount.provenance_note,
        },
        "city_assessments": [_city_assessment_to_json(c) for c in result.city_assessments],
        "rule_terms": [_rule_term_to_json(t) for t in result.rule_terms],
        "city_costs": [_city_cost_to_json(c) for c in result.city_costs],
        "spend_origin": result.spend_origin,
    }


@router.get("/spec", response_class=HTMLResponse)
def get_spec_form(request: Request) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    return templates.TemplateResponse(
        request=request,
        name="spec_form.html",
        context={"public_path": PUBLIC_PATH, "refusal_reason": None, "validation_error": None},
    )


@router.post("/spec", response_class=HTMLResponse)
def post_spec_form(
    request: Request,
    production_type: str = Form(...),
    shoot_days_stage: int = Form(...),
    shoot_days_location: int = Form(...),
    crew_size: str = Form(""),
    crew_tier: str = Form(""),
    principal_cast_count: int = Form(...),
    principal_cast_imported_count: int = Form(...),
    crew_imported_count: int = Form(...),
    crew_hired_locally_count: int = Form(...),
    start_quarter: str = Form(...),
    start_year: int = Form(...),
    candidate_cities: str = Form(...),
    total_budget: str = Form(""),
) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    crew_size_text = crew_size.strip()
    try:
        crew_size_value = int(crew_size_text) if crew_size_text else None
    except ValueError:
        return templates.TemplateResponse(
            request=request,
            name="spec_form.html",
            context={
                "public_path": PUBLIC_PATH,
                "refusal_reason": None,
                "validation_error": f"Crew size must be a whole number; got {crew_size_text!r}.",
            },
            status_code=422,
        )

    try:
        raw = SpecFormSubmission(
            production_type=production_type,
            shoot_days_stage=shoot_days_stage,
            shoot_days_location=shoot_days_location,
            crew_size=crew_size_value,
            crew_tier=crew_tier.strip() or None,
            principal_cast_count=principal_cast_count,
            principal_cast_imported_count=principal_cast_imported_count,
            crew_imported_count=crew_imported_count,
            crew_hired_locally_count=crew_hired_locally_count,
            start_quarter=start_quarter,
            start_year=start_year,
            candidate_cities=_split_cities(candidate_cities),
            total_budget=total_budget.strip() or None,
        )
        result = handle_spec_submission(raw)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="spec_form.html",
            context={
                "public_path": PUBLIC_PATH,
                "refusal_reason": None,
                "validation_error": str(exc),
            },
            status_code=422,
        )

    if isinstance(result, RefusalResult):
        # Never a 500 and never a bare framework error page — the form
        # re-renders with the reason the visitor can actually read.
        return templates.TemplateResponse(
            request=request,
            name="spec_form.html",
            context={
                "public_path": PUBLIC_PATH,
                "refusal_reason": result.reason,
                "validation_error": None,
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="spec_result.html",
        context={"public_path": PUBLIC_PATH, "result": result},
    )


@router.post("/api/v1/spec")
def post_spec_json(raw: SpecFormSubmission) -> dict:
    try:
        result = handle_spec_submission(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    if isinstance(result, RefusalResult):
        raise HTTPException(status_code=422, detail=result.reason)

    return _spec_result_to_json(result)
