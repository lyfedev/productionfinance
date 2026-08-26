"""D-63 — the CI gate: no `Figure` reachable from a Route A total ever
carries `confidence: "validated"`.

D-39 made this promise for one YAML table (Phase 2); this generalises it
to the entire cost side, where the surface is now hundreds of Figures
deep. Submits a `SpecFormSubmission` naming New York through
`handle_spec_submission`, serializes every returned Figure through
`figure_to_dict`, and walks the FULL recursive `inputs` DAG from both
`cost_total` and `total_landed_cost` for every `CityCost`.

**Non-vacuity proof (performed once, by hand, and reverted):** to prove
this test is not vacuously green, `app/services/spec.py::_price_candidate_cities`'s
`price_jurisdiction(...)` call was temporarily edited to pass
`spend_confidence="validated"` instead of `"researched"`, and this test
suite was re-run. Observed result: RED —
`test_no_validated_confidence_anywhere_in_the_dag` failed with:

    AssertionError: found a 'validated'-confidence node reachable from a
    Route A total: ['Total landed net cash across all programmes',
    'Gross credit', 'Qualifying base', 'Core expenditure (pre-cap)',
    'Excluded line items total'] — D-63 requires every node reachable
    from a Route A total to be, at most, 'researched'

Every one of those five nodes inherited `confidence: "validated"` because
New York's `jurisdiction.status` is `curated_validated` and the temporary
edit removed the only thing (`spend_confidence`) keeping the derivation at
`"researched"` — exactly the failure mode D-63/D-71 exist to prevent. The
edit was reverted immediately afterward (confirmed green again); the
assertions below are the permanent, always-green version guarding the
reverted (correct) code path.
"""

from __future__ import annotations

from app.services.spec import SpecFormSubmission, SpecResult, handle_spec_submission
from engine.figure_serialize import figure_to_dict

# A minimum node count high enough that a future refactor which flattens
# or truncates the Figure tree (silently deleting the provenance evidence,
# D-45) makes this test fail loudly rather than pass vacuously over a
# one-or-two-node tree.
_MINIMUM_VISITED_NODES = 6


def _base_submission_kwargs(**overrides: object) -> dict:
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
        "total_budget": None,
    }
    kwargs.update(overrides)
    return kwargs


def _walk(node: dict) -> list[dict]:
    """Walk the full recursive `inputs` DAG rooted at `node` (a
    `figure_to_dict` output), returning every node visited, `node` itself
    included. No depth cap, no summarization (D-45)."""
    visited = [node]
    for child in node.get("inputs", []):
        visited.extend(_walk(child))
    return visited


def _route_a_new_york_result() -> SpecResult:
    raw = SpecFormSubmission(**_base_submission_kwargs())
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)
    assert result.city_costs, "expected at least one CityCost for a New York candidate"
    return result


def test_no_validated_confidence_anywhere_in_the_dag():
    result = _route_a_new_york_result()

    all_nodes: list[dict] = []
    for city_cost in result.city_costs:
        all_nodes.extend(_walk(figure_to_dict(city_cost.cost_total)))
        all_nodes.extend(_walk(figure_to_dict(city_cost.total_landed_cost)))

    validated_nodes = [node for node in all_nodes if node["confidence"] == "validated"]
    assert not validated_nodes, (
        "found a 'validated'-confidence node reachable from a Route A total: "
        f"{[node['label'] for node in validated_nodes]!r} — D-63 requires every node "
        "reachable from a Route A total to be, at most, 'researched'"
    )


def test_every_node_reachable_from_a_cost_total_has_a_non_null_basis():
    result = _route_a_new_york_result()

    for city_cost in result.city_costs:
        nodes = _walk(figure_to_dict(city_cost.cost_total))
        assert nodes, "expected a non-empty cost_total subtree"
        for node in nodes:
            assert node["basis"] is not None, (
                f"cost-side node {node['label']!r} carries a null basis — every "
                "cost-side Figure must declare its own basis (D-58)"
            )


def test_the_walk_visits_a_non_trivial_number_of_nodes():
    """A future refactor that flattens or truncates the Figure tree must
    make this test fail loudly, never pass vacuously over a one-or-two-
    node stub tree."""
    result = _route_a_new_york_result()

    all_nodes: list[dict] = []
    for city_cost in result.city_costs:
        all_nodes.extend(_walk(figure_to_dict(city_cost.total_landed_cost)))

    assert len(all_nodes) >= _MINIMUM_VISITED_NODES, (
        f"walk visited only {len(all_nodes)} node(s), fewer than the declared minimum "
        f"of {_MINIMUM_VISITED_NODES} — this test must never pass vacuously over a "
        "flattened or truncated tree"
    )
