"""Job 1: reproduce New York government disclosure pairs end to end.

`run_job1` executes the fixed D-82 sequence with no substitutions and no
branch that skips a stage: status check -> Search -> primary-domain filter
-> Extract -> Gemini -> price EVERY extracted award through the existing
engine with `spend_confidence="researched"` (D-63 / PRV-02 — a figure an
LLM read out of a document has not been transcribed and checked by a human,
so it is never `validated`).

Nothing in this module invents, defaults, or backfills an award (D-87): if
Search returns no primary-domain result, Extract returns nothing usable, or
Gemini returns zero awards, the run reports that plainly through a closed
`TerminalReason` enum with an empty award list. An award whose money fields
do not parse (`agent.numbers.parse_money`, D-88) is recorded as an
`ExtractionFailure` carrying the raw string and the exception text — it is
neither dropped silently nor guessed at.

`search_fn`, `extract_fn` and `extract_awards_fn` are injectable seams
(each defaulting to `None`, resolved to the real client function) so an
offline test can drive the whole extract-price loop against a committed
fixture with zero network access (plan 05-02 Task 3) without ever making a
test double the default. `run_mode` on the returned `Job1Run` is `"live"`
only when none of those three seams were overridden AND both integrations
were configured — a run driven by any injected fake is always `"replay"`
and must never be rendered as a product accuracy figure (T-05-10).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Literal

from agent.gemini_client import ExtractionResult, extract_awards
from agent.numbers import UnparseableFigureError, parse_money
from agent.parallel_client import DisclosureDocument, extract_document, search_for_disclosure
from agent.schema import ExtractedAward
from agent.settings import integration_status
from app.services._paths import REPO_ROOT
from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction

__all__ = [
    "ExtractionFailure",
    "Job1Run",
    "PricedAward",
    "TerminalReason",
    "run_job1",
]

_JURISDICTION_ID = "us-ny"
_RULESET_PATH = REPO_ROOT / "jurisdictions" / f"{_JURISDICTION_ID}.yaml"
_PROGRAMME_ID = "ny-film-production-tax-credit"

SearchFn = Callable[[], "str | None"]
ExtractFn = Callable[[str], "DisclosureDocument | None"]
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
    """One extracted award whose money fields did not parse (D-88). Carries
    the raw string(s) and the exception text — never dropped silently,
    never guessed at."""

    production_title: str
    raw_value: str
    error: str


@dataclass(frozen=True)
class PricedAward:
    production_title: str
    disclosed_qualified_spend: Decimal
    disclosed_credit: Decimal
    computed_credit: Decimal
    source_row_text: str
    diversity_credit_amount: Decimal | None = None
    derivation: tuple[str, ...] = field(default_factory=tuple)


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
    priced_awards: tuple[PricedAward, ...] = field(default_factory=tuple)
    extraction_failures: tuple[ExtractionFailure, ...] = field(default_factory=tuple)

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


def _price_award(award: ExtractedAward) -> PricedAward | ExtractionFailure:
    """Parse and price one extracted award through the existing engine
    (D-85: the same `price_jurisdiction` entry point
    `app/services/validate.py` already uses for a committed fixture).
    Returns an `ExtractionFailure` — never a fabricated figure (D-87) —
    when the award's money fields do not parse or the engine cannot price
    it."""
    try:
        qualified_spend, disclosed_credit, diversity_credit = _parse_award_figures(award)
    except UnparseableFigureError as exc:
        return ExtractionFailure(
            production_title=award.production_title,
            raw_value=(
                f"qualified_spend={award.qualified_spend!r} "
                f"credit_amount={award.credit_amount!r}"
            ),
            error=str(exc),
        )

    ruleset = load_ruleset(_RULESET_PATH)
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

    return PricedAward(
        production_title=award.production_title,
        disclosed_qualified_spend=qualified_spend,
        disclosed_credit=disclosed_credit,
        computed_credit=programme.gross_credit.value,
        source_row_text=award.source_row_text,
        diversity_credit_amount=diversity_credit,
        derivation=programme.gross_credit.derivation,
    )


def run_job1(
    limit: int | None = None,
    *,
    search_fn: SearchFn | None = None,
    extract_fn: ExtractFn | None = None,
    extract_awards_fn: ExtractAwardsFn | None = None,
) -> Job1Run:
    """Execute the fixed D-82 sequence and return a `Job1Run`.

    `limit` bounds how many extracted awards are priced (default: `None`
    — every row the document lists, AGT-01). `search_fn`/`extract_fn`/
    `extract_awards_fn` are test seams; a test double is never a default.
    """
    using_real_seams = search_fn is None and extract_fn is None and extract_awards_fn is None
    search = search_fn or search_for_disclosure
    extract = extract_fn or extract_document
    do_extract_awards = extract_awards_fn or extract_awards

    status = integration_status()
    run_mode: Literal["live", "replay"] = (
        "live"
        if using_real_seams and status.parallel_configured and status.gemini_configured
        else "replay"
    )

    if not status.parallel_configured or not status.gemini_configured:
        return Job1Run(
            run_mode=run_mode,
            terminal_reason=TerminalReason.not_configured,
            message=status.not_configured_message(),
        )

    url = search()
    if url is None:
        return Job1Run(
            run_mode=run_mode,
            terminal_reason=TerminalReason.no_primary_source_found,
            message="Search returned no primary-government-domain result",
        )

    document = extract(url)
    if document is None:
        return Job1Run(
            run_mode=run_mode,
            terminal_reason=TerminalReason.document_extract_failed,
            message="Extract returned no usable content for the search result",
            search_url=url,
        )

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
        )

    selected = awards[:limit] if limit is not None else awards
    priced_awards: list[PricedAward] = []
    extraction_failures: list[ExtractionFailure] = []
    for award in selected:
        result = _price_award(award)
        if isinstance(result, ExtractionFailure):
            extraction_failures.append(result)
        else:
            priced_awards.append(result)

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
        priced_awards=tuple(priced_awards),
        extraction_failures=tuple(extraction_failures),
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
        "priced_awards": [
            {
                "production_title": pa.production_title,
                "disclosed_qualified_spend": str(pa.disclosed_qualified_spend),
                "disclosed_credit": str(pa.disclosed_credit),
                "computed_credit": str(pa.computed_credit),
                "source_row_text": pa.source_row_text,
                "diversity_credit_amount": (
                    str(pa.diversity_credit_amount)
                    if pa.diversity_credit_amount is not None
                    else None
                ),
            }
            for pa in run.priced_awards
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

    if run.terminal_reason != TerminalReason.ok and not run.priced_awards:
        print(f"Job 1: {run.message or run.terminal_reason.value}")
        return 0

    print(f"Search URL: {run.search_url}")
    print(
        f"Document: {run.document_char_count} chars, sha256={run.document_sha256}, "
        f"truncated={run.truncated}"
    )
    print(f"Gemini model: {run.gemini_model}")
    print(f"Rows read: {run.raw_award_count}, priced: {len(run.priced_awards)}, "
          f"parse failures: {len(run.extraction_failures)}")
    for pa in run.priced_awards:
        print(f"\nProduction: {pa.production_title}")
        print(f"  Disclosed qualified spend: {pa.disclosed_qualified_spend}")
        print(f"  Disclosed credit:          {pa.disclosed_credit}")
        print(f"  Engine-computed credit:    {pa.computed_credit}")
    for ef in run.extraction_failures:
        print(f"\nParse failure: {ef.production_title}: {ef.error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
