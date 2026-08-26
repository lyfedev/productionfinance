"""Route B business logic: closed pair allowlist, fixture read,
`price_jurisdiction` call, exact/bounded verdict.

Direct production extraction of `tests/test_engine_against_validation_pairs
.py::_gross_credit_via_pipeline`'s already-proven sequence (03-PATTERNS.md
"exact match" analog) — this module does not invent new pricing logic, it
exposes the already-tested one through a callable a router can use for both
the JSON and HTML views (D-43: one handler's output, two views).

Every filesystem path is anchored to `REPO_ROOT`, never a CWD-relative
literal — `deploy/prodfin.service` sets `WorkingDirectory=/opt/prodfin` on
the host, and pytest runs from the repo root; only a module-anchored path
is correct in both.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from app.services._paths import REPO_ROOT, RULESET_PATH_BY_JURISDICTION
from engine.figure import Figure
from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction

__all__ = [
    "REPO_ROOT",
    "RULESET_PATH_BY_JURISDICTION",
    "VALIDATION_PAIRS_DIR",
    "MalformedFixtureError",
    "SelectablePair",
    "UnknownPairError",
    "ValidateResult",
    "reproduce_disclosure",
    "selectable_pairs",
]

VALIDATION_PAIRS_DIR = REPO_ROOT / "tests" / "fixtures" / "validation_pairs"


class UnknownPairError(Exception):
    """Raised by `reproduce_disclosure` when `pair_id` is not a member of
    the closed set of currently-selectable validation pairs (T-03-01)."""


class MalformedFixtureError(Exception):
    """Raised by `reproduce_disclosure` when a validation-pair fixture's
    own internal structure is inconsistent with its declared ruleset — a
    missing or malformed `assertion` block, an `assertion.mode` this
    function does not recognize, a `bounded` assertion missing
    `tolerance_bps`, a `program_id` that matches no priced programme in
    the ruleset, or a `qualified_spend` of zero (making the bounded-
    tolerance arithmetic undefined). These are repo-committed
    fixture-authoring bugs, not attacker input and not a rule file that
    legitimately cannot complete (see the `price_jurisdiction` `ValueError`
    handling above, which is WINDOWS.md #3's distinct honest-refusal
    path) — but a bad fixture must still never surface as an unhandled
    500; callers should catch this and render a readable refusal."""


@dataclass(frozen=True)
class SelectablePair:
    pair_id: str
    production_title: str
    # `str | None`, not `str` — populated from `data.get("jurisdiction_id")`
    # (selectable_pairs(), below), which returns None for any fixture
    # missing the key. A malformed fixture missing this key would
    # otherwise silently violate a non-Optional type hint at runtime
    # (03-REVIEW.md WR-05) — this doesn't crash today (`None not in
    # RULESET_PATH_BY_JURISDICTION` just resolves to the "no curated rule
    # model" branch), but the annotation must match what actually happens.
    jurisdiction_id: str | None
    selectable: bool
    unselectable_reason: str | None


@dataclass(frozen=True)
class ValidateResult:
    pair_id: str
    production_title: str
    jurisdiction_id: str
    disclosed_qualified_spend: Decimal
    disclosed_credit: Decimal
    computed_credit: Decimal | None
    verdict: str
    assertion_mode: str | None
    tolerance_bps: int | None
    computed_figure: Figure | None
    source_url: str | None
    source_document: str | None
    source_document_sha256: str | None
    report_period: str | None
    date_checked: str | None
    refusal_reason: str | None


def _load_fixture(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def selectable_pairs() -> tuple[SelectablePair, ...]:
    """Enumerate every committed validation-pair fixture. A pair is
    selectable only when its `status` is `active` **and** its
    `jurisdiction_id` has a curated rule model in this phase. An
    unselectable pair is never dropped from the returned tuple — it is
    reported with a plain-words reason so a caller can render it visibly
    rather than silently omit it."""
    pairs: list[SelectablePair] = []
    for fixture_path in sorted(VALIDATION_PAIRS_DIR.glob("*.yaml")):
        data = _load_fixture(fixture_path)
        pair_id = fixture_path.stem
        jurisdiction_id = data.get("jurisdiction_id")
        status = data.get("status")

        if status == "active" and jurisdiction_id in RULESET_PATH_BY_JURISDICTION:
            selectable = True
            reason: str | None = None
        elif status != "active":
            blocker = data.get("blocker")
            blocker_text = blocker.strip() if isinstance(blocker, str) and blocker.strip() else (
                f"status is {status!r}"
            )
            selectable = False
            reason = f"disclosure blocked: {blocker_text}"
        else:
            selectable = False
            reason = f"no curated rule model for {jurisdiction_id} in this phase"

        pairs.append(
            SelectablePair(
                pair_id=pair_id,
                production_title=data.get("production_title", pair_id),
                jurisdiction_id=jurisdiction_id,
                selectable=selectable,
                unselectable_reason=reason,
            )
        )
    return tuple(pairs)


def reproduce_disclosure(pair_id: str) -> ValidateResult:
    """Reproduce the disclosed credit for `pair_id` through the engine's
    real pipeline entry point (`price_jurisdiction`) and compare against
    the fixture's own disclosed figure.

    T-03-01: the FIRST statement of this function body checks `pair_id`
    against the closed set of currently-selectable pair ids. Only after
    that check does any path get built, and it is built from an
    already-validated member of that closed set — the untrusted `pair_id`
    string itself never reaches an `open()` call.
    """
    selectable_ids = {pair.pair_id for pair in selectable_pairs() if pair.selectable}
    if pair_id not in selectable_ids:
        raise UnknownPairError(pair_id)

    fixture_path = VALIDATION_PAIRS_DIR / f"{pair_id}.yaml"
    pair = _load_fixture(fixture_path)

    ruleset = load_ruleset(RULESET_PATH_BY_JURISDICTION[pair["jurisdiction_id"]])
    qualified_spend = Decimal(pair["qualified_spend"])
    disclosed = Decimal(pair["credit_amount"])
    assertion = pair.get("assertion")
    if not isinstance(assertion, dict):
        raise MalformedFixtureError(
            f"{pair_id}: fixture is missing a valid 'assertion' block"
        )
    mode = assertion.get("mode")
    if mode is None:
        raise MalformedFixtureError(f"{pair_id}: assertion is missing 'mode'")
    tolerance_bps = assertion.get("tolerance_bps")

    common_kwargs = {
        "pair_id": pair_id,
        "production_title": pair["production_title"],
        "jurisdiction_id": pair["jurisdiction_id"],
        "disclosed_qualified_spend": qualified_spend,
        "disclosed_credit": disclosed,
        "assertion_mode": mode,
        "tolerance_bps": tolerance_bps,
        "source_url": pair.get("source_url"),
        "source_document": pair.get("source_document"),
        "source_document_sha256": pair.get("source_document_sha256"),
        "report_period": pair.get("report_period"),
        "date_checked": pair.get("date_checked"),
    }

    try:
        priced = price_jurisdiction(ruleset, qualified_spend)
    except ValueError as exc:
        # WINDOWS.md #3: a rule file that cannot complete (the known case is
        # a `transferable` programme with a null `transfer_discount` range)
        # is caught and returned as an honest refusal, never a 500 and
        # never an invented rate. Phase 3 is NY-only so this is a guard
        # rail that no active NY pair currently exercises.
        return ValidateResult(
            **common_kwargs,
            computed_credit=None,
            computed_figure=None,
            verdict="cannot be computed",
            refusal_reason=str(exc),
        )

    program_id = pair.get("program_id")
    priced_programme = next(
        (pp for pp in priced.programmes if pp.programme_id == program_id), None
    )
    if priced_programme is None:
        raise MalformedFixtureError(
            f"{pair['production_title']!r} ({pair_id}): no priced programme matches "
            f"program_id {program_id!r} — check the ruleset's programme id "
            "against the fixture"
        )

    # RD-03: gross credit, never net cash — a disclosure reports the credit
    # issued/allocated, not what a producer nets after fees.
    computed_figure = priced_programme.gross_credit
    computed = computed_figure.value

    if mode == "exact":
        verdict = "exact match" if computed == disclosed else "MISMATCH"
    elif mode == "bounded":
        if tolerance_bps is None:
            raise MalformedFixtureError(
                f"{pair_id}: assertion.mode is 'bounded' but tolerance_bps is missing"
            )
        if qualified_spend == 0:
            raise MalformedFixtureError(
                f"{pair_id}: cannot compute a bounded-tolerance verdict — disclosed "
                "qualified_spend is 0"
            )
        implied_bps = (abs(disclosed - computed) / qualified_spend) * Decimal(10000)
        if implied_bps <= Decimal(tolerance_bps):
            verdict = (
                f"within declared tolerance ({implied_bps.quantize(Decimal('0.01'))} bps "
                f"of {tolerance_bps} bps)"
            )
        else:
            verdict = "MISMATCH"
    else:
        raise MalformedFixtureError(f"{pair_id}: unrecognized assertion.mode {mode!r}")

    return ValidateResult(
        **common_kwargs,
        computed_credit=computed,
        computed_figure=computed_figure,
        verdict=verdict,
        refusal_reason=None,
    )
