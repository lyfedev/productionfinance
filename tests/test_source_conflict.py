"""PRV-07/D-99 — the source-conflict data model and its render path,
`app.services.proof.load_source_conflicts` /
`app.templates._conflict.html::render_conflict`.

Distinct focus from `tests/test_app_proof_panel.py`: this module tests the
conflict machinery in isolation (the dataclasses, the loader's edge cases,
the macro's rendering rules) rather than the proof panel's HTTP surface.
"""

from __future__ import annotations

from app.main import templates
from app.services.proof import (
    SOURCE_CONFLICTS_PATH,
    ConflictSource,
    SourceConflict,
    load_source_conflicts,
)

_render_conflict = templates.env.get_template("_conflict.html").module.render_conflict


# ---------------------------------------------------------------------------
# The real committed file — never manufactured (08-01-PLAN.md's own
# prohibition: "do not manufacture a conflict to demonstrate the feature").
# ---------------------------------------------------------------------------


def test_the_real_committed_source_conflicts_file_is_empty():
    # This is the honest state of this project's research as of this
    # phase: both candidate conflicts investigated (NY $700M/$800M, GA
    # loan-out withholding) were closed against a primary source, not left
    # open. A future session may add a real entry; nothing may be added
    # here to make this test (or the feature) look more populated.
    assert SOURCE_CONFLICTS_PATH.is_file()
    assert load_source_conflicts() == ()


# ---------------------------------------------------------------------------
# load_source_conflicts — loader edge cases
# ---------------------------------------------------------------------------


def test_missing_file_returns_empty_tuple_not_an_exception(tmp_path):
    assert load_source_conflicts(tmp_path / "nope.yaml") == ()


def test_file_with_empty_conflicts_key_returns_empty_tuple(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("conflicts: []\n", encoding="utf-8")
    assert load_source_conflicts(path) == ()


def test_loads_multiple_conflicts_each_with_multiple_sources(tmp_path):
    path = tmp_path / "conflicts.yaml"
    path.write_text(
        """
conflicts:
  - topic: "Topic one"
    sources:
      - label: "A"
        value: "10"
        source_url: "https://example.com/a"
        source_document: "sources/example/a.pdf"
        source_document_sha256: "deadbeef"
        date_checked: "2026-01-01"
      - label: "B"
        value: "20"
        source_url: "https://example.com/b"
        source_document: null
        source_document_sha256: null
        date_checked: "2026-01-02"
      - label: "C"
        value: "30"
        source_url: null
        source_document: null
        source_document_sha256: null
        date_checked: null
    note: "Three sources, three different figures."
  - topic: "Topic two"
    sources:
      - label: "D"
        value: "x"
        source_url: null
        source_document: null
        source_document_sha256: null
        date_checked: null
      - label: "E"
        value: "y"
        source_url: null
        source_document: null
        source_document_sha256: null
        date_checked: null
    note: "A second, unrelated conflict."
""",
        encoding="utf-8",
    )

    conflicts = load_source_conflicts(path)
    assert len(conflicts) == 2

    first = conflicts[0]
    assert isinstance(first, SourceConflict)
    assert first.topic == "Topic one"
    assert len(first.sources) == 3
    assert all(isinstance(s, ConflictSource) for s in first.sources)
    assert first.sources[2].source_url is None
    assert first.sources[2].source_document is None

    second = conflicts[1]
    assert second.topic == "Topic two"
    assert len(second.sources) == 2


# ---------------------------------------------------------------------------
# render_conflict — the macro's rendering rules
# ---------------------------------------------------------------------------


def _conflict(**overrides) -> SourceConflict:
    sources = overrides.pop(
        "sources",
        (
            ConflictSource(
                label="Source A",
                value="$700 million",
                source_url="https://example.gov/a",
                source_document=None,
                source_document_sha256=None,
                date_checked="2026-01-01",
            ),
            ConflictSource(
                label="Source B",
                value="$800 million",
                source_url="https://example.gov/b",
                source_document=None,
                source_document_sha256=None,
                date_checked="2026-01-02",
            ),
        ),
    )
    defaults = {"topic": "Example topic", "sources": sources, "note": "Example note."}
    defaults.update(overrides)
    return SourceConflict(**defaults)


def test_render_conflict_shows_every_source_with_equal_weight():
    rendered = _render_conflict(_conflict())
    assert "Source A" in rendered
    assert "Source B" in rendered
    assert "$700 million" in rendered
    assert "$800 million" in rendered
    assert rendered.index("Source A") < rendered.index("Source B")


def test_render_conflict_states_the_disagreement_is_unresolved():
    rendered = _render_conflict(_conflict())
    assert "unresolved" in rendered.lower()


def test_render_conflict_never_declares_a_winner_or_an_average():
    rendered = _render_conflict(_conflict())
    lowered = rendered.lower()
    for forbidden in ("winner", "correct answer", "average of", "the right figure"):
        assert forbidden not in lowered


def test_render_conflict_shows_the_note():
    rendered = _render_conflict(_conflict(note="A genuinely unresolved disagreement."))
    assert "A genuinely unresolved disagreement." in rendered


def test_render_conflict_with_archived_document_shows_path_and_sha256():
    sources = (
        ConflictSource(
            label="Archived source",
            value="30 percent",
            source_url=None,
            source_document="sources/example/doc.pdf",
            source_document_sha256="cafebabe",
            date_checked="2026-01-01",
        ),
        ConflictSource(
            label="Other source",
            value="35 percent",
            source_url="https://example.gov/other",
            source_document=None,
            source_document_sha256=None,
            date_checked="2026-01-01",
        ),
    )
    rendered = _render_conflict(_conflict(sources=sources))
    assert "sources/example/doc.pdf" in rendered
    assert "cafebabe" in rendered


def test_render_conflict_with_no_citation_at_all_states_that_plainly():
    sources = (
        ConflictSource(
            label="Uncited source",
            value="unknown",
            source_url=None,
            source_document=None,
            source_document_sha256=None,
            date_checked=None,
        ),
        ConflictSource(
            label="Second source",
            value="also unknown",
            source_url=None,
            source_document=None,
            source_document_sha256=None,
            date_checked=None,
        ),
    )
    rendered = _render_conflict(_conflict(sources=sources))
    assert "no citation recorded" in rendered
