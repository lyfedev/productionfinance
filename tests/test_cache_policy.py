"""AGT-10's cache-vs-live boundary — the single point `app.services.cache_policy`
is required to be.

The mutation test at the bottom (`test_run_job2_reports_a_cache_boundary_violation_and_fires_no_search`)
proves `assert_live` is load-bearing rather than decorative: flip the
policy table's verdict for `uncurated_city_research` to `\"cached\"` and
prove the live research path stops before it ever fires a Search call.
"""

from __future__ import annotations

import dataclasses

import pytest

from app.services.cache_policy import (
    POLICY,
    CacheBoundaryViolation,
    DataClass,
    assert_live,
    may_use_cache,
)


def test_data_class_has_exactly_five_members():
    assert {m.value for m in DataClass} == {
        "curated_rule_model",
        "cap_consumption",
        "programme_open_status",
        "fx_rate",
        "uncurated_city_research",
    }


def test_policy_matches_agt_10_word_for_word():
    assert POLICY[DataClass.curated_rule_model].verdict == "cached"
    for data_class in (
        DataClass.cap_consumption,
        DataClass.programme_open_status,
        DataClass.fx_rate,
        DataClass.uncurated_city_research,
    ):
        assert POLICY[data_class].verdict == "live"


def test_may_use_cache_matches_the_policy_table():
    assert may_use_cache(DataClass.curated_rule_model) is True
    for data_class in (
        DataClass.cap_consumption,
        DataClass.programme_open_status,
        DataClass.fx_rate,
        DataClass.uncurated_city_research,
    ):
        assert may_use_cache(data_class) is False


def test_assert_live_returns_none_under_the_shipped_policy():
    assert assert_live(DataClass.uncurated_city_research) is None


def test_assert_live_raises_for_a_non_data_class_value():
    with pytest.raises(CacheBoundaryViolation):
        assert_live("uncurated_city_research")  # a bare string, not the enum


def test_may_use_cache_raises_for_a_non_data_class_value():
    with pytest.raises(CacheBoundaryViolation):
        may_use_cache("curated_rule_model")  # a bare string, not the enum


def test_assert_live_raises_when_the_policy_is_mutated_to_cached(monkeypatch):
    """The non-vacuity proof: flip the policy entry for
    `uncurated_city_research` to `\"cached\"` and prove `assert_live`
    genuinely fails."""
    mutated = dataclasses.replace(POLICY[DataClass.uncurated_city_research], verdict="cached")
    monkeypatch.setitem(POLICY, DataClass.uncurated_city_research, mutated)

    with pytest.raises(CacheBoundaryViolation):
        assert_live(DataClass.uncurated_city_research)


def test_run_job2_reports_a_cache_boundary_violation_and_fires_no_search(monkeypatch, tmp_path):
    """`agent.job2.run_job2` must assert live BEFORE its first Search call —
    proven by mutating the policy table and asserting the fake search seam
    is never invoked, and that the run terminates naming the violation."""
    import agent.job2 as job2_module
    import agent.research_runs as research_runs_module

    monkeypatch.setattr(research_runs_module, "RESEARCH_RUNS_DIR", tmp_path)

    mutated = dataclasses.replace(POLICY[DataClass.uncurated_city_research], verdict="cached")
    monkeypatch.setitem(POLICY, DataClass.uncurated_city_research, mutated)

    search_calls: list[dict] = []

    def _fake_search(**kwargs):
        search_calls.append(kwargs)
        return []

    def _fake_judge(**kwargs):
        raise AssertionError("judge must never be called after a cache boundary violation")

    run = job2_module.run_job2(
        "Nowhereville",
        None,
        job_id="a" * 32,
        search_fn=_fake_search,
        judge_fn=_fake_judge,
    )

    assert search_calls == []
    assert run.status == "terminal"
    assert run.terminal_reason == "cache_boundary_violation"
    assert "uncurated_city_research" in (run.message or "")
