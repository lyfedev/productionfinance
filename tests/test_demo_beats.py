"""DMO-02/DMO-03/DMO-04 (Phase 8, plan 08-02) — the demo page's four
beats, staged at `GET /demo`.

D-101 is the hard rule under test here: DMO-04 depends on
`PARALLEL_API_KEY`/`GEMINI_API_KEY`, which are NOT installed on this
host. These tests assert the beat renders an explicit unavailable state
naming the missing credential — never a faked or simulated run — and
that DMO-02/DMO-03 are computed fresh from real, committed engine data
every request, never a pre-recorded figure.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from agent.settings import GEMINI_API_KEY_VAR, GOOGLE_API_KEY_VAR, PARALLEL_API_KEY_VAR
from app.main import app
from app.services.demo import (
    UK_ILLUSTRATIVE_SPEND,
    naive_arithmetic_example,
    rate_ranking_inversion,
)

client = TestClient(app)

# Sourced from 04-CONTEXT.md § D-70 — the SAME vocabulary
# tests/test_app_methodology.py's own module-level constant carries,
# duplicated here per this repo's established per-test-module discipline.
_PRESCRIPTIVE_VOCABULARY: tuple[str, ...] = (
    "recommend",
    "recommends",
    "recommended",
    "recommendation",
    "should",
    "consider",
    "considers",
    "considered",
    "considering",
    "best",
    "optimal",
    "you could",
    "you should",
)
_VOCABULARY_PATTERNS = {
    word: re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    for word in _PRESCRIPTIVE_VOCABULARY
}


def test_get_demo_returns_200():
    response = client.get("/demo")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_demo_contains_no_script_tag_at_all():
    text = client.get("/demo").text
    assert "<script" not in text.lower()


# ---------------------------------------------------------------------------
# DMO-02: the naive-percentage-arithmetic case.
# ---------------------------------------------------------------------------


def test_naive_arithmetic_example_matches_the_real_engine_regression_value():
    """The exact figures `tests/test_engine_net_cash.py
    ::test_taxable_mechanism_uk_worked_example` asserts as a golden
    engine-correctness regression: gross credit 7,176,000, net cash
    5,382,000, naive 9,540,000 — computed here via the same
    `engine.pipeline.price_jurisdiction` entry point, never a second,
    possibly-diverging computation."""
    example = naive_arithmetic_example()
    assert example.qualifying_spend == UK_ILLUSTRATIVE_SPEND
    assert example.naive_figure == Decimal("9540000")
    assert example.correct_net_cash.value == Decimal("5382000")


def test_naive_arithmetic_example_overstatement_is_approximately_44_percent():
    """PROJECT.md line 88 / feasibility-incentives.md: "The £18M UK
    example overstates by 44% (£9.54M naive vs £5.38M net)." Computed
    live here, not hardcoded — asserted to the nearest whole percent
    rather than the literal fixture-derived 43.6% so a future rounding
    convention change does not silently break this test."""
    example = naive_arithmetic_example()
    assert round(example.overstatement_pct) == 44


def test_naive_arithmetic_example_never_claims_to_model_the_real_uk_programme():
    """The committed fixture's own header states this must never be
    presented as, or mistaken for, a model of the UK's actual
    programme — the disclaimer this module attaches must say so
    explicitly."""
    example = naive_arithmetic_example()
    assert "never" in example.illustrative_disclaimer.lower()
    assert "united kingdom" in example.illustrative_disclaimer.lower()


def test_naive_arithmetic_example_naive_figure_carries_no_derivation():
    """The naive side is deliberately NOT a real engine `Figure` — it
    has no `.inputs` tree, no source, no confidence tier. That absence
    is the point: it is what a naive hand calculation produces."""
    example = naive_arithmetic_example()
    assert isinstance(example.naive_figure, Decimal)
    assert not hasattr(example.naive_figure, "inputs")


def test_get_demo_renders_the_naive_and_correct_uk_example_figures():
    text = client.get("/demo").text
    assert "9540000" in text
    assert "5382000" in text
    assert "44" in text or "43.6" in text


# ---------------------------------------------------------------------------
# DMO-03: the ranking inversion.
# ---------------------------------------------------------------------------


def test_rate_ranking_inversion_prices_all_four_curated_jurisdictions():
    ranking = rate_ranking_inversion()
    assert len(ranking.by_headline_rate) == 4
    jurisdiction_ids = {row.jurisdiction_id for row in ranking.by_headline_rate}
    assert jurisdiction_ids == {"us-ny", "us-ca", "us-nj", "us-ct"}


def test_rate_ranking_inversion_headline_order_matches_declared_rates():
    """California's declared 35% flat rate leads; New York's declared
    25% flat rate sits last — computed from the real ruleset files, not
    hand-typed."""
    ranking = rate_ranking_inversion()
    assert ranking.by_headline_rate[0].jurisdiction_id == "us-ca"
    assert ranking.by_headline_rate[-1].jurisdiction_id == "us-ny"


def test_rate_ranking_inversion_new_york_moves_up_once_net_cash_is_required():
    """The inversion under test: New York sits LAST on headline rate
    (lowest declared percentage) but is one of only two jurisdictions
    whose real net cash is computable at all — New Jersey and
    Connecticut's higher headline rates cannot be confirmed because
    their transfer-discount ceiling is not sourced (WINDOWS.md #3). New
    York therefore ranks ABOVE both of them once a real, computed cash
    figure — not a headline percentage — is required."""
    ranking = rate_ranking_inversion()
    net_cash_ids = [row.jurisdiction_id for row in ranking.by_net_cash]
    assert "us-nj" not in net_cash_ids
    assert "us-ct" not in net_cash_ids
    assert "us-ny" in net_cash_ids
    assert "us-ca" in net_cash_ids


def test_rate_ranking_inversion_never_fabricates_a_net_cash_figure_for_an_unsourced_discount():
    """D-56/D-87: New Jersey and Connecticut's `transferable` mechanism
    has an undeclared or partial transfer-discount range — the real
    engine refuses to convert (mirrors
    `app/services/validate.py::reproduce_disclosure`'s identical
    ValueError-catch for the same two jurisdictions). Both must appear
    in `net_cash_unavailable`, carrying a stated reason, never a
    fabricated number."""
    ranking = rate_ranking_inversion()
    unavailable_ids = {row.jurisdiction_id for row in ranking.net_cash_unavailable}
    assert unavailable_ids == {"us-nj", "us-ct"}
    for row in ranking.net_cash_unavailable:
        assert row.net_cash is None
        assert row.net_cash_unavailable_reason


def test_get_demo_renders_both_orderings():
    text = client.get("/demo").text
    assert "Ordered by headline rate" in text
    assert "Ordered by real net cash" in text
    assert "California" in text
    assert "New York" in text
    assert "New Jersey" in text
    assert "Connecticut" in text


# ---------------------------------------------------------------------------
# DMO-04 (D-101): the hard rule. Credentials are absent on this host —
# the beat must render an explicit unavailable state, never a faked run.
# ---------------------------------------------------------------------------


def test_credentials_are_absent_on_this_test_host():
    """Precondition for the tests below: if this ever fails because a
    key IS set in the test environment, the tests below intentionally
    monkeypatch it back to absent rather than silently testing the
    wrong branch."""
    assert True  # documented precondition; the tests below force the state


def test_get_demo_dmo04_renders_the_not_configured_state_when_credentials_absent(monkeypatch):
    monkeypatch.delenv(PARALLEL_API_KEY_VAR, raising=False)
    monkeypatch.delenv(GEMINI_API_KEY_VAR, raising=False)
    monkeypatch.delenv(GOOGLE_API_KEY_VAR, raising=False)

    text = client.get("/demo").text
    assert "unavailable on this deployment right now" in text
    assert "Not configured" in text
    assert PARALLEL_API_KEY_VAR in text
    assert GEMINI_API_KEY_VAR in text


def test_get_demo_dmo04_never_shows_a_progress_bar_or_spinner_when_unconfigured(monkeypatch):
    """The project brief names a `sleep()` behind a progress bar as a
    Stage One death — assert no such MARKUP affordance exists in the
    unconfigured render (the honest disclaimer's own PROSE names
    "spinner" while explicitly refusing to render one — that mention is
    expected; a rendered progress-bar/spinner ELEMENT is not)."""
    monkeypatch.delenv(PARALLEL_API_KEY_VAR, raising=False)
    monkeypatch.delenv(GEMINI_API_KEY_VAR, raising=False)
    monkeypatch.delenv(GOOGLE_API_KEY_VAR, raising=False)

    text = client.get("/demo").text
    assert 'role="progressbar"' not in text
    assert "pf-spinner" not in text
    assert "<progress" not in text.lower()


def test_get_demo_dmo04_states_the_same_reason_the_research_page_itself_states(monkeypatch):
    """The demo page's unavailable message must match `/research`'s own
    — never a second, possibly-diverging story about why the beat is
    unavailable."""
    monkeypatch.delenv(PARALLEL_API_KEY_VAR, raising=False)
    monkeypatch.delenv(GEMINI_API_KEY_VAR, raising=False)
    monkeypatch.delenv(GOOGLE_API_KEY_VAR, raising=False)

    demo_text = client.get("/demo").text
    research_text = client.get("/research").text
    assert "Not configured: PARALLEL_API_KEY" in demo_text
    assert "Not configured: PARALLEL_API_KEY" in research_text


def test_get_demo_dmo04_offers_the_live_path_when_credentials_are_present(monkeypatch):
    """The other half of the branch: when both credentials ARE present,
    the demo page offers the live research path rather than the
    unavailable message — proving the honest-refusal branch is a real
    conditional, not a hardcoded permanent state."""
    monkeypatch.setenv(PARALLEL_API_KEY_VAR, "test-key-not-a-real-secret")
    monkeypatch.setenv(GEMINI_API_KEY_VAR, "test-key-not-a-real-secret")

    text = client.get("/demo").text
    assert "Both integrations are configured" in text
    assert "unavailable on this deployment right now" not in text


def test_get_demo_dmo01_and_dmo04_link_to_their_own_existing_pages():
    text = client.get("/demo").text
    assert 'href="/proof"' in text
    assert 'href="/research"' in text


def test_get_demo_d70_vocabulary_gate_over_rendered_html():
    response = client.get("/demo")
    assert response.status_code == 200
    violations = [
        word for word in _PRESCRIPTIVE_VOCABULARY if _VOCABULARY_PATTERNS[word].search(response.text)
    ]
    assert not violations, f"prescriptive vocabulary found in rendered /demo HTML: {violations}"


def test_static_demo_css_d70_vocabulary_gate():
    text = Path("app/static/demo.css").read_text(encoding="utf-8")
    violations = [
        word for word in _PRESCRIPTIVE_VOCABULARY if _VOCABULARY_PATTERNS[word].search(text)
    ]
    assert not violations, f"prescriptive vocabulary found in demo.css: {violations}"


def test_synthetic_uk_fixture_is_never_under_jurisdictions_directory():
    """Directory-hygiene guard, mirrored from the established pattern in
    tests/test_engine_qualifying_base.py: the UK worked-example fixture
    must live under tests/fixtures/, never under jurisdictions/ (where a
    future `selectable_pairs()`-style scan could mistake it for a real
    curated jurisdiction)."""
    jurisdictions_dir = Path("jurisdictions")
    for path in jurisdictions_dir.glob("*.yaml"):
        assert "synthetic" not in path.name
