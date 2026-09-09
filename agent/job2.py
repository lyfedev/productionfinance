"""Job 2: research an uncurated jurisdiction through a genuine agent loop.

D-90: this is deliberately NOT `agent/job1.py`'s fixed sequence. The driver
below is a `while True:` loop whose exit is decided entirely by the model's
own `decision` value (`SufficiencyVerdict.decision`, D-91) — no integer
bounds how many rounds it may run, and no round counter is ever compared
against a constant. `JOB2_WALL_CLOCK_CEILING_SECONDS` is a monotonic
wall-clock BACKSTOP checked between rounds (never mid-SDK-call, never by
comparing a round counter to an integer) — a resource bound on total run
length, not a bound on how many rounds the agent may take. Its own terminal
reason (`TerminalReason.budget_exhausted`) stays structurally distinct from
the agent's own `TerminalReason.agent_gave_up` so a reader can always tell
which one happened.

Each round: issue a Parallel Search under the run's one `session_id` (the
07-SDK-FINDINGS spine — this is what makes round N+1 contextually aware of
rounds 1..N), build the round's evidence text from the results, call
`google-genai` for a `SufficiencyVerdict` against D-91's five named fields,
persist the round to disk via `agent.research_runs.append_round` BEFORE the
next round starts (D-92), then branch on `verdict.decision`: `sufficient`,
`give_up` and `no_programme_found` each exit with a terminal reason from the
closed `TerminalReason` taxonomy; `continue` carries the refined
objective/queries/mode into the next round. Refinement is expressed through
a restated `objective` (`build_refined_objective`), never by editing the
previous round's query strings — 07-SDK-FINDINGS is explicit that
`search_queries` stay short keyword sets and `objective` carries the intent.

Findings accumulate across rounds via `merge_findings`: a field determined
once stays determined, and a later unsourced value can never overwrite a
sourced one (D-94's monotonic-merge discipline applied to the sufficiency
judgment itself). A `\"sufficient\"` claim that the merged findings do not
actually support is rejected as `TerminalReason.contradictory_verdict`
rather than believed. `no_programme_found` and every other non-`sufficient`
terminal state construct nothing and price nothing — `ruleset_path` and
`priced` are forced to `None` on every terminal write in this module.

`import parallel` and `from google import genai` are INSIDE the functions
that call them, never at module top level (lazy import — the 472 MB
production box depends on this; a test enforces it).

`search_fn`/`judge_fn` are injectable seams (each defaulting to `None`,
resolved to the real client function), exactly the way `agent/job1.py`
takes `search_fn`/`extract_fn` — a test double is never a default.
"""

from __future__ import annotations

import time
import unicodedata
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from pydantic import ValidationError

