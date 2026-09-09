"""UI-06/PRV-04 (Phase 6, plan 06-03) — the provenance rendering layer.

Task 1 proves `app/templates/_figure.html` (rendered standalone, via
Jinja's own `Template.module` — the documented way to call a macro
directly without a surrounding page) never renders a figure as a bare
number, and that `basis`/`confidence` are two visually and structurally
distinct elements (RD-02) — never merged into one badge.

Task 2 proves `GET /assumptions` (a real rendered comparison surface)
derives its rate list from the ACTUAL Figure tree the engine produced —
never a hand-maintained list — and that the D-59/D-60 honesty
requirements hold on real, non-synthetic data: the default New York/Los
Angeles/London comparison genuinely contains a `modelling_assumption`-
basis leaf (the department crew-share ratios, `data/crew_tiers.yaml`),
so this is not a fixture invented to make the test pass — see
`data/cost_profiles/*.yaml`'s own comments confirming this basis is real
for every one of the three floor cities.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app, templates
from app.services.provenance import (
    build_rate_sheet,
    build_rate_sheets,
    collect_distinct_figures,
    collect_rate_figures,
    figure_provenance_state,
)
from engine.figure import Figure

client = TestClient(app)

_FLOOR_CITIES = ["New York, NY", "Los Angeles, CA", "London, UK"]

# Sourced from 04-CONTEXT.md § D-70 — the SAME vocabulary
# tests/test_app_compare_route.py's own module-level constant carries,
# duplicated here per this repo's established per-test-module discipline.
_PRESCRIPTIVE_VOCABULARY: tuple[str, ...] = (
    "recommend",
    "recommends",
    "recommended",
    "recommendation",
    "should",
    "consider",
    "considers",
    "considered",
    "considering",
    "best",
    "optimal",
    "you could",
    "you should",
)
_VOCABULARY_PATTERNS = {
    word: re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    for word in _PRESCRIPTIVE_VOCABULARY
}

_SPAN_TAG = re.compile(r"<span\b|</span>")


def _extract_figure_blocks(html: str) -> list[str]:
    """Every top-level `<span class="pf-figure" ...>...</span>` block in
    `html`, extracted with balanced-tag matching (not a naive
    non-greedy regex, which would stop at the FIRST inner `</span>`
    rather than the one that actually closes the figure)."""
    blocks: list[str] = []
    marker = '<span class="pf-figure"'
    idx = 0
    while True:
        start = html.find(marker, idx)
        if start == -1:
            break
        depth = 0
        end = None
        for match in _SPAN_TAG.finditer(html, start):
            if match.group() == "</span>":
                depth -= 1
                if depth == 0:
                    end = match.end()
                    break
            else:
                depth += 1
        assert end is not None, "unbalanced <span> found while extracting a pf-figure block"
        blocks.append(html[start:end])
        idx = end
    return blocks


def _minimal_figure(**overrides) -> Figure:
    defaults = {
        "value": Decimal(100),
        "unit": "USD",
        "label": "Test figure",
        "derivation": ("a derivation line",),
        "inputs": (),
        "source_url": None,
        "date_checked": None,
        "confidence": "researched",
        "live_fetched_this_run": False,
        "basis": "sourced",
    }
    defaults.update(overrides)
    return Figure(**defaults)


def _render(figure: Figure) -> str:
    tmpl = templates.env.get_template("_figure.html")
    return str(tmpl.module.render_figure(figure))


# ---------------------------------------------------------------------------
# Task 1 — _figure.html: no bare numbers, two distinct provenance axes
# ---------------------------------------------------------------------------


def test_figure_with_full_provenance_shows_source_link_and_date_checked():
    figure = _minimal_figure(
        source_url="https://example.gov/doc",
        date_checked=date(2026, 1, 1),
        basis="sourced",
        confidence="validated",
    )
    html = _render(figure)
    assert 'href="https://example.gov/doc"' in html
    assert "checked 2026-01-01" in html
    assert "pf-figure-provenance-unavailable" not in html


def test_leaf_figure_with_no_source_and_sourced_basis_shows_unavailable_state():
    """A leaf figure (no `.inputs`) that is missing a citation is a
    genuine dead end — must say so explicitly, never render as a bare
    number."""
    figure = _minimal_figure(source_url=None, basis="sourced")
    html = _render(figure)
    assert "provenance unavailable" in html
    assert "no source citation was recorded" in html
    # The value is still shown — never omitted, always framed.
    assert "100 USD" in html


def test_leaf_figure_modelling_assumption_names_the_specific_reason():
    figure = _minimal_figure(source_url=None, basis="modelling_assumption")
    html = _render(figure)
    assert "provenance unavailable" in html
    assert "modelling assumption" in html
    assert "no public source exists" in html


def test_aggregate_figure_with_no_source_url_is_never_labelled_unavailable():
    """An aggregate (has `.inputs`, no `source_url` of its own) has fully
    reachable provenance through its inputs — this must NOT render the
    "provenance unavailable" state, which would falsely claim a dead end
    where none exists."""
    leaf = _minimal_figure(label="Leaf", source_url="https://example.gov/leaf")
    aggregate = _minimal_figure(label="Aggregate total", inputs=(leaf,), source_url=None)
    html = _render(aggregate)
    assert "pf-figure-provenance-unavailable" not in html
    assert "computed from 1 input figure" in html


def test_basis_and_confidence_are_two_distinct_elements_never_merged():
    figure = _minimal_figure(basis="modelling_assumption", confidence="researched")
    html = _render(figure)
    basis_span = re.search(r'<span class="pf-figure-basis">(.*?)</span>', html, re.DOTALL)
    confidence_span = re.search(
        r'<span class="pf-figure-confidence">(.*?)</span>', html, re.DOTALL
    )
    assert basis_span is not None
    assert confidence_span is not None
    # The confidence label never contains the word "basis" and vice
    # versa — two separate statements, not one concatenated string.
    assert "confidence" not in basis_span.group(1)
    assert "basis" not in confidence_span.group(1)
    assert "modelling_assumption" in basis_span.group(1)
    assert "researched" in confidence_span.group(1)


def test_incentive_side_none_basis_is_labelled_not_applicable_never_missing():
    """`basis=None` on an incentive-side figure is a deliberate
    axis-does-not-apply state (engine/figure.py's own docstring), never
    rendered as though data were simply missing."""
    figure = _minimal_figure(basis=None)
    html = _render(figure)
    assert "not applicable to this figure" in html


def test_caveat_is_always_rendered_when_present():
    """D-61: the per-diem ceiling caveat must survive to the rendered
    page — this is the one component whose macro cannot drop it."""
    figure = _minimal_figure(
        caveat="federal reimbursement ceiling, not a market rate; actual cost is likely higher"
    )
    html = _render(figure)
    assert "federal reimbursement ceiling" in html


def test_confidence_label_never_carries_the_four_tier_source_vocabulary():
    """RD-02: `Figure.confidence` is a closed two-value axis. Assert the
    rendered confidence label never accidentally leaks the UNRELATED
    four-tier source-document-reliability vocabulary
    (`LOW`/`MEDIUM`/`MEDIUM-HIGH`/`HIGH`) — the two are never conflated."""
    for value in ("validated", "researched"):
        html = _render(_minimal_figure(confidence=value))
        confidence_span = re.search(
            r'<span class="pf-figure-confidence">(.*?)</span>', html, re.DOTALL
        )
        assert confidence_span is not None
        text = confidence_span.group(1)
        for forbidden in ("LOW", "MEDIUM", "MEDIUM-HIGH", "HIGH"):
            assert forbidden not in text


# ---------------------------------------------------------------------------
# app/services/provenance.py — the Figure-tree walk itself
# ---------------------------------------------------------------------------


def test_figure_provenance_state_classifies_all_three_states():
    sourced = _minimal_figure(source_url="https://example.gov/x")
    assert figure_provenance_state(sourced).state == "sourced"

    leaf = _minimal_figure(source_url="https://x.example/leaf")
    aggregate = _minimal_figure(inputs=(leaf,), source_url=None)
    assert figure_provenance_state(aggregate).state == "computed"

    dead_end = _minimal_figure(source_url=None, inputs=())
    state = figure_provenance_state(dead_end)
    assert state.state == "unavailable"
    assert state.reason


def test_collect_distinct_figures_dedupes_by_figure_id_over_a_dag():
    shared_leaf = _minimal_figure(label="Shared")
    branch_a = _minimal_figure(label="A", inputs=(shared_leaf,))
    branch_b = _minimal_figure(label="B", inputs=(shared_leaf,))
    total = _minimal_figure(label="Total", inputs=(branch_a, branch_b))

    distinct = collect_distinct_figures([total])
    assert len(distinct) == 4  # total, A, B, shared_leaf — shared_leaf counted once


def test_collect_rate_figures_returns_only_leaves_deduped_by_content():
    leaf_1 = _minimal_figure(label="Rate", value=Decimal(10), source_url="https://x/1")
    # Content-identical to leaf_1 but a distinct object (distinct
    # figure_id) — simulates the same published rate consulted twice.
    leaf_1_again = _minimal_figure(label="Rate", value=Decimal(10), source_url="https://x/1")
    leaf_2 = _minimal_figure(label="Other rate", value=Decimal(20), source_url="https://x/2")
    aggregate = _minimal_figure(label="Total", inputs=(leaf_1, leaf_1_again, leaf_2))

    rates = collect_rate_figures([aggregate])
    assert len(rates) == 2, f"expected 2 distinct rates, got {[r.label for r in rates]}"
    assert all(not rate.inputs for rate in rates)


def test_collect_rate_figures_never_includes_the_aggregate_itself():
    leaf = _minimal_figure(label="Leaf")
    aggregate = _minimal_figure(label="Aggregate", inputs=(leaf,))
    rates = collect_rate_figures([aggregate])
    labels = [r.label for r in rates]
    assert "Aggregate" not in labels
    assert "Leaf" in labels


# ---------------------------------------------------------------------------
# Task 2 — GET /assumptions: a real rendered comparison, no bare numbers,
# rate list derived from the actual Figure tree
# ---------------------------------------------------------------------------


def test_get_assumptions_bare_request_returns_200_with_default_floor_cities():
    response = client.get("/assumptions")
    assert response.status_code == 200
    text = response.text
    assert "us-ny-new-york" in text
    assert "us-ca-los-angeles" in text
    assert "gb-london" in text


def test_get_assumptions_no_bare_numbers_every_figure_has_provenance_or_unavailable_state():
    response = client.get("/assumptions")
    assert response.status_code == 200
    blocks = _extract_figure_blocks(response.text)
    assert len(blocks) >= 10, "expected many figures across three cities' rate sheets"

    for block in blocks:
        has_source_link = '<a class="pf-figure-source"' in block
        has_computed_note = "pf-figure-computed-from" in block
        has_unavailable_note = "pf-figure-provenance-unavailable" in block
        assert has_source_link or has_computed_note or has_unavailable_note, (
            f"figure block has no reachable provenance and no unavailable state "
            f"(a bare number): {block[:300]!r}"
        )
        # Every block also always carries its own value — the "no bare
        # number" guarantee never means the number itself is hidden.
        assert "pf-figure-value" in block


def test_get_assumptions_rate_list_matches_the_real_figure_tree_independently():
    """Non-vacuity check: independently re-walk the SAME comparison's
    `total_landed_cost` tree via a from-scratch implementation (mirrors
    `tests/test_route_a_basis_walk.py`'s own established `_collect_tree`
    pattern) and assert every leaf label the independent walk finds is
    present in the rendered page — proving the panel is derived from the
    tree, not a hand-maintained list that happens to overlap."""
    from app.services.compare import CompareInputs, build_comparison

    comparison = build_comparison(CompareInputs(candidate_cities=["New York, NY"]))
    city = comparison.net_ranked[0] if comparison.net_ranked else comparison.incentive_not_modelled[0]

    def _independent_walk(root: Figure) -> list[Figure]:
        seen: dict[str, Figure] = {}
        stack = [root]
        while stack:
            fig = stack.pop()
            if fig.figure_id in seen:
                continue
            seen[fig.figure_id] = fig
            stack.extend(fig.inputs)
        return [f for f in seen.values() if not f.inputs]

    independent_leaves = _independent_walk(city.total_landed_cost)
    assert independent_leaves, "expected at least one leaf figure in a real priced tree"

    response = client.get("/assumptions", params={"candidate_cities": "New York, NY"})
    assert response.status_code == 200
    text = response.text

    from markupsafe import escape as _escape

    distinct_labels = {leaf.label for leaf in independent_leaves}
    for label in distinct_labels:
        # Jinja's autoescaping renders "&" etc. as HTML entities — compare
        # against the SAME escaped form the page actually renders.
        assert str(_escape(label)) in text, (
            f"leaf figure label {label!r} from the real tree is absent from the rendered "
            "assumptions page"
        )


def test_get_assumptions_default_comparison_contains_a_real_modelling_assumption_rate():
    """Non-fabricated evidence for D-59: the default floor-city
    comparison genuinely reaches a `modelling_assumption`-basis leaf
    (department crew-share ratios, `data/crew_tiers.yaml`) for every
    committed city — confirmed directly against real data, not a
    constructed fixture."""
    response = client.get("/assumptions")
    assert response.status_code == 200
    assert 'data-basis="modelling_assumption"' in response.text


def test_get_assumptions_totals_never_present_a_mixed_basis_total_as_sourced():
    """D-59: for each city sheet, if the underlying rate list contains a
    `modelling_assumption` figure, that same city's rendered
    `Total landed cost` figure must ALSO carry `basis:
    modelling_assumption` — never `sourced` — proving the total's own
    label is truthful about its weakest input, using real computed data
    (no basis is recomputed by the rendering layer; it only displays what
    `engine.figure.combined_basis` already decided)."""
    from app.services.compare import CompareInputs, build_comparison

    comparison = build_comparison(CompareInputs(candidate_cities=list(_FLOOR_CITIES)))
    sheets = build_rate_sheets((*comparison.net_ranked, *comparison.incentive_not_modelled))
    assert sheets, "expected at least one priced city"

    for sheet in sheets:
        basis_values = {rate.basis for rate in sheet.rates}
        if "modelling_assumption" in basis_values:
            assert sheet.total_landed_cost.basis == "modelling_assumption", (
                f"{sheet.city_id}: rate list contains a modelling_assumption input but "
                f"total_landed_cost.basis is {sheet.total_landed_cost.basis!r}, not "
                "'modelling_assumption' — a mixed-basis total must never present a "
                "stronger tier than its weakest input"
            )


def test_get_assumptions_gaps_are_a_named_list_never_a_dollar_line():
    response = client.get("/assumptions")
    assert response.status_code == 200
    text = response.text
    for exclusion in (
        "overtime",
        "turnaround penalties",
        "meal penalties",
        "kit fees",
        "non-union local differentials",
        "negotiated hotel rates",
    ):
        assert exclusion in text

    gaps_section = re.search(r'<section class="pf-gaps".*?</section>', text, re.DOTALL)
    assert gaps_section is not None
    # Scoped to the actual rendered list markup, not the section's own
    # explanatory prose (which legitimately DESCRIBES the "never a $0"
    # rule in words) — the honesty requirement is about what appears as
    # a LINE ITEM, not about the word "$0" appearing anywhere at all.
    exclusions_list = re.search(
        r'<ul class="pf-permanent-exclusions-list">.*?</ul>', gaps_section.group(0), re.DOTALL
    )
    assert exclusions_list is not None
    money_shaped = re.search(r"\$\s?0(\.0+)?\b", exclusions_list.group(0))
    assert money_shaped is None, "a $0 line item found in the acknowledged-gaps list"


def test_get_assumptions_query_string_bounds_candidate_cities():
    """Mirrors app/routers/compare.py's own T-06-05 bound — /assumptions
    reuses build_comparison unchanged, so the same cap applies."""
    too_many = [f"City {i}" for i in range(20)]
    response = client.get("/assumptions", params=[("candidate_cities", c) for c in too_many])
    assert response.status_code == 422


def test_get_assumptions_d70_vocabulary_gate_over_rendered_html():
    response = client.get(
        "/assumptions",
        params=[("candidate_cities", c) for c in [*_FLOOR_CITIES, "Nowhereville, ZZ"]],
    )
    assert response.status_code == 200
    violations = [
        word for word in _PRESCRIPTIVE_VOCABULARY if _VOCABULARY_PATTERNS[word].search(response.text)
    ]
    assert not violations, f"prescriptive vocabulary found in rendered /assumptions HTML: {violations}"


def test_get_assumptions_script_tag_city_not_reflected_unescaped():
    response = client.get(
        "/assumptions", params=[("candidate_cities", "<script>alert(1)</script>")]
    )
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text


def test_build_rate_sheet_carries_the_engines_own_not_priced_and_exclusions():
    from app.services.compare import CompareInputs, build_comparison

    comparison = build_comparison(CompareInputs(candidate_cities=["New York, NY"]))
    city = comparison.net_ranked[0] if comparison.net_ranked else comparison.incentive_not_modelled[0]
    sheet = build_rate_sheet(city)
    assert sheet.permanent_exclusions == city.landed_cost.permanent_exclusions
    assert sheet.not_priced == city.landed_cost.not_priced
