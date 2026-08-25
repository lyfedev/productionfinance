"""Structural assertions over .planning/SOURCE-TRUTH.md and the sources/
archive (SRC-01, SRC-02, SRC-04, SRC-05).

This suite does not judge whether an answer is *correct* — whether a source
is genuinely primary, and whether a conflict is genuinely closed, are human
judgments (01-VALIDATION.md), not runtime assertions. What it does assert is
that the record is structurally honest: every requirement has exactly one
entry carrying the minimum provenance fields (D-11), and that the archive,
the manifest, and the validation-pair fixtures all agree with each other —
the assertion that makes "we extracted this figure from *this exact
byte-identical document*" (D-10) structurally true rather than aspirational.
"""

import hashlib
import re
from datetime import date
from glob import glob

import pytest
import yaml

SOURCE_TRUTH_PATH = ".planning/SOURCE-TRUTH.md"
MANIFEST_PATH = "sources/MANIFEST.yaml"
FIXTURE_DIR = "tests/fixtures/validation_pairs"

REQUIREMENT_IDS = ("SRC-01", "SRC-02", "SRC-04", "SRC-05")

# SRC-04's source is the project owner's direct confirmation, not a public
# URL — the plan explicitly instructs the entry to say so rather than invent
# a citation, so the URL requirement below is scoped to exclude it.
REQUIRES_URL = {"SRC-01", "SRC-02", "SRC-05"}

# Fixed confidence-tier vocabulary this project uses throughout
# 01-RESEARCH.md and SOURCE-TRUTH.md — a tier outside this set is either a
# typo or an invented tier not grounded in the project's own vocabulary.
LEGAL_CONFIDENCE_TIERS = {"LOW", "MEDIUM", "MEDIUM-HIGH", "HIGH"}

# Headings look like "## SRC-01 — New York's annual cap" — split on any line
# starting with "## SRC-" so an entry's own body text can safely mention
# other requirement IDs without corrupting section boundaries (unlike a
# plain substring split, which would break the moment one entry's prose
# refers to another SRC-0x id).
_SECTION_RE = re.compile(r"^##\s+(SRC-\d\d)\b.*$", re.MULTILINE)


def _load_source_truth_text() -> str:
    with open(SOURCE_TRUTH_PATH) as f:
        return f.read()


def _split_into_sections(text: str) -> dict:
    """Return {requirement_id: section_body} for every '## SRC-xx' heading in
    the file. section_body runs from just after the heading line to the
    start of the next '## SRC-xx' heading (or end of file)."""
    matches = list(_SECTION_RE.finditer(text))
    sections: dict[str, list[str]] = {}
    for i, m in enumerate(matches):
        req_id = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.setdefault(req_id, []).append(text[start:end])
    return sections


def _extract_confidence_tier(section: str) -> str | None:
    m = re.search(r"\*\*Confidence:\*\*\s*([A-Z][A-Z-]*)", section)
    return m.group(1) if m else None


def _extract_date_checked(section: str) -> str | None:
    m = re.search(r"\*\*date_checked:\*\*\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", section)
    return m.group(1) if m else None


def _extract_urls(section: str) -> list[str]:
    return re.findall(r"https?://[^\s`)\]]+", section)


# ---------------------------------------------------------------------------
# Group 1: entry shape (D-11)
# ---------------------------------------------------------------------------


def test_source_truth_file_exists_and_is_non_empty():
    with open(SOURCE_TRUTH_PATH) as f:
        content = f.read()
    assert content.strip(), f"{SOURCE_TRUTH_PATH} exists but is empty"


def test_every_requirement_has_exactly_one_section():
    text = _load_source_truth_text()
    sections = _split_into_sections(text)

    missing = set(REQUIREMENT_IDS) - sections.keys()
    assert not missing, f"{SOURCE_TRUTH_PATH} is missing section(s) for: {missing}"

    duplicated = {req_id: len(bodies) for req_id, bodies in sections.items() if len(bodies) > 1}
    assert not duplicated, (
        f"{SOURCE_TRUTH_PATH} has more than one '## {{req_id}}' heading for: "
        f"{duplicated} — D-11 requires exactly one entry per question"
    )


