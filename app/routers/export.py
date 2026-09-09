"""`/export` (UI-09) — Phase 8 plan 02, Task 1. Follows
`app/routers/methodology.py`'s established shape: imports
`PUBLIC_PATH`/`templates` from `app.main` inside each handler (never at
module import — avoids a circular import with `app.main`, which includes
this router), and holds no business logic of its own. Its
query-parameter list mirrors `app/routers/compare.py::get_compare`'s own
signature (the established per-module duplication discipline this
repo's routers already use — see `app/routers/methodology.py`'s
docstring for the same note) so a comparison's own URL can be turned
into its export URL by changing only the path.

(`/demo` — DMO-01..04 — is added to this same router in Task 2/3 of this
plan; see this module's git history for that follow-up commit.)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.services.compare import CompareInputs
from app.services.export import build_export_document

__all__ = ["router"]

router = APIRouter()

# Mirrors app/routers/compare.py's own default floor-city set (D-54) — the
# same three committed cost profiles every Phase 4/5 golden test prices
# against, so a bare `GET /export` (no query string) renders the export of
# the identical default comparison `GET /compare` shows.
_DEFAULT_CANDIDATE_CITIES: tuple[str, ...] = ("New York, NY", "Los Angeles, CA", "London, UK")


@router.get("/export", response_class=HTMLResponse)
def get_export(
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
    # UI-05: carried through so an export can be produced for the SAME
    # two-city gap a visitor was looking at on /compare, not only the
    # default pair.
    gap_city_a: str | None = Query(None),
    gap_city_b: str | None = Query(None),
) -> HTMLResponse:
    """UI-09: a self-contained, server-rendered export document for one
    comparison. Generated entirely server-side — complete without
    JavaScript (see `app/services/export.py`'s own docstring)."""
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
            gap_city_a=gap_city_a,
            gap_city_b=gap_city_b,
        )
        document = build_export_document(inputs)
    except ValidationError as exc:
        # include_context=False: pydantic-core's default errors() embeds
        # the raw ValueError instance for a validator-raised error under
        # ctx.error — not JSON-serializable, which would otherwise turn
        # this 422 into a 500 at response time. Mirrors
        # app/routers/compare.py and app/routers/methodology.py's
        # identical, already-established fix.
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc

    return templates.TemplateResponse(
        request=request,
        name="export_document.html",
        context={"public_path": PUBLIC_PATH, "document": document},
    )
