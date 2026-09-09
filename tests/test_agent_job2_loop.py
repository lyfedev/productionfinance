"""The standing CI gate for D-90 and D-94, over `agent/job2.py`'s finished
D-90 loop — findings that accumulate across rounds, an objective that
restates the gap, deterministic query/mode normalization, the closed
nine-value `TerminalReason` taxonomy, and the AST-level proof that the round
count is never bounded by anything but the model's own verdicts.

Follows `tests/test_agent_job1_offline.py`'s discipline: an inspection of
the parsed syntax tree, never a text grep, because a grep counts a
docstring and is therefore self-invalidating (D-87's precedent, applied
here to D-90/D-94).

## Non-vacuity (recorded in `07-02-SUMMARY.md`)

Two mutations must make the AST gates in this module fail. Both were
performed by hand against the real `agent/job2.py` (and `agent/settings.py`
for the second), observed to fail the relevant gate here, then reverted —
never embedded as permanent code in this repo:

1. Rewrite `run_job2`'s round-driving `while True:` loop as a `for
   round_number in range(50):` loop (a generated integer sequence) —
   `test_run_job2_source_has_no_range_driven_for_loop` must fail.
2. Add a literal rate assignment somewhere in `agent/` — e.g.
   `base_rate = 25.0` — `test_agent_tree_has_no_rate_literal_assignments`
   must fail.
"""

from __future__ import annotations

import ast
import time
import uuid
from pathlib import Path

import pytest

