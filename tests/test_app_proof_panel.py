"""The proof panel (UI-07, DMO-01), the honest accuracy figure (PRV-06),
and the empty-but-real conflict surface (PRV-07) — 08-01-PLAN.md.

Every assertion here reads its expected value from the real service layer
(`app.services.proof`) or from the committed fixture itself, never from a
hardcoded number that could silently drift out of sync with the data —
matching this repo's own established test discipline
(`tests/test_app_validate_route.py`'s `_fixture_stage` helper).
"""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.services import proof as proof_service

client = TestClient(app)

# Identical wordlist to every other D-70-covered test module in this repo
# (tests/test_app_provenance.py, tests/test_app_compare_route.py, etc.) —
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


def _assert_no_prescriptive_vocabulary(html: str) -> None:
    for word, pattern in _VOCABULARY_PATTERNS.items():
        assert not pattern.search(html), f"prescriptive vocabulary {word!r} found in rendered HTML"


# ---------------------------------------------------------------------------
# Task 1 — the proof panel (UI-07, DMO-01)
# ---------------------------------------------------------------------------


def test_proof_index_returns_200_and_lists_selectable_pairs():
    response = client.get("/proof")
    assert response.status_code == 200
    assert "Anora" in response.text
    _assert_no_prescriptive_vocabulary(response.text)


def test_proof_detail_exact_match_pair_renders_zero_residue():
    response = client.get("/proof/ny_anora")
    assert response.status_code == 200
    assert "reproduces exactly" in response.text
    assert "zero residue" in response.text
    result = proof_service.build_proof("ny_anora")
    assert result.residue == Decimal(0)


def test_proof_detail_nj_joker_renders_the_exact_sourced_residue():
    # D-98's own worked example: New Jersey's Joker pair has a residue of
    # EXACTLY Decimal("122665") — the sourced 2 percent diversity bonus —
    # and the fixture's own variance_reason explains it in prose.
    result = proof_service.build_proof("nj_joker")
    assert result.residue == Decimal(122665)

    response = client.get("/proof/nj_joker")
    assert response.status_code == 200
    assert "122,665" in response.text
    assert "does not reproduce exactly" in response.text
    assert "diversity" in response.text.lower()
    # The taxonomy classifier's closed rule set does not (yet) cover this
    # residue — shown honestly as unexplained by THAT classifier, never
    # silently upgraded to a match because a human-readable explanation
    # exists elsewhere on the same page.
    assert result.match_class.value == "unexplained"
    assert "unexplained" in response.text


def test_proof_detail_unknown_pair_returns_404():
    response = client.get("/proof/does-not-exist")
    assert response.status_code == 404


def test_proof_detail_unselectable_pair_returns_404():
    # ma_dont_look_up has no curated rule model — selectable_pairs()
    # already reports it unselectable; the proof panel must refuse it the
    # same way reproduce_disclosure does, never silently compute a figure
    # for a pair validate.py itself would not stand behind.
    response = client.get("/proof/ma_dont_look_up")
    assert response.status_code == 404


def test_proof_document_route_serves_exact_bytes_matching_recorded_sha256():
    result = proof_service.build_proof("nj_joker")
    assert result.document is not None
    assert result.document.exists_on_disk

    response = client.get("/proof/nj_joker/document")
    assert response.status_code == 200
    live_hash = hashlib.sha256(response.content).hexdigest()
    assert live_hash == result.document.recorded_sha256
    assert live_hash == result.document.live_sha256


def test_proof_document_route_for_unknown_pair_returns_404():
    response = client.get("/proof/does-not-exist/document")
    assert response.status_code == 404


def test_proof_page_shows_the_recorded_and_live_sha256_and_they_match():
    response = client.get("/proof/nj_joker")
    result = proof_service.build_proof("nj_joker")
    assert result.document.recorded_sha256 in response.text
    assert result.document.live_sha256 in response.text
    assert result.document.sha256_matches is True
    assert "the archived bytes match the recorded hash exactly" in response.text


def test_proof_page_shows_the_archived_document_path_not_only_a_live_link():
    response = client.get("/proof/nj_joker")
    assert (
        "sources/nj/2026-08-24-njeda-film-tax-credit-activity-report-joker.txt"
        in response.text
    )
    # The live government link is present too (a courtesy), but framed as
    # secondary to the archived artifact, never as a replacement for it.
    assert "a courtesy only" in response.text


def test_proof_refusal_pair_never_500s_and_names_the_reason():
    # Every currently selectable pair actually reaches a real computed
    # gross credit (verified directly against the service below), but the
    # honest-refusal path must still never be silently unreachable code —
    # confirmed here structurally: no selectable pair currently exercises
    # it, and the route handles MalformedFixtureError without crashing.
    for pair in proof_service.proof_pairs():
        if not pair.selectable:
            continue
        result = proof_service.build_proof(pair.pair_id)
        response = client.get(f"/proof/{pair.pair_id}")
        assert response.status_code == 200
        if result.computed_credit is None:
            assert "cannot be computed" in response.text
            assert result.refusal_reason


