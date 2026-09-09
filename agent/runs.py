"""JSON persistence for a Job 1 run.

`save_run` writes both the freshest snapshot (`var/job1/latest.json`, used
by `GET /job1` to render without paying for a new SDK call) and one
timestamped-by-id record under `var/job1/{run_id}.json`. `runs/job1/` is a
SEPARATE, committed directory (tracked in git — plan 05-03 Task 3) holding
the one verified live run whose evidence turns AGT-03 green; it is never
written here automatically, only copied in by hand after a human verifies
the run.

`run_id` arrives from a URL path segment (`GET /job1/{run_id}`) and is
therefore untrusted input. `load_run` validates it against a strict
32-hex-character pattern BEFORE building any path — the same
closed-allowlist discipline `app/services/validate.py::reproduce_disclosure`
already applies to `pair_id` (T-05-12: the untrusted string never reaches
`open()`).
"""

from __future__ import annotations

import json
import re
import uuid
from decimal import Decimal
from pathlib import Path

from agent.enactment import EnactmentStatus, EnactmentVerdict
from agent.job1 import ExtractionFailure, Job1Run, TerminalReason
from agent.schema import ExtractedAward
from agent.taxonomy import AccuracySummary, AwardResult, MatchClass, VarianceExplanation
from app.services._paths import REPO_ROOT

__all__ = [
    "COMMITTED_RUNS_DIR",
    "RUNS_DIR",
    "InvalidRunIdError",
    "load_latest",
    "load_run",
    "new_run_id",
    "newest_committed_run",
    "run_to_dict",
    "save_run",
]

RUNS_DIR: Path = REPO_ROOT / "var" / "job1"
COMMITTED_RUNS_DIR: Path = REPO_ROOT / "runs" / "job1"

# T-05-12: `run_id` from a URL path segment must never reach `open()`
# unvalidated. `uuid4().hex` is always exactly 32 lowercase hex characters,
# so this single pattern is both the id format AND the sole membership
# check performed before any path is built.
_RUN_ID_RE = re.compile(r"^[0-9a-f]{32}$")


class InvalidRunIdError(ValueError):
    """Raised by `load_run` when `run_id` does not match the strict
    32-hex-character shape — before any path is built (T-05-12)."""


def new_run_id() -> str:
    """A fresh `run_id`: always exactly 32 lowercase hex characters."""
    return uuid.uuid4().hex


def _award_to_dict(result: AwardResult) -> dict:
    """Serialise one `AwardResult`, including the underlying `ExtractedAward`
    fields so a saved run can be reconstructed exactly. `derivation` is
    already a tuple of plain strings by the time it reaches this dataclass
    (agent.taxonomy) — no `Figure` object exists anywhere in this tree, so
    `engine.figure_serialize.figure_to_dict` has no applicable input here.
    Were a `Figure` ever attached to a future field, that existing
    serialiser — never a second hand-written one — is the only sanctioned
    way to convert it (Pitfall 4: a bare `Decimal`/`date` crashes the
    default JSON encoder)."""
    return {
        "production_title": result.award.production_title,
        "qualified_spend": result.award.qualified_spend,
        "credit_amount": result.award.credit_amount,
        "diversity_credit_amount": result.award.diversity_credit_amount,
        "programme_hint": result.award.programme_hint,
        "source_row_text": result.award.source_row_text,
        "disclosed": str(result.disclosed),
        "computed": str(result.computed) if result.computed is not None else None,
        "match_class": result.match_class.value,
        "explanation": (
            {
                "rule_id": result.explanation.rule_id,
                "reason": result.explanation.reason,
                "source_url": result.explanation.source_url,
                "date_checked": result.explanation.date_checked,
            }
            if result.explanation is not None
            else None
        ),
        "derivation": list(result.derivation),
        "corroborates_committed_fixture": result.corroborates_committed_fixture,
    }


def _award_from_dict(data: dict) -> AwardResult:
    # `.model_validate(...)`, never the bare `ExtractedAward(...)`
    # constructor — the same sanctioned deserialization shape
    # `agent/gemini_client.py` uses for the real Gemini response (D-87's
    # AST gate, tests/test_agent_job1_offline.py, permits this exact call
    # shape at this exact call site: reading back a run this process
    # itself already saved, never fabricating one).
    award = ExtractedAward.model_validate(
        {
            "production_title": data["production_title"],
            "qualified_spend": data["qualified_spend"],
            "credit_amount": data["credit_amount"],
            "diversity_credit_amount": data.get("diversity_credit_amount"),
            "programme_hint": data.get("programme_hint"),
            "source_row_text": data.get("source_row_text", ""),
        }
    )
    explanation_data = data.get("explanation")
    explanation = (
        VarianceExplanation(
            rule_id=explanation_data["rule_id"],
            reason=explanation_data["reason"],
            source_url=explanation_data["source_url"],
            date_checked=explanation_data["date_checked"],
        )
        if explanation_data
        else None
    )
    return AwardResult(
        award=award,
        disclosed=Decimal(data["disclosed"]),
        computed=Decimal(data["computed"]) if data.get("computed") is not None else None,
        match_class=MatchClass(data["match_class"]),
        explanation=explanation,
        derivation=tuple(data.get("derivation", ())),
        corroborates_committed_fixture=bool(data.get("corroborates_committed_fixture", False)),
    )


def _extraction_failure_to_dict(failure: ExtractionFailure) -> dict:
    return {
        "production_title": failure.production_title,
        "raw_value": failure.raw_value,
        "error": failure.error,
    }


def _enactment_to_dict(verdict: EnactmentVerdict) -> dict:
    return {
        "status": verdict.status.value,
        "matched_markers": list(verdict.matched_markers),
        "evidence": list(verdict.evidence),
    }


