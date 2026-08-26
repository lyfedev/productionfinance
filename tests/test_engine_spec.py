"""Validation matrix for `engine.spec.ProductionSpec` and crew-tier
resolution (INP-01...INP-07, D-38/D-39).

Mirrors `tests/test_engine_models.py`'s construct-valid/assert-ValidationError
shape. Decision Task 1 (checkpoint) selected option A — `production_type`
alone, no separate numeric "scale" field — so this file has no episode_count
coverage.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
import yaml
from pydantic import ValidationError

from engine.spec import (
    CREW_TIERS_PATH,
    CrewTier,
    ProductionSpec,
    resolve_crew_tier,
)


def _base_kwargs(**overrides: object) -> dict:
    kwargs = {
        "production_type": "feature",
        "shoot_days_stage": 10,
        "shoot_days_location": 5,
        "crew_size": 50,
        "crew_tier": None,
        "principal_cast_count": 3,
        "principal_cast_imported_count": 1,
        "crew_imported_count": 10,
        "crew_hired_locally_count": 40,
        "start_quarter": "Q2",
        "start_year": 2026,
        "candidate_cities": ["New York, NY"],
    }
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# Valid construction
# ---------------------------------------------------------------------------


def test_valid_spec_with_explicit_crew_size():
    spec = ProductionSpec(**_base_kwargs())
    assert spec.crew_size == 50
    assert spec.crew_tier is None


def test_valid_spec_with_crew_tier_only():
    spec = ProductionSpec(
        **_base_kwargs(
            crew_size=None,
            crew_tier="mid",
            crew_imported_count=0,
            crew_hired_locally_count=0,
        )
    )
    assert spec.crew_tier == "mid"
    assert spec.crew_size is None


# ---------------------------------------------------------------------------
# INP-03 — exactly one of crew_size / crew_tier
# ---------------------------------------------------------------------------


def test_both_crew_inputs_rejected():
    with pytest.raises(ValidationError) as exc_info:
        ProductionSpec(**_base_kwargs(crew_size=50, crew_tier="mid"))
    message = str(exc_info.value)
    assert "crew_size" in message
    assert "crew_tier" in message


def test_neither_crew_input_rejected():
    with pytest.raises(ValidationError) as exc_info:
        ProductionSpec(**_base_kwargs(crew_size=None, crew_tier=None))
    message = str(exc_info.value)
    assert "crew_size" in message
    assert "crew_tier" in message


# ---------------------------------------------------------------------------
# extra="forbid" and the no-money-field structural gate
# ---------------------------------------------------------------------------


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        ProductionSpec(**_base_kwargs(unexpected_field="nope"))


_MONEY_FRAGMENTS = ("budget", "cost", "spend", "amount", "usd", "dollars", "price")


def test_no_money_field_exists():
    for field_name in ProductionSpec.model_fields:
        lowered = field_name.lower()
        for fragment in _MONEY_FRAGMENTS:
            assert fragment not in lowered, (
                f"ProductionSpec.{field_name} looks money-shaped (matches {fragment!r}) "
                "— no field on this model may represent a dollar amount (D-35/INP-08)"
            )


# ---------------------------------------------------------------------------
# INP-04 boundary — imported cast <= total
# ---------------------------------------------------------------------------


def test_imported_cast_equal_to_total_accepted():
    spec = ProductionSpec(
        **_base_kwargs(principal_cast_count=3, principal_cast_imported_count=3)
    )
    assert spec.principal_cast_imported_count == 3


def test_imported_cast_one_over_total_rejected():
    with pytest.raises(ValidationError):
        ProductionSpec(
            **_base_kwargs(principal_cast_count=3, principal_cast_imported_count=4)
        )


# ---------------------------------------------------------------------------
# Precision edges — fractional headcounts/shoot-days rejected
# ---------------------------------------------------------------------------


def test_fractional_shoot_days_rejected():
    with pytest.raises(ValidationError):
        ProductionSpec(**_base_kwargs(shoot_days_stage=5.5))


def test_integer_valued_float_shoot_days_accepted():
    spec = ProductionSpec(**_base_kwargs(shoot_days_stage=5.0))
    assert spec.shoot_days_stage == 5
    assert isinstance(spec.shoot_days_stage, int)


def test_fractional_cast_count_rejected():
    with pytest.raises(ValidationError):
        ProductionSpec(**_base_kwargs(principal_cast_count=3.5))


# ---------------------------------------------------------------------------
# Negative / zero shoot-days
# ---------------------------------------------------------------------------


def test_negative_shoot_days_rejected():
    with pytest.raises(ValidationError):
        ProductionSpec(**_base_kwargs(shoot_days_stage=-1))


def test_zero_shoot_days_accepted():
    spec = ProductionSpec(
        **_base_kwargs(shoot_days_stage=0, shoot_days_location=0)
    )
    assert spec.shoot_days_stage == 0
    assert spec.shoot_days_location == 0


# ---------------------------------------------------------------------------
# INP-07 empty / blank candidate_cities edges
# ---------------------------------------------------------------------------


def test_empty_candidate_cities_rejected():
    with pytest.raises(ValidationError):
        ProductionSpec(**_base_kwargs(candidate_cities=[]))


def test_single_candidate_city_accepted():
    spec = ProductionSpec(**_base_kwargs(candidate_cities=["Buffalo"]))
    assert spec.candidate_cities == ["Buffalo"]


def test_blank_candidate_city_rejected():
    with pytest.raises(ValidationError):
        ProductionSpec(**_base_kwargs(candidate_cities=["New York, NY", "   "]))


def test_candidate_cities_are_stripped_not_reordered_or_deduplicated():
    spec = ProductionSpec(
        **_base_kwargs(candidate_cities=["  Buffalo  ", "Buffalo", "Albany"])
    )
    assert spec.candidate_cities == ["Buffalo", "Buffalo", "Albany"]


# ---------------------------------------------------------------------------
# Pitfall 3 — crew-split sum check guarded to the explicit crew_size branch
# ---------------------------------------------------------------------------


def test_crew_split_must_equal_explicit_crew_size():
    with pytest.raises(ValidationError):
        ProductionSpec(
            **_base_kwargs(
                crew_size=50,
                crew_imported_count=10,
                crew_hired_locally_count=39,
            )
        )


def test_crew_split_matching_explicit_crew_size_accepted():
    spec = ProductionSpec(
        **_base_kwargs(
            crew_size=50,
            crew_imported_count=10,
            crew_hired_locally_count=40,
        )
    )
    assert spec.crew_imported_count + spec.crew_hired_locally_count == spec.crew_size


def test_crew_split_not_checked_when_tier_only():
    # No exception even though imported+local would "mismatch" an unset
    # crew_size — a tier resolves to a range, not a scalar to sum against.
    spec = ProductionSpec(
        **_base_kwargs(
            crew_size=None,
            crew_tier="small",
            crew_imported_count=999,
            crew_hired_locally_count=0,
        )
    )
    assert spec.crew_tier == "small"


# ---------------------------------------------------------------------------
# INP-06 — start_year bounds (D-41)
# ---------------------------------------------------------------------------


def test_start_year_bounds():
    with pytest.raises(ValidationError):
        ProductionSpec(**_base_kwargs(start_year=2023))
    ProductionSpec(**_base_kwargs(start_year=2024))
    ProductionSpec(**_base_kwargs(start_year=2036))
    with pytest.raises(ValidationError):
        ProductionSpec(**_base_kwargs(start_year=2037))


# ---------------------------------------------------------------------------
# Crew-tier table resolution
# ---------------------------------------------------------------------------


def test_resolve_crew_tier_returns_range():
    for tier in ("micro", "small", "mid", "large", "tentpole"):
        headcount = resolve_crew_tier(tier)
        assert headcount.low > 0
        assert headcount.high > 0
        assert headcount.low <= headcount.high


def test_resolve_crew_tier_covers_every_literal():
    import typing

    literal_values = set(typing.get_args(CrewTier))
    with open(CREW_TIERS_PATH, encoding="utf-8") as handle:
        table = yaml.safe_load(handle)
    assert set(table["tiers"].keys()) == literal_values


def test_crew_tier_table_declares_no_confidence_tier():
    with open(CREW_TIERS_PATH, encoding="utf-8") as handle:
        table = yaml.safe_load(handle)

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                assert key not in ("confidence", "status"), (
                    f"data/crew_tiers.yaml must never declare a {key!r} key — "
                    "this table is a modelling assumption, not a sourced rule file (D-39)"
                )
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(table)
    assert table["basis"] == "modelling_assumption"
    assert isinstance(table["provenance_note"], str)
    assert table["provenance_note"].strip() != ""


def test_resolve_crew_tier_unknown_tier_raises():
    with pytest.raises(KeyError):
        resolve_crew_tier("nonexistent")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# D-44 — engine/ stays HTTP-free
# ---------------------------------------------------------------------------


def test_engine_spec_is_http_free():
    # Run in a fresh subprocess — checking sys.modules in-process is
    # order-dependent on whatever the rest of this pytest session already
    # imported (e.g. tests/test_health.py pulling in app.main -> fastapi
    # earlier in the same session). Only a clean interpreter proves
    # importing engine.spec alone never drags fastapi in.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys, engine.spec; "
                "assert 'fastapi' not in {m.split('.')[0] for m in sys.modules}"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
