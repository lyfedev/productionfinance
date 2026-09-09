"""D-86/AGT-04: the three-value mismatch taxonomy. `explained_variance`
must be reachable ONLY through a named, sourced rule in
`agent/variance_rules.yaml` (T-05-07); an unknown predicate must raise at
load time; `AccuracySummary` must expose bucket counts only, never a
percentage/mean/blended figure of any kind.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from agent.schema import ExtractedAward
from agent.taxonomy import (
    AccuracySummary,
    AwardResult,
    MatchClass,
    UnknownPredicateError,
    VarianceExplanation,
    classify,
    load_variance_rules,
    summarize,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
VARIANCE_RULES_PATH = REPO_ROOT / "agent" / "variance_rules.yaml"


def _award(**overrides: object) -> ExtractedAward:
    defaults = {
        "production_title": "Test Production",
        "qualified_spend": "10000000",
        "credit_amount": "2500000",
        "diversity_credit_amount": None,
        "programme_hint": None,
        "source_row_text": "Test Production | $10,000,000 | $2,500,000",
    }
    defaults.update(overrides)
    return ExtractedAward(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# MatchClass — exactly three members
# ---------------------------------------------------------------------------


def test_match_class_has_exactly_three_members() -> None:
    assert {m.value for m in MatchClass} == {"exact_match", "explained_variance", "unexplained"}


# ---------------------------------------------------------------------------
# classify()
# ---------------------------------------------------------------------------


def test_classify_exact_equal_returns_exact_match_with_no_explanation() -> None:
    match_class, explanation = classify(Decimal("2500000"), Decimal("2500000"), _award(), ())
    assert match_class is MatchClass.exact_match
    assert explanation is None


def test_classify_diversity_credit_delta_returns_explained_variance() -> None:
    rules = load_variance_rules(VARIANCE_RULES_PATH)
    award = _award(diversity_credit_amount="4956")
    disclosed = Decimal("2500000") + Decimal("4956")
    computed = Decimal("2500000")

    match_class, explanation = classify(disclosed, computed, award, rules)

    assert match_class is MatchClass.explained_variance
    assert isinstance(explanation, VarianceExplanation)
    assert explanation.rule_id == "diversity-credit-column"
    assert explanation.reason
    assert explanation.source_url.startswith("https://")


def test_classify_any_other_difference_is_unexplained() -> None:
    rules = load_variance_rules(VARIANCE_RULES_PATH)
    award = _award(diversity_credit_amount=None)

    match_class, explanation = classify(Decimal("2600000"), Decimal("2500000"), award, rules)

    assert match_class is MatchClass.unexplained
    assert explanation is None


def test_classify_never_rounds_a_one_cent_difference_into_a_match() -> None:
    rules = load_variance_rules(VARIANCE_RULES_PATH)
    award = _award(diversity_credit_amount=None)

    match_class, _ = classify(Decimal("2500000.01"), Decimal("2500000.00"), award, rules)

    assert match_class is MatchClass.unexplained


# ---------------------------------------------------------------------------
# load_variance_rules() — closed predicate set (T-05-07)
# ---------------------------------------------------------------------------


def test_load_variance_rules_loads_the_committed_file() -> None:
    rules = load_variance_rules(VARIANCE_RULES_PATH)
    assert len(rules) == 2
    ids = {rule.id for rule in rules}
    assert ids == {"diversity-credit-column", "alternate-programme-declared-rate"}


def test_load_variance_rules_raises_on_unknown_predicate(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad_rules.yaml"
    bad_file.write_text(
        yaml.safe_dump(
            {
                "rules": [
                    {
                        "id": "malicious",
                        "predicate": "eval_arbitrary_expression",
                        "reason": "attempted injection",
                        "source_url": "https://example.invalid",
                        "date_checked": "2026-01-01",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(UnknownPredicateError) as excinfo:
        load_variance_rules(bad_file)

    assert "eval_arbitrary_expression" in str(excinfo.value)


def test_alternate_programme_predicate_is_a_real_reachable_function() -> None:
    """Rule 2 is grounded in real committed data (jurisdictions/us-ny.yaml's
    own 25% base_rate) but us-ny.yaml currently models only one programme,
    so this predicate never fires against real NY awards today. Prove it is
    real, reachable code — not dead weight — by exercising it directly with
    a case engineered to match."""
    rules = load_variance_rules(VARIANCE_RULES_PATH)
    award = _award(
        qualified_spend="10000000",
        programme_hint="ny-independent-film-credit",
    )
    # implied rate = disclosed / qualified_spend = 0.25 exactly, matching
    # the rule's declared_rate for ny-film-production-tax-credit.
    disclosed = Decimal("2500000")
    computed = Decimal("2600000")  # deliberately different from disclosed

    match_class, explanation = classify(disclosed, computed, award, rules)

    assert match_class is MatchClass.explained_variance
    assert explanation is not None
    assert explanation.rule_id == "alternate-programme-declared-rate"


# ---------------------------------------------------------------------------
# AccuracySummary — counts only, no percentage/mean/blended field (D-86)
# ---------------------------------------------------------------------------


def _result(match_class: MatchClass) -> AwardResult:
    return AwardResult(
        award=_award(),
        disclosed=Decimal("1"),
        computed=Decimal("1"),
        match_class=match_class,
        explanation=None,
        derivation=("step",),
    )


def test_accuracy_summary_counts_sum_correctly() -> None:
    results = [
        _result(MatchClass.exact_match),
        _result(MatchClass.exact_match),
        _result(MatchClass.explained_variance),
        _result(MatchClass.unexplained),
    ]
    summary = summarize(results, extraction_failures=1)

    assert summary.exact_match == 2
    assert summary.explained_variance == 1
    assert summary.unexplained == 1
    assert summary.extraction_failures == 1
    assert (
        summary.exact_match + summary.explained_variance + summary.unexplained
        + summary.extraction_failures
        == summary.awards_extracted
    )


def test_accuracy_summary_exposes_no_percentage_mean_or_blended_field() -> None:
    forbidden_substrings = ("pct", "percent", "mean", "average", "blended", "aggregate", "error")
    field_names = {f.name for f in dataclasses.fields(AccuracySummary)}
    member_names = {name for name in dir(AccuracySummary) if not name.startswith("_")}

    for name in field_names | member_names:
        lowered = name.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lowered, f"AccuracySummary exposes forbidden field/method {name!r}"


def test_accuracy_summary_zero_results_is_all_zero_and_does_not_divide() -> None:
    summary = summarize([], extraction_failures=0)
    assert summary.awards_extracted == 0
    assert summary.exact_match == 0
    assert summary.explained_variance == 0
    assert summary.unexplained == 0
    assert summary.extraction_failures == 0
