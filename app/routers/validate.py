"""Route B — "Reproduce a disclosure". Both the JSON and HTML views call
`app.services.validate.reproduce_disclosure` — one handler's business
logic, two views (D-43); this module holds no pricing logic of its own."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.services.validate import UnknownPairError, ValidateResult, reproduce_disclosure
from engine.figure_serialize import figure_to_dict

__all__ = ["router"]

router = APIRouter()


def _validate_result_to_json(result: ValidateResult) -> dict:
    """A raw `Figure` must never be returned from a route — its `Decimal`
    and `date` fields are not JSON-native and crash the default encoder
    with a 500, not a 422 (Pitfall 4). Every `Decimal` here is converted
    with `str(...)`."""
    return {
        "pair_id": result.pair_id,
        "production_title": result.production_title,
        "jurisdiction_id": result.jurisdiction_id,
        "disclosed_qualified_spend": str(result.disclosed_qualified_spend),
        "disclosed_credit": str(result.disclosed_credit),
        "computed_credit": str(result.computed_credit) if result.computed_credit is not None else None,
        "verdict": result.verdict,
        "assertion_mode": result.assertion_mode,
        "tolerance_bps": result.tolerance_bps,
        "figure_tree": figure_to_dict(result.computed_figure) if result.computed_figure else None,
        "source_url": result.source_url,
        "source_document": result.source_document,
        "source_document_sha256": result.source_document_sha256,
        "report_period": result.report_period,
        "date_checked": result.date_checked,
        "refusal_reason": result.refusal_reason,
    }


@router.get("/api/v1/validate/{pair_id}")
def get_validate_json(pair_id: str) -> dict:
    try:
        result = reproduce_disclosure(pair_id)
    except UnknownPairError as exc:
        raise HTTPException(status_code=404, detail=f"unknown validation pair: {exc}") from exc
    return _validate_result_to_json(result)


@router.get("/validate/{pair_id}", response_class=HTMLResponse)
def get_validate_html(request: Request, pair_id: str) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    try:
        result = reproduce_disclosure(pair_id)
    except UnknownPairError as exc:
        raise HTTPException(status_code=404, detail=f"unknown validation pair: {exc}") from exc
    return templates.TemplateResponse(
        request=request,
        name="validate_result.html",
        context={"result": result, "public_path": PUBLIC_PATH},
    )
