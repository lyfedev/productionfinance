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


MIN_BLOCKER_LENGTH = 40


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=FIXTURE_PATHS)
def test_fixture_has_required_fields(path):
    data = _load(path)

    missing = REQUIRED_FIELDS - data.keys()
    assert not missing, f"{path} is missing required fields: {missing}"

    for field in ("source_url", "status"):
        value = data[field]
        assert isinstance(value, str) and value.strip(), (
            f"{path}: '{field}' must be a non-empty string, got {value!r}"
        )

    assert data["status"] in LEGAL_STATUSES, (
        f"{path}: status {data['status']!r} not in {LEGAL_STATUSES}"
    )

    # D-06: a blocked fixture has a *stricter* requirement than an active one
    # — it must explain itself — not a looser one. This is an explicit branch
    # per status, not a single loosened blanket assertion, because "may be
    # null" and "must be present" are different obligations, not degrees of
    # the same obligation.
    if data["status"] == "blocked":
        blocker = data.get("blocker")
        assert isinstance(blocker, str) and len(blocker.strip()) > MIN_BLOCKER_LENGTH, (
            f"{path}: status is 'blocked' but 'blocker' is not a string longer "
            f"than {MIN_BLOCKER_LENGTH} characters, got {blocker!r}"
        )
        # qualified_spend and disclosure_stage MAY be null while blocked —
        # not required to be null, just permitted to be, since a pair could
        # in principle be blocked for a reason unrelated to those two fields.
        disclosure_stage = data.get("disclosure_stage")
        assert disclosure_stage is None or disclosure_stage in LEGAL_DISCLOSURE_STAGES, (
            f"{path}: disclosure_stage {disclosure_stage!r} must be null or one "
            f"of {LEGAL_DISCLOSURE_STAGES} while blocked"
        )
    else:  # status == "active"
        blocker = data.get("blocker")
        assert blocker is None, (
            f"{path}: status is 'active' but 'blocker' is not null, got {blocker!r}"
        )
        disclosure_stage = data.get("disclosure_stage")
        assert isinstance(disclosure_stage, str) and disclosure_stage.strip(), (
            f"{path}: status is 'active' but 'disclosure_stage' is not a "
            f"non-empty string, got {disclosure_stage!r}"
        )
        assert disclosure_stage in LEGAL_DISCLOSURE_STAGES, (
            f"{path}: disclosure_stage {disclosure_stage!r} not in "
            f"{LEGAL_DISCLOSURE_STAGES}"
        )

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
    """D-07: disclosure stages are never averaged together. Every *active*
    fixture belongs to exactly one stage cohort, stage values are drawn only
    from the three legal stages, and no fixture carries a stage value blended
    from more than one — this is a schema-level guarantee, not a
    reporting-layer one (PITFALLS §B1, §B5; ROADMAP Phase 5 success criterion
    4). Blocked fixtures are exempt: D-06 permits disclosure_stage: null while
    blocked, and a null stage cannot itself blend cohorts."""
    fixtures = [_load(p) for p in FIXTURE_PATHS]
    active_fixtures = [f for f in fixtures if f["status"] == "active"]

    stages_seen = {f["disclosure_stage"] for f in active_fixtures}
    assert stages_seen <= LEGAL_DISCLOSURE_STAGES, (
        f"Unexpected disclosure_stage values: {stages_seen - LEGAL_DISCLOSURE_STAGES}"
    )

    for fixture in active_fixtures:
        stage = fixture["disclosure_stage"]
        # A single scalar string field cannot itself represent more than one
        # cohort; this assertion documents and locks that invariant so a
        # future schema change (e.g. a list-valued stage) cannot silently
        # blend cohorts without this test catching it.
        assert isinstance(stage, str) and stage in LEGAL_DISCLOSURE_STAGES, (
            f"Fixture disclosure_stage must be exactly one legal stage, got {stage!r}"
        )


def test_curated_jurisdictions_have_coverage():
    """The guard that makes the zero-Connecticut gap 01-RESEARCH.md's SRC-03
    Critical scope finding #2 found impossible to repeat silently: each of
    the four curated jurisdictions (JUR-01..04 — NY, CA, NJ, CT) must have at
    least one *active* validation pair. If Connecticut is later cut under
    deadline pressure (ROADMAP names JUR-04 as the first cuttable item in
    Accounts), this test is where that cut becomes a visible, deliberate
    change rather than an absence nobody notices."""
    fixtures = [_load(p) for p in FIXTURE_PATHS]
    curated = {"us-ny", "us-ca", "us-nj", "us-ct"}

    active_jurisdictions = {f["jurisdiction_id"] for f in fixtures if f["status"] == "active"}

    missing = curated - active_jurisdictions
    assert not missing, (
        f"Curated jurisdiction(s) with zero active validation coverage: {missing} "
        "— this is exactly the silent-gap failure mode SRC-03 Critical scope "
        "finding #2 identified for Connecticut; a jurisdiction losing its only "
        "active pair must fail this test, not go unnoticed."
    )


