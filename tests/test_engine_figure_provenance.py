"""PRV-01, PRV-02 and PRV-03 as executable property assertions over a real
computed tree.

Every number the engine returns is proven — by pricing Anora's disclosed
qualified spend through the committed ``jurisdictions/us-ny.yaml`` via
``price_jurisdiction`` and walking the resulting figures recursively through
their ``inputs`` edges — to carry its source, the date it was checked, a
confidence tier drawn from a closed two-value set, and a derivation that
records every step including the ones that did nothing. Hand-built
``Figure`` fixtures are used only for the constructor-level assertions
(distinct identifiers, rejected confidence values, omitted confidence,
combined confidence, input ordering) where a real tree cannot exercise the
negative case.

RD-02: ``Figure.confidence`` (this file's subject) is a closed two-value
axis measuring whether a *computed figure* has been checked against a real
government disclosure (``validated``) or only researched (``researched``).
This is a different axis from ``tests/test_source_truth.py``'s
``LEGAL_CONFIDENCE_TIERS`` four-tier *source-document-reliability*
vocabulary (``LOW``/``MEDIUM``/``MEDIUM-HIGH``/``HIGH``). The four rejected
strings below are written out literally, never imported from
``tests.test_source_truth`` — importing that set would couple the two
vocabularies at exactly the seam this file exists to keep apart.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from engine.figure import Figure, combined_confidence
from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction

# ---------------------------------------------------------------------------
# Real, non-synthetic computed tree: New York's curated rule file pricing
# Anora's disclosed qualified spend.
# ---------------------------------------------------------------------------

NY_RULESET = load_ruleset("jurisdictions/us-ny.yaml")
ANORA_QUALIFIED_SPEND = Decimal("3964760")


def _priced_anora():
    return price_jurisdiction(NY_RULESET, ANORA_QUALIFIED_SPEND)


def _collect_tree(roots: list[Figure]) -> list[Figure]:
    """Walk every root Figure recursively through its ``inputs`` edges,
    collecting every distinct node once, deduped by ``figure_id``."""
    seen: dict[str, Figure] = {}
    stack: list[Figure] = list(roots)
    while stack:
        figure = stack.pop()
        if figure.figure_id in seen:
            continue
        seen[figure.figure_id] = figure
        stack.extend(figure.inputs)
    return list(seen.values())


def _anora_tree() -> list[Figure]:
    """The full set of distinct figures reachable from every top-level
    result ``price_jurisdiction`` returns for Anora: the summed total, and
    each programme's gross credit, qualifying base and net-cash bounds —
    not just whatever happens to be reachable from a single root, since
    ``gross_credit`` and ``net_cash.point`` are sibling lineages (both
    evolved via ``Figure.with_step`` from the same starting figure) rather
    than parent/child."""
    result = _priced_anora()
    programme = result.programmes[0]
    roots = [
        result.total_net_cash,
        programme.gross_credit,
        programme.qualifying_base,
        programme.net_cash.low,
        programme.net_cash.high,
    ]
    if programme.net_cash.point is not None:
        roots.append(programme.net_cash.point)
    return _collect_tree(roots)


# ---------------------------------------------------------------------------
# PRV-01: source_url / date_checked, over the real priced tree
# ---------------------------------------------------------------------------


def test_every_figure_in_priced_tree_has_source_or_explicit_null():
    tree = _anora_tree()
    assert tree, "the priced Anora tree must contain at least one figure"
    for figure in tree:
        assert figure.source_url is None or (
            isinstance(figure.source_url, str) and figure.source_url != ""
        ), f"{figure.label}: source_url must be a non-empty string or None, got {figure.source_url!r}"
        assert figure.date_checked is None or isinstance(figure.date_checked, date), (
            f"{figure.label}: date_checked must be a date or None, got {figure.date_checked!r}"
        )


def test_at_least_one_figure_has_real_source_url():
    """A tree where every source is None would pass the check above while
    proving nothing — assert a non-zero count of figures carrying a real
    source_url, not just that no figure carries an invalid one."""
    tree = _anora_tree()
    with_source = [figure for figure in tree if figure.source_url]
    assert len(with_source) > 0


def test_priced_tree_visits_at_least_four_distinct_figures():
    tree = _anora_tree()
    assert len(tree) >= 4, f"expected at least 4 distinct figures, got {len(tree)}"


# ---------------------------------------------------------------------------
# PRV-01 adjacency: distinct source_url -> distinct figure_id, never merged
# ---------------------------------------------------------------------------


def _minimal_figure(**overrides) -> Figure:
    defaults = dict(
        value=Decimal("100"),
        unit="USD",
        label="Test figure",
        derivation=("test derivation line",),
        inputs=(),
        source_url=None,
        date_checked=None,
        confidence="validated",
        live_fetched_this_run=False,
    )
    defaults.update(overrides)
    return Figure(**defaults)


def test_distinct_source_url_yields_distinct_figure_id():
    """Two Figures constructed with identical value and identical label but
    different source_url values must have different figure_id values and
    must never be merged into one identity."""
    fig_a = _minimal_figure(source_url="https://a.example/document")
    fig_b = _minimal_figure(source_url="https://b.example/document")
    assert fig_a.value == fig_b.value
    assert fig_a.label == fig_b.label
    assert fig_a.figure_id != fig_b.figure_id


# ---------------------------------------------------------------------------
# PRV-02: closed two-value confidence enum, no default, never coupled to the
# four-tier source-document-reliability vocabulary
# ---------------------------------------------------------------------------


def test_confidence_is_closed_enum():
    accepted = {"validated", "researched"}
    for value in accepted:
        figure = _minimal_figure(confidence=value)
        assert figure.confidence == value

    # The four-tier source-document-reliability vocabulary from
    # tests/test_source_truth.py's LEGAL_CONFIDENCE_TIERS — a different
    # axis, written out literally here (not imported) so the two
    # vocabularies stay uncoupled.
    rejected_source_reliability_tiers = ("HIGH", "MEDIUM", "MEDIUM-HIGH", "LOW")
    for value in rejected_source_reliability_tiers:
        with pytest.raises(ValueError):
            _minimal_figure(confidence=value)


def test_confidence_omitted_raises():
    with pytest.raises(TypeError):
        Figure(
            value=Decimal("100"),
            unit="USD",
            label="Test figure",
            derivation=("test derivation line",),
            inputs=(),
            source_url=None,
            date_checked=None,
            live_fetched_this_run=False,
        )


def test_combined_confidence_reports_researched_when_mixed():
    """A Figure built from one validated input and one researched input
    reports researched — the weaker tier always wins, aggregation never
    upgrades confidence."""
    validated_figure = _minimal_figure(confidence="validated")
    researched_figure = _minimal_figure(confidence="researched")
    assert combined_confidence([validated_figure, researched_figure]) == "researched"


# ---------------------------------------------------------------------------
# Inputs ordering: preserved regardless of a member's confidence tier
# ---------------------------------------------------------------------------


def test_inputs_order_preserved_regardless_of_member_confidence():
    fig_a = _minimal_figure(label="A", confidence="validated")
    fig_b = _minimal_figure(label="B", confidence="researched")
    combined = _minimal_figure(label="Combined", inputs=(fig_a, fig_b))
    assert combined.inputs == (fig_a, fig_b)

    # Figure is frozen — "swapping" a member's confidence tier means
    # constructing a fresh Figure with the same label but a different
    # confidence, then re-checking the order is unaffected.
    fig_a_upgraded = _minimal_figure(label="A", confidence="researched")
    combined_swapped = _minimal_figure(label="Combined", inputs=(fig_a_upgraded, fig_b))
    assert [f.label for f in combined_swapped.inputs] == [f.label for f in combined.inputs]


# ---------------------------------------------------------------------------
# PRV-03: non-empty, never-silent, ordered derivation over the real tree
# ---------------------------------------------------------------------------


def test_every_figure_in_priced_tree_has_non_empty_derivation():
    tree = _anora_tree()
    for figure in tree:
        assert figure.derivation, (
            f"{figure.label}: derivation must be non-empty (PRV-03), including "
            "a figure that had zero adjustments applied"
        )


def test_five_adjustment_steps_present_and_in_order():
    """New York's rule file declares no per-person ceiling and no
    per-project cap — the exact case a naive implementation could
    short-circuit a no-op step out of the sequence. Assert all five step
    markers are present as distinct derivation lines and appear strictly
    in application order: per-person ceiling, uplift stacking, rate,
    per-project cap, annual programme cap."""
    result = _priced_anora()
    derivation = result.programmes[0].gross_credit.derivation

    markers = [
        "per-person ceiling",
        "uplift stacking",
        "rate",
        "per-project cap",
        "annual programme cap",
    ]
    indices = []
    for marker in markers:
        matches = [i for i, line in enumerate(derivation) if marker in line]
        assert matches, f"no derivation line contains {marker!r}: {derivation}"
        indices.append(matches[0])

    assert len(set(indices)) == 5, (
        "two of the five step markers matched the same derivation line — the "
        f"count of distinct step lines must not collapse: indices {indices} "
        f"for derivation {derivation}"
    )
    assert indices == sorted(indices), (
        f"the five adjustment steps are not in application order: markers "
        f"{markers} matched at indices {indices} in {derivation}"
    )


def test_derivation_is_byte_identical_across_two_runs():
    """Pricing the same input twice in one process yields byte-identical
    derivation tuples — the derivation is a pure function of the rule file
    and the input spend, never influenced by process-local randomness
    (figure_id's uuid4 is deliberately excluded from this comparison)."""
    first = _priced_anora().programmes[0].gross_credit.derivation
    second = _priced_anora().programmes[0].gross_credit.derivation
    assert first == second
