"""`/methodology` and `/assumptions` — Phase 6's provenance surfaces
(PRV-04/PRV-05). Follows `app/routers/spec.py`/`app/routers/compare.py`'s
established shape: imports `PUBLIC_PATH`/`templates` from `app.main`
inside each handler (never at module import — avoids a circular import
with `app.main`, which includes this router), and holds no pricing logic
of its own.

`/assumptions` reuses `app.services.compare.build_comparison` UNCHANGED —
the identical pipeline `/compare` calls — so the rates listed are
provably the ones the current comparison actually used, never a second,
possibly-diverging computation. The query-parameter list below
deliberately mirrors `app/routers/compare.py::get_compare`'s own
parameter-by-parameter signature (not imported or shared) — this repo's
established per-module duplication discipline (see
`tests/test_app_compare_route.py`'s and `tests/test_app_spec_route.py`'s
own independently-duplicated `_PRESCRIPTIVE_VOCABULARY` constants) rather
than reaching into a sibling-owned router module for a shared dependency.

`/methodology` takes no query-string input at all and renders a stable,
comparison-independent page (PRV-05) — a link someone can send that
persists regardless of what a visitor was comparing when they found it.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.services.compare import CompareInputs, build_comparison
from app.services.provenance import build_rate_sheets
from engine.landed_cost import COST_CATEGORIES, PERMANENT_EXCLUSIONS

__all__ = ["router"]

router = APIRouter()

# Mirrors app/routers/compare.py's own default floor-city set (D-54) — the
# same three committed cost profiles every Phase 4/5 golden test prices
# against, so a bare `GET /assumptions` (no query string) renders the
# identical default comparison `GET /compare` does.
_DEFAULT_CANDIDATE_CITIES: tuple[str, ...] = ("New York, NY", "Los Angeles, CA", "London, UK")


@router.get("/methodology", response_class=HTMLResponse)
def get_methodology(request: Request) -> HTMLResponse:
    """PRV-05: a stable, linkable page explaining how figures are
    computed. Takes no input and reads no comparison — it persists
    independently. `cost_categories`/`permanent_exclusions` are read from
    `engine.landed_cost` rather than typed into the template, so this
    page cannot drift out of sync with the engine's own declared
    vocabulary (D-60)."""
    from app.main import PUBLIC_PATH, templates

    return templates.TemplateResponse(
        request=request,
        name="methodology.html",
        context={
            "public_path": PUBLIC_PATH,
            "cost_categories": COST_CATEGORIES,
            "permanent_exclusions": PERMANENT_EXCLUSIONS,
        },
    )


@router.get("/assumptions", response_class=HTMLResponse)
def get_assumptions(
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
    # default itself is the immutable `None` (mirrors
    # app/routers/compare.py::get_compare's identical, already-reviewed
    # workaround) — resolved below, never mutated.
    candidate_cities: list[str] | None = Query(None),  # noqa: B008
    reporting_currency: str = Query("USD"),
) -> HTMLResponse:
    """PRV-04: the consolidated, printable assumptions panel for THIS
    comparison. Builds the identical `Comparison` `/compare` renders (via
    the unchanged `app.services.compare.build_comparison`), then derives
    the rate list from that comparison's real Figure tree
    (`app.services.provenance.build_rate_sheets`) — never a
    hand-maintained rate list that could drift from what the pipeline
    actually used."""
    from app.main import PUBLIC_PATH, templates

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
        # never a bare framework error page. `include_context=False`:
        # pydantic v2's default `.errors()` embeds the raw, non-JSON-
        # serializable exception object for a `model_validator`-raised
        # `ValueError` under `ctx.error` — passing that straight to
        # `HTTPException(detail=...)` crashes the JSON encoder with a
        # 500 instead of the intended 422 (discovered here; the
        # identical pattern in app/routers/compare.py, which this plan
        # does not own or edit, carries the same latent bug — see
        # 06-03-SUMMARY.md "Issues Encountered").
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc

    rate_sheets = build_rate_sheets((*comparison.net_ranked, *comparison.incentive_not_modelled))

    return templates.TemplateResponse(
        request=request,
        name="assumptions.html",
        context={
            "public_path": PUBLIC_PATH,
            "comparison": comparison,
            "rate_sheets": rate_sheets,
        },
    )
