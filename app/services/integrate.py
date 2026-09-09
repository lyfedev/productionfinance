"""The integration contract: price a jurisdiction from a plain JSON request.

This is the shape a host production-accounting system would send us and the
shape we return. It deliberately exposes the same `engine.pipeline.price_
jurisdiction` call the rest of the product uses — no separate code path, no
demo-only arithmetic (D-85/AGT-07) — so what an integrator sees on
`/integrate` is what they get from the API.

A refusal is part of the contract, not an error case bolted on: a programme
whose transfer discount is unsourced returns `computed: null` with a stated
`refusal_reason`, because the honest answer to "what is this credit worth in
cash" is sometimes "unknown".
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.services._paths import RULESET_PATH_BY_JURISDICTION
from engine.figure_serialize import figure_to_dict
from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction

__all__ = [
    "PRESETS",
    "IntegrationRequest",
    "available_jurisdictions",
    "price_from_request",
]


@dataclass(frozen=True)
class IntegrationRequest:
    jurisdiction_id: str
    qualified_spend: str
    spend_confidence: str = "validated"


# One preset that reproduces a published government figure exactly, and one
# that refuses. Both are real committed data, not illustrations.
PRESETS: dict[str, dict[str, Any]] = {
    "exact_match": {
        "label": "Reproduces a published government figure exactly",
        "note": (
            "Anora's qualified spend as disclosed in the New York ESD Q3 2025 "
            "quarterly report. The engine returns 991190 USD; ESD disclosed "
            "991190 USD."
        ),
        "request": {
            "jurisdiction_id": "us-ny",
            "qualified_spend": "3964760",
            "spend_confidence": "validated",
        },
    },
    "refusal": {
        "label": "Refuses — transfer discount unsourced",
        "note": (
            "New Jersey's credit is transferable, and no New Jersey government "
            "document states a transfer discount ceiling. The engine declines "
            "to convert the credit to net cash rather than inventing a rate."
        ),
        "request": {
            "jurisdiction_id": "us-nj",
            "qualified_spend": "10000000",
            "spend_confidence": "validated",
        },
    },
}


def available_jurisdictions() -> tuple[str, ...]:
    return tuple(sorted(RULESET_PATH_BY_JURISDICTION))


def price_from_request(request: IntegrationRequest) -> dict[str, Any]:
    """Run the real pricing pipeline and return the integration response.

    Every failure mode is a structured response, never an exception escaping
    to a 500: an unknown jurisdiction, an unparseable amount, and an engine
    refusal are all things a host system must be able to handle.
    """
    path: Path | None = RULESET_PATH_BY_JURISDICTION.get(request.jurisdiction_id)
    if path is None:
        return {
            "status": "rejected",
            "reason": f"unknown jurisdiction_id: {request.jurisdiction_id!r}",
            "available": list(available_jurisdictions()),
        }

    try:
        spend = Decimal(str(request.qualified_spend).replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return {
            "status": "rejected",
            "reason": f"qualified_spend is not a decimal amount: {request.qualified_spend!r}",
        }
    if spend <= 0:
        return {"status": "rejected", "reason": "qualified_spend must be greater than zero"}

    ruleset = load_ruleset(path)

    try:
        priced = price_jurisdiction(
            ruleset, spend, spend_confidence=request.spend_confidence  # type: ignore[arg-type]
        )
    except ValueError as exc:
        # The engine's own refusal. Surfaced verbatim — an integrator needs
        # the reason, not a generic failure.
        return {
            "status": "cannot_be_computed",
            "jurisdiction_id": request.jurisdiction_id,
            "jurisdiction": {
            "id": ruleset.jurisdiction.id,
            "country_code": ruleset.jurisdiction.country_code,
            "currency": ruleset.jurisdiction.currency,
            "level": ruleset.jurisdiction.level,
        },
            "qualified_spend": str(spend),
            "computed": None,
            "refusal_reason": str(exc),
        }

    programmes = []
    for programme in priced.programmes:
        entry: dict[str, Any] = {"programme_id": programme.programme_id}
        for field in ("qualifying_base", "gross_credit"):
            figure = getattr(programme, field, None)
            if figure is None:
                # A null here is meaningful: net_cash is absent when the
                # engine declined to convert. Report the absence, never a
                # zero, which would assert the credit is worthless.
                entry[field] = None
                continue
            entry[field] = {
                "value": str(figure.value),
                "unit": figure.unit,
                "confidence": figure.confidence,
                "derivation_tree": figure_to_dict(figure),
            }
        net = getattr(programme, "net_cash", None)
        # NetCashResult is a low/point/high range plus an arrival date, not
        # a single Figure. A transferable credit with a sourced discount
        # range has low != high; that spread is real information about how
        # much cash the credit is actually worth, so it is reported rather
        # than collapsed to a midpoint.
        if net is None:
            entry["net_cash"] = None
        else:
            entry["net_cash"] = {
                "low": str(net.low.value) if getattr(net, "low", None) is not None else None,
                "point": str(net.point.value) if getattr(net, "point", None) is not None else None,
                "high": str(net.high.value) if getattr(net, "high", None) is not None else None,
                "arrival": str(getattr(net, "arrival", None)),
                "derivation_tree": (
                    figure_to_dict(net.point) if getattr(net, "point", None) is not None else None
                ),
            }
        entry["availability"] = str(getattr(programme, "availability", None))
        programmes.append(entry)

    return {
        "status": "ok",
        "jurisdiction_id": request.jurisdiction_id,
        "jurisdiction": {
            "id": ruleset.jurisdiction.id,
            "country_code": ruleset.jurisdiction.country_code,
            "currency": ruleset.jurisdiction.currency,
            "level": ruleset.jurisdiction.level,
        },
        "qualified_spend": str(spend),
        "programmes": programmes,
    }
