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

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.services.compare import CompareInputs, Comparison, GapSelection, build_comparison
from app.services.currency_display import (
    DISPLAY_CURRENCIES,
    build_city_displays,
    build_original_currency_figures,
)
from app.services.permalink import (
    PermalinkDecodeError,
    PermalinkDiffView,
    PermalinkState,
    build_diff_view,
    decode_permalink,
    encode_permalink,
    record_figures,
)
from app.services.provenance import collect_rate_figures
from engine.figure import Figure
from engine.figure_serialize import figure_to_dict
from engine.ranker import RankedCity

__all__ = ["router"]

router = APIRouter()

_DEFAULT_CANDIDATE_CITIES: tuple[str, ...] = ("New York, NY", "Los Angeles, CA", "London, UK")


def _current_rate_figures(comparison: Comparison) -> tuple[Figure, ...]:
    """The leaf rate figures behind THIS comparison's own totals, walked
    fresh from the real `Figure` tree `app.services.compare
    .build_comparison` just produced — the same source both the
    UI-08 "share this comparison" token and the UI-12 diff read, so they
    can never disagree about what "this comparison's rates" means."""
    roots = [
        city.total_landed_cost
        for city in (*comparison.net_ranked, *comparison.incentive_not_modelled)
    ]
    return collect_rate_figures(roots)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _currency_display_context(comparison: Comparison) -> tuple[dict, dict]:
    """UI-11's two mechanisms, built together for a single `comparison`:
    `figure_displays` (the visitor's chosen-currency conversion) and
    `original_currency_figures` (the unconditional "as originally
    priced" disclosure). When BOTH would show the SAME currency for the
    SAME figure (the visitor chose GBP as their display currency for a
    city whose true original IS GBP), the chosen-currency entry is
    dropped — the reconstruction is the more precise of the two (exact,
    from disclosed leaves, versus a fresh `resolve_fx` conversion FROM
    the reporting-currency total), so showing both would present two
    slightly different GBP figures for the identical total."""
    cities = (*comparison.net_ranked, *comparison.incentive_not_modelled)
    original_currency_figures = build_original_currency_figures(cities)
    figure_displays = build_city_displays(
        cities, comparison.inputs.display_currency, on_date=datetime.now(UTC).date()
    )
    for figure_id, original in original_currency_figures.items():
        if original.source_currency == comparison.inputs.display_currency:
            figure_displays.pop(figure_id, None)
    return figure_displays, original_currency_figures


def _share_permalink_token(comparison: Comparison, current_rate_figures: tuple[Figure, ...]) -> str:
    """UI-08: a freshly-created-now token for THIS comparison — offered
    on every render, whether this request itself arrived via a permalink
    or not, so reopening a shared link and then sharing it again always
    hands out a token recording the state as of right now, not the
    original creation time."""
    return encode_permalink(
        PermalinkState(
            inputs=comparison.inputs,
            created_at=_now_iso(),
            recorded_figures=record_figures(current_rate_figures),
        )
    )


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


