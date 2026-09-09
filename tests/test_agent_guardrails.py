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

from agent.groundedness import check_grounded
from agent.job1 import ExtractionFailure, run_job1
from agent.schema import ExtractedAward

# ---------------------------------------------------------------------------
# The registry — see module docstring. Filled in incrementally as each
# guardrail's coverage lands; the assertion in
# test_every_guardrail_has_a_firing_test only checks the ids present here.
# ---------------------------------------------------------------------------

GUARDRAIL_IDS: tuple[str, ...] = ("groundedness",)


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