@pytest.mark.parametrize("requirement_id", REQUIREMENT_IDS)
def test_every_entry_has_provenance(requirement_id):
    """D-11: every entry carries a question, a non-empty answer, a
    date_checked that parses as a date, and a confidence tier drawn from the
    project's fixed vocabulary. SRC-01, SRC-02 and SRC-05 additionally
    require at least one URL — SRC-04 is exempt because its source is an
    owner confirmation, not a public document (see REQUIRES_URL above)."""
    text = _load_source_truth_text()
    sections = _split_into_sections(text)
    section = sections[requirement_id][0]

    assert "**Question" in section or "**Question (verbatim" in section, (
        f"{requirement_id}: entry is missing a '**Question' field"
    )
    assert "**Answer" in section, f"{requirement_id}: entry is missing an '**Answer' field"
    # The answer itself must be non-trivial, not just the literal word
    # "Answer:" with nothing meaningful after it before the next field. The
    # entries in this file bold the lead sentence of the answer inline
    # ("**Answer: CLOSED against the enacted budget bill text.**"), so the
    # answer text sits *inside* the bold span, between "Answer:" and the
    # closing "**" — not after a standalone "**Answer:**" marker.
    answer_match = re.search(r"\*\*Answer:\s*(.*?)\*\*", section, re.DOTALL)
    assert answer_match and answer_match.group(1).strip(), (
        f"{requirement_id}: '**Answer' field is present but has no content"
    )

    date_checked = _extract_date_checked(section)
    assert date_checked, f"{requirement_id}: entry is missing a 'date_checked' value"
    try:
        date.fromisoformat(date_checked)
    except ValueError:
        pytest.fail(f"{requirement_id}: date_checked {date_checked!r} does not parse as a date")

    confidence = _extract_confidence_tier(section)
    assert confidence, f"{requirement_id}: entry is missing a '**Confidence:**' field"
    assert confidence in LEGAL_CONFIDENCE_TIERS, (
        f"{requirement_id}: confidence tier {confidence!r} not in {LEGAL_CONFIDENCE_TIERS}"
    )

    what_refuted = "what was refuted or refined" in section.lower()
    assert what_refuted, (
        f"{requirement_id}: entry is missing a 'What was refuted or refined' section (D-12)"
    )

    if requirement_id in REQUIRES_URL:
        urls = _extract_urls(section)
        assert urls, (
            f"{requirement_id}: entry must contain at least one primary-source URL"
        )
    # else: SRC-04's source is the project owner's direct confirmation, not
    # a public URL — the plan explicitly instructs the entry to say so
    # rather than invent a citation, so no URL is required here.


def test_src04_has_reverification_log():
    """SRC-04's outstanding work is a re-check against the submission portal
    at filing time (Phase 8), which this phase cannot observe — the
    predicate this test can check is only that the log *exists* and carries
    the original dated confirmation; whether a later append happened is a
    'backstop' truth per 01-05-PLAN.md's flagged planner assumption, and a
    verifier that cannot confirm it with explicit evidence must abstain
    rather than pass it silently."""
    text = _load_source_truth_text()
    sections = _split_into_sections(text)
    section = sections["SRC-04"][0]

    assert "Re-verification log" in section, (
        "SRC-04: entry is missing the 'Re-verification log' subsection"
    )
    log_start = section.index("Re-verification log")
    log_body = section[log_start:]
    assert re.search(r"2026-08-24", log_body), (
        "SRC-04: Re-verification log is missing the original 2026-08-24 dated confirmation line"
    )


# ---------------------------------------------------------------------------
# Group 2: manifest reconciliation (D-10) — the assertion that makes the
# audit trail structurally true rather than aspirational.
# ---------------------------------------------------------------------------


def _load_manifest() -> list[dict]:
    with open(MANIFEST_PATH) as f:
        data = yaml.safe_load(f)
    return data["documents"]


def test_manifest_hashes_match_files_on_disk():
    documents = _load_manifest()
    assert documents, f"{MANIFEST_PATH} has no documents — nothing to reconcile"

    failures = []
    for doc in documents:
        path = doc["path"]
        try:
            with open(path, "rb") as f:
                actual_sha256 = hashlib.sha256(f.read()).hexdigest()
        except FileNotFoundError:
            failures.append(f"{path}: file does not exist on disk")
            continue
        if actual_sha256 != doc["sha256"]:
            failures.append(
                f"{path}: recorded sha256 {doc['sha256']} does not match "
                f"computed sha256 {actual_sha256}"
            )
    assert not failures, "Manifest/disk hash mismatch(es):\n" + "\n".join(failures)


def test_every_archived_file_has_a_manifest_row():
    """The reverse direction of the reconciliation: an archived document
    cannot sit in the repository uncited and unhashed. Every file under
    sources/ other than MANIFEST.yaml itself must appear as a manifest
    `path`."""
    import os

    manifest_paths = {doc["path"] for doc in _load_manifest()}

    on_disk = []
    for root, _dirs, files in os.walk("sources"):
        for name in files:
            rel_path = os.path.join(root, name).replace(os.sep, "/")
            if rel_path == MANIFEST_PATH:
                continue
            on_disk.append(rel_path)

    missing_rows = sorted(set(on_disk) - manifest_paths)
    assert not missing_rows, (
        f"Archived file(s) under sources/ with no sources/MANIFEST.yaml row: {missing_rows}"
    )


# ---------------------------------------------------------------------------
# Group 3: cross-reference — a fixture cannot cite a document that was
# never archived.
# ---------------------------------------------------------------------------


def test_fixture_source_documents_resolve_to_manifest():
    manifest_paths = {doc["path"] for doc in _load_manifest()}

    fixture_paths = sorted(glob(f"{FIXTURE_DIR}/*.yaml"))
    assert fixture_paths, f"No fixture files found under {FIXTURE_DIR}/*.yaml"

    failures = []
    for path in fixture_paths:
        with open(path) as f:
            data = yaml.safe_load(f)
        source_document = data.get("source_document")
        if source_document is None:
            # A blocked fixture (D-06) may legitimately have no archived
            # source — nothing to cross-reference.
            continue
        if source_document not in manifest_paths:
            failures.append(f"{path}: source_document {source_document!r} has no manifest row")

    assert not failures, "Fixture(s) citing an unarchived source_document:\n" + "\n".join(
        failures
    )
