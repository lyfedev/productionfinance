"""Route E — the proof panel (UI-07, DMO-01), the honest accuracy figure
(PRV-06), and unresolved source conflicts (PRV-07). All business logic
lives in `app/services/proof.py` (D-43); this module is routing only.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from app.services.proof import (
    MalformedFixtureError,
    UnknownPairError,
    accuracy_over_validation_pairs,
    build_proof,
    load_source_conflicts,
    proof_pairs,
    resolve_document_path,
)

__all__ = ["router"]

router = APIRouter()


@router.get("/proof", response_class=HTMLResponse)
def get_proof_index(request: Request) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    return templates.TemplateResponse(
        request=request,
        name="proof.html",
        context={
            "public_path": PUBLIC_PATH,
            "pairs": proof_pairs(),
            "accuracy": accuracy_over_validation_pairs(),
            "conflicts": load_source_conflicts(),
            "result": None,
        },
    )


@router.get("/proof/{pair_id}", response_class=HTMLResponse)
def get_proof_detail(request: Request, pair_id: str) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    try:
        result = build_proof(pair_id)
    except UnknownPairError as exc:
        raise HTTPException(status_code=404, detail=f"unknown validation pair: {exc}") from exc
    except MalformedFixtureError as exc:
        # A repo-committed fixture-authoring bug, not the visitor's fault
        # (mirrors app/routers/validate.py's identical handled-500 shape)
        # — never an unhandled crash.
        raise HTTPException(
            status_code=500, detail=f"validation pair fixture is malformed: {exc}"
        ) from exc

    return templates.TemplateResponse(
        request=request,
        name="proof.html",
        context={
            "public_path": PUBLIC_PATH,
            "pairs": proof_pairs(),
            "accuracy": accuracy_over_validation_pairs(),
            "conflicts": load_source_conflicts(),
            "result": result,
        },
    )


@router.get("/proof/{pair_id}/document")
def get_proof_document(pair_id: str) -> FileResponse:
    """Serve the archived document's own bytes (D-98) — the artifact
    itself, not a redirect to a live government URL that may 404
    (Connecticut's DECD page already does).

    T-03-01/T-05-12 discipline: `pair_id` is resolved through
    `build_proof`'s own closed-selectable-set membership check before any
    filesystem path is touched — an unknown or unselectable `pair_id`
    never reaches `resolve_document_path`."""
    try:
        result = build_proof(pair_id)
    except UnknownPairError as exc:
        raise HTTPException(status_code=404, detail=f"unknown validation pair: {exc}") from exc
    except MalformedFixtureError as exc:
        raise HTTPException(
            status_code=500, detail=f"validation pair fixture is malformed: {exc}"
        ) from exc

    if result.document is None or not result.document.exists_on_disk:
        raise HTTPException(
            status_code=404,
            detail=f"no archived source document is available for {pair_id!r}",
        )

    # `result.document.repo_relative_path` is already a value read back
    # from the committed fixture, not request input — resolved through
    # the same module-anchored helper the proof panel itself uses.
    path = resolve_document_path(result.document.repo_relative_path)
    return FileResponse(
        path,
        media_type=result.document.media_type,
        filename=path.name,
    )
