"""Route A — "Price a production". All three routes call the identical
`app.services.spec.handle_spec_submission` (D-43); this module holds no
business logic of its own."""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.services.spec import (
    CityAssessment,
    CityAssumptions,
    ModelAssumptions,
    RefusalResult,
    RuleTerm,
    SpecFormSubmission,
    SpecResult,
    handle_spec_submission,
)
from engine.figure_serialize import figure_to_dict
from engine.gap import GapDecomposition
from engine.ranker import RankedCity
from engine.sensitivity import SensitivityRow

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


def _ranked_city_to_json(city: RankedCity) -> dict:
    # `figure_to_dict` is the only path a Figure takes to JSON (Pitfall 4)
    # — never `dataclasses.asdict`, which would crash on the Decimal/date
    # fields Figure carries. `band` and `reason` are the two bands' own
    # separate-state markers (D-55) — the JSON contract never collapses
    # them into a single flat list with a boolean flag.
    return {
        "city_id": city.city_id,
        "band": city.band,
        "reason": city.reason,
        "total_landed_cost": figure_to_dict(city.total_landed_cost),
        "cost_only_total": figure_to_dict(city.cost_only_total),
        "incentive_figure": (
            figure_to_dict(city.incentive_figure) if city.incentive_figure is not None else None
        ),
    }


def _gap_to_json(gap: GapDecomposition | None) -> dict | None:
    if gap is None:
        return None
    return {
        "city_a_id": gap.city_a_id,
        "city_b_id": gap.city_b_id,
        "sign_convention": gap.sign_convention,
        "components": [figure_to_dict(c) for c in gap.components],
        "headline_gap": figure_to_dict(gap.headline_gap),
    }


def _sensitivity_row_to_json(row: SensitivityRow) -> dict:
    # D-68: every Decimal converted with str(...) so precision survives
    # the JSON boundary intact — the same rule figure_to_dict already
    # follows for a Figure's own `value` field.
    return {
        "step_id": row.step_id,
        "spec_field": row.spec_field,
        "step_text": row.step_text,
        "baseline_gap": str(row.baseline_gap),
        "perturbed_gap": str(row.perturbed_gap),
        "delta": str(row.delta),
        "direction": row.direction,
        "cliff_crossings": list(row.cliff_crossings),
        "note": row.note,
    }


def _city_assumptions_to_json(assumptions: CityAssumptions) -> dict:
    seasonality = assumptions.seasonality_state
    return {
        "city_id": assumptions.city_id,
        "quarter_invariant_lines": list(assumptions.quarter_invariant_lines),
        "quarter_variant_lines": list(assumptions.quarter_variant_lines),
        "seasonality_state": (
            {"state": seasonality.state, "reason": seasonality.reason}
            if seasonality is not None
            else None
        ),
    }


def _assumptions_to_json(assumptions: ModelAssumptions | None) -> dict | None:
    if assumptions is None:
        return None
    return {
        "shoot_days_per_week": assumptions.shoot_days_per_week,
        "shoot_days_per_week_note": assumptions.shoot_days_per_week_note,
        "department_share_note": assumptions.department_share_note,
        "permanent_exclusions": list(assumptions.permanent_exclusions),
        "by_city": [_city_assumptions_to_json(c) for c in assumptions.by_city],
    }


def _spec_result_to_json(result: SpecResult) -> dict:
    # Every value converted to a JSON-native type before returning — the
    # result carries no bare Decimal, but rule-term `date_checked` values
    # are not JSON-native and would crash the default encoder with a 500
    # at encode time rather than a 422 if returned raw (Pitfall 4).
    #
    # D-55: the two bands are SEPARATE top-level JSON keys, never one list
    # carrying a `band` flag a consumer has to filter on — a caller that
    # forgets to check the flag would silently treat an unranked city's
    # cost-only total as though it were net-ranked. `result.ranked_cities`
    # itself stays ONE ordered tuple at the Python level (engine.ranker
    # .rank's own natural shape: ranked band first, unranked band second,
    # 04-06-PLAN.md's own instruction) — this split happens only at the
    # JSON boundary.
    net_ranked_cities = [c for c in result.ranked_cities if c.band == "net_ranked"]
    incentive_not_modelled_cities = [
        c for c in result.ranked_cities if c.band == "incentive_not_modelled"
    ]
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
        "net_ranked_cities": [_ranked_city_to_json(c) for c in net_ranked_cities],
        "incentive_not_modelled_cities": [
            _ranked_city_to_json(c) for c in incentive_not_modelled_cities
        ],
        "gap": _gap_to_json(result.gap),
        "spend_origin": result.spend_origin,
        "sensitivity": [_sensitivity_row_to_json(r) for r in result.sensitivity],
        "sensitivity_reason": result.sensitivity_reason,
        "most_moving_sensitivity_row": (
            _sensitivity_row_to_json(result.most_moving_sensitivity_row)
            if result.most_moving_sensitivity_row is not None
            else None
        ),
        "assumptions": _assumptions_to_json(result.assumptions),
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