def _enactment_from_dict(data: dict) -> EnactmentVerdict:
    return EnactmentVerdict(
        status=EnactmentStatus(data["status"]),
        matched_markers=tuple(data.get("matched_markers", ())),
        evidence=tuple(data.get("evidence", ())),
    )


def run_to_dict(run: Job1Run) -> dict:
    """Every `Decimal` via `str(...)`, every enum via `.value`. Never
    includes an environment variable, a key, or a raw document/prompt
    (T-05-14) — `sdk_calls` carries only what `agent.telemetry.sdk_call`
    itself records: sdk/op/target/elapsed_ms/outcome/at."""
    return {
        "run_mode": run.run_mode,
        "terminal_reason": run.terminal_reason.value,
        "message": run.message,
        "search_url": run.search_url,
        "document_sha256": run.document_sha256,
        "document_char_count": run.document_char_count,
        "truncated": run.truncated,
        "gemini_model": run.gemini_model,
        "report_title": run.report_title,
        "report_period": run.report_period,
        "raw_award_count": run.raw_award_count,
        "accuracy": {
            "awards_extracted": run.accuracy.awards_extracted,
            "exact_match": run.accuracy.exact_match,
            "explained_variance": run.accuracy.explained_variance,
            "unexplained": run.accuracy.unexplained,
            "extraction_failures": run.accuracy.extraction_failures,
        },
        "awards": [_award_to_dict(r) for r in run.awards],
        "extraction_failures": [
            _extraction_failure_to_dict(ef) for ef in run.extraction_failures
        ],
        "sdk_calls": [dict(record) for record in run.sdk_calls],
        "source_enactment": (
            _enactment_to_dict(run.source_enactment) if run.source_enactment is not None else None
        ),
    }


def run_from_dict(data: dict) -> Job1Run:
    """Reconstruct a `Job1Run` from `run_to_dict`'s own output — the only
    way a saved run is read back, whether from `var/job1/` or the
    committed `runs/job1/` directory."""
    accuracy_data = data.get("accuracy") or {}
    accuracy = AccuracySummary(
        awards_extracted=accuracy_data.get("awards_extracted", 0),
        exact_match=accuracy_data.get("exact_match", 0),
        explained_variance=accuracy_data.get("explained_variance", 0),
        unexplained=accuracy_data.get("unexplained", 0),
        extraction_failures=accuracy_data.get("extraction_failures", 0),
    )
    awards = tuple(_award_from_dict(a) for a in data.get("awards", []))
    extraction_failures = tuple(
        ExtractionFailure(
            production_title=ef["production_title"],
            raw_value=ef["raw_value"],
            error=ef["error"],
        )
        for ef in data.get("extraction_failures", [])
    )
    # A run persisted before this change (AGT-08's enactment guardrail,
    # D-97, plan 05-07) has no "source_enactment" key at all —
    # `data.get(...)` returns None for it, and this loads that pre-existing
    # run with a null verdict rather than raising.
    enactment_data = data.get("source_enactment")
    source_enactment = _enactment_from_dict(enactment_data) if enactment_data else None
    return Job1Run(
        run_mode=data["run_mode"],
        terminal_reason=TerminalReason(data["terminal_reason"]),
        message=data.get("message"),
        search_url=data.get("search_url"),
        document_sha256=data.get("document_sha256"),
        document_char_count=data.get("document_char_count"),
        truncated=data.get("truncated", False),
        gemini_model=data.get("gemini_model"),
        report_title=data.get("report_title"),
        report_period=data.get("report_period"),
        raw_award_count=data.get("raw_award_count", 0),
        awards=awards,
        extraction_failures=extraction_failures,
        accuracy=accuracy,
        sdk_calls=tuple(data.get("sdk_calls", [])),
        source_enactment=source_enactment,
    )


def save_run(run: Job1Run, run_id: str | None = None) -> str:
    """Persist `run` under `var/job1/{run_id}.json` and rewrite
    `var/job1/latest.json` with the same payload. Returns the `run_id`
    used (minted fresh via `new_run_id()` when not supplied)."""
    run_id = run_id or new_run_id()
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    payload = run_to_dict(run)
    payload["run_id"] = run_id
    serialised = json.dumps(payload, indent=2)

    (RUNS_DIR / f"{run_id}.json").write_text(serialised, encoding="utf-8")
    (RUNS_DIR / "latest.json").write_text(serialised, encoding="utf-8")
    return run_id


def load_run(run_id: str) -> Job1Run | None:
    """Load a persisted run by id, or None if none exists with that id.

    Raises `InvalidRunIdError` if `run_id` is not exactly 32 lowercase hex
    characters — checked BEFORE any path is built (T-05-12)."""
    if not _RUN_ID_RE.match(run_id):
        raise InvalidRunIdError(run_id)

    run_path = RUNS_DIR / f"{run_id}.json"
    if not run_path.is_file():
        return None
    return run_from_dict(json.loads(run_path.read_text(encoding="utf-8")))


def load_latest() -> Job1Run | None:
    """Load the most recently saved run in `var/job1/`, if any."""
    latest_path = RUNS_DIR / "latest.json"
    if not latest_path.is_file():
        return None
    return run_from_dict(json.loads(latest_path.read_text(encoding="utf-8")))


def newest_committed_run() -> Job1Run | None:
    """Load the newest committed run artifact under `runs/job1/`, if any —
    the fallback `GET /job1` uses when no fresher `var/job1/latest.json`
    exists yet (e.g. immediately after a fresh deploy)."""
    if not COMMITTED_RUNS_DIR.is_dir():
        return None
    candidates = sorted(COMMITTED_RUNS_DIR.glob("*.json"))
    if not candidates:
        return None
    return run_from_dict(json.loads(candidates[-1].read_text(encoding="utf-8")))
