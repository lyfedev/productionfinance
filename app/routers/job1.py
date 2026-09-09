"""Route C — "Job 1" (the SHP-05/SHP-06 eligibility spine, on the hosted
page). Business logic lives in this module; `app/templates/job1_result.html`
is the sole view, shared across GET /job1 (latest run + trigger form),
GET /job1/{run_id} (one run), and POST /job1's refusal renders (D-43).

T-05-04 (Denial of service): an anonymous POST can trigger real, metered
third-party API spend. This module holds the single-flight lock
(`_RUN_LOCK`) and the `MIN_SECONDS_BETWEEN_RUNS` rate limit that bound it,
plus starts `run_job1` on a background `daemon=True` thread so a
tens-of-seconds SDK pipeline never holds the Apache reverse-proxy timeout
open — the request returns a 303 immediately.

T-05-15 (Spoofing): a replay run must never be rendered as a product
accuracy figure. `_run_render_context` enforces this by simply never
putting `awards`/`accuracy` into the template context unless
`run.run_mode == "live"` — a template rewrite cannot render data that was
never handed to it.
"""

from __future__ import annotations

import os
import threading
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from agent.job1 import Job1Run, TerminalReason, run_job1
from agent.runs import (
    InvalidRunIdError,
    load_latest,
    load_run,
    new_run_id,
    newest_committed_run,
    run_to_dict,
    save_run,
)
from agent.settings import integration_status

__all__ = ["router"]

router = APIRouter()

# T-05-04: bounds how often an anonymous visitor can trigger a real,
# metered Parallel + Gemini pipeline. Overridable for local testing only —
# production keeps the documented default of 60s.
MIN_SECONDS_BETWEEN_RUNS = float(os.environ.get("PRODFIN_JOB1_MIN_INTERVAL_S", "60"))

# Single-flight: only one Job 1 run may execute at a time, system-wide.
_RUN_LOCK = threading.Lock()
# Guards the two pieces of shared, mutable run-tracking state below —
# held only for the brief synchronous check-and-mint, never across the
# run itself (which happens on its own background thread).
_STATE_LOCK = threading.Lock()
_LAST_RUN_STARTED_MONO: float | None = None
# run_id -> {"status": "running"|"done"|"error", "stage": str|None,
#            "error": str (only when status == "error")}
# Populated only while a run is in flight or has just failed; a terminal
# success is read back from disk via agent.runs.load_run, not from here.
_RUN_REGISTRY: dict[str, dict] = {}


def _start_run() -> dict:
    """Attempt to start a new Job 1 run. Returns a dict describing the
    outcome — never raises for an expected refusal (unconfigured,
    in-flight, rate-limited); those are ordinary outcomes both views
    render legibly."""
    global _LAST_RUN_STARTED_MONO

    status = integration_status()
    if not status.parallel_configured or not status.gemini_configured:
        return {"kind": "not_configured", "message": status.not_configured_message()}

    with _STATE_LOCK:
        now = time.monotonic()
        if _LAST_RUN_STARTED_MONO is not None:
            elapsed = now - _LAST_RUN_STARTED_MONO
            if elapsed < MIN_SECONDS_BETWEEN_RUNS:
                remaining = int(MIN_SECONDS_BETWEEN_RUNS - elapsed) + 1
                return {"kind": "rate_limited", "retry_after_seconds": remaining}

        if not _RUN_LOCK.acquire(blocking=False):
            return {"kind": "in_flight"}

        run_id = new_run_id()
        _RUN_REGISTRY[run_id] = {"status": "running", "stage": "starting"}
        _LAST_RUN_STARTED_MONO = now

    def _on_stage(stage: str) -> None:
        entry = _RUN_REGISTRY.get(run_id)
        if entry is not None:
            entry["stage"] = stage

    def _worker() -> None:
        try:
            run = run_job1(on_stage=_on_stage)
            save_run(run, run_id=run_id)
            _RUN_REGISTRY[run_id] = {"status": "done", "stage": None}
        except Exception as exc:  # noqa: BLE001 — a background thread must never die silently
            _RUN_REGISTRY[run_id] = {"status": "error", "stage": None, "error": str(exc)}
        finally:
            _RUN_LOCK.release()

    threading.Thread(target=_worker, daemon=True).start()
    return {"kind": "started", "run_id": run_id}


def _run_render_context(run: Job1Run) -> dict:
    """T-05-15, enforced here, not only in the template: `awards` and
    `accuracy` are populated ONLY for a `run_mode == "live"` run that
    reached its `ok` terminal state — a template rewrite cannot render an
    accuracy figure for data that was never put in the context.

    `source_enactment` (AGT-08, D-97, plan 05-07) is a property of the
    SOURCE DOCUMENT, not of a priced figure — it renders for any run that
    reached Extract, live or replay alike, and is never used to imply a
    figure was validated (it says nothing about `awards`/`accuracy`)."""
    is_live = run.run_mode == "live"
    show_accuracy = is_live and run.terminal_reason == TerminalReason.ok
    return {
        "run": run,
        "is_live": is_live,
        "show_accuracy": show_accuracy,
        "non_live_banner": (
            None
            if is_live
            else "This run was a REPLAY, not a live SDK call, and carries no accuracy claim."
        ),
        "awards": run.awards if show_accuracy else (),
        "accuracy": run.accuracy if show_accuracy else None,
        "source_enactment": run.source_enactment,
    }


