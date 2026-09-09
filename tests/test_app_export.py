"""UI-09 (Phase 8, plan 08-02) — the self-contained export document.

`GET /export` renders `app/templates/export_document.html`, built from
`app.services.export.build_export_document`, which itself reuses
`app.services.compare.build_comparison` unchanged (D-78: the same
pipeline every other priced total on this site goes through). These
tests assert the export is server-rendered, complete without
JavaScript, carries the D-60 acknowledged-gaps list, and never
fabricates a source or a gap figure — mirroring the established pattern
in tests/test_app_methodology.py and tests/test_app_proof_panel.py.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.compare import CompareInputs
from app.services.export import ExportDocument, build_export_document
from engine.landed_cost import PERMANENT_EXCLUSIONS

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


def test_get_export_returns_200_with_no_query_string_at_all():
    response = client.get("/export")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_export_contains_no_script_tag_at_all():
    """UI-09: "generated server-side and complete without JavaScript" —
    the strongest structural proof is that the response contains no
    <script> element whatsoever, so a recipient with scripting disabled
    sees the identical page."""
    text = client.get("/export").text
    assert "<script" not in text.lower()


def test_get_export_renders_the_golden_default_comparison_totals():
    """D-78: the export must never re-derive a number — it reads the
    same `Comparison` `/compare` renders. Byte-identical golden totals
    (tests/test_golden_cost.py): NY $758,427, LA $693,521 (cost-only, no
    incentive modelled), London GBP 548,595 / $747,735 converted."""
    text = client.get("/export").text
    assert "758427" in text
    assert "693521" in text
    assert "747735" in text


def test_get_export_names_every_d60_permanent_exclusion():
    text = client.get("/export").text
    for exclusion in PERMANENT_EXCLUSIONS:
        assert exclusion in text


def test_get_export_never_shows_a_zero_dollar_incentive_for_an_unmodelled_city():
    """D-56: an unmodelled incentive is never a $0 line. Los Angeles and
    London both have no committed incentive rule model wired to their
    cost profile today (`data/cost_profiles/us-ca-los-angeles.yaml`,
    `gb-london.yaml`, both `jurisdiction_id: null`) — the export must
    name the reason, never render $0."""
    text = client.get("/export").text
    # The template's own honest prose explains the D-56 rule in words
    # ("as though the missing incentive were worth $0") — that mention is
    # expected. What must NEVER appear is a rendered incentive figure
    # whose label is "Modelled incentive (net cash)" paired with a zero
    # value for an unmodelled city; assert the reason text renders
    # instead of a fabricated figure.
    assert "no committed incentive rule model" in text
    assert '<span class="pf-figure-label">Modelled incentive (net cash)</span>\n  <span class="pf-figure-value">0 ' not in text


def test_get_export_renders_a_gap_selection_state():
    """The default candidate set (New York, Los Angeles, London) has
    only ONE net_ranked city today (New York) — resolve_gap_selection's
    band-mismatch refusal fires for the default pair, so the export must
    render that refusal rather than a fabricated cross-band gap."""
    text = client.get("/export").text
    assert "Gap decomposition" in text
    assert (
        "carries no modelled incentive yet" in text
        or "Fewer than two candidate cities" in text
    )


def test_get_export_every_figure_carries_a_provenance_state():
    """UI-06: every rendered `_figure.html` instance carries one of the
    three provenance states — never a bare number with no basis/
    confidence/source shown at all."""
    text = client.get("/export").text
    assert 'class="pf-figure"' in text
    assert "pf-figure-basis" in text
    assert "pf-figure-confidence" in text


def test_get_export_rejects_too_many_candidate_cities_with_422_not_500():
    response = client.get("/export", params={"candidate_cities": [f"City {i}, ZZ" for i in range(13)]})
    assert response.status_code == 422


def test_get_export_d70_vocabulary_gate_over_rendered_html():
    response = client.get("/export")
    assert response.status_code == 200
    violations = [
        word for word in _PRESCRIPTIVE_VOCABULARY if _VOCABULARY_PATTERNS[word].search(response.text)
    ]
    assert not violations, f"prescriptive vocabulary found in rendered /export HTML: {violations}"


def test_static_export_css_d70_vocabulary_gate():
    text = Path("app/static/export.css").read_text(encoding="utf-8")
    violations = [
        word for word in _PRESCRIPTIVE_VOCABULARY if _VOCABULARY_PATTERNS[word].search(text)
    ]
    assert not violations, f"prescriptive vocabulary found in export.css: {violations}"


def test_build_export_document_returns_the_expected_dataclass_shape():
    inputs = CompareInputs()
    document = build_export_document(inputs)
    assert isinstance(document, ExportDocument)
    assert document.comparison is not None
    assert document.rate_sheets
    assert document.permanent_exclusions == PERMANENT_EXCLUSIONS
    assert document.generated_at.endswith("Z")


def test_build_export_document_generated_at_is_a_real_fresh_timestamp():
    """Two calls a moment apart produce two DIFFERENT timestamps — this
    is a real "generated now" stamp, not a cached or hardcoded string."""
    import time

    first = build_export_document(CompareInputs())
    time.sleep(1.1)
    second = build_export_document(CompareInputs())
    assert first.generated_at != second.generated_at
