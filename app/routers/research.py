"""Route D — "Job 2", the live research agent (D-89/D-90). Business logic
lives in this module; `app/templates/research_result.html` is the sole
view, shared across GET /research (form + optional `city=` prefill),
GET /research/{job_id} (one job's record, running or terminal), and
POST /research's refusal renders.

T-07-01 (Denial of service): an anonymous POST can trigger a real, metered,
multi-round Parallel + Gemini pipeline. This module holds the single-flight
lock (`_RUN_LOCK`) and the `PRODFIN_JOB2_MIN_INTERVAL_S` rate limit that
bound it, plus starts `run_job2` on a background `daemon=True` thread so a
minutes-scale pipeline never holds the Apache reverse-proxy timeout open —
the request returns a 303 immediately, exactly `app/routers/job1.py`'s
shape.

There is no CLI entry point in this module or in `agent/job2.py`. Every
`parallel-web` call site the D-90 loop reaches is reachable ONLY from this
request handler chain — the D-96 audit input.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from agent.job2 import InvalidCityInputError, run_job2, validate_city_input
from agent.research_runs import (
    SCHEMA_VERSION,
    InvalidJobIdError,
    boot_id,
    load_run,
    new_job_id,
    save_run,
)
from agent.settings import JOB2_WALL_CLOCK_CEILING_SECONDS, integration_status

__all__ = ["router"]

router = APIRouter()

# T-07-01: bounds how often an anonymous visitor can trigger a real,
# metered, multi-round Parallel + Gemini pipeline. Overridable for local
# testing only — production keeps the documented default of 60s.
MIN_SECONDS_BETWEEN_RUNS = float(os.environ.get("PRODFIN_JOB2_MIN_INTERVAL_S", "60"))

# Single-flight: only one Job 2 run may execute at a time, system-wide.
_RUN_LOCK = threading.Lock()
# Guards the two pieces of shared, mutable rate-limit state below — held
# only for the brief synchronous check-and-mint, never across the run
# itself (which happens on its own background thread).
_STATE_LOCK = threading.Lock()
_LAST_RUN_STARTED_MONO: float | None = None
# job_id -> error message. Populated ONLY when the background thread dies
# unexpectedly — every MODELED terminal state (not_configured,
# invalid_input, cache_boundary_violation, sufficient/give_up/
# no_programme_found) is written straight to the durable record by
# `run_job2` itself and never needs this registry.
_ERROR_REGISTRY: dict[str, str] = {}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _start_job(city_input: str, qualified_spend_input: str | None) -> dict:
    """Attempt to start a new Job 2 run. Returns a dict describing the
    outcome — never raises for an expected refusal (unconfigured, invalid
    input, in-flight, rate-limited); those are ordinary outcomes both views
    render legibly."""
    global _LAST_RUN_STARTED_MONO

    status = integration_status()
    if not status.parallel_configured or not status.gemini_configured:
        return {"kind": "not_configured", "message": status.not_configured_message()}

    try:
        clean_city = validate_city_input(city_input)
    except InvalidCityInputError as exc:
        return {"kind": "invalid_input", "message": str(exc)}

    with _STATE_LOCK:
        now = time.monotonic()
        if _LAST_RUN_STARTED_MONO is not None:
            elapsed = now - _LAST_RUN_STARTED_MONO
            if elapsed < MIN_SECONDS_BETWEEN_RUNS:
                remaining = int(MIN_SECONDS_BETWEEN_RUNS - elapsed) + 1
                return {"kind": "rate_limited", "retry_after_seconds": remaining}

        if not _RUN_LOCK.acquire(blocking=False):
            return {"kind": "in_flight"}

        job_id = new_job_id()
        _LAST_RUN_STARTED_MONO = now

    # Written synchronously, BEFORE the background thread starts, so
    # GET /research/{job_id} never 404s in the brief window before the
    # thread's own first write (mirrors app/routers/job1.py's in-memory
    # registry, done here as a durable record instead — `run_job2` fills in
    # the real `session_id` on its own first save).
    save_run(
        {
            "schema_version": SCHEMA_VERSION,
            "job_id": job_id,
            "city_input": clean_city,
            "qualified_spend_input": qualified_spend_input,
            "session_id": None,
            "status": "running",
            "terminal_reason": None,
            "message": None,
            "rounds": [],
            "sdk_calls": [],
            "started_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
            "ceiling_seconds": JOB2_WALL_CLOCK_CEILING_SECONDS,
            "boot_id": boot_id(),
            "round_count": 0,
        }
    )

    def _worker() -> None:
        try:
            run_job2(clean_city, qualified_spend_input, job_id=job_id)
        except Exception as exc:  # noqa: BLE001 — a background thread must never die silently
            _ERROR_REGISTRY[job_id] = str(exc)
        finally:
            _RUN_LOCK.release()

    threading.Thread(target=_worker, daemon=True).start()
    return {"kind": "started", "job_id": job_id}


def _base_context(*, public_path: str, show_form: bool, city_prefill: str = "") -> dict:
    return {
        "public_path": public_path,
        "show_form": show_form,
        "city_prefill": city_prefill,
        "not_configured_message": None,
        "refusal_reason": None,
        "record": None,
        "in_flight": False,
        "min_interval_seconds": int(MIN_SECONDS_BETWEEN_RUNS),
        "ceiling_seconds": int(JOB2_WALL_CLOCK_CEILING_SECONDS),
    }


def _get_job_or_error(job_id: str) -> dict | None:
    """Resolve `job_id` to either its error entry or its persisted record,
    or None (unknown/invalid id -> 404 at the caller). Never touches the
    filesystem for a `job_id` that fails the strict 32-hex-character check
    (T-07-04) — `load_run` raises before building any path, caught here and
    treated identically to "not found"."""
    if job_id in _ERROR_REGISTRY:
        return {"error": _ERROR_REGISTRY[job_id]}

    try:
        record = load_run(job_id)
    except InvalidJobIdError:
        return None
    if record is None:
        return None
    return {"record": record}


@router.get("/research", response_class=HTMLResponse)
def get_research_form(request: Request, city: str | None = None) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    status = integration_status()
    prefill = ""
    if city:
        try:
            prefill = validate_city_input(city)
        except InvalidCityInputError:
            prefill = ""

    context = _base_context(public_path=PUBLIC_PATH, show_form=True, city_prefill=prefill)
    if not (status.parallel_configured and status.gemini_configured):
        context["not_configured_message"] = status.not_configured_message()

    return templates.TemplateResponse(
        request=request, name="research_result.html", context=context
    )


@router.post("/research", response_class=HTMLResponse)
def post_research(
    request: Request, city: str = Form(""), qualified_spend: str = Form("")
) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    outcome = _start_job(city, qualified_spend or None)

    if outcome["kind"] == "started":
        return RedirectResponse(
            url=f"{PUBLIC_PATH}/research/{outcome['job_id']}", status_code=303
        )

    context = _base_context(public_path=PUBLIC_PATH, show_form=True, city_prefill=city[:120])
    if outcome["kind"] == "not_configured":
        context["not_configured_message"] = outcome["message"]
    elif outcome["kind"] == "invalid_input":
        context["refusal_reason"] = outcome["message"]
    elif outcome["kind"] == "in_flight":
        context["refusal_reason"] = "A research run is already in progress. Try again shortly."
    elif outcome["kind"] == "rate_limited":
        context["refusal_reason"] = (
            f"Please wait {outcome['retry_after_seconds']}s before starting another run "
            f"(minimum interval: {int(MIN_SECONDS_BETWEEN_RUNS)}s)."
        )
    return templates.TemplateResponse(
        request=request, name="research_result.html", context=context
    )


@router.post("/api/v1/research")
def post_research_json(city: str = "", qualified_spend: str = "") -> dict:
    outcome = _start_job(city, qualified_spend or None)

    if outcome["kind"] == "started":
        return {"status": "started", "job_id": outcome["job_id"]}
    if outcome["kind"] == "not_configured":
        return {"status": "not_configured", "message": outcome["message"]}
    if outcome["kind"] == "invalid_input":
        raise HTTPException(status_code=422, detail=outcome["message"])
    if outcome["kind"] == "in_flight":
        raise HTTPException(status_code=429, detail="A research run is already in progress.")
    # rate_limited
    raise HTTPException(
        status_code=429,
        detail=f"Retry after {outcome['retry_after_seconds']}s.",
    )


@router.get("/research/{job_id}", response_class=HTMLResponse)
def get_research_job_html(request: Request, job_id: str) -> HTMLResponse:
    from app.main import PUBLIC_PATH, templates

    result = _get_job_or_error(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"unknown research job: {job_id}")

    context = _base_context(public_path=PUBLIC_PATH, show_form=False)
    if "error" in result:
        context["refusal_reason"] = f"The run failed: {result['error']}"
    else:
        record = result["record"]
        context["record"] = record
        context["in_flight"] = record.get("status") == "running"

    return templates.TemplateResponse(
        request=request, name="research_result.html", context=context
    )


@router.get("/api/v1/research/{job_id}")
def get_research_job_json(job_id: str) -> dict:
    result = _get_job_or_error(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"unknown research job: {job_id}")
    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return result["record"]