_EMPTY_RUN_CONTEXT = {
    "run": None,
    "is_live": False,
    "show_accuracy": False,
    "non_live_banner": None,
    "awards": (),
    "accuracy": None,
    "source_enactment": None,
}


def _base_context(*, public_path: str, show_form: bool) -> dict:
    return {
        "public_path": public_path,
        "show_form": show_form,
        "not_configured_message": None,
        "refusal_reason": None,
        "in_flight": False,
        "stage": None,
        "min_interval_seconds": int(MIN_SECONDS_BETWEEN_RUNS),
        **_EMPTY_RUN_CONTEXT,
    }


def _get_run_or_inflight(run_id: str) -> dict | None:
    """Resolve `run_id` to either its in-flight registry entry, its error
    entry, its saved `Job1Run`, or None (unknown id -> 404 at the caller).
    Never touches the filesystem for a `run_id` that fails the strict
    32-hex-character check (T-05-12) — `load_run` raises before building
    any path, caught here and treated identically to "not found"."""
    entry = _RUN_REGISTRY.get(run_id)
    if entry is not None and entry.get("status") == "running":
        return {"in_flight": True, "stage": entry.get("stage")}
    if entry is not None and entry.get("status") == "error":
        return {"error": entry.get("error") or "unknown error"}

    try:
        run = load_run(run_id)
    except InvalidRunIdError:
        return None
    if run is None:
        return None
    return {"run": run}


@router.get("/job1", response_class=HTMLResponse)
def get_job1_form(request: Request) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    status = integration_status()
    context = _base_context(public_path=PUBLIC_PATH, show_form=True)
    if not (status.parallel_configured and status.gemini_configured):
        context["not_configured_message"] = status.not_configured_message()

    run = load_latest() or newest_committed_run()
    if run is not None:
        context.update(_run_render_context(run))

    return templates.TemplateResponse(request=request, name="job1_result.html", context=context)


@router.post("/job1", response_class=HTMLResponse)
def post_job1(request: Request) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    outcome = _start_run()

    if outcome["kind"] == "started":
        return RedirectResponse(url=f"{PUBLIC_PATH}/job1/{outcome['run_id']}", status_code=303)

    context = _base_context(public_path=PUBLIC_PATH, show_form=True)
    if outcome["kind"] == "not_configured":
        context["not_configured_message"] = outcome["message"]
    elif outcome["kind"] == "in_flight":
        context["refusal_reason"] = "A Job 1 run is already in progress. Try again shortly."
    elif outcome["kind"] == "rate_limited":
        context["refusal_reason"] = (
            f"Please wait {outcome['retry_after_seconds']}s before starting another run "
            f"(minimum interval: {int(MIN_SECONDS_BETWEEN_RUNS)}s)."
        )
    return templates.TemplateResponse(request=request, name="job1_result.html", context=context)


@router.post("/api/v1/job1")
def post_job1_json() -> dict:
    outcome = _start_run()

    if outcome["kind"] == "started":
        return {"status": "started", "run_id": outcome["run_id"]}
    if outcome["kind"] == "not_configured":
        return {"status": "not_configured", "message": outcome["message"]}
    if outcome["kind"] == "in_flight":
        raise HTTPException(status_code=429, detail="A Job 1 run is already in progress.")
    # rate_limited
    raise HTTPException(
        status_code=429,
        detail=f"Retry after {outcome['retry_after_seconds']}s.",
    )


@router.get("/job1/{run_id}", response_class=HTMLResponse)
def get_job1_run_html(request: Request, run_id: str) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    result = _get_run_or_inflight(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"unknown Job 1 run: {run_id}")

    context = _base_context(public_path=PUBLIC_PATH, show_form=False)
    if "in_flight" in result:
        context["in_flight"] = True
        context["stage"] = result["stage"]
    elif "error" in result:
        context["refusal_reason"] = f"The run failed: {result['error']}"
    else:
        context.update(_run_render_context(result["run"]))

    return templates.TemplateResponse(request=request, name="job1_result.html", context=context)


@router.get("/api/v1/job1/{run_id}")
def get_job1_run_json(run_id: str) -> dict:
    result = _get_run_or_inflight(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"unknown Job 1 run: {run_id}")

    if "in_flight" in result:
        return {"status": "running", "stage": result["stage"]}
    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return run_to_dict(result["run"])