from agent import job2, research_runs
from agent.job2 import (
    TerminalReason,
    build_refined_objective,
    merge_findings,
    normalize_mode,
    normalize_queries,
    run_job2,
    unmet_fields,
)
from agent.research_schema import (
    FieldFinding,
    JurisdictionIdentity,
    SufficiencyField,
    SufficiencyVerdict,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = REPO_ROOT / "agent"
JOB2_PATH = AGENT_DIR / "job2.py"

_KEY_VARS = ("PARALLEL_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PRODFIN_GEMINI_MODEL")


@pytest.fixture(autouse=True)
def _no_agent_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _KEY_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _isolated_job2_runs_dir(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(research_runs, "RESEARCH_RUNS_DIR", tmp_path)


def _job_id() -> str:
    return uuid.uuid4().hex


def _finding(
    field: SufficiencyField,
    determined: bool,
    value_text: str | None = None,
    source_url: str | None = None,
) -> FieldFinding:
    return FieldFinding(
        field=field, determined=determined, value_text=value_text, source_url=source_url
    )


# ---------------------------------------------------------------------------
# Task 1: merge_findings, unmet_fields, build_refined_objective,
# normalize_queries, normalize_mode — pure functions, no SDK call.
# ---------------------------------------------------------------------------


def test_merge_findings_keys_all_five_fields_even_from_an_empty_previous_state():
    merged, discarded = merge_findings({}, [])
    assert set(merged) == set(SufficiencyField)
    assert all(not v.determined for v in merged.values())
    assert discarded == []


def test_merge_findings_keeps_a_field_determined_after_a_round_that_says_nothing():
    previous = {SufficiencyField.rate: _finding(SufficiencyField.rate, True, "25%", "https://a")}
    merged, discarded = merge_findings(previous, [])
    assert merged[SufficiencyField.rate].determined is True
    assert merged[SufficiencyField.rate].value_text == "25%"
    assert discarded == []


def test_merge_findings_never_flips_determined_true_back_to_false():
    previous = {SufficiencyField.rate: _finding(SufficiencyField.rate, True, "25%", "https://a")}
    incoming = [_finding(SufficiencyField.rate, False)]
    merged, discarded = merge_findings(previous, incoming)
    assert merged[SufficiencyField.rate].determined is True
    assert discarded == [SufficiencyField.rate]


def test_merge_findings_discards_an_unsourced_overwrite_of_a_determined_field():
    previous = {SufficiencyField.rate: _finding(SufficiencyField.rate, True, "25%", "https://a")}
    unsourced = [_finding(SufficiencyField.rate, True, "30%", None)]
    merged, discarded = merge_findings(previous, unsourced)
    assert merged[SufficiencyField.rate].value_text == "25%"
    assert discarded == [SufficiencyField.rate]


def test_merge_findings_accepts_a_sourced_overwrite_of_a_determined_field():
    previous = {SufficiencyField.rate: _finding(SufficiencyField.rate, True, "25%", "https://a")}
    sourced = [_finding(SufficiencyField.rate, True, "30%", "https://b")]
    merged, discarded = merge_findings(previous, sourced)
    assert merged[SufficiencyField.rate].value_text == "30%"
    assert discarded == []


def test_merge_findings_accepts_a_first_time_determination_even_when_unsourced():
    incoming = [_finding(SufficiencyField.caps, True, "no cap", None)]
    merged, discarded = merge_findings({}, incoming)
    assert merged[SufficiencyField.caps].determined is True
    assert discarded == []


def test_unmet_fields_returns_undetermined_members_in_declaration_order():
    merged = {f: _finding(f, False) for f in SufficiencyField}
    merged[SufficiencyField.rate] = _finding(SufficiencyField.rate, True, "25%", "https://a")
    assert unmet_fields(merged) == [f for f in SufficiencyField if f != SufficiencyField.rate]


def test_build_refined_objective_names_the_city_and_every_unmet_field():
    merged = {f: _finding(f, False) for f in SufficiencyField}
    merged[SufficiencyField.rate] = _finding(SufficiencyField.rate, True, "25%", "https://a")
    objective = build_refined_objective("Nowhereville", merged)
    assert "Nowhereville" in objective
    for f in unmet_fields(merged):
        assert f.value.replace("_", " ") in objective


def test_build_refined_objective_never_reproduces_a_previous_search_query():
    merged = {f: _finding(f, False) for f in SufficiencyField}
    previous_queries = [
        "Nowhereville film tax incentive",
        "Nowhereville production incentive programme",
    ]
    objective = build_refined_objective("Nowhereville", merged)
    for q in previous_queries:
        assert q not in objective


def test_normalize_queries_keeps_at_most_three_and_truncates_to_six_words():
    raw = [
        "one two three four five six seven eight",
        "a b",
        "x y z",
        "should be dropped entirely",
    ]
    queries, changed = normalize_queries(raw)
    assert queries == ["one two three four five six", "a b", "x y z"]
    assert changed is True


def test_normalize_queries_reports_unchanged_when_nothing_moves():
    queries, changed = normalize_queries(["short query", "another one"])
    assert queries == ["short query", "another one"]
    assert changed is False


def test_normalize_queries_never_adds_a_word_the_model_did_not_produce():
    queries, _ = normalize_queries(["alpha beta"])
    assert queries == ["alpha beta"]
    assert set(queries[0].split()) <= {"alpha", "beta"}


def test_normalize_queries_drops_empty_strings():
    queries, changed = normalize_queries(["", "  ", "real query"])
    assert queries == ["real query"]
    assert changed is True


def test_normalize_mode_passes_through_a_valid_literal():
    mode, changed = normalize_mode("advanced")
    assert (mode, changed) == ("advanced", False)


def test_normalize_mode_substitutes_fast_for_an_invalid_or_missing_value():
    assert normalize_mode("ultra-turbo") == ("fast", True)
    assert normalize_mode(None) == ("fast", True)


# ---------------------------------------------------------------------------
# Task 2: the closed nine-value TerminalReason taxonomy.
# ---------------------------------------------------------------------------

_FIXTURE_RESULT = {
    "url": "https://example.org/incentive-programme",
    "title": "Example jurisdiction production incentive",
    "excerpts": ["A 25% rebate applies to qualifying local spend, capped annually."],
}

_FULL_IDENTITY = JurisdictionIdentity(
    jurisdiction_name="Nowhereville",
    country_code="XX",
    level="city",
    currency="USD",
)


def _all_determined_findings() -> list[FieldFinding]:
    return [
        _finding(f, True, f"value-{f.value}", "https://example.org/incentive-programme")
        for f in SufficiencyField
    ]


def _scripted_seams(decisions: list[str]):
    """A `search_fn`/`judge_fn` pair scripted to walk `decisions` in order.
    A `\"sufficient\"` decision carries all five fields determined AND a
    full jurisdiction identity, so it is genuinely sufficient under the
    driver's own contradiction/identity checks."""
    remaining = list(decisions)
    search_calls: list[dict] = []

    def _search_fn(**kwargs):
        search_calls.append(kwargs)
        return [dict(_FIXTURE_RESULT)]

    def _judge_fn(**kwargs):
        decision = remaining.pop(0)
        round_number = kwargs["round_number"]
        findings: list[FieldFinding] = []
        identity = None
        if decision == "sufficient":
            findings = _all_determined_findings()
            identity = _FULL_IDENTITY
        return SufficiencyVerdict(
            decision=decision,
            findings=findings,
            identity=identity,
            summary=f"round {round_number}: {decision}",
            next_objective=f"refined objective after round {round_number}",
            next_queries=[f"refined round {round_number} a", f"refined round {round_number} b"],
            next_mode="fast",
        )

    return _search_fn, _judge_fn, search_calls


def test_terminal_reason_is_the_closed_nine_member_set():
    assert {r.value for r in TerminalReason} == {
        "sufficient",
        "agent_gave_up",
        "no_programme_found",
        "insufficient_identity",
        "budget_exhausted",
        "contradictory_verdict",
        "cache_boundary_violation",
        "not_configured",
        "sdk_error",
    }


def test_scripted_sufficient_with_all_five_and_full_identity_is_sufficient():
    search_fn, judge_fn, _ = _scripted_seams(["sufficient"])
    run = run_job2("Nowhereville", None, job_id=_job_id(), search_fn=search_fn, judge_fn=judge_fn)
    assert run.terminal_reason == TerminalReason.sufficient.value


def test_sufficient_verdict_leaving_caps_undetermined_is_contradictory():
    def _search_fn(**kwargs):
        return [dict(_FIXTURE_RESULT)]

    def _judge_fn(**kwargs):
        findings = [f for f in _all_determined_findings() if f.field != SufficiencyField.caps]
        findings.append(_finding(SufficiencyField.caps, False))
        return SufficiencyVerdict(
            decision="sufficient",
            findings=findings,
            identity=_FULL_IDENTITY,
            summary="claims sufficient",
        )

    run = run_job2("Nowhereville", None, job_id=_job_id(), search_fn=_search_fn, judge_fn=_judge_fn)
    assert run.terminal_reason == TerminalReason.contradictory_verdict.value
    assert "caps" in (run.message or "")


def test_give_up_verdict_lists_every_unmet_field_when_nothing_was_determined():
    search_fn, judge_fn, _ = _scripted_seams(["give_up"])
    run = run_job2("Nowhereville", None, job_id=_job_id(), search_fn=search_fn, judge_fn=judge_fn)
    assert run.terminal_reason == TerminalReason.agent_gave_up.value
    last_round = run.rounds[-1]
    for f in SufficiencyField:
        assert f.value in last_round["unmet_fields"]
        assert f.value.replace("_", " ") in (run.undetermined_disclosures or ())


def test_no_programme_found_is_a_legitimate_terminal_that_prices_nothing():
    search_fn, judge_fn, _ = _scripted_seams(["no_programme_found"])
    run = run_job2("Nowhereville", None, job_id=_job_id(), search_fn=search_fn, judge_fn=judge_fn)
    assert run.status == "terminal"
    assert run.terminal_reason == TerminalReason.no_programme_found.value
    assert run.priced is None
    assert run.ruleset_path is None


def test_no_programme_found_record_round_trips_with_priced_and_ruleset_path_none():
    job_id = _job_id()
    search_fn, judge_fn, _ = _scripted_seams(["no_programme_found"])
    run_job2("Nowhereville", None, job_id=job_id, search_fn=search_fn, judge_fn=judge_fn)

    on_disk = research_runs.load_run(job_id)
    assert on_disk is not None
    assert on_disk.get("priced") is None
    assert on_disk.get("ruleset_path") is None


def test_sufficient_with_all_five_fields_but_no_identity_is_insufficient_identity():
    def _search_fn(**kwargs):
        return [dict(_FIXTURE_RESULT)]

    def _judge_fn(**kwargs):
        return SufficiencyVerdict(
            decision="sufficient",
            findings=_all_determined_findings(),
            identity=None,
            summary="five determined, identity unknown",
        )

    run = run_job2("Nowhereville", None, job_id=_job_id(), search_fn=_search_fn, judge_fn=_judge_fn)
    assert run.terminal_reason == TerminalReason.insufficient_identity.value
    for name in ("jurisdiction_name", "country_code", "level", "currency"):
        assert name in (run.message or "")


def test_sufficient_with_partial_identity_names_only_the_missing_field():
    def _search_fn(**kwargs):
        return [dict(_FIXTURE_RESULT)]

    def _judge_fn(**kwargs):
        partial = JurisdictionIdentity(
            jurisdiction_name="Nowhereville", country_code="XX", level="city", currency=None
        )
        return SufficiencyVerdict(
            decision="sufficient",
            findings=_all_determined_findings(),
            identity=partial,
            summary="five determined, currency unknown",
        )

    run = run_job2("Nowhereville", None, job_id=_job_id(), search_fn=_search_fn, judge_fn=_judge_fn)
    assert run.terminal_reason == TerminalReason.insufficient_identity.value
    assert "currency" in (run.message or "")
    assert "jurisdiction_name" not in (run.message or "")


def test_wall_clock_ceiling_stops_between_rounds_not_mid_call(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(job2, "JOB2_WALL_CLOCK_CEILING_SECONDS", 0.01)

    def _search_fn(**kwargs):
        return [dict(_FIXTURE_RESULT)]

    def _judge_fn(**kwargs):
        time.sleep(0.05)
        return SufficiencyVerdict(
            decision="continue",
            findings=[],
            summary="still looking",
            next_objective="keep going",
            next_queries=["keep looking here"],
            next_mode="fast",
        )

    run = run_job2("Nowhereville", None, job_id=_job_id(), search_fn=_search_fn, judge_fn=_judge_fn)
    assert run.terminal_reason == TerminalReason.budget_exhausted.value
    assert "0.01" in (run.message or "")
    # Round 1 itself ran to completion — the guard never interrupts a
    # round already in flight, only the decision to start another one.
    assert len(run.rounds) >= 1
    assert run.rounds[0]["decision"] == "continue"


def test_budget_exhausted_is_distinguishable_from_agent_gave_up():
    assert TerminalReason.budget_exhausted != TerminalReason.agent_gave_up
    assert TerminalReason.budget_exhausted.value != TerminalReason.agent_gave_up.value


def test_exception_in_search_fn_produces_a_durable_sdk_error_record():
    job_id = _job_id()

    def _search_fn(**kwargs):
        raise RuntimeError("simulated Parallel outage")

    def _judge_fn(**kwargs):
        raise AssertionError("judge must never be called after a search failure")

    run = run_job2("Nowhereville", None, job_id=job_id, search_fn=_search_fn, judge_fn=_judge_fn)
    assert run.status == "terminal"
    assert run.terminal_reason == TerminalReason.sdk_error.value
    assert "simulated Parallel outage" in (run.message or "")

    on_disk = research_runs.load_run(job_id)
    assert on_disk is not None
    assert on_disk["status"] == "terminal"


def test_exception_in_judge_fn_also_produces_sdk_error():
    def _search_fn(**kwargs):
        return [dict(_FIXTURE_RESULT)]

    def _judge_fn(**kwargs):
        raise RuntimeError("simulated Gemini parse failure")

    run = run_job2("Nowhereville", None, job_id=_job_id(), search_fn=_search_fn, judge_fn=_judge_fn)
    assert run.terminal_reason == TerminalReason.sdk_error.value
    assert "simulated Gemini parse failure" in (run.message or "")


# ---------------------------------------------------------------------------
# Task 3: D-90's substance — the same driver, four different scripted
# futures, four different round counts. Nothing else varies.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "decisions,expected_rounds",
    [
        (["sufficient"], 1),
        (["continue", "sufficient"], 2),
        (["continue", "continue", "continue", "continue", "give_up"], 5),
        (["continue"] * 8 + ["sufficient"], 9),
    ],
)
def test_round_count_is_a_property_of_the_scripted_verdicts_not_the_driver(
    decisions, expected_rounds
):
    search_fn, judge_fn, search_calls = _scripted_seams(decisions)
    run = run_job2("Nowhereville", None, job_id=_job_id(), search_fn=search_fn, judge_fn=judge_fn)
    assert len(run.rounds) == expected_rounds
    assert len(search_calls) == expected_rounds


# ---------------------------------------------------------------------------
# Task 3: AST gates, not text greps.
# ---------------------------------------------------------------------------


def _run_job2_function_node() -> ast.FunctionDef:
    tree = ast.parse(JOB2_PATH.read_text(encoding="utf-8"), filename=str(JOB2_PATH))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run_job2":
            return node
    raise AssertionError("run_job2 function not found in agent/job2.py")


def _is_int_constant(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    )


def _references_round_counter(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and "round" in node.id.lower()


def test_run_job2_source_has_no_range_driven_for_loop():
    """D-90: no `ast.For` inside `run_job2` whose `iter` is a call to
    `range` — a hardcoded iteration count is precisely what D-90 rules
    out."""
    func = _run_job2_function_node()
    violations = []
    for node in ast.walk(func):
        if isinstance(node, ast.For):
            it = node.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
                violations.append(f"line {node.lineno}: for-loop driven by range(...)")
    assert not violations, violations


def test_run_job2_never_compares_the_round_counter_to_an_int_constant():
    """D-90: no `ast.Compare` inside `run_job2` where one side is an
    integer `ast.Constant` and the other references the round counter name
    (`round_number`) — the wall-clock guard compares elapsed time against
    a NAMED seconds constant, never the round counter against an integer."""
    func = _run_job2_function_node()
    violations = []
    for node in ast.walk(func):
        if isinstance(node, ast.Compare):
            sides = [node.left, *node.comparators]
            has_int_const = any(_is_int_constant(s) for s in sides)
            has_round_name = any(_references_round_counter(s) for s in sides)
            if has_int_const and has_round_name:
                violations.append(f"line {node.lineno}: round counter compared to an int constant")
    assert not violations, violations


_RATE_IDENTIFIERS = {
    "base_rate",
    "rate",
    "additional_rate",
    "standard_rate",
    "enhanced_rate",
    "corporation_tax_rate",
    "loanout_withholding_rate",
}


def _is_numeric_constant(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    )


def _rate_literal_violations(tree: ast.Module, filename: str) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_numeric_constant(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in _RATE_IDENTIFIERS:
                    violations.append(
                        f"{filename}:{node.lineno}: {target.id} = {node.value.value!r}"
                    )
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and _is_numeric_constant(node.value)
            and isinstance(node.target, ast.Name)
            and node.target.id in _RATE_IDENTIFIERS
        ):
            violations.append(f"{filename}:{node.lineno}: {node.target.id} = {node.value.value!r}")
    return violations


def test_agent_tree_has_no_rate_literal_assignments():
    """D-94: no numeric literal is ever assigned to a rate-bearing
    identifier anywhere in `agent/` — the AST-level no-fabricated-rate
    gate. A closed identifier set, not a name any string happens to
    contain."""
    violations: list[str] = []
    for path in sorted(AGENT_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations.extend(_rate_literal_violations(tree, path.name))
    assert not violations, "rate literal assignment found in agent/:\n" + "\n".join(violations)
