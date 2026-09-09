"""Single-shot live checks (Task 2, plan 07-04): cap consumption and
programme open/closed status — AGT-10's other two live data classes,
alongside FX (`app/services/live_fx.py`) and uncurated-city research
(`agent/job2.py`).

Deliberately NOT the D-90 Job 2 loop shape: each check here is exactly
ONE Search plus ONE structured judgment. There is no refinement round —
the question ("what's the remaining cap allocation right now" / "is this
programme currently open") is narrow enough to be answerable or not in
one pass, unlike Job 2's open-ended "build me a cost model" sufficiency
loop over five named fields (D-91).

`check_cap_consumption` and `check_programme_open` both call
`app.services.cache_policy.assert_live` themselves before doing anything
— defense in depth (mirrors `agent/job2.py`'s dual-validation pattern from
plan 07-01), even though `app.services.cache_policy.resolve_cap_consumption`
/ `resolve_programme_status` already assert live before calling in here.
This is also what makes this module one of AGT-10's four "consumer"
modules for the single-point-of-truth AST gate
(`tests/test_cache_policy_live.py`).

With no API key configured, both return their undetermined result
immediately, naming the missing variable(s), and fire NO SDK call at all
— `google-genai` and `parallel-web` are both imported lazily, inside the
`try` block that only runs once keys are confirmed present, so CI (no
keys) never touches either SDK and stays fully deterministic. Any failure
once a call IS attempted (timeout, malformed response, an unparseable
money string) is caught and reported the same way — never an uncaught
exception escaping into the `/spec` request, and never a fabricated
number (D-94).

Both response schemas are defined here and nowhere else (D-83): each is
sourced straight into `response_json_schema` via `model_json_schema()`,
never a second hand-written JSON schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from agent.numbers import UnparseableFigureError, parse_money
from agent.settings import gemini_api_key, integration_status, parallel_api_key
from agent.telemetry import sdk_call
from app.services.cache_policy import DataClass, assert_live

__all__ = [
    "CapConsumptionResult",
    "ProgrammeStatusResult",
    "check_cap_consumption",
    "check_programme_open",
]

# Short, explicit per-call timeouts (T-07-22) — narrow enough to sit on a
# visitor's own /spec request, unlike Job 2's minutes-scale research loop
# (agent/job2.py's JOB2_WALL_CLOCK_CEILING_SECONDS is a different budget
# entirely, for a different shape of question).
_LIVE_CHECK_SEARCH_TIMEOUT_SECONDS = 12.0
_LIVE_CHECK_MODEL = "gemini-3.6-flash"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class CapConsumptionResult:
    """`determined=False` with a non-`None` reason covers every
    undetermined path: no keys configured, the Search returned nothing
    usable, or the model's own reported value did not parse. `remaining`
    is populated ONLY when `determined` is True — never a partial or
    guessed value."""

    determined: bool
    remaining: Decimal | None
    value_text: str | None
    source_url: str | None
    checked_at: str
    reason: str | None


@dataclass(frozen=True)
class ProgrammeStatusResult:
    state: Literal["open", "closed", "unknown"]
    source_url: str | None
    checked_at: str
    reason: str


class _CapConsumptionJudgment(BaseModel):
    """D-83: the single schema definition for this judgment."""

    model_config = ConfigDict(extra="forbid")

    determined: bool
    remaining_value_text: str | None = None
    source_url: str | None = None
    reason: str | None = None


class _ProgrammeStatusJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["open", "closed", "unknown"]
    source_url: str | None = None
    reason: str | None = None


def _search_excerpts(client: object, objective: str, queries: list[str], target: str) -> str:
    """One bounded Search call, wrapped in `sdk_call` exactly like
    `agent/parallel_client.py`'s own call sites. `client` is typed
    `object` deliberately — the `parallel` SDK is imported lazily by the
    caller, never at this module's top level (T-07-01)."""
    with sdk_call("parallel-web", "search", target):
        result = client.search(  # type: ignore[attr-defined]
            objective=objective,
            search_queries=queries,
            timeout=_LIVE_CHECK_SEARCH_TIMEOUT_SECONDS,
        )
    chunks: list[str] = []
    for web_result in result.results[:5]:
        excerpt_text = "\n".join(web_result.excerpts or [])
        chunks.append(f"URL: {web_result.url}\n{excerpt_text}")
    return "\n\n".join(chunks)