def test_committed_pair_count():
    """SRC-03's literal requirement ('all 11 sourced production/award pairs')
    made checkable rather than merely asserted: at least 11 fixtures exist,
    and at least 11 of them correspond to the named pairs in
    feasibility-incentives.md (by production_title, case-insensitive,
    ignoring a leading 'The '/trailing ', The' article so 'The Trial of the
    Chicago 7' and 'Trial of the Chicago 7, The' are recognized as the same
    production). A twelfth (Connecticut) pair is additive, not a
    substitution — see the 'Flagged planner assumption' note in
    01-04-PLAN.md."""
    fixtures = [_load(p) for p in FIXTURE_PATHS]
    assert len(fixtures) >= 11, (
        f"Expected at least 11 committed validation-pair fixtures (SRC-03), "
        f"found {len(fixtures)}"
    )

    named_pairs = {
        "anora",
        "succession s4",
        "the gilded age s2",
        "clueless s1 (reboot)",
        "disney's hexed",
        "joker",
        "the trial of the chicago 7",
        "don't look up",
        "madame web",
        "creed ii",
        "knock at the cabin",
    }

    def _normalize(title: str) -> str:
        t = title.strip().lower()
        # The leading/trailing "the" article ("The Trial of the Chicago 7"
        # vs "Trial of the Chicago 7, The") and a trailing parenthetical
        # like "(reboot)" are the only punctuation-level differences between
        # feasibility-incentives.md's naming and this project's fixtures.
        if t.endswith(", the"):
            t = "the " + t[: -len(", the")]
        t = t.replace(" (reboot)", "")
        return t

    def _fixture_key(fixture: dict) -> str:
        # D-03 splits a series' season into its own `season` field (e.g.
        # production_title "Succession", season 4) rather than folding it
        # into the title string. feasibility-incentives.md's naming keeps
        # them joined ("Succession S4"). Rejoin here so the two naming
        # conventions compare equal.
        title = _normalize(fixture["production_title"])
        season = fixture.get("season")
        if isinstance(season, int):
            title = f"{title} s{season}"
        return title

    fixture_titles = {_fixture_key(f) for f in fixtures}
    named_normalized = {_normalize(t) for t in named_pairs}

    matched = named_normalized & fixture_titles
    assert len(matched) >= 11, (
        f"Expected at least 11 fixtures matching the named pairs in "
        f"feasibility-incentives.md, matched {len(matched)}: {matched}. "
        f"Fixture titles present: {fixture_titles}"
    )


def accuracy_denominator_by_stage(fixtures=None):
    """D-07 made structural: returns a mapping from disclosure_stage to the
    count of *active* fixtures at that stage. Blocked fixtures appear in no
    key of the returned mapping (D-06 — excluded from the accuracy
    denominator). The function never returns, and never exposes, a single
    total across stages — that blended figure is exactly the failure ROADMAP
    Phase 5 success criterion 4 prohibits ("silently absorbing a real
    model bug"). Callers needing a grand total must sum the per-stage values
    themselves, deliberately, at the call site — not get one for free here.

    Importable by Phase 5's Job 1 mismatch taxonomy via
    ``from tests.test_validation_pair_fixtures import accuracy_denominator_by_stage``.
    """
    if fixtures is None:
        fixtures = [_load(p) for p in FIXTURE_PATHS]

    denominator: dict[str, int] = {}
    for fixture in fixtures:
        if fixture["status"] != "active":
            continue
        stage = fixture["disclosure_stage"]
        denominator[stage] = denominator.get(stage, 0) + 1
    return denominator


def test_denominator_excludes_blocked_and_separates_stages():
    """D-07's prohibition on a blended mean-error number, enforced at the
    data layer (ROADMAP Phase 5 success criterion 4) rather than deferred to
    the reporting layer."""
    fixtures = [_load(p) for p in FIXTURE_PATHS]
    result = accuracy_denominator_by_stage(fixtures)

    # One key per stage actually present among active fixtures — no more,
    # no fewer.
    active_stages = {f["disclosure_stage"] for f in fixtures if f["status"] == "active"}
    assert set(result.keys()) == active_stages, (
        f"accuracy_denominator_by_stage() keys {set(result.keys())} do not "
        f"match the active disclosure stages actually present {active_stages}"
    )
    assert set(result.keys()) <= LEGAL_DISCLOSURE_STAGES

    # Blocked fixtures appear in none of the per-stage counts.
    blocked_count = sum(1 for f in fixtures if f["status"] == "blocked")
    active_count = sum(1 for f in fixtures if f["status"] == "active")
    assert blocked_count > 0, "expected at least one blocked fixture to exercise this guard"
    assert sum(result.values()) == active_count, (
        f"accuracy_denominator_by_stage() must count only active fixtures "
        f"({active_count}), got a total of {sum(result.values())} — blocked "
        f"fixtures must not silently inflate any stage's count"
    )

    # No aggregate-across-stages value is exposed anywhere on the return
    # value — it is a plain dict of per-stage ints, nothing more. A caller
    # wanting a grand total must write sum(result.values()) explicitly at
    # the call site; the helper itself never computes or names one.
    assert isinstance(result, dict)
    for key, value in result.items():
        assert isinstance(key, str) and isinstance(value, int)
