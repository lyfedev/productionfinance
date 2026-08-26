"""Schema-load tests for `engine.cost_profile.CityCostProfile` — mirrors
`tests/test_engine_models.py`'s schema-load test shape for
`JurisdictionRuleSet`. A valid synthetic profile loads; `extra="forbid"`
rejects an unknown field; a `basis: "sourced"` line with a null
`source_url` is rejected (D-58/D-59); a non-`sourced` line missing
`method_note` is rejected (PITFALLS E1/E5).
"""

from __future__ import annotations

from glob import glob

import pytest
import yaml
from pydantic import ValidationError

from engine.cost_profile import CityCostProfile, load_cost_profile

FIXTURE_DIR = "tests/fixtures/cost_profiles"
FIXTURE_PATHS = sorted(glob(f"{FIXTURE_DIR}/*.yaml"))

if not FIXTURE_PATHS:
    raise RuntimeError(
        f"No fixture files found under {FIXTURE_DIR}/*.yaml — an empty cost-profile "
        "fixture set must fail loudly, not report a vacuous green (T-01-15 discipline)."
    )


def _load_raw(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_fixture_glob_is_non_empty_and_loads():
    assert FIXTURE_PATHS
    for path in FIXTURE_PATHS:
        profile = load_cost_profile(path)
        assert isinstance(profile, CityCostProfile)


def test_synthetic_minimal_profile_loads_with_expected_shape():
    profile = load_cost_profile(f"{FIXTURE_DIR}/synthetic-minimal.yaml")
    assert profile.city_id == "synthetic-minimal"
    assert profile.jurisdiction_id is None
    assert len(profile.cost_lines) == 2

    sourced_line = next(line for line in profile.cost_lines if line.basis == "sourced")
    assert sourced_line.source_url is not None

    estimated_line = next(line for line in profile.cost_lines if line.basis == "estimated")
    assert estimated_line.method_note is not None


def test_unknown_field_is_rejected_by_extra_forbid():
    raw = _load_raw(f"{FIXTURE_DIR}/synthetic-minimal.yaml")
    raw["an_unrecognised_field"] = "should never be accepted"
    with pytest.raises(ValidationError):
        CityCostProfile.model_validate(raw)


def test_unknown_cost_line_field_is_rejected_by_extra_forbid():
    raw = _load_raw(f"{FIXTURE_DIR}/synthetic-minimal.yaml")
    raw["cost_lines"][0]["an_unrecognised_field"] = "nope"
    with pytest.raises(ValidationError):
        CityCostProfile.model_validate(raw)


def test_sourced_basis_with_null_source_url_is_rejected():
    raw = _load_raw(f"{FIXTURE_DIR}/synthetic-minimal.yaml")
    sourced_line = next(line for line in raw["cost_lines"] if line["basis"] == "sourced")
    sourced_line["source_url"] = None
    with pytest.raises(ValidationError, match="source_url"):
        CityCostProfile.model_validate(raw)


def test_non_sourced_basis_missing_method_note_is_rejected():
    raw = _load_raw(f"{FIXTURE_DIR}/synthetic-minimal.yaml")
    estimated_line = next(line for line in raw["cost_lines"] if line["basis"] == "estimated")
    estimated_line["method_note"] = None
    with pytest.raises(ValidationError, match="method_note"):
        CityCostProfile.model_validate(raw)


def test_modelling_assumption_basis_also_requires_method_note():
    raw = _load_raw(f"{FIXTURE_DIR}/synthetic-minimal.yaml")
    line = raw["cost_lines"][1]
    line["basis"] = "modelling_assumption"
    line["method_note"] = None
    with pytest.raises(ValidationError, match="method_note"):
        CityCostProfile.model_validate(raw)


def test_every_numeric_looking_field_is_a_quoted_string_in_committed_fixtures():
    """RD-01: an unquoted YAML numeric parses as a native float/int, which
    corrupts through naive Decimal() conversion. `unit_rate` must always
    come back as `str` from the raw YAML load, never `float` or `int`."""
    for path in FIXTURE_PATHS:
        raw = _load_raw(path)
        for line in raw["cost_lines"]:
            assert isinstance(line["unit_rate"], str), (
                f"{path}: cost line {line['line_id']!r}'s unit_rate is not a quoted "
                f"string (got {type(line['unit_rate'])!r}) — RD-01 violation"
            )