def _gap_selection_to_json(selection: GapSelection) -> dict:
    # UI-05: `decomposition` is `None` whenever `refusal` is populated —
    # never both, and never a computed number alongside a refusal. See
    # `app.services.compare.resolve_gap_selection`'s own docstring for
    # the band-honesty gate this mirrors into JSON unchanged.
    decomposition = selection.decomposition
    return {
        "options": [
            {"city_id": option.city_id, "label": option.label, "band": option.band}
            for option in selection.options
        ],
        "city_a_id": selection.city_a_id,
        "city_b_id": selection.city_b_id,
        "refusal": selection.refusal,
        "decomposition": (
            None
            if decomposition is None
            else {
                "city_a_id": decomposition.city_a_id,
                "city_b_id": decomposition.city_b_id,
                "sign_convention": decomposition.sign_convention,
                "components": [figure_to_dict(c) for c in decomposition.components],
                "headline_gap": figure_to_dict(decomposition.headline_gap),
            }
        ),
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
        # UI-05.
        "gap": _gap_selection_to_json(comparison.gap_selection),
        # UI-03: the slider's own fixed tick sequence plus the position
        # matching this response's own start_quarter/start_year — a date
        # lookup the client reads to label the slider, never a figure.
        "slider": {
            "options": list(comparison.slider_options),
            "current_index": comparison.slider_current_index,
        },
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
    # UI-03: the slider's own settled position. Overrides start_quarter/
    # start_year above when present (CompareInputs' own validator) —
    # the no-JS path (a plain `<input type="range">` submitting a full
    # form) reaches this exact query parameter.
    start_index: int | None = Query(None),
    # B008 fires on this one because of the `list[str]` annotation; the
    # default itself is the immutable `None` (FastAPI's own idiom for an
    # optional repeated query parameter) — resolved below, never mutated.
    candidate_cities: list[str] | None = Query(None),  # noqa: B008
    reporting_currency: str = Query("USD"),
    # UI-05: the two-city gap picker's own selection — a plain GET form
    # submit, mirroring every other input on this page.
    gap_city_a: str | None = Query(None),
    gap_city_b: str | None = Query(None),
    # UI-11 (plan 06-04): the visitor's chosen DISPLAY currency — a pure
    # rendering choice, never fed into `CompareInputs`' pricing fields.
    display_currency: str = Query("USD"),
    # UI-08 (plan 06-04): the permalink token. When present, this token
    # is the SOLE source of truth for `CompareInputs` — every other query
    # parameter above is ignored, so there is never an ambiguity about
    # which input source wins. This is also the ONLY reachable path to
    # UI-12's diff: a permalink carries the creation-time recorded rates
    # a fresh query string never could.
    permalink: str | None = Query(None),
) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    permalink_diff: PermalinkDiffView | None = None

    if permalink is not None:
        try:
            state = decode_permalink(permalink)
        except PermalinkDecodeError as exc:
            # Never silently falls back to a default comparison for an
            # unreadable link — a 422 naming the reason, exactly like
            # every other CompareInputs validation failure on this
            # route (UI-08's own "worse than failing to encode" clause).
            raise HTTPException(status_code=422, detail=f"invalid permalink: {exc}") from exc
        inputs = state.inputs
        comparison = build_comparison(inputs)
        current_rate_figures = _current_rate_figures(comparison)
        permalink_diff = build_diff_view(state, current_rate_figures)
    else:
        # A bare `GET /compare` (no `candidate_cities` in the query
        # string at all) renders the real default comparison — never an
        # error. Resolved here, not as a mutable list default on the
        # signature itself (B008).
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
                start_index=start_index,
                candidate_cities=resolved_candidate_cities,
                reporting_currency=reporting_currency,
                display_currency=display_currency,
                gap_city_a=gap_city_a,
                gap_city_b=gap_city_b,
            )
            comparison = build_comparison(inputs)
        except ValidationError as exc:
            # Readable 422 naming the field and the reason — never a 500
            # and never a bare framework error page. `include_context=
            # False`: pydantic-core's default `errors()` embeds the raw
            # `ValueError` instance itself in `ctx.error` for a
            # validator-raised error (this plan's `start_index`/
            # candidate-city-count checks both are) — a value
            # `json.dumps` cannot serialize, which would otherwise turn
            # a clean 422 into an unhandled 500 at RESPONSE time. Mirrors
            # `app/routers/methodology.py`'s own fix for the identical
            # pydantic-core behavior.
            raise HTTPException(
                status_code=422, detail=exc.errors(include_context=False)
            ) from exc
        current_rate_figures = _current_rate_figures(comparison)

    # UI-11: computed AFTER `comparison` exists on either path above (a
    # permalink's OWN `display_currency`, carried inside `state.inputs`,
    # is honoured identically to a fresh query string's).
    figure_displays, original_currency_figures = _currency_display_context(comparison)

    # UI-08: every render — whether reached via a fresh query string or
    # via an existing permalink — offers a freshly-created-now token for
    # THIS comparison, so "share" always hands out a link recording the
    # state as of right now.
    share_permalink_token = _share_permalink_token(comparison, current_rate_figures)

    return templates.TemplateResponse(
        request=request,
        name="compare.html",
        context={
            "public_path": PUBLIC_PATH,
            "comparison": comparison,
            "figure_displays": figure_displays,
            "original_currency_figures": original_currency_figures,
            "display_currencies": DISPLAY_CURRENCIES,
            "share_permalink_token": share_permalink_token,
            "permalink_diff": permalink_diff,
        },
    )


@router.post("/api/v1/compare")
def post_compare_json(inputs: CompareInputs) -> dict:
    try:
        comparison = build_comparison(inputs)
    except ValidationError as exc:
        # Same fix as the GET handler above: `include_context=False`
        # drops pydantic-core's raw `ValueError` instance from `ctx.error`
        # (embedded there by default for a validator-raised error — both
        # `CompareInputs._resolve_start_index` and
        # `_candidate_city_count_within_bound` raise this way), which
        # `json.dumps` cannot serialize and would otherwise turn this
        # clean 422 into an unhandled 500 while rendering the response.
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc

    from app.main import PUBLIC_PATH, templates

    # UI-11: identical to the GET handler — `inputs.display_currency`
    # reaches this endpoint via the SAME hidden form field every other
    # carried-forward input already uses (`compare.html`'s slider/gap
    # forms), so the settled-slider JS path preserves a visitor's chosen
    # display currency with zero changes to `app/static/compare.js`.
    figure_displays, original_currency_figures = _currency_display_context(comparison)

    payload = _comparison_to_json(comparison)
    payload["display_currency"] = comparison.inputs.display_currency
    # UI-03: the SAME `_ranked_list.html` a full page load renders,
    # rendered here as a standalone fragment so the settled-slider JS
    # path (`app/static/compare.js`) injects server-rendered markup
    # verbatim — never a client-side re-implementation of this page's
    # own formatting/templating logic, which would be a second,
    # divertible source of truth for what a figure looks like even
    # though not for what it IS.
    payload["ranked_list_html"] = templates.get_template("_ranked_list.html").render(
        comparison=comparison,
        public_path=PUBLIC_PATH,
        figure_displays=figure_displays,
        original_currency_figures=original_currency_figures,
    )
    return payload
