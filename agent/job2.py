"""Job 2: research an uncurated jurisdiction through a genuine agent loop.

D-90: this is deliberately NOT `agent/job1.py`'s fixed sequence. The driver
below is a `while True:` loop whose exit is decided entirely by the model's
own `decision` value (`SufficiencyVerdict.decision`, D-91) — no integer
bounds how many rounds it may run, and no round counter is ever compared
against a constant.

Each round: issue a Parallel Search under the run's one `session_id` (the
07-SDK-FINDINGS spine — this is what makes round N+1 contextually aware of
rounds 1..N), build the round's evidence text from the results, call
`google-genai` for a `SufficiencyVerdict` against D-91's five named fields,
persist the round to disk via `agent.research_runs.append_round` BEFORE the
next round starts (D-92), then branch on `verdict.decision`: `sufficient`,
`give_up` and `no_programme_found` each exit with that terminal reason;
`continue` carries the refined objective/queries/mode into the next round.

`import parallel` and `from google import genai` are INSIDE the functions
that call them, never at module top level (lazy import — the 472 MB
production box depends on this; a test enforces it).

`search_fn`/`judge_fn` are injectable seams (each defaulting to `None`,
resolved to the real client function), exactly the way `agent/job1.py`
takes `search_fn`/`extract_fn` — a test double is never a default.
"""

from __future__ import annotations

import unicodedata
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from agent.research_runs import SCHEMA_VERSION, append_round, boot_id, save_run
from agent.research_schema import (
    FieldFinding,
    SufficiencyField,
    SufficiencyVerdict,
    research_response_schema,
)
from agent.settings import (
    GEMINI_MODEL,
    JOB2_MAX_CHARS_PER_SEARCH,
    JOB2_WALL_CLOCK_CEILING_SECONDS,
    SEARCH_TIMEOUT_SECONDS,
    gemini_api_key,
    integration_status,
    parallel_api_key,
)
from agent.telemetry import collecting, sdk_call
from app.services.cache_policy import CacheBoundaryViolation, DataClass, assert_live

__all__ = [
    "InvalidCityInputError",
    "ResearchRun",
    "run_job2",
    "validate_city_input",
]

_ALL_FIELDS: tuple[SufficiencyField, ...] = tuple(SufficiencyField)
_MAX_CITY_INPUT_CHARS = 120

SearchFn = Callable[..., Sequence[dict]]
JudgeFn = Callable[..., SufficiencyVerdict]


class InvalidCityInputError(ValueError):
    """Raised when the visitor's city string is empty, too long, or
    contains a control/format character (T-07-05). A rejected input is
    never truncated and used anyway."""


def validate_city_input(city_input: str) -> str:
    """Bound the visitor's city string before it ever reaches an objective
    or a query: strip, reject empty, reject over
    `_MAX_CITY_INPUT_CHARS`, reject any `Cc`/`Cf` (control/format)
    character. Returns the stripped, validated string."""
    stripped = (city_input or "").strip()
    if not stripped:
        raise InvalidCityInputError("City name must not be empty.")
    if len(stripped) > _MAX_CITY_INPUT_CHARS:
        raise InvalidCityInputError(
            f"City name must be at most {_MAX_CITY_INPUT_CHARS} characters."
        )
    for ch in stripped:
        if unicodedata.category(ch) in ("Cc", "Cf"):
            raise InvalidCityInputError("City name contains a control character.")
    return stripped


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class ResearchRun:
    """The in-process return value mirroring the on-disk record. Fields
    later plans fill (`findings`, `undetermined_disclosures`,
    `ruleset_path`, `priced`) are declared now with `None` defaults so the
    record shape does not churn (D-92's costly-reversibility note)."""

    job_id: str
    city_input: str
    qualified_spend_input: str | None
    session_id: str
    status: Literal["running", "terminal", "interrupted"]
    terminal_reason: str | None
    message: str | None
    rounds: tuple[dict, ...] = field(default_factory=tuple)
    sdk_calls: tuple[dict, ...] = field(default_factory=tuple)
    started_at: str = ""
    updated_at: str = ""
    ceiling_seconds: float = JOB2_WALL_CLOCK_CEILING_SECONDS
    findings: tuple[dict, ...] | None = None
    undetermined_disclosures: tuple[str, ...] | None = None
    ruleset_path: str | None = None
    priced: dict | None = None