def check_cap_consumption(
    jurisdiction_name: str, programme_name: str, source_url_hint: str | None
) -> CapConsumptionResult:
    """One Search plus one structured judgment, asking specifically for
    the CURRENT remaining annual allocation. `source_url_hint` (the rule
    file's own `cap_consumption_check.source_url`, when declared) is
    folded into the search query when present — never trusted as the
    answer itself without a Search+judgment round confirming it."""
    assert_live(DataClass.cap_consumption)
    checked_at = _utc_now_iso()

    status = integration_status()
    if not (status.parallel_configured and status.gemini_configured):
        return CapConsumptionResult(
            determined=False,
            remaining=None,
            value_text=None,
            source_url=None,
            checked_at=checked_at,
            reason=f"not checked at request time — {status.not_configured_message()}",
        )

    objective = (
        f"Find the most recent, dated, official disclosure of the CURRENT "
        f"remaining annual allocation (how much of the annual cap has NOT yet "
        f"been consumed) for the {programme_name!r} film/TV production tax "
        f"incentive programme administered by {jurisdiction_name!r}."
    )
    queries = [f"{jurisdiction_name} {programme_name} annual cap remaining allocation"]
    if source_url_hint:
        queries.append(source_url_hint)

    try:
        import parallel
        from google import genai
        from google.genai import types

        client = parallel.Parallel(api_key=parallel_api_key())
        excerpts = _search_excerpts(
            client, objective, queries, f"cap-consumption:{jurisdiction_name}"
        )
        if not excerpts.strip():
            return CapConsumptionResult(
                determined=False,
                remaining=None,
                value_text=None,
                source_url=None,
                checked_at=checked_at,
                reason="Search returned no usable result for the cap-consumption question",
            )

        prompt = (
            f"{objective}\n\nSEARCH RESULTS:\n{excerpts}\n\nIf a current "
            "remaining allocation figure is not disclosed, set determined=false "
            "and explain why in reason — never estimate or infer one."
        )
        gemini_client = genai.Client(api_key=gemini_api_key())
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=_CapConsumptionJudgment.model_json_schema(),
        )
        with sdk_call("google-genai", "generate_content", f"cap-consumption:{jurisdiction_name}"):
            response = gemini_client.models.generate_content(
                model=_LIVE_CHECK_MODEL, contents=prompt, config=config
            )
        judgment = _CapConsumptionJudgment.model_validate_json(response.text)
    except Exception as exc:  # noqa: BLE001 — never let a live-check failure 500 /spec
        return CapConsumptionResult(
            determined=False,
            remaining=None,
            value_text=None,
            source_url=None,
            checked_at=checked_at,
            reason=f"live cap-consumption check failed: {exc}",
        )

    if not judgment.determined or judgment.remaining_value_text is None:
        return CapConsumptionResult(
            determined=False,
            remaining=None,
            value_text=judgment.remaining_value_text,
            source_url=judgment.source_url,
            checked_at=checked_at,
            reason=judgment.reason or "model reported it could not determine a remaining figure",
        )

    try:
        remaining = parse_money(judgment.remaining_value_text)
    except UnparseableFigureError as exc:
        return CapConsumptionResult(
            determined=False,
            remaining=None,
            value_text=judgment.remaining_value_text,
            source_url=judgment.source_url,
            checked_at=checked_at,
            reason=f"model-reported figure did not parse: {exc}",
        )

    return CapConsumptionResult(
        determined=True,
        remaining=remaining,
        value_text=judgment.remaining_value_text,
        source_url=judgment.source_url,
        checked_at=checked_at,
        reason=None,
    )


def check_programme_open(jurisdiction_name: str, programme_name: str) -> ProgrammeStatusResult:
    """One Search plus one structured judgment asking whether the
    programme is currently accepting applications. Never writes into
    `Jurisdiction.status` — the caller
    (`app.services.cache_policy.resolve_programme_status`) carries this
    alongside the priced result, on its own line, with its own source and
    check time."""
    assert_live(DataClass.programme_open_status)
    checked_at = _utc_now_iso()

    status = integration_status()
    if not (status.parallel_configured and status.gemini_configured):
        return ProgrammeStatusResult(
            state="unknown",
            source_url=None,
            checked_at=checked_at,
            reason=f"not checked at request time — {status.not_configured_message()}",
        )

    objective = (
        f"Determine whether the {programme_name!r} film/TV production tax "
        f"incentive programme administered by {jurisdiction_name!r} is CURRENTLY "
        "open to new applications, closed, or its status cannot be determined."
    )
    queries = [f"{jurisdiction_name} {programme_name} program status open applications"]

    try:
        import parallel
        from google import genai
        from google.genai import types

        client = parallel.Parallel(api_key=parallel_api_key())
        excerpts = _search_excerpts(
            client, objective, queries, f"programme-status:{jurisdiction_name}"
        )
        if not excerpts.strip():
            return ProgrammeStatusResult(
                state="unknown",
                source_url=None,
                checked_at=checked_at,
                reason="Search returned no usable result for the programme-status question",
            )

        prompt = (
            f"{objective}\n\nSEARCH RESULTS:\n{excerpts}\n\nIf the current "
            "status cannot be determined from what was found, set "
            'state="unknown" and explain why in reason.'
        )
        gemini_client = genai.Client(api_key=gemini_api_key())
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=_ProgrammeStatusJudgment.model_json_schema(),
        )
        with sdk_call("google-genai", "generate_content", f"programme-status:{jurisdiction_name}"):
            response = gemini_client.models.generate_content(
                model=_LIVE_CHECK_MODEL, contents=prompt, config=config
            )
        judgment = _ProgrammeStatusJudgment.model_validate_json(response.text)
    except Exception as exc:  # noqa: BLE001
        return ProgrammeStatusResult(
            state="unknown",
            source_url=None,
            checked_at=checked_at,
            reason=f"live programme-status check failed: {exc}",
        )

    return ProgrammeStatusResult(
        state=judgment.state,
        source_url=judgment.source_url,
        checked_at=checked_at,
        reason=judgment.reason or f"model reported state={judgment.state!r}",
    )
