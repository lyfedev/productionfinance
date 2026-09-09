"""PRV-05 (Phase 6, plan 06-03) — the methodology page: a stable,
linkable page explaining how figures are computed, that persists
independently of any comparison."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import app
from engine.landed_cost import COST_CATEGORIES, PERMANENT_EXCLUSIONS

client = TestClient(app)

# Sourced from 04-CONTEXT.md § D-70 — the SAME vocabulary
# tests/test_app_compare_route.py's own module-level constant carries,
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


def test_get_methodology_returns_200_with_no_query_string_at_all():
    response = client.get("/methodology")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_methodology_is_identical_regardless_of_query_string():
    """PRV-05: the page persists independently of any comparison — a
    query string (which a comparison-scoped page like /compare or
    /assumptions would use to select a production) has no effect here."""
    bare = client.get("/methodology")
    with_junk = client.get("/methodology", params={"candidate_cities": "Nowhereville, ZZ"})
    assert bare.status_code == with_junk.status_code == 200
    assert bare.text == with_junk.text


def test_get_methodology_explains_the_basis_vocabulary():
    text = client.get("/methodology").text
    for term in ("sourced", "estimated", "modelling_assumption"):
        assert term in text


def test_get_methodology_explains_the_two_confidence_axes_are_distinct():
    text = client.get("/methodology").text
    assert "validated" in text
    assert "researched" in text
    # The four-tier source-document-reliability vocabulary is referenced
    # only descriptively (as "a different subject", never as a value a
    # Figure.confidence can take) — this page must not present the two
    # vocabularies as interchangeable.
    assert "never the same field" in text or "never combined into a single label" in text


def test_get_methodology_explains_honest_refusal_states():
    text = client.get("/methodology").text
    assert "unknown" in text.lower()
    assert "never a $0" in text or "never a $0 incentive" in text or "never a fabricated" in text.lower() or "0 incentive" in text.lower()


def test_get_methodology_permanent_exclusions_are_read_from_engine_not_hand_typed():
    """The rendered list must be EXACTLY engine.landed_cost
    .PERMANENT_EXCLUSIONS, proving this page cannot drift out of sync
    with the engine's own declared D-60 vocabulary."""
    text = client.get("/methodology").text
    for exclusion in PERMANENT_EXCLUSIONS:
        assert exclusion in text
    # The rendered LIST ITEMS themselves are never a dollar amount —
    # scoped to the actual <ul> markup, not the page's own surrounding
    # prose (which legitimately describes the "never a $0" rule in
    # words).
    exclusions_list = re.search(
        r'<ul class="pf-permanent-exclusions-list">.*?</ul>', text, re.DOTALL
    )
    assert exclusions_list is not None
    assert re.search(r"\$\s?0(\.0+)?\b", exclusions_list.group(0)) is None


def test_get_methodology_cost_categories_are_read_from_engine_not_hand_typed():
    text = client.get("/methodology").text
    for category in COST_CATEGORIES:
        assert category in text


def test_get_methodology_links_to_the_assumptions_panel():
    text = client.get("/methodology").text
    assert 'href="/assumptions"' in text or "/assumptions" in text


def test_get_methodology_d70_vocabulary_gate_over_rendered_html():
    response = client.get("/methodology")
    assert response.status_code == 200
    violations = [
        word for word in _PRESCRIPTIVE_VOCABULARY if _VOCABULARY_PATTERNS[word].search(response.text)
    ]
    assert not violations, f"prescriptive vocabulary found in rendered /methodology HTML: {violations}"


def test_static_provenance_css_d70_vocabulary_gate():
    import pathlib

    text = pathlib.Path("app/static/provenance.css").read_text(encoding="utf-8")
    violations = [
        word for word in _PRESCRIPTIVE_VOCABULARY if _VOCABULARY_PATTERNS[word].search(text)
    ]
    assert not violations, f"prescriptive vocabulary found in provenance.css: {violations}"


def test_get_methodology_never_fabricates_a_source_or_date():
    """This page renders no comparison-scoped Figure at all (it is
    comparison-independent, PRV-05) — assert it contains no
    `pf-figure-source` link and no fabricated `date_checked` claim,
    since anything presented as a citation here would necessarily be
    invented rather than drawn from a real request."""
    text = client.get("/methodology").text
    assert 'class="pf-figure-source"' not in text