from agent.numbers import UnparseableFigureError, parse_money
from agent.research_runs import SCHEMA_VERSION, append_round, boot_id, save_run
from agent.research_schema import (
    FieldFinding,
    JurisdictionIdentity,
    SufficiencyField,
    SufficiencyVerdict,
    research_response_schema,
)
from agent.rule_coercion import (
    RuleCoercionError,
    build_rule_document,
    cited_source_urls,
    neutral_default_disclosures,
    serialize_priced_jurisdiction,
    write_rule_file,
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
from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction

__all__ = [
    "InvalidCityInputError",
    "ResearchRun",
    "TerminalReason",
    "build_refined_objective",
    "merge_findings",
    "normalize_mode",
    "normalize_queries",
    "run_job2",
    "unmet_fields",
    "validate_city_input",
]

_ALL_FIELDS: tuple[SufficiencyField, ...] = tuple(SufficiencyField)
_MAX_CITY_INPUT_CHARS = 120
_VALID_MODES: tuple[str, ...] = ("turbo", "fast", "basic", "advanced")
_IDENTITY_FIELD_NAMES: tuple[str, ...] = (
    "jurisdiction_name",
    "country_code",
    "level",
    "currency",
)

SearchFn = Callable[..., Sequence[dict]]
JudgeFn = Callable[..., SufficiencyVerdict]


class TerminalReason(str, Enum):
    """The closed set of terminal states `run_job2` can reach. Distinct
    from `SufficiencyVerdict.decision` (D-90's four literals: `continue`,
    `sufficient`, `give_up`, `no_programme_found`) because a terminal state
    also has to capture failures the model's own decision cannot express: a
    self-contradicting claim, a missing jurisdiction identity, an exhausted
    wall-clock budget, a cache-boundary policy violation, missing
    configuration, or an SDK-level failure. Plan 07-05 adds two more —
    `pricing_refused` (the engine's own refusal to convert to net cash,
    e.g. a transferable programme with no sourced discount range) and
    `rule_schema_violation` (the coerced document failed schema
    validation, or the visitor's qualified-spend string could not be
    parsed) — both additions to this closed set, never replacements.
    Eleven members total — adding a twelfth later is cheap; renaming one
    is not (this vocabulary is rendered by the UI and quoted in the
    written submission)."""

    sufficient = "sufficient"
    agent_gave_up = "agent_gave_up"
    no_programme_found = "no_programme_found"
    insufficient_identity = "insufficient_identity"
    budget_exhausted = "budget_exhausted"
    contradictory_verdict = "contradictory_verdict"
    cache_boundary_violation = "cache_boundary_violation"
    not_configured = "not_configured"
    sdk_error = "sdk_error"
    pricing_refused = "pricing_refused"
    rule_schema_violation = "rule_schema_violation"


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
    """The in-process return value mirroring the on-disk record."""

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
    findings = record.get("findings")
    disclosures = record.get("undetermined_disclosures")
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
        findings=tuple(findings) if findings is not None else None,
        undetermined_disclosures=tuple(disclosures) if disclosures is not None else None,
        ruleset_path=record.get("ruleset_path"),
        priced=record.get("priced"),
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


def _empty_findings() -> dict[SufficiencyField, FieldFinding]:
    return {f: FieldFinding(field=f, determined=False) for f in _ALL_FIELDS}


# ---------------------------------------------------------------------------
# Pure functions (Task 1): free of any SDK call, directly unit-testable.
# ---------------------------------------------------------------------------


def merge_findings(
    previous: dict[SufficiencyField, FieldFinding],
    incoming: Sequence[FieldFinding],
) -> tuple[dict[SufficiencyField, FieldFinding], list[SufficiencyField]]:
    """Fold `incoming` (one round's raw findings) into `previous` (the
    accumulated state across all prior rounds). Returns the new merged
    mapping — always keyed by all five `SufficiencyField` members — and the
    list of fields where an unsourced later value was discarded rather than
    applied.

    `determined` never flips True -> False (D-90/D-94's monotonic-merge
    rule). A field already determined only accepts a later overwrite when
    the later finding is itself `determined` AND carries a non-empty
    `source_url`; anything else touching an already-determined field is
    discarded and reported, never silently dropped.
    """
    merged: dict[SufficiencyField, FieldFinding] = {
        f: previous.get(f) or FieldFinding(field=f, determined=False) for f in _ALL_FIELDS
    }

    discarded: list[SufficiencyField] = []
    for finding in incoming:
        current = merged[finding.field]
        if not current.determined:
            merged[finding.field] = finding
            continue
        if finding.determined and finding.source_url:
            merged[finding.field] = finding
        else:
            discarded.append(finding.field)

    return merged, discarded


def unmet_fields(merged: dict[SufficiencyField, FieldFinding]) -> list[SufficiencyField]:
    """The `SufficiencyField` members still undetermined, in the enum's own
    declaration order — a stable, readable list."""
    return [
        f
        for f in _ALL_FIELDS
        if not merged.get(f, FieldFinding(field=f, determined=False)).determined
    ]


def build_refined_objective(city_input: str, merged: dict[SufficiencyField, FieldFinding]) -> str:
    """A self-contained sentence naming the city and every field still
    unmet — the fallback used only when the model's own `next_objective`
    was empty. Takes no query text as input, so it can never reproduce a
    substring of a previous round's `search_queries` (07-SDK-FINDINGS:
    refinement is a restated objective, never a mutated query string)."""
    unmet = unmet_fields(merged)
    if not unmet:
        return (
            f"Confirm the film/TV production incentive programme for {city_input} is "
            "fully determined; no additional research is required."
        )
    names = ", ".join(f.value.replace("_", " ") for f in unmet)
    return (
        f"Continue researching the film/TV production incentive programme for "
        f"{city_input}. Still undetermined: {names}. Find sourced evidence for each "
        "of these before concluding the research is sufficient."
    )


def normalize_queries(raw: Sequence[str] | None) -> tuple[list[str], bool]:
    """Keep at most the first three queries, truncate each to its first six
    words, drop empties, and report whether normalization changed anything.
    Never adds a word the model did not produce."""
    raw_list = list(raw or [])
    changed = len(raw_list) > 3
    kept: list[str] = []
    for query in raw_list[:3]:
        words = query.split()
        cleaned = " ".join(words[:6]).strip()
        if not cleaned:
            changed = True
            continue
        if cleaned != query:
            changed = True
        kept.append(cleaned)
    return kept, changed


def normalize_mode(raw: str | None) -> tuple[str, bool]:
    """Return `raw` unchanged when it is one of the four closed literals,
    else fall back to `\"fast\"` and report the substitution."""
    if raw in _VALID_MODES:
        return raw, False
    return "fast", True


def _missing_identity_fields(identity: JurisdictionIdentity | None) -> list[str]:
    if identity is None:
        return list(_IDENTITY_FIELD_NAMES)
    missing = [name for name in _IDENTITY_FIELD_NAMES if not getattr(identity, name)]
    return missing


def _terminal_for_decision(
    verdict: SufficiencyVerdict,
    merged: dict[SufficiencyField, FieldFinding],
    unmet: list[SufficiencyField],
    identity: JurisdictionIdentity | None,
) -> tuple[TerminalReason, str] | None:
    """Decide the terminal reason for a non-`continue` verdict, cross-checking
    the verdict's own claim against the accumulated findings (D-94's
    discipline applied to the sufficiency judgment itself). Returns `None`
    when the loop should keep running."""
    if verdict.decision == "continue":
        return None

    if verdict.decision == "sufficient":
        if unmet:
            names = ", ".join(f.value.replace("_", " ") for f in unmet)
            message = (
                "The agent reported sufficient evidence, but its own findings "
                f"leave {names} undetermined."
            )
            return (TerminalReason.contradictory_verdict, message)
        missing_identity = _missing_identity_fields(identity)
        if missing_identity:
            names = ", ".join(missing_identity)
            message = (
                "All five sufficiency fields were determined, but the "
                f"jurisdiction identity could not be established: {names}."
            )
            return (TerminalReason.insufficient_identity, message)
        return (TerminalReason.sufficient, verdict.summary)

    if verdict.decision == "give_up":
        names = ", ".join(f.value.replace("_", " ") for f in unmet) or "nothing further"
        message = (
            f"The agent decided further research is unlikely to help. Still undetermined: {names}."
        )
        return (TerminalReason.agent_gave_up, message)

    if verdict.decision == "no_programme_found":
        return (TerminalReason.no_programme_found, verdict.summary)

    raise AssertionError(f"unreachable SufficiencyVerdict.decision: {verdict.decision!r}")


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


def _judge_prompt(city_input: str, objective: str, evidence_text: str) -> str:
    return f"""You are judging whether the search results below are enough to build
a film/TV production incentive cost model for {city_input}. The sufficiency
contract has exactly five fields: {_field_prose()}.

Objective this round: {objective}

For each of the five fields, report whether it was determined from the
evidence below: the value (verbatim where possible), a short evidence
quote, and the source URL. If you can also determine the jurisdiction's
identity (name, ISO country code, level — national/state/provincial/city —
and currency), report that too; it is required in addition to the five
fields, not instead of any of them. Then decide:
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


# ---------------------------------------------------------------------------
# Plan 07-05: findings -> a rule document -> the curated loader -> the
# curated pricing call (AGT-07), only ever attempted on the `sufficient`
# path. `agent/rule_coercion.py` never imports engine/ at all; the two
# sanctioned names (`load_ruleset`, `price_jurisdiction`) are called HERE,
# the one place this plan's AST gate already covers.
# ---------------------------------------------------------------------------

_EFFECTIVE_DATE_CONFIRMATION_DISCLOSURE = (
    "The rule model's effective-from date is set to today, the date the programme's "
    "current availability was confirmed in force by this research — not the date the "
    "programme's rules originally took effect, which was not separately determined."
)

_NO_SPEND_SUPPLIED_DISCLOSURE = (
    "No qualified spend was supplied for this run, so the rule model was built and "
    "loaded but not priced against a dollar figure."
)


def _attempt_coercion_and_pricing(
    job_id: str,
    qualified_spend_input: str | None,
    merged: dict[SufficiencyField, FieldFinding],
    identity: JurisdictionIdentity,
    original_message: str,
) -> tuple[TerminalReason, str, str | None, dict | None, list[str]]:
    """Only called once the driver has already accepted a `sufficient`
    verdict (D-91's five fields determined, identity complete). Returns
    `(reason, message, ruleset_path, priced, extra_disclosures)`.

    `reason` stays `TerminalReason.sufficient` unless one of Task 2's
    three named refusals fires, in which case it becomes
    `rule_schema_violation` (a schema violation, or an unparseable
    non-empty qualified-spend string) or `pricing_refused` (the engine's
    own refusal to convert to net cash — e.g. `engine.net_cash
    .transferable` with no sourced discount range). Never raises: every
    refusal this function can name is caught here so the caller can
    always write a durable terminal record without a background-thread
    crash (T-07-01)."""
    disclosures = neutral_default_disclosures(merged) + [_EFFECTIVE_DATE_CONFIRMATION_DISCLOSURE]

    sources = cited_source_urls(merged)
    try:
        document = build_rule_document(job_id, identity, merged, sources)
    except RuleCoercionError as exc:
        # RuleCoercionError's UnslugableIdentityError subclass (a
        # researched name that cannot be turned into a usable id) is
        # caught by this same clause — both are "the document could not
        # be built without inventing a value", the substance
        # rule_schema_violation exists to name.
        return TerminalReason.rule_schema_violation, str(exc), None, None, []

    try:
        path = write_rule_file(job_id, document)
    except RuleCoercionError as exc:
        return TerminalReason.rule_schema_violation, str(exc), None, None, []

    try:
        ruleset = load_ruleset(path)
    except ValidationError as exc:
        return (
            TerminalReason.rule_schema_violation,
            f"the coerced rule document failed schema validation: {exc}",
            None,
            None,
            [],
        )

    if not qualified_spend_input or not qualified_spend_input.strip():
        return (
            TerminalReason.sufficient,
            original_message,
            str(path),
            None,
            [*disclosures, _NO_SPEND_SUPPLIED_DISCLOSURE],
        )

    try:
        spend_value = parse_money(qualified_spend_input)
    except UnparseableFigureError as exc:
        return (
            TerminalReason.rule_schema_violation,
            f"the qualified spend {qualified_spend_input!r} could not be parsed: {exc}",
            str(path),
            None,
            disclosures,
        )

    try:
        priced = price_jurisdiction(ruleset, spend_value, spend_confidence="researched")
    except ValueError as exc:
        return TerminalReason.pricing_refused, str(exc), str(path), None, disclosures

    return (
        TerminalReason.sufficient,
        original_message,
        str(path),
        serialize_priced_jurisdiction(priced),
        disclosures,
    )


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

    def _terminal_record(reason: TerminalReason, message: str) -> dict:
        record = {
            "schema_version": SCHEMA_VERSION,
            "job_id": job_id,
            "city_input": city_input,
            "qualified_spend_input": qualified_spend_input,
            "session_id": None,
            "status": "terminal",
            "terminal_reason": reason.value,
            "message": message,
            "rounds": [],
            "sdk_calls": [],
            "started_at": started_at,
            "updated_at": _utc_now_iso(),
            "ceiling_seconds": JOB2_WALL_CLOCK_CEILING_SECONDS,
            "boot_id": boot_id(),
            "round_count": 0,
            "findings": None,
            "undetermined_disclosures": None,
            "ruleset_path": None,
            "priced": None,
        }
        save_run(record)
        return record

    if using_real_seams:
        status = integration_status()
        if not status.parallel_configured or not status.gemini_configured:
            return _run_from_record(
                _terminal_record(TerminalReason.not_configured, status.not_configured_message())
            )

    try:
        clean_city = validate_city_input(city_input)
    except InvalidCityInputError as exc:
        # Not part of the closed TerminalReason taxonomy (D-90's agent loop
        # never starts on this path) — a fast, pre-loop input rejection.
        term_record = {
            "schema_version": SCHEMA_VERSION,
            "job_id": job_id,
            "city_input": city_input,
            "qualified_spend_input": qualified_spend_input,
            "session_id": None,
            "status": "terminal",
            "terminal_reason": "invalid_input",
            "message": str(exc),
            "rounds": [],
            "sdk_calls": [],
            "started_at": started_at,
            "updated_at": _utc_now_iso(),
            "ceiling_seconds": JOB2_WALL_CLOCK_CEILING_SECONDS,
            "boot_id": boot_id(),
            "round_count": 0,
            "findings": None,
            "undetermined_disclosures": None,
            "ruleset_path": None,
            "priced": None,
        }
        save_run(term_record)
        return _run_from_record(term_record)

    # D-89/AGT-10, made structural: the live research path must not read
    # from cache. This is asserted BEFORE the first Search call — a
    # `CacheBoundaryViolation` here means no Search ever fires.
    try:
        assert_live(DataClass.uncurated_city_research)
    except CacheBoundaryViolation as exc:
        return _run_from_record(_terminal_record(TerminalReason.cache_boundary_violation, str(exc)))

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
        "findings": None,
        "undetermined_disclosures": None,
        "ruleset_path": None,
        "priced": None,
    }
    save_run(record)

    def _write_terminal(
        reason: TerminalReason,
        message: str,
        merged: dict[SufficiencyField, FieldFinding],
        identity: JurisdictionIdentity | None,
        *,
        ruleset_path: str | None = None,
        priced: dict | None = None,
        extra_disclosures: Sequence[str] = (),
    ) -> ResearchRun:
        unmet = unmet_fields(merged)
        record["status"] = "terminal"
        record["terminal_reason"] = reason.value
        record["message"] = message
        record["findings"] = [v.model_dump(mode="json") for v in merged.values()]
        disclosures = [f.value.replace("_", " ") for f in unmet]
        disclosures.extend(extra_disclosures)
        record["undetermined_disclosures"] = disclosures
        record["ruleset_path"] = ruleset_path
        record["priced"] = priced
        if identity is not None:
            record["identity"] = identity.model_dump(mode="json")
        record["updated_at"] = _utc_now_iso()
        save_run(record)
        return _run_from_record(record)

    objective = _round1_objective(clean_city)
    queries = _round1_queries(clean_city)
    queries_normalized = False
    mode: str = "fast"
    mode_normalized = False
    round_number = 0
    sdk_calls: list[dict] = []
    merged = _empty_findings()
    identity: JurisdictionIdentity | None = None

    with collecting(sdk_calls):
        loop_started_at = time.monotonic()
        while True:
            round_number += 1

            try:
                results = search(
                    search_queries=queries,
                    objective=objective,
                    session_id=session_id,
                    mode=mode,
                    max_chars_total=JOB2_MAX_CHARS_PER_SEARCH,
                    timeout=SEARCH_TIMEOUT_SECONDS,
                    round_number=round_number,
                )
            except Exception as exc:  # noqa: BLE001 — any SDK-level failure is a terminal state
                return _write_terminal(TerminalReason.sdk_error, str(exc), merged, identity)

            evidence_text = _evidence_text(results)

            try:
                verdict = judge(
                    city_input=clean_city,
                    objective=objective,
                    evidence_text=evidence_text,
                    round_number=round_number,
                )
            except Exception as exc:  # noqa: BLE001 — any SDK-level failure is a terminal state
                return _write_terminal(TerminalReason.sdk_error, str(exc), merged, identity)

            before_determined = {f for f, v in merged.items() if v.determined}
            merged, discarded = merge_findings(merged, verdict.findings)
            newly_determined = [
                f.value for f in _ALL_FIELDS if merged[f].determined and f not in before_determined
            ]
            unmet = unmet_fields(merged)
            identity = verdict.identity or identity

            round_record = {
                "round_number": round_number,
                "objective": objective,
                "search_queries": list(queries),
                "queries_normalized": queries_normalized,
                "mode": mode,
                "mode_normalized": mode_normalized,
                "results": [{"url": r.get("url"), "title": r.get("title")} for r in results],
                "decision": verdict.decision,
                "findings": [f.model_dump(mode="json") for f in verdict.findings],
                "summary": verdict.summary,
                "newly_determined": newly_determined,
                "unmet_fields": [f.value for f in unmet],
                "discarded_fields": [f.value for f in discarded],
                "at": _utc_now_iso(),
            }
            record = append_round(job_id, round_record)
            record["sdk_calls"] = list(sdk_calls)
            record["updated_at"] = _utc_now_iso()

            if on_round is not None:
                on_round(round_record)

            terminal = _terminal_for_decision(verdict, merged, unmet, identity)
            if terminal is not None:
                reason, message = terminal
                if reason == TerminalReason.sufficient:
                    assert identity is not None  # guaranteed by _terminal_for_decision
                    try:
                        (
                            reason,
                            message,
                            ruleset_path,
                            priced,
                            extra_disclosures,
                        ) = _attempt_coercion_and_pricing(
                            job_id, qualified_spend_input, merged, identity, message
                        )
                    except Exception as exc:  # noqa: BLE001 — an unexpected coercion bug
                        # must still durably terminate, never crash the background
                        # thread (T-07-01/T-07-34).
                        reason = TerminalReason.rule_schema_violation
                        message = (
                            f"unexpected error while pricing the researched jurisdiction: {exc}"
                        )
                        ruleset_path, priced, extra_disclosures = None, None, []
                    return _write_terminal(
                        reason,
                        message,
                        merged,
                        identity,
                        ruleset_path=ruleset_path,
                        priced=priced,
                        extra_disclosures=extra_disclosures,
                    )
                return _write_terminal(reason, message, merged, identity)

            save_run(record)

            # The wall-clock BACKSTOP, checked here — between rounds, never
            # mid-SDK-call, and never by comparing `round_number` to
            # anything. This is a resource bound distinct from the agent's
            # own decision (D-90); it fires only when the agent would
            # otherwise start another round.
            elapsed = time.monotonic() - loop_started_at
            if elapsed > JOB2_WALL_CLOCK_CEILING_SECONDS:
                return _write_terminal(
                    TerminalReason.budget_exhausted,
                    "Research exceeded the "
                    f"{JOB2_WALL_CLOCK_CEILING_SECONDS}-second wall-clock research "
                    "ceiling before the agent reached its own decision.",
                    merged,
                    identity,
                )

            next_queries, queries_normalized = normalize_queries(verdict.next_queries)
            queries = next_queries or list(queries)
            mode, mode_normalized = normalize_mode(verdict.next_mode)
            objective = verdict.next_objective or build_refined_objective(clean_city, merged)
