"""Job 1: reproduce New York government disclosure pairs end to end.

`run_job1` executes the fixed D-82 sequence with no substitutions and no
branch that skips a stage: status check -> Search -> primary-domain filter
-> Extract -> Gemini -> price EVERY extracted award through the existing
engine with `spend_confidence="researched"` (D-63 / PRV-02 — a figure an
LLM read out of a document has not been transcribed and checked by a human,
so it is never `validated`) -> classify each disclosed-vs-computed pair
through the D-86 three-value taxonomy (`agent.taxonomy`).

Nothing in this module invents, defaults, or backfills an award (D-87): if
Search returns no primary-domain result, Extract returns nothing usable, or
Gemini returns zero awards, the run reports that plainly through a closed
`TerminalReason` enum with an empty award list. An award whose money fields
do not parse (`agent.numbers.parse_money`, D-88) is recorded as an
`ExtractionFailure` carrying the raw string and the exception text — it is
neither dropped silently nor guessed at.

`search_fn`, `extract_fn` and `extract_awards_fn` are injectable seams
(each defaulting to `None`, resolved to the real client function) so an
offline test can drive the whole extract-price-classify loop against a
committed fixture with zero network access (plan 05-02 Task 3) without ever
making a test double the default. `run_mode` on the returned `Job1Run` is
`"live"` only when none of those three seams were overridden AND both
integrations were configured — a run driven by any injected fake is always
`"replay"` and must never be rendered as a product accuracy figure
(T-05-10).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Literal

import yaml

from agent.enactment import EnactmentVerdict, classify_enactment
from agent.gemini_client import ExtractionResult, extract_awards
from agent.groundedness import check_grounded
from agent.numbers import UnparseableFigureError, parse_money
from agent.parallel_client import (
    DisclosureDocument,
    extract_document,
    search_for_disclosure_candidates,
)
from agent.schema import ExtractedAward
from agent.settings import integration_status
from agent.taxonomy import (
    AccuracySummary,
    AwardResult,
    VarianceRule,
    classify,
    load_variance_rules,
    summarize,
)
from agent.telemetry import collecting
from app.services._paths import REPO_ROOT
from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction

# `JurisdictionRuleSet` (the return type of `load_ruleset`, and the type of
# `_price_and_classify_award`'s `ruleset` parameter below) is deliberately
# NOT imported here — D-85's gate is that `agent/` imports nothing from
# `engine/` except `load_ruleset` and `price_jurisdiction` themselves, so
# the parameter below is left unannotated rather than adding a third
# engine import purely for a type hint.

__all__ = [
    "ExtractionFailure",
    "Job1Run",
    "TerminalReason",
    "run_job1",
]

_JURISDICTION_ID = "us-ny"
_RULESET_PATH = REPO_ROOT / "jurisdictions" / f"{_JURISDICTION_ID}.yaml"
_PROGRAMME_ID = "ny-film-production-tax-credit"
_VARIANCE_RULES_PATH = REPO_ROOT / "agent" / "variance_rules.yaml"
_VALIDATION_PAIRS_DIR = REPO_ROOT / "tests" / "fixtures" / "validation_pairs"

_EMPTY_ACCURACY = AccuracySummary(
    awards_extracted=0, exact_match=0, explained_variance=0, unexplained=0, extraction_failures=0
)

SearchFn = Callable[[], str | None]
ExtractFn = Callable[[str], DisclosureDocument | None]
ExtractAwardsFn = Callable[[str], ExtractionResult]


class TerminalReason(str, Enum):
    """A closed set — every non-`ok` value returns a `Job1Run` with an
    empty award-result list and a readable `message` (D-87). No branch
    anywhere in `agent/` constructs an extracted-award object to fill a
    gap when one of these is returned; the only place an `ExtractedAward`
    is ever built is the Pydantic parse of the real Gemini response
    (`agent.schema.ExtractedAwardSet.model_validate_json`)."""

    ok = "ok"
    not_configured = "not_configured"
    no_primary_source_found = "no_primary_source_found"
    document_extract_failed = "document_extract_failed"
    zero_awards_extracted = "zero_awards_extracted"
    sdk_error = "sdk_error"


@dataclass(frozen=True)
class ExtractionFailure:
    """One extracted award whose money fields did not parse, or that the
    engine could not price (D-88). Carries the raw string(s) and the
    exception text — never dropped silently, never guessed at."""

    production_title: str
    raw_value: str
    error: str


@dataclass(frozen=True)
class Job1Run:
    run_mode: Literal["live", "replay"]
    terminal_reason: TerminalReason
    message: str | None = None
    search_url: str | None = None
    document_sha256: str | None = None
    document_char_count: int | None = None
    truncated: bool = False
    gemini_model: str | None = None
    report_title: str | None = None
    report_period: str | None = None
    raw_award_count: int = 0
    awards: tuple[AwardResult, ...] = field(default_factory=tuple)
    extraction_failures: tuple[ExtractionFailure, ...] = field(default_factory=tuple)
    accuracy: AccuracySummary = _EMPTY_ACCURACY
    # The D-84 evidence block (plan 05-03): the exact same records the
    # PRODFIN_SDK_CALL log lines report, captured via
    # `agent.telemetry.collecting` — never a second, independently-produced
    # claim. Empty for a replay run driven entirely by injected fakes.
    sdk_calls: tuple[dict, ...] = field(default_factory=tuple)
    # AGT-08's enactment guardrail (D-97, plan 05-07): a defaulted field so
    # every existing construction of Job1Run keeps working unchanged.
    # Populated as soon as Extract returns a usable document — a property
    # of the SOURCE DOCUMENT, not of any individual award, so it is never
    # gated by `run_mode` the way `awards`/`accuracy` are (T-05-15's rule
    # protects PRICED FIGURES from a replay run, not this classification).
    source_enactment: EnactmentVerdict | None = None

    @property
    def ran_live(self) -> bool:
        """Backward-compatible alias: True whenever the run actually
        reached Search (i.e. was not short-circuited by a missing key)."""
        return self.terminal_reason != TerminalReason.not_configured


def _parse_award_figures(
    award: ExtractedAward,
) -> tuple[Decimal, Decimal, Decimal | None]:
    """Parse an award's money fields via `parse_money`. Raises
    `UnparseableFigureError` naming every field that failed (not just the
    first) if any field is ambiguous."""
    errors: list[str] = []
    qualified_spend: Decimal | None = None
    disclosed_credit: Decimal | None = None
    diversity_credit: Decimal | None = None

    try:
        qualified_spend = parse_money(award.qualified_spend)
    except UnparseableFigureError as exc:
        errors.append(f"qualified_spend={award.qualified_spend!r}: {exc}")

    try:
        disclosed_credit = parse_money(award.credit_amount)
    except UnparseableFigureError as exc:
        errors.append(f"credit_amount={award.credit_amount!r}: {exc}")

    if award.diversity_credit_amount is not None:
        try:
            diversity_credit = parse_money(award.diversity_credit_amount)
        except UnparseableFigureError as exc:
            errors.append(f"diversity_credit_amount={award.diversity_credit_amount!r}: {exc}")

    if errors:
        raise UnparseableFigureError("; ".join(errors))

    assert qualified_spend is not None
    assert disclosed_credit is not None
    return qualified_spend, disclosed_credit, diversity_credit


def _load_committed_fixtures() -> tuple[dict, ...]:
    """Every committed `tests/fixtures/validation_pairs/*.yaml` fixture, for
    the `corroborates_committed_fixture` bonus check below. Not a gate — an
    extracted pair remains `spend_confidence="researched"` regardless of
    whether it happens to agree with a human-transcribed fixture (PRV-02)."""
    fixtures: list[dict] = []
    for path in sorted(_VALIDATION_PAIRS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        if isinstance(data, dict):
            fixtures.append(data)
    return tuple(fixtures)


def _corroborates_committed_fixture(
    production_title: str, qualified_spend: Decimal, disclosed_credit: Decimal
) -> bool:
    """True only when the extracted title and BOTH extracted figures match
    a committed validation-pair fixture exactly — a bonus proof for the
    demo, never a gate, and never a promotion to `validated`."""
    for fixture in _load_committed_fixtures():
        if fixture.get("production_title") != production_title:
            continue
        try:
            fixture_spend = Decimal(str(fixture.get("qualified_spend")))
            fixture_credit = Decimal(str(fixture.get("credit_amount")))
        except (InvalidOperation, TypeError):
            continue
        if fixture_spend == qualified_spend and fixture_credit == disclosed_credit:
            return True
    return False


def _price_and_classify_award(
    award: ExtractedAward,
    ruleset,  # engine.models.JurisdictionRuleSet — unannotated, see D-85 note above
    rules: Sequence[VarianceRule],
    *,
    document_text: str,
) -> AwardResult | ExtractionFailure:
    """Parse and price one extracted award through the existing engine
    (D-85: the same `price_jurisdiction` entry point
    `app/services/validate.py` already uses for a committed fixture), then
    classify the disclosed-vs-computed comparison through the D-86
    taxonomy. Returns an `ExtractionFailure` — never a fabricated figure
    (D-87) — when the award's money fields do not parse or the engine
    cannot price it.

    `document_text` is keyword-only with no default (AGT-08's groundedness
    guardrail, D-97): every caller must supply the extracted document's own
    text so the award's `source_row_text` and reported money figures can be
    checked against it BEFORE anything is parsed or priced. An ungrounded
    award becomes an `ExtractionFailure` naming the guardrail — it is never
    priced, never dropped silently, and never replaced by a fabricated
    substitute (D-87)."""
    verdict = check_grounded(
        award.source_row_text,
        document_text,
        (award.qualified_spend, award.credit_amount, award.diversity_credit_amount or ""),
    )
    if not verdict.grounded:
        return ExtractionFailure(
            production_title=award.production_title,
            raw_value=verdict.quote_prefix,
            error=f"groundedness guardrail: {verdict.reason}",
        )

    try:
        qualified_spend, disclosed_credit, _diversity_credit = _parse_award_figures(award)
    except UnparseableFigureError as exc:
        return ExtractionFailure(
            production_title=award.production_title,
            raw_value=(
                f"qualified_spend={award.qualified_spend!r} "
                f"credit_amount={award.credit_amount!r}"
            ),
            error=str(exc),
        )

    priced = price_jurisdiction(ruleset, qualified_spend, spend_confidence="researched")
    programme = next(
        (p for p in priced.programmes if p.programme_id == _PROGRAMME_ID),
        None,
    )
    if programme is None:
        return ExtractionFailure(
            production_title=award.production_title,
            raw_value=award.source_row_text,
            error=f"no priced programme {_PROGRAMME_ID!r} in ruleset {_RULESET_PATH}",
        )

    computed = programme.gross_credit.value
    match_class, explanation = classify(disclosed_credit, computed, award, rules)
    corroborates = _corroborates_committed_fixture(
        award.production_title, qualified_spend, disclosed_credit
    )

    return AwardResult(
        award=award,
        disclosed=disclosed_credit,
        computed=computed,
        match_class=match_class,
        explanation=explanation,
        derivation=programme.gross_credit.derivation,
        corroborates_committed_fixture=corroborates,
    )


_MAX_DISCLOSURE_CANDIDATES = 3


def _disclosure_candidates(search: object) -> tuple[str, ...]:
    """Normalize a search seam's return into a candidate tuple.

    `search_for_disclosure_candidates` returns a tuple; the older
    single-URL seam (and every injected test fake) returns one URL or None.
    Both shapes are accepted so existing fakes keep working unchanged.
    """
    result = search()  # type: ignore[operator]
    if result is None:
        return ()
    if isinstance(result, str):
        return (result,)
    return tuple(result)


def run_job1(
    limit: int | None = None,
    *,
    search_fn: SearchFn | None = None,
    extract_fn: ExtractFn | None = None,
    extract_awards_fn: ExtractAwardsFn | None = None,
    on_stage: Callable[[str], None] | None = None,
) -> Job1Run:
    """Execute the fixed D-82 sequence and return a `Job1Run`.

    `limit` bounds how many extracted awards are priced (default: `None`
    — every row the document lists, AGT-01). `search_fn`/`extract_fn`/
    `extract_awards_fn` are test seams; a test double is never a default.
    `on_stage`, if given, is called with one of "searching", "extracting",
    "reading" or "pricing" as the run enters each stage — plan 05-03's
    `/job1` page uses this to name the in-flight stage instead of a bare
    spinner.

    The `PARALLEL_API_KEY`/`GEMINI_API_KEY` configuration check below only
    applies when using the REAL client functions — a caller driving the
    pipeline entirely from injected fakes (the offline CI path, plan 05-02
    Task 3) never needs a key, since it never reaches an SDK call.
    """
    using_real_seams = search_fn is None and extract_fn is None and extract_awards_fn is None
    search = search_fn or search_for_disclosure_candidates
    extract = extract_fn or extract_document
    do_extract_awards = extract_awards_fn or extract_awards

    def _stage(name: str) -> None:
        if on_stage is not None:
            on_stage(name)

    status = integration_status()
    run_mode: Literal["live", "replay"] = (
        "live"
        if using_real_seams and status.parallel_configured and status.gemini_configured
        else "replay"
    )

    if using_real_seams and (not status.parallel_configured or not status.gemini_configured):
        return Job1Run(
            run_mode=run_mode,
            terminal_reason=TerminalReason.not_configured,
            message=status.not_configured_message(),
        )

    sdk_calls: list[dict] = []

    with collecting(sdk_calls):
        _stage("searching")
        # Rank order does not predict which report carries per-production
        # data. Not every ESD quarterly report does — the Q3 2023 report
        # gives only aggregate totals and monthly application counts, and a
        # live run against it correctly extracted zero awards. So try the
        # ranked candidates in order and keep the first that yields a usable
        # document with at least one award. The extraction is the test; no
        # heuristic guesses at document shape. Bounded by
        # _MAX_DISCLOSURE_CANDIDATES so a poor search cannot fan out.
        candidates = _disclosure_candidates(search)
        if not candidates:
            return Job1Run(
                run_mode=run_mode,
                terminal_reason=TerminalReason.no_primary_source_found,
                message="Search returned no primary-government-domain result",
                sdk_calls=tuple(sdk_calls),
            )

        _stage("extracting")
        url = candidates[0]
        document = None
        extraction = None
        for candidate in candidates[:_MAX_DISCLOSURE_CANDIDATES]:
            candidate_document = extract(candidate)
            if candidate_document is None:
                continue
            if document is None:
                url, document = candidate, candidate_document
            candidate_extraction = do_extract_awards(candidate_document.markdown)
            if candidate_extraction.award_set.awards:
                url, document, extraction = candidate, candidate_document, candidate_extraction
                break

        if document is None:
            return Job1Run(
                run_mode=run_mode,
                terminal_reason=TerminalReason.document_extract_failed,
                message="Extract returned no usable content for any search result",
                search_url=url,
                sdk_calls=tuple(sdk_calls),
            )

        # AGT-08's enactment guardrail (D-97): classified as soon as a
        # usable document exists, from that document's own URL and text —
        # a property of the source document, populated for every terminal
        # state from here on, never gated by run_mode.
        source_enactment = classify_enactment(document.url, document.markdown)

        _stage("reading")
        # The candidate loop above already read this document; reuse that
        # result rather than paying for a second identical Gemini call.
        if extraction is None:
            extraction = do_extract_awards(document.markdown)

    awards = extraction.award_set.awards
    if not awards:
        return Job1Run(
            run_mode=run_mode,
            terminal_reason=TerminalReason.zero_awards_extracted,
            message="Gemini extracted zero awards from the document",
            search_url=url,
            document_sha256=document.sha256,
            document_char_count=document.char_count,
            truncated=extraction.truncated,
            gemini_model=extraction.model,
            report_title=extraction.award_set.report_title,
            report_period=extraction.award_set.report_period,
            sdk_calls=tuple(sdk_calls),
            source_enactment=source_enactment,
        )

    _stage("pricing")
    selected = awards[:limit] if limit is not None else awards
    ruleset = load_ruleset(_RULESET_PATH)
    rules = load_variance_rules(_VARIANCE_RULES_PATH)

    results: list[AwardResult] = []
    extraction_failures: list[ExtractionFailure] = []
    for award in selected:
        outcome = _price_and_classify_award(
            award, ruleset, rules, document_text=document.markdown
        )
        if isinstance(outcome, ExtractionFailure):
            extraction_failures.append(outcome)
        else:
            results.append(outcome)

    accuracy = summarize(results, extraction_failures=len(extraction_failures))

    return Job1Run(
        run_mode=run_mode,
        terminal_reason=TerminalReason.ok,
        search_url=url,
        document_sha256=document.sha256,
        document_char_count=document.char_count,
        truncated=extraction.truncated,
        gemini_model=extraction.model,
        report_title=extraction.award_set.report_title,
        report_period=extraction.award_set.report_period,
        raw_award_count=len(awards),
        awards=tuple(results),
        extraction_failures=tuple(extraction_failures),
        accuracy=accuracy,
        sdk_calls=tuple(sdk_calls),
        source_enactment=source_enactment,
    )


def _run_to_dict(run: Job1Run) -> dict:
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
        "source_enactment": (
            {
                "status": run.source_enactment.status.value,
                "matched_markers": list(run.source_enactment.matched_markers),
                "evidence": list(run.source_enactment.evidence),
            }
            if run.source_enactment is not None
            else None
        ),
        "accuracy": {
            "awards_extracted": run.accuracy.awards_extracted,
            "exact_match": run.accuracy.exact_match,
            "explained_variance": run.accuracy.explained_variance,
            "unexplained": run.accuracy.unexplained,
            "extraction_failures": run.accuracy.extraction_failures,
        },
        "awards": [
            {
                "production_title": r.award.production_title,
                "disclosed": str(r.disclosed),
                "computed": str(r.computed) if r.computed is not None else None,
                "match_class": r.match_class.value,
                "explanation": (
                    {
                        "rule_id": r.explanation.rule_id,
                        "reason": r.explanation.reason,
                        "source_url": r.explanation.source_url,
                        "date_checked": r.explanation.date_checked,
                    }
                    if r.explanation is not None
                    else None
                ),
                "derivation": list(r.derivation),
                "corroborates_committed_fixture": r.corroborates_committed_fixture,
                "source_row_text": r.award.source_row_text,
            }
            for r in run.awards
        ],
        "extraction_failures": [
            {
                "production_title": ef.production_title,
                "raw_value": ef.raw_value,
                "error": ef.error,
            }
            for ef in run.extraction_failures
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Job 1 — reproduce New York government disclosure production/award "
            "pairs through Parallel Search, Parallel Extract, google-genai "
            "structured extraction, and the existing pricing engine (D-82)."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Price at most this many extracted awards (default: every row, AGT-01).",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Exit 2 instead of 0 when API keys are not configured.",
    )
    args = parser.parse_args(argv)

    status = integration_status()
    if not status.parallel_configured or not status.gemini_configured:
        print(status.not_configured_message())
        return 2 if args.require_live else 0

    run = run_job1(limit=args.limit)

    if args.json:
        print(json.dumps(_run_to_dict(run), indent=2))
        return 0

    if run.terminal_reason != TerminalReason.ok and not run.awards:
        print(f"Job 1: {run.message or run.terminal_reason.value}")
        return 0

    print(f"Search URL: {run.search_url}")
    print(
        f"Document: {run.document_char_count} chars, sha256={run.document_sha256}, "
        f"truncated={run.truncated}"
    )
    print(f"Gemini model: {run.gemini_model}")
    print(
        f"Rows read: {run.raw_award_count} | exact_match={run.accuracy.exact_match} "
        f"explained_variance={run.accuracy.explained_variance} "
        f"unexplained={run.accuracy.unexplained} "
        f"extraction_failures={run.accuracy.extraction_failures}"
    )
    for r in run.awards:
        print(f"\nProduction: {r.award.production_title} [{r.match_class.value}]")
        print(f"  Disclosed credit:       {r.disclosed}")
        print(f"  Engine-computed credit: {r.computed}")
        if r.explanation is not None:
            print(f"  Explained by rule:      {r.explanation.rule_id} — {r.explanation.reason}")
    for ef in run.extraction_failures:
        print(f"\nParse failure: {ef.production_title}: {ef.error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