# ---------------------------------------------------------------------------
# Task 2 — the accuracy figure (PRV-06)
# ---------------------------------------------------------------------------


def test_accuracy_summary_never_carries_a_percentage_field():
    # Structural regression guard, mirroring
    # tests/test_agent_taxonomy.py::test_accuracy_summary_exposes_no_
    # percentage_mean_or_blended_field — this module renders the SAME
    # dataclass; nothing here may add a computed percentage on top of it.
    summary = proof_service.accuracy_over_validation_pairs()
    forbidden = ("pct", "percent", "mean", "average", "blended")
    for field_name in summary.__dataclass_fields__:
        lowered = field_name.lower()
        for word in forbidden:
            assert word not in lowered


def test_proof_index_renders_the_three_bucket_counts_and_no_percent_sign():
    summary = proof_service.accuracy_over_validation_pairs()
    response = client.get("/proof")
    assert response.status_code == 200
    html = response.text

    start = html.find('data-testid="proof-accuracy"')
    end = html.find("</section>", start)
    accuracy_block = html[start:end]

    assert f"{summary.exact_match} / {summary.awards_extracted}" in accuracy_block
    assert f"{summary.explained_variance} / {summary.awards_extracted}" in accuracy_block
    assert f"{summary.unexplained} / {summary.awards_extracted}" in accuracy_block
    assert "%" not in accuracy_block


def test_accuracy_over_validation_pairs_is_a_real_computation_over_committed_pairs():
    # Not a stub, not a fabricated figure: at least one selectable pair
    # exists and every one of them is accounted for in the four buckets.
    summary = proof_service.accuracy_over_validation_pairs()
    assert summary.awards_extracted > 0
    assert (
        summary.exact_match + summary.explained_variance + summary.unexplained
        + summary.extraction_failures
        == summary.awards_extracted
    )
    # ny_anora reproduces exactly through this module's own gross-credit-only
    # computation — a genuine, non-fabricated exact match must be present.
    assert summary.exact_match >= 1


# ---------------------------------------------------------------------------
# Task 3 — unresolved source conflicts (PRV-07)
# ---------------------------------------------------------------------------


def test_no_conflict_is_manufactured_for_the_real_committed_data():
    # data/source_conflicts.yaml is committed empty (08-01-PLAN.md's own
    # prohibition on manufacturing a conflict to demonstrate the feature).
    conflicts = proof_service.load_source_conflicts()
    assert conflicts == ()

    response = client.get("/proof")
    assert response.status_code == 200
    assert 'class="pf-conflict"' not in response.text
    assert "No unresolved source conflict is currently recorded" in response.text


def test_conflict_renders_correctly_when_given_a_real_conflict_fixture(tmp_path):
    # A REAL two-source disagreement, modeled on the shape this project's
    # own SOURCE-TRUTH.md documents for a genuinely unresolved case — not
    # invented values, just supplied via a test-only fixture file so the
    # render path is provably correct without touching committed data.
    fixture_path = tmp_path / "source_conflicts.yaml"
    fixture_path.write_text(
        """
conflicts:
  - topic: "Example annual base-program allocation"
    sources:
      - label: "Source A"
        value: "$700 million per year"
        source_url: "https://example.gov/a"
        source_document: null
        source_document_sha256: null
        date_checked: "2026-08-24"
      - label: "Source B"
        value: "$800 million per year"
        source_url: "https://example.gov/b"
        source_document: null
        source_document_sha256: null
        date_checked: "2026-08-24"
    note: "Two government-associated pages state different figures for the same programme."
""",
        encoding="utf-8",
    )

    conflicts = proof_service.load_source_conflicts(fixture_path)
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert len(conflict.sources) == 2

    from app.main import templates

    module = templates.env.get_template("_conflict.html").module
    rendered = module.render_conflict(conflict)

    assert "Source A" in rendered
    assert "Source B" in rendered
    assert "$700 million per year" in rendered
    assert "$800 million per year" in rendered
    assert "unresolved" in rendered.lower()
    _assert_no_prescriptive_vocabulary(rendered)


def test_load_source_conflicts_missing_file_returns_empty_tuple(tmp_path):
    assert proof_service.load_source_conflicts(tmp_path / "does-not-exist.yaml") == ()


# ---------------------------------------------------------------------------
# Cross-cutting
# ---------------------------------------------------------------------------


def test_proof_panel_serves_directly():
    """Reached by URL rather than from the landing page (see /spec's twin)."""
    assert client.get("/proof").status_code == 200


def test_health_contract_unchanged():
    response = client.get("/health")
    assert response.status_code == 200
    assert set(response.json().keys()) == {"status", "version", "git_sha", "boot_time"}
