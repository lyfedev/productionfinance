"""Fixture-shape assertions for tests/fixtures/validation_pairs/ (SRC-03).

These tests do not assert that any engine reproduces a given figure — Phase 5's
Job 1 does that. This suite asserts the fixture *set itself* is structurally
honest: every committed pair carries the minimum field set (D-03), a declared
assertion tier (D-04), a legal disclosure stage that is never blended across
cohorts (D-07), and a source citation. It also guards against the specific
failure mode of an empty or malformed fixture directory silently reporting
green (T-01-15).
"""

from decimal import Decimal, InvalidOperation
from glob import glob

import pytest
import yaml

FIXTURE_DIR = "tests/fixtures/validation_pairs"

# Sorted glob: parametrization order is deterministic across runs, on any OS,
# independent of filesystem directory-listing order.
FIXTURE_PATHS = sorted(glob(f"{FIXTURE_DIR}/*.yaml"))

# A parametrized test over an empty collection reports a vacuous green — it
# asserts nothing while looking like a passing suite. Fail collection itself
# rather than let that happen silently (T-01-15).
if not FIXTURE_PATHS:
    raise RuntimeError(
        f"No fixture files found under {FIXTURE_DIR}/*.yaml — an empty "
        "validation-pair set must fail loudly, not report a vacuous green."
    )

REQUIRED_FIELDS = {
    "production_title",
    "jurisdiction_id",
    "program_id",
    "production_type",
    "season",
    "qualified_spend",
    "credit_amount",
    "diversity_credit_amount",
    "disclosure_stage",
    "status",
    "blocker",
    "source_url",
    "source_document",
    "source_document_sha256",
    "report_period",
    "date_checked",
    "assertion",
    "notes",
}

LEGAL_DISCLOSURE_STAGES = {"issued", "allocated", "estimated"}
LEGAL_STATUSES = {"active", "blocked"}
LEGAL_ASSERTION_MODES = {"exact", "bounded"}

MONEY_FIELDS = ("qualified_spend", "credit_amount", "diversity_credit_amount")


def _load(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=FIXTURE_PATHS)
def test_fixture_has_required_fields(path):
    data = _load(path)

    missing = REQUIRED_FIELDS - data.keys()
    assert not missing, f"{path} is missing required fields: {missing}"

    for field in ("source_url", "disclosure_stage", "status"):
        value = data[field]
        assert isinstance(value, str) and value.strip(), (
            f"{path}: '{field}' must be a non-empty string, got {value!r}"
        )

    assert data["disclosure_stage"] in LEGAL_DISCLOSURE_STAGES, (
        f"{path}: disclosure_stage {data['disclosure_stage']!r} not in "
        f"{LEGAL_DISCLOSURE_STAGES}"
    )
    assert data["status"] in LEGAL_STATUSES, (
        f"{path}: status {data['status']!r} not in {LEGAL_STATUSES}"
    )

    if data["status"] == "active":
        for field in MONEY_FIELDS:
            raw = data.get(field)
            if field == "diversity_credit_amount" and raw is None:
                # Not every jurisdiction publishes a diversity/equity credit
                # line item (CA and NJ's disclosures do not). null means "no
                # such column exists in the source" — distinct from "0",
                # which would assert the column exists and reported zero.
                # qualified_spend and credit_amount remain mandatory strings
                # for every active fixture; only this field may be absent.
                continue
            assert isinstance(raw, str), (
                f"{path}: money field '{field}' must be a YAML string "
                f"(never a float), got {type(raw).__name__}: {raw!r}"
            )
            try:
                Decimal(raw)
            except InvalidOperation:
                pytest.fail(f"{path}: '{field}' value {raw!r} does not parse to Decimal")

    assertion = data.get("assertion")
    assert isinstance(assertion, dict), f"{path}: 'assertion' must be a mapping"
    mode = assertion.get("mode")
    assert mode in LEGAL_ASSERTION_MODES, (
        f"{path}: assertion.mode {mode!r} not in {LEGAL_ASSERTION_MODES}"
    )
    if mode == "bounded":
        assert assertion.get("tolerance_bps") is not None, (
            f"{path}: assertion.mode is 'bounded' but tolerance_bps is missing"
        )
        variance_reason = assertion.get("variance_reason")
        assert isinstance(variance_reason, str) and variance_reason.strip(), (
            f"{path}: assertion.mode is 'bounded' but variance_reason is empty"
        )


def test_fixture_filenames_are_unique():
    """Two disclosure batches of the same production must not collapse into
    one record on disk (PITFALLS §B3) — enforced at the filename level since
    D-01 puts one pair per file."""
    import os

    basenames = [os.path.basename(p) for p in FIXTURE_PATHS]
    duplicates = {name for name in basenames if basenames.count(name) > 1}
    assert not duplicates, f"Duplicate fixture filenames found: {duplicates}"


def test_disclosure_stages_are_separable():
    """D-07: disclosure stages are never averaged together. Every fixture
    belongs to exactly one stage cohort, stage values are drawn only from the
    three legal stages, and no fixture carries a stage value blended from more
    than one — this is a schema-level guarantee, not a reporting-layer one
    (PITFALLS §B1, §B5; ROADMAP Phase 5 success criterion 4)."""
    fixtures = [_load(p) for p in FIXTURE_PATHS]

    stages_seen = {f["disclosure_stage"] for f in fixtures}
    assert stages_seen <= LEGAL_DISCLOSURE_STAGES, (
        f"Unexpected disclosure_stage values: {stages_seen - LEGAL_DISCLOSURE_STAGES}"
    )

    for fixture in fixtures:
        stage = fixture["disclosure_stage"]
        # A single scalar string field cannot itself represent more than one
        # cohort; this assertion documents and locks that invariant so a
        # future schema change (e.g. a list-valued stage) cannot silently
        # blend cohorts without this test catching it.
        assert isinstance(stage, str) and stage in LEGAL_DISCLOSURE_STAGES, (
            f"Fixture disclosure_stage must be exactly one legal stage, got {stage!r}"
        )
