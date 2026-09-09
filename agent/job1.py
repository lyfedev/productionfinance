"""Job 1: reproduce New York government disclosure pairs end to end.

`run_job1` executes the fixed D-82 sequence with no substitutions and no
branch that skips a stage: status check -> Search -> primary-domain filter
-> Extract -> Gemini -> price each extracted award through the existing
engine with `spend_confidence="researched"` (D-63 / PRV-02 — a figure an
LLM read out of a document has not been transcribed and checked by a human,
so it is never `validated`).

Nothing in this module invents, defaults, or backfills an award (D-87): if
Search returns no primary-domain result, or Gemini returns zero awards, the
run reports that plainly with an empty award list and an explicit terminal
reason.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from agent.gemini_client import extract_awards
from agent.parallel_client import extract_document, search_for_disclosure
from agent.schema import ExtractedAward
from agent.settings import integration_status
from app.services._paths import REPO_ROOT
from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction

__all__ = ["Job1Run", "PricedAward", "run_job1"]

_JURISDICTION_ID = "us-ny"
_RULESET_PATH = REPO_ROOT / "jurisdictions" / f"{_JURISDICTION_ID}.yaml"
_PROGRAMME_ID = "ny-film-production-tax-credit"


@dataclass(frozen=True)
class PricedAward:
    production_title: str
    disclosed_qualified_spend: Decimal
    disclosed_credit: Decimal
    computed_credit: Decimal
    source_row_text: str


@dataclass(frozen=True)
class Job1Run:
    ran_live: bool
    terminal_reason: str | None
    search_url: str | None = None
    document_sha256: str | None = None
    document_char_count: int | None = None
    truncated: bool = False
    gemini_model: str | None = None
    report_title: str | None = None
    report_period: str | None = None
    raw_award_count: int = 0
    priced_awards: tuple[PricedAward, ...] = field(default_factory=tuple)


def _price_award(award: ExtractedAward) -> PricedAward | None:
    """Price one extracted award through the existing engine. Returns None
    (never a fabricated figure, D-87) if the award's money fields do not
    parse as Decimal — a malformed extraction is reported, not silently
    coerced.
    """
    try:
        qualified_spend = Decimal(award.qualified_spend.replace(",", "").replace("$", ""))
        disclosed_credit = Decimal(award.credit_amount.replace(",", "").replace("$", ""))
    except InvalidOperation:
        return None

    ruleset = load_ruleset(_RULESET_PATH)
    priced = price_jurisdiction(ruleset, qualified_spend, spend_confidence="researched")

    programme = next(
        (p for p in priced.programmes if p.programme_id == _PROGRAMME_ID),
        None,
    )
    if programme is None:
        return None

    return PricedAward(
        production_title=award.production_title,
        disclosed_qualified_spend=qualified_spend,
        disclosed_credit=disclosed_credit,
        computed_credit=programme.gross_credit.value,
        source_row_text=award.source_row_text,
    )


def run_job1(limit: int | None = None) -> Job1Run:
    """Execute the fixed D-82 sequence and return a `Job1Run`.

    `limit` bounds how many extracted awards are priced (default: all).
    """
    status = integration_status()
    if not status.parallel_configured or not status.gemini_configured:
        return Job1Run(ran_live=False, terminal_reason=status.not_configured_message())

    url = search_for_disclosure()
    if url is None:
        return Job1Run(
            ran_live=True,
            terminal_reason="Search returned no primary-government-domain result",
        )

    document = extract_document(url)
    if document is None:
        return Job1Run(
            ran_live=True,
            terminal_reason="Extract returned no usable content for the search result",
            search_url=url,
        )

    extraction = extract_awards(document.markdown)
    awards = extraction.award_set.awards
    if not awards:
        return Job1Run(
            ran_live=True,
            terminal_reason="Gemini extracted zero awards from the document",
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
    for award in selected:
        priced = _price_award(award)
        if priced is not None:
            priced_awards.append(priced)

    return Job1Run(
        ran_live=True,
        terminal_reason=None if priced_awards else "No extracted award priced successfully",
        search_url=url,
        document_sha256=document.sha256,
        document_char_count=document.char_count,
        truncated=extraction.truncated,
        gemini_model=extraction.model,
        report_title=extraction.award_set.report_title,
        report_period=extraction.award_set.report_period,
        raw_award_count=len(awards),
        priced_awards=tuple(priced_awards),
    )


def _run_to_dict(run: Job1Run) -> dict:
    return {
        "ran_live": run.ran_live,
        "terminal_reason": run.terminal_reason,
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
            }
            for pa in run.priced_awards
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
        "--limit", type=int, default=1, help="Price at most this many extracted awards."
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

    if run.terminal_reason and not run.priced_awards:
        print(f"Job 1: {run.terminal_reason}")
        return 0

    print(f"Search URL: {run.search_url}")
    print(
        f"Document: {run.document_char_count} chars, sha256={run.document_sha256}, "
        f"truncated={run.truncated}"
    )
    print(f"Gemini model: {run.gemini_model}")
    for pa in run.priced_awards:
        print(f"\nProduction: {pa.production_title}")
        print(f"  Disclosed qualified spend: {pa.disclosed_qualified_spend}")
        print(f"  Disclosed credit:          {pa.disclosed_credit}")
        print(f"  Engine-computed credit:    {pa.computed_credit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
