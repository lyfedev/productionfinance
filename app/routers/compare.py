"""`/compare` — the map + ranked-list product surface (Phase 6, UI-01/
UI-02/UI-04). Follows `app/routers/spec.py`'s established shape: imports
`PUBLIC_PATH`/`templates` from `app.main` inside the handler (never at
module import — avoids a circular import with `app.main`, which includes
this router), and holds no business logic of its own — every dollar
figure comes from `app.services.compare.build_comparison`, which itself
calls the identical `app.services.spec.handle_spec_submission` `/spec`
uses.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.services.compare import CompareInputs, Comparison, build_comparison
from engine.figure_serialize import figure_to_dict
from engine.ranker import RankedCity

__all__ = ["router"]

router = APIRouter()

_DEFAULT_CANDIDATE_CITIES: tuple[str, ...] = ("New York, NY", "Los Angeles, CA", "London, UK")


def _ranked_city_to_json(city: RankedCity) -> dict:
    return {
        "city_id": city.city_id,
        "band": city.band,
        "reason": city.reason,
        "total_landed_cost": figure_to_dict(city.total_landed_cost),
        "cost_only_total": figure_to_dict(city.cost_only_total),
        "incentive_figure": (
            figure_to_dict(city.incentive_figure) if city.incentive_figure is not None else None
        ),
        # UI-04: one entry per priced programme, named by programme_id —
        # never a single blended or earliest date. Empty for an
        # incentive_not_modelled city (never priced).
        "arrival": [
            {
                "programme_id": entry.programme_id,
                "estimated_date": (
                    entry.estimated_date.isoformat() if entry.estimated_date else None
                ),
                "typical_days": entry.typical_days,
                "reason": entry.reason,
            }
            for entry in city.arrival
        ],
    }


def _comparison_to_json(comparison: Comparison) -> dict:
    return {
        "net_ranked": [_ranked_city_to_json(c) for c in comparison.net_ranked],
        "incentive_not_modelled": [
            _ranked_city_to_json(c) for c in comparison.incentive_not_modelled
        ],
        # The third explicit state (UI-01) — never silently dropped.
        "unpriced_cities": [
            {"name": city.name, "reason": city.reason} for city in comparison.unpriced_cities
        ],
        "geojson": comparison.geojson,
        "fx_resolutions": [
            {
                "base": fx.base,
                "quote": fx.quote,
                "rate": str(fx.rate),
                "origin": fx.origin,
                "disclosure": fx.disclosure,
            }
            for fx in comparison.fx_resolutions
        ],
        "live_programme_checks": [
            {
                "jurisdiction_id": check.jurisdiction_id,
                "programme_id": check.programme_id,
                "availability": check.availability,
                "availability_reason": check.availability_reason,
                "programme_status_state": check.programme_status_state,
                "programme_status_reason": check.programme_status_reason,
                "programme_status_source_url": check.programme_status_source_url,
                "programme_status_checked_at": check.programme_status_checked_at,
            }
            for check in comparison.live_programme_checks
        ],
    }


@router.get("/compare", response_class=HTMLResponse)
def get_compare(
    request: Request,
    production_type: str = Query("feature"),
    shoot_days_stage: int = Query(10),
    shoot_days_location: int = Query(5),
    crew_size: int = Query(50),
    crew_tier: str | None = Query(None),
    principal_cast_count: int = Query(3),
    principal_cast_imported_count: int = Query(1),
    crew_imported_count: int = Query(10),
    crew_hired_locally_count: int = Query(40),
    start_quarter: str = Query("Q2"),
    start_year: int = Query(2026),
    # B008 fires on this one because of the `list[str]` annotation; the
    # default itself is the immutable `None` (FastAPI's own idiom for an
    # optional repeated query parameter) — resolved below, never mutated.
    candidate_cities: list[str] | None = Query(None),  # noqa: B008
    reporting_currency: str = Query("USD"),
) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    # A bare `GET /compare` (no `candidate_cities` in the query string at
    # all) renders the real default comparison — never an error. Resolved
    # here, not as a mutable list default on the signature itself (B008).
    resolved_candidate_cities = (
        candidate_cities if candidate_cities is not None else list(_DEFAULT_CANDIDATE_CITIES)
    )

    try:
        inputs = CompareInputs(
            production_type=production_type,
            shoot_days_stage=shoot_days_stage,
            shoot_days_location=shoot_days_location,
            crew_size=crew_size,
            crew_tier=crew_tier,
            principal_cast_count=principal_cast_count,
            principal_cast_imported_count=principal_cast_imported_count,
            crew_imported_count=crew_imported_count,
            crew_hired_locally_count=crew_hired_locally_count,
            start_quarter=start_quarter,
            start_year=start_year,
            candidate_cities=resolved_candidate_cities,
            reporting_currency=reporting_currency,
        )
        comparison = build_comparison(inputs)
    except ValidationError as exc:
        # Readable 422 naming the field and the reason — never a 500 and
        # never a bare framework error page.
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    return templates.TemplateResponse(
        request=request,
        name="compare.html",
        context={"public_path": PUBLIC_PATH, "comparison": comparison},
    )


@router.post("/api/v1/compare")
def post_compare_json(inputs: CompareInputs) -> dict:
    try:
        comparison = build_comparison(inputs)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    return _comparison_to_json(comparison)
