"""The three-pane integration demonstration surface.

`GET /integrate` renders the contract; `POST /api/v1/integrate` is the
contract. The page's right-hand pane shows exactly what that endpoint
returns — the page has no formatting path of its own, so what an integrator
reads on the page is what their host system receives.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.services.integrate import (
    PRESETS,
    IntegrationRequest,
    available_jurisdictions,
    price_from_request,
)

router = APIRouter()


class IntegrationPayload(BaseModel):
    jurisdiction_id: str = Field(..., description="e.g. us-ny")
    qualified_spend: str = Field(..., description="decimal amount, e.g. 3964760")
    spend_confidence: str = Field(default="validated")


@router.post("/api/v1/integrate")
def post_integrate(payload: IntegrationPayload) -> dict:
    return price_from_request(
        IntegrationRequest(
            jurisdiction_id=payload.jurisdiction_id,
            qualified_spend=payload.qualified_spend,
            spend_confidence=payload.spend_confidence,
        )
    )


@router.get("/integrate", response_class=HTMLResponse)
def get_integrate(
    request: Request,
    jurisdiction_id: str | None = None,
    qualified_spend: str | None = None,
    submitted: str | None = None,
) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    selected = jurisdiction_id or "us-ny"
    spend = qualified_spend or "3964760"

    inbound = {
        "jurisdiction_id": selected,
        "qualified_spend": spend,
        "spend_confidence": "validated",
    }

    response_json = None
    if submitted:
        response_json = json.dumps(
            price_from_request(
                IntegrationRequest(
                    jurisdiction_id=selected,
                    qualified_spend=spend,
                    spend_confidence="validated",
                )
            ),
            indent=2,
        )

    return templates.TemplateResponse(
        request=request,
        name="integrate.html",
        context={
            "public_path": PUBLIC_PATH,
            "jurisdictions": available_jurisdictions(),
            "selected": selected,
            "spend": spend,
            "inbound_json": json.dumps(inbound, indent=2),
            "response_json": response_json,
            "presets": PRESETS,
        },
    )
