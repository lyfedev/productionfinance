"""AGT-08's standing gate — the complete four-clause guardrail set restored
by D-97 (D-88, which reduced it to two, is struck; see `.planning/phases/
05-curated-breadth-the-validation-loop/05-CONTEXT.md`).

This module is the single place that maps each of AGT-08's four clauses to
its implementing module/function and to the test function in THIS module
that proves it fires:

| AGT-08 clause                                    | Implementation                                                    | Proven by                                                                |
|----------------------------------------------------|----------------------------------------------------------------------|-----------------------------------------------------------------------------|
| groundedness checks on extracted quotes             | `agent.groundedness.check_grounded` (new, plan 05-07)                | `test_groundedness_*`, `test_run_job1_rejects_ungrounded_award_*`           |
| preference for primary government domains           | `agent.parallel_client.is_primary_government_url` (pre-existing)     | `test_primary_domain_*` (built in plan 05-07 Task 3 — this guardrail's implementation predates this plan, its test coverage does not) |
| locale-aware number parsing                         | `agent.numbers.parse_money` (pre-existing, already fully tested)     | `test_locale_aware_parsing_*` — entry point only; the full case set lives in `tests/test_agent_numbers.py`, never re-derived here |
| proposed bill vs. enacted law classification         | `agent.enactment.classify_enactment` (new, plan 05-07)               | `test_enactment_*`                                                          |

`test_every_guardrail_has_a_firing_test` is the registry test (added once
all four sections exist): it declares the four guardrail identifiers below
as a tuple and asserts, by introspecting this module's own function names,
that each identifier is covered by at least one `test_*` function. A future
removal of a guardrail then fails a test instead of silently going
unnoticed.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.enactment import EnactmentStatus, classify_enactment
from agent.groundedness import check_grounded
from agent.job1 import ExtractionFailure, run_job1
from agent.numbers import UnparseableFigureError, parse_money
from agent.parallel_client import is_primary_government_url
from agent.schema import ExtractedAward

# ---------------------------------------------------------------------------
# The registry — see module docstring. All four guardrail identifiers;
# test_every_guardrail_has_a_firing_test asserts each is covered.
# ---------------------------------------------------------------------------

GUARDRAIL_IDS: tuple[str, ...] = (
    "groundedness",
    "primary_domain",
    "locale_aware_parsing",
    "enactment",
)


def test_every_guardrail_has_a_firing_test() -> None:
    """Introspect this module's own function names: each declared guardrail
    identifier must be a substring of at least one `test_*` function name
    in this module. Fails loudly if a guardrail's coverage is ever
    silently removed."""
    import sys

    this_module = sys.modules[__name__]
    test_function_names = [
        name
        for name in dir(this_module)
        if name.startswith("test_") and callable(getattr(this_module, name))
    ]
    for guardrail_id in GUARDRAIL_IDS:
        matches = [name for name in test_function_names if guardrail_id in name]
        assert matches, (
            f"no test function name in {__name__} contains guardrail id "
            f"{guardrail_id!r} — AGT-08 requires every guardrail to have a "
            f"firing test"
        )


# ---------------------------------------------------------------------------
# Guardrail 1: groundedness (new, plan 05-07)
# ---------------------------------------------------------------------------

_DOC_TEXT = (
    "# ESD Report\n\n"
    "| Production | Qualified Costs | Credit Issued | Diversity Credit |\n"
    "|---|---|---|---|\n"
    "| Anora Productions | $20,000,000 | $5,000,000 | — |\n"
)


def test_groundedness_quote_present_verbatim_is_grounded() -> None:
    quote = "Anora Productions | $20,000,000 | $5,000,000 | —"
    verdict = check_grounded(quote, _DOC_TEXT, ("$20,000,000", "$5,000,000"))
    assert verdict.grounded is True


def test_groundedness_whitespace_nbsp_and_table_punctuation_variants_are_grounded() -> None:
    # Non-breaking space, a run of whitespace, and the whole quote wrapped
    # in leading/trailing pipes — none of these should defeat the match.
    quote = "| Anora Productions  |   $20,000,000 | $5,000,000 |  — |"
    verdict = check_grounded(quote, _DOC_TEXT, ("$20,000,000", "$5,000,000"))
    assert verdict.grounded is True


def test_groundedness_quote_not_in_document_is_ungrounded() -> None:
    quote = "Nonexistent Pictures | $99,000,000 | $25,000,000 | —"
    verdict = check_grounded(quote, _DOC_TEXT, ("$99,000,000", "$25,000,000"))
    assert verdict.grounded is False
    assert "not appear" in verdict.reason


def test_groundedness_figure_missing_from_present_quote_is_ungrounded() -> None:
    # The quote itself is a real passage, but the figure attributed to it
    # is not actually inside that passage — the money-doesn't-match case.
    quote = "Anora Productions | $20,000,000 | $5,000,000 | —"
    verdict = check_grounded(quote, _DOC_TEXT, ("$20,000,000", "$9,999,999"))
    assert verdict.grounded is False
    assert "9,999,999" in verdict.reason


def test_groundedness_empty_quote_is_ungrounded() -> None:
    verdict = check_grounded("", _DOC_TEXT, ())
    assert verdict.grounded is False

    verdict_whitespace = check_grounded("   ", _DOC_TEXT, ())
    assert verdict_whitespace.grounded is False


def test_run_job1_rejects_ungrounded_award_as_extraction_failure() -> None:
    """The wired path: `run_job1` never prices an ungrounded award, never
    drops it silently, and never fabricates a substitute (D-87) — it
    becomes an `ExtractionFailure` naming the groundedness guardrail."""
    ungrounded_award = ExtractedAward(
        production_title="Ghost Pictures",
        qualified_spend="$50,000,000",
        credit_amount="$12,500,000",
        diversity_credit_amount=None,
        source_row_text="Ghost Pictures | $50,000,000 | $12,500,000 | —",
    )

    from agent.gemini_client import ExtractionResult
    from agent.parallel_client import DisclosureDocument
    from agent.schema import ExtractedAwardSet

    def _fake_search() -> str:
        return "https://esd.ny.gov/fake-report.pdf"

    def _fake_extract(url: str) -> DisclosureDocument:
        return DisclosureDocument(
            url=url, markdown=_DOC_TEXT, sha256="deadbeef", char_count=len(_DOC_TEXT)
        )

    def _fake_extract_awards(_markdown: str) -> ExtractionResult:
        return ExtractionResult(
            award_set=ExtractedAwardSet(awards=[ungrounded_award]),
            truncated=False,
            model="test-double",
        )

    run = run_job1(
        search_fn=_fake_search,
        extract_fn=_fake_extract,
        extract_awards_fn=_fake_extract_awards,
    )

    assert run.terminal_reason.value == "ok"
    assert run.awards == ()
    assert len(run.extraction_failures) == 1
    failure = run.extraction_failures[0]
    assert isinstance(failure, ExtractionFailure)
    assert failure.production_title == "Ghost Pictures"
    assert "groundedness" in failure.error
    # AccuracySummary gains no new field (D-86): the rejection lands in the
    # existing extraction-failure count and nowhere else.
    assert run.accuracy.extraction_failures == 1
    assert run.accuracy.exact_match == 0
    assert run.accuracy.explained_variance == 0
    assert run.accuracy.unexplained == 0


# ---------------------------------------------------------------------------
# Guardrail 2: preference for primary government domains (pre-existing —
# agent.parallel_client.is_primary_government_url and the ranked-result
# loop inside search_for_disclosure — but previously untested anywhere in
# this suite. agent/parallel_client.py is NOT modified to close this gap.
# ---------------------------------------------------------------------------


def test_primary_domain_run_job1_prefers_a_government_result_over_a_higher_ranked_one() -> None:
    """`search_for_disclosure`'s own ranked-result loop lives inside the
    real Parallel client call and is not reachable offline, so this drives
    the guardrail through `run_job1`'s `search_fn` seam with a fake that
    reproduces the loop's own contract: given a ranked list whose top
    result is on a non-government host and a lower one is on a government
    host, only the government URL is ever returned to the rest of the
    pipeline."""
    ranked_results = [
        "https://filmnews.example.com/esd-report-summary",  # non-government, ranked first
        "https://esd.ny.gov/real-report.pdf",  # government, ranked lower
    ]

    def _search_preferring_government() -> str | None:
        for url in ranked_results:
            if is_primary_government_url(url):
                return url
        return None

    from agent.gemini_client import ExtractionResult
    from agent.parallel_client import DisclosureDocument
    from agent.schema import ExtractedAwardSet

    captured_urls: list[str] = []

    def _fake_extract(url: str) -> DisclosureDocument:
        captured_urls.append(url)
        return DisclosureDocument(
            url=url, markdown=_DOC_TEXT, sha256="x", char_count=len(_DOC_TEXT)
        )

    def _fake_extract_awards(_markdown: str) -> ExtractionResult:
        return ExtractionResult(
            award_set=ExtractedAwardSet(awards=[]), truncated=False, model="t"
        )

    run = run_job1(
        search_fn=_search_preferring_government,
        extract_fn=_fake_extract,
        extract_awards_fn=_fake_extract_awards,
    )

    assert run.search_url == "https://esd.ny.gov/real-report.pdf"
    assert captured_urls == ["https://esd.ny.gov/real-report.pdf"]


def test_primary_domain_run_job1_terminates_with_no_primary_source_when_none_qualify() -> None:
    """No result in the ranked list is government — the run must terminate
    with the no-primary-source reason and an empty award list, never fall
    back to the top-ranked non-government result (D-87: no fallback)."""
    ranked_results = [
        "https://filmnews.example.com/esd-report-summary",
        "https://blog.example.org/ny-tax-credits",
    ]

    def _search_no_government_result() -> str | None:
        for url in ranked_results:
            if is_primary_government_url(url):
                return url
        return None

    def _must_not_be_called(*_args, **_kwargs):
        raise AssertionError("extract/extract_awards must not be called past the search gate")

    run = run_job1(
        search_fn=_search_no_government_result,
        extract_fn=_must_not_be_called,
        extract_awards_fn=_must_not_be_called,
    )

    assert run.terminal_reason.value == "no_primary_source_found"
    assert run.awards == ()


def test_primary_domain_rejects_government_looking_string_in_path_not_host() -> None:
    """T-05-29/T-05-01: the check is on the PARSED HOSTNAME, never a
    substring of the whole URL — a government-looking string sitting in
    the path or query of an attacker-controlled host must be rejected."""
    assert is_primary_government_url("https://attacker.example/?redirect=esd.ny.gov") is False
    assert is_primary_government_url("https://attacker.example/esd.ny.gov/report.pdf") is False
    assert is_primary_government_url("https://esd.ny.gov.attacker.example/report.pdf") is False
    # Sanity: the real government host still passes.
    assert is_primary_government_url("https://esd.ny.gov/report.pdf") is True


# ---------------------------------------------------------------------------
# Guardrail 3: locale-aware number parsing (pre-existing, fully proven in
# tests/test_agent_numbers.py — this is the AGT-08 entry point only, never
# a re-derivation of that case set. agent/numbers.py is NOT modified here.)
# ---------------------------------------------------------------------------


def test_locale_aware_parsing_ambiguous_figure_raises_rather_than_guessing() -> None:
    with pytest.raises(UnparseableFigureError):
        parse_money("1,2345")


def test_locale_aware_parsing_both_grouping_conventions_parse_to_the_same_decimal() -> None:
    us_convention = parse_money("3,964,760.00")
    european_convention = parse_money("3.964.760,00")
    assert us_convention == european_convention == Decimal("3964760.00")


# ---------------------------------------------------------------------------
# Guardrail 4: proposed bill vs. enacted law classification (new, plan
# 05-07)
# ---------------------------------------------------------------------------


def test_enactment_document_with_enactment_marker_classifies_as_enacted() -> None:
    text = "Chapter 59 of the Laws of 2023. Approved and signed into law by the Governor."
    verdict = classify_enactment("https://www.nysenate.gov/legislation/laws/TAX/24", text)
    assert verdict.status is EnactmentStatus.enacted
    assert verdict.matched_markers
    assert len(verdict.matched_markers) == len(verdict.evidence)


def test_enactment_document_with_pending_marker_only_classifies_as_proposed() -> None:
    text = "S1234-2023: Referred to the Committee on Ways and Means. Introduced by Sen. Doe."
    verdict = classify_enactment("https://www.nysenate.gov/legislation/bills/2023/S1234", text)
    assert verdict.status is EnactmentStatus.proposed
    assert verdict.matched_markers


def test_enactment_document_with_neither_marker_classifies_as_unknown() -> None:
    text = "This press release discusses the film production tax credit program generally."
    verdict = classify_enactment("https://esd.ny.gov/press-release", text)
    assert verdict.status is EnactmentStatus.unknown
    assert verdict.matched_markers == ()
    assert verdict.evidence == ()


def test_enactment_document_with_both_markers_prefers_enacted_and_records_both() -> None:
    text = (
        "Chapter 59 of the Laws of 2023, signed into law, which amended the bill "
        "as introduced and referred to committee prior to passage."
    )
    verdict = classify_enactment("https://www.nysenate.gov/legislation/laws/TAX/24", text)
    assert verdict.status is EnactmentStatus.enacted
    # The precedence rule (module docstring, agent/enactment.py): enacted
    # wins, but BOTH marker sets are recorded, never laundered away.
    assert len(verdict.matched_markers) >= 2
    assert "referred_to_committee" in verdict.matched_markers
    assert "chapter_of_the_laws_of" in verdict.matched_markers