def _run_from_record(record: dict) -> ResearchRun:
    return ResearchRun(
        job_id=record["job_id"],
        city_input=record["city_input"],
        qualified_spend_input=record.get("qualified_spend_input"),
        session_id=record.get("session_id") or "",
        status=record["status"],
        terminal_reason=record.get("terminal_reason"),
        message=record.get("message"),
        rounds=tuple(record.get("rounds", ())),
        sdk_calls=tuple(record.get("sdk_calls", ())),
        started_at=record.get("started_at", ""),
        updated_at=record.get("updated_at", ""),
        ceiling_seconds=record.get("ceiling_seconds", JOB2_WALL_CLOCK_CEILING_SECONDS),
    )


def _field_prose() -> str:
    return ", ".join(f.value.replace("_", " ") for f in _ALL_FIELDS)


def _round1_objective(city_input: str) -> str:
    return (
        f"Determine whether {city_input} (or the jurisdiction it is in) has an "
        "active film/TV production incentive programme, and if so, find enough "
        f"about it to build a cost model: {_field_prose()}."
    )


def _round1_queries(city_input: str) -> list[str]:
    return [f"{city_input} film tax incentive", f"{city_input} production incentive programme"]


def _evidence_text(results: Sequence[dict]) -> str:
    blocks: list[str] = []
    for result in results:
        title = result.get("title") or "(untitled)"
        url = result.get("url", "")
        excerpts = result.get("excerpts") or []
        body = "\n".join(excerpts)
        blocks.append(f"### {title}\n{url}\n{body}")
    return "\n\n".join(blocks)


def _unmet_field_names(findings: Sequence[FieldFinding]) -> list[str]:
    determined = {f.field for f in findings if f.determined}
    return [f.value for f in _ALL_FIELDS if f not in determined]


def _judge_prompt(city_input: str, objective: str, evidence_text: str) -> str:
    return f"""You are judging whether the search results below are enough to build
a film/TV production incentive cost model for {city_input}. The sufficiency
contract has exactly five fields: {_field_prose()}.

Objective this round: {objective}

For each of the five fields, report whether it was determined from the
evidence below: the value (verbatim where possible), a short evidence
quote, and the source URL. Then decide:
- "sufficient" if all five fields are determined.
- "continue" if not yet determined but more research could plausibly help
  (supply next_objective as a self-contained restated goal naming what is
  still missing, and 2-3 next_queries of 3-6 words each).
- "give_up" if further research is unlikely to help.
- "no_programme_found" if the evidence indicates no such programme exists
  for {city_input}.
Return only the structured JSON described by the response schema.

SEARCH RESULTS:
{evidence_text}
"""


def _real_search(
    *,
    search_queries: Sequence[str],
    objective: str,
    session_id: str,
    mode: str,
    max_chars_total: int,
    timeout: float,
    round_number: int,
) -> list[dict]:
    import parallel  # lazy import (see module docstring)

    client = parallel.Parallel(api_key=parallel_api_key())
    with sdk_call("parallel-web", "search", f"job2-round-{round_number}"):
        result = client.search(
            search_queries=list(search_queries),
            objective=objective,
            session_id=session_id,
            mode=mode,
            max_chars_total=max_chars_total,
            timeout=timeout,
        )
    return [{"url": r.url, "title": r.title, "excerpts": list(r.excerpts)} for r in result.results]


def _real_judge(
    *,
    city_input: str,
    objective: str,
    evidence_text: str,
    round_number: int,
) -> SufficiencyVerdict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=gemini_api_key())
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=research_response_schema(),
    )
    prompt = _judge_prompt(city_input, objective, evidence_text)

    with sdk_call("google-genai", "generate_content", GEMINI_MODEL, round=round_number):
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config,
        )
    return SufficiencyVerdict.model_validate_json(response.text)


def run_job2(
    city_input: str,
    qualified_spend_input: str | None,
    *,
    job_id: str,
    search_fn: SearchFn | None = None,
    judge_fn: JudgeFn | None = None,
    on_round: Callable[[dict], None] | None = None,
) -> ResearchRun:
    """Execute the D-90 self-terminating research loop and return a
    `ResearchRun`. `search_fn`/`judge_fn` are test seams; a test double is
    never a default. `on_round`, if given, is called with each round's dict
    record right after it is persisted.
    """
    started_at = _utc_now_iso()
    using_real_seams = search_fn is None and judge_fn is None

    def _terminal_record(reason: str, message: str) -> dict:
        record = {
            "schema_version": SCHEMA_VERSION,
            "job_id": job_id,
            "city_input": city_input,
            "qualified_spend_input": qualified_spend_input,
            "session_id": None,
            "status": "terminal",
            "terminal_reason": reason,
            "message": message,
            "rounds": [],
            "sdk_calls": [],
            "started_at": started_at,
            "updated_at": _utc_now_iso(),
            "ceiling_seconds": JOB2_WALL_CLOCK_CEILING_SECONDS,
            "boot_id": boot_id(),
            "round_count": 0,
        }
        save_run(record)
        return record

    if using_real_seams:
        status = integration_status()
        if not status.parallel_configured or not status.gemini_configured:
            return _run_from_record(
                _terminal_record("not_configured", status.not_configured_message())
            )

    try:
        clean_city = validate_city_input(city_input)
    except InvalidCityInputError as exc:
        return _run_from_record(_terminal_record("invalid_input", str(exc)))

    # D-89/AGT-10, made structural: the live research path must not read
    # from cache. This is asserted BEFORE the first Search call — a
    # `CacheBoundaryViolation` here means no Search ever fires.
    try:
        assert_live(DataClass.uncurated_city_research)
    except CacheBoundaryViolation as exc:
        return _run_from_record(_terminal_record("cache_boundary_violation", str(exc)))

    search = search_fn or _real_search
    judge = judge_fn or _real_judge

    session_id = uuid.uuid4().hex
    record = {
        "schema_version": SCHEMA_VERSION,
        "job_id": job_id,
        "city_input": clean_city,
        "qualified_spend_input": qualified_spend_input,
        "session_id": session_id,
        "status": "running",
        "terminal_reason": None,
        "message": None,
        "rounds": [],
        "sdk_calls": [],
        "started_at": started_at,
        "updated_at": _utc_now_iso(),
        "ceiling_seconds": JOB2_WALL_CLOCK_CEILING_SECONDS,
        "boot_id": boot_id(),
        "round_count": 0,
    }
    save_run(record)

    objective = _round1_objective(clean_city)
    queries = _round1_queries(clean_city)
    mode: Literal["turbo", "fast", "basic", "advanced"] = "fast"
    round_number = 0
    sdk_calls: list[dict] = []

    with collecting(sdk_calls):
        while True:
            round_number += 1

            results = search(
                search_queries=queries,
                objective=objective,
                session_id=session_id,
                mode=mode,
                max_chars_total=JOB2_MAX_CHARS_PER_SEARCH,
                timeout=SEARCH_TIMEOUT_SECONDS,
                round_number=round_number,
            )
            evidence_text = _evidence_text(results)

            verdict = judge(
                city_input=clean_city,
                objective=objective,
                evidence_text=evidence_text,
                round_number=round_number,
            )

            round_record = {
                "round_number": round_number,
                "objective": objective,
                "search_queries": list(queries),
                "mode": mode,
                "results": [{"url": r.get("url"), "title": r.get("title")} for r in results],
                "decision": verdict.decision,
                "findings": [f.model_dump(mode="json") for f in verdict.findings],
                "summary": verdict.summary,
                "unmet_fields": _unmet_field_names(verdict.findings),
                "at": _utc_now_iso(),
            }
            record = append_round(job_id, round_record)
            record["sdk_calls"] = list(sdk_calls)
            record["updated_at"] = _utc_now_iso()

            if on_round is not None:
                on_round(round_record)

            if verdict.decision != "continue":
                record["status"] = "terminal"
                record["terminal_reason"] = verdict.decision
                record["message"] = verdict.summary
                save_run(record)
                return _run_from_record(record)

            save_run(record)
            objective = verdict.next_objective or objective
            queries = verdict.next_queries or queries
            mode = verdict.next_mode
