"""JUR-05 as an executable pricing assertion, plus the concurrency/purity
invariant the additivity claim depends on (plan 02-06, Task 3).

Three assertions:

1. Pricing: `tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml` — a
   jurisdiction the engine has never seen, sharing no base_definition.type,
   rate_structure.type, mechanism, or currency with either curated file —
   prices correctly against expected values computed BY HAND from the
   fixture's own declared numbers (never by calling the engine on itself).
2. No-jurisdiction-specific-code: every jurisdiction identifier used
   anywhere in the repository (collected by globbing both rule-file
   directories, never a hard-coded list) is absent from `engine/`'s own
   source, comment-only lines removed.
3. Concurrency/purity: pricing two different jurisdictions in the same
   process, in both orderings, gives each the same result as pricing it
   alone — proving `engine/` holds no module-level mutable state.

The manual half this test CANNOT do — proving the commit that adds this
fixture and this test touches zero files under `engine/` — is recorded
verbatim in 02-06-SUMMARY.md from `git diff --name-only HEAD~1 HEAD | grep
'^engine/'`, per `02-VALIDATION.md`'s "Manual-Only Verifications" row: a
test cannot observe its own diff.
"""

from __future__ import annotations

from decimal import Decimal
from glob import glob
from pathlib import Path

import yaml

from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction

FIXTURE_PATH = "tests/fixtures/jurisdictions/zz-fixture-throwaway.yaml"
CURATED_DIR = "jurisdictions"
FIXTURE_DIR = "tests/fixtures/jurisdictions"
ENGINE_DIR = "engine"

TOTAL_QUALIFIED_SPEND = Decimal("50000000")  # CZK — invented, this fixture's own number

# ---------------------------------------------------------------------------
# 1. Pricing: expected values computed BY HAND from zz-fixture-throwaway.yaml's
# own declared numbers (see the fixture's own header comment for the full
# worked derivation). Never obtained by calling the engine — that would
# assert only that the engine agrees with itself.
# ---------------------------------------------------------------------------

# primary-throwaway: labour_only base (= total, via SpendBreakdown.from_total)
# = 50,000,000. blended_by_ceiling_split, no pct_core_cap declared:
#   enhanced_slice = min(50,000,000, 20,000,000) = 20,000,000
#   standard_slice = max(0, 50,000,000 - 20,000,000) = 30,000,000
#   enhanced_amount = 20,000,000 x 0.30 = 6,000,000
#   standard_amount = 30,000,000 x 0.20 = 6,000,000
#   gross credit (pre-cap) = 12,000,000
# per-project cap of 10,000,000 BINDS (12,000,000 > 10,000,000):
EXPECTED_PRIMARY_GROSS_CREDIT = Decimal("10000000")
# audit fee: qualifying base 50,000,000 falls in the declared [0, null) band
# -> deduct flat fee 25,000. rebate_grant: no further conversion.
EXPECTED_PRIMARY_NET_CASH = Decimal("10000000") - Decimal("25000")  # 9,975,000

# secondary-throwaway: labour_only base = 50,000,000, flat 0.05, no
# ceiling/minimum/caps declared, no audit fee schedule declared (-> $0
# deducted).
EXPECTED_SECONDARY_GROSS_CREDIT = Decimal("50000000") * Decimal("0.05")  # 2,500,000
EXPECTED_SECONDARY_NET_CASH = EXPECTED_SECONDARY_GROSS_CREDIT  # no fee deducted

# No mutual exclusivity is declared between the two programmes -> both
# contribute to the jurisdiction total.
EXPECTED_TOTAL_NET_CASH = EXPECTED_PRIMARY_NET_CASH + EXPECTED_SECONDARY_NET_CASH  # 12,475,000


def test_zz_fixture_throwaway_prices_correctly_against_hand_computed_values():
    """A jurisdiction the engine has never seen, exercising a base_definition
    type, rate_structure type, mechanism, and currency that neither
    `jurisdictions/us-ny.yaml` nor `jurisdictions/us-ct.yaml` uses, prices
    correctly on the first try."""
    ruleset = load_ruleset(FIXTURE_PATH)

    assert ruleset.jurisdiction.status == "synthetic_fixture"
    assert ruleset.jurisdiction.currency == "CZK"
    assert ruleset.jurisdiction.currency not in ("USD",), (
        "the fixture must declare a currency other than USD, per this plan's own instruction"
    )

    priced = price_jurisdiction(ruleset, TOTAL_QUALIFIED_SPEND)
    by_id = {pp.programme_id: pp for pp in priced.programmes}

    primary = by_id["primary-throwaway"]
    secondary = by_id["secondary-throwaway"]

    assert primary.gross_credit.value == EXPECTED_PRIMARY_GROSS_CREDIT
    assert primary.net_cash.point.value == EXPECTED_PRIMARY_NET_CASH

    assert secondary.gross_credit.value == EXPECTED_SECONDARY_GROSS_CREDIT
    assert secondary.net_cash.point.value == EXPECTED_SECONDARY_NET_CASH

    assert priced.total_net_cash.value == EXPECTED_TOTAL_NET_CASH
    assert priced.total_net_cash.value == Decimal("12475000")

    # The per-project cap genuinely bound (12,000,000 pre-cap credit clipped
    # to the declared 10,000,000 cap) — a derivation line records it.
    assert any(
        "per-project cap" in line and "clipped" in line for line in primary.gross_credit.derivation
    )


# ---------------------------------------------------------------------------
# 2. No-jurisdiction-specific code: every jurisdiction identifier used
# anywhere in the repository is absent from engine/'s own source.
# ---------------------------------------------------------------------------


def _collect_declared_jurisdiction_ids() -> set[str]:
    """Every `jurisdiction.id` declared under both rule-file directories,
    collected by globbing rather than a hard-coded list — so a jurisdiction
    added later is automatically covered by this assertion. Fails loud if
    either glob is empty (a vacuous pass over zero files proves nothing)."""
    curated_paths = sorted(glob(f"{CURATED_DIR}/*.yaml"))
    fixture_paths = sorted(glob(f"{FIXTURE_DIR}/*.yaml"))

    if not curated_paths:
        raise RuntimeError(
            f"No curated rule files found under {CURATED_DIR}/*.yaml — an empty glob "
            "must fail loudly, not silently cover zero jurisdiction identifiers."
        )
    if not fixture_paths:
        raise RuntimeError(
            f"No fixture files found under {FIXTURE_DIR}/*.yaml — an empty glob must "
            "fail loudly, not silently cover zero jurisdiction identifiers."
        )

    ids: set[str] = set()
    for path in (*curated_paths, *fixture_paths):
        with open(path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        ids.add(raw["jurisdiction"]["id"])
    return ids


def _engine_source_files_without_comment_only_lines() -> dict[str, str]:
    """Every `engine/**/*.py` file's source with comment-only lines (lines
    whose stripped content starts with `#`) removed. Trailing inline
    comments and docstrings are intentionally left intact — the check is
    meant to catch a jurisdiction identifier appearing ANYWHERE meaningful
    in engine code, not just executable statements; comment-only lines are
    excluded solely because prose (like this file's own header, and
    engine/credit.py's own explanatory comments) legitimately discusses
    jurisdictions like New York and Georgia by name without that being a
    JUR-05 violation."""
    sources: dict[str, str] = {}
    engine_paths = sorted(Path(ENGINE_DIR).rglob("*.py"))
    if not engine_paths:
        raise RuntimeError(
            f"No Python source files found under {ENGINE_DIR}/**/*.py — the "
            "no-jurisdiction-specific-code assertion has nothing to check."
        )
    for path in engine_paths:
        text = path.read_text(encoding="utf-8")
        kept_lines = [line for line in text.splitlines() if not line.strip().startswith("#")]
        sources[str(path)] = "\n".join(kept_lines)
    return sources


# Recorded amendment, Phase 4 plan 04-01 (D-53/T-04-01): `engine/city_profile_lookup.py`
# is a committed, explicit, allow-list dict mapping a visitor-supplied city
# STRING to a committed cost-profile STEM — never a jurisdiction-conditional
# code branch. JUR-05's actual concern (dimension 11, SCOPE-FREEZE.md) is
# that `engine/` must never DISPATCH on a jurisdiction id string; this file
# never dispatches on one, it only returns a stem string as inert data for
# the caller to join to a path. That stem follows the project-wide
# `{jurisdiction}-{city}` cost-profile naming convention fixed across every
# wave of this phase (`us-ny-new-york`, `us-ca-los-angeles`, `gb-london`,
# ...) — the SAME convention `data/cost_profiles/*.yaml`'s own committed
# filenames use — so it will always embed a jurisdiction-id substring by
# design, for every city this phase ever adds. This is structurally
# identical to `app/services/_paths.py::RULESET_PATH_BY_JURISDICTION`'s
# jurisdiction-id-to-path mapping, which the Phase 4 plan places OUTSIDE
# `engine/` for exactly this reason; `engine/city_profile_lookup.py`'s
# equivalent lookup must live INSIDE `engine/` instead (the plan's own
# T-04-01 path-safety boundary names it as "the ONLY module that maps a
# city string to a profile stem"), so the exclusion is narrowly scoped to
# this one file rather than weakening the scan generally.
# `test_engine_cost_localizer_dispatch_carries_no_jurisdiction_identifier`
# below re-asserts, independently, that the actual PRICING/dispatch code in
# `engine/cost_localizer.py` remains fully clean — this exclusion never
# extends there.
_JURISDICTION_ID_ALLOWED_FILES = {str(Path(ENGINE_DIR) / "city_profile_lookup.py")}


def test_no_jurisdiction_identifier_appears_in_engine_source():
    """`engine/` dispatches only on declared field values
    (`base_definition.type`, `rate_structure.type`, `mechanism`, etc.) —
    never on a jurisdiction identifier string. Every declared
    `jurisdiction.id`, collected by glob (never a hard-coded list, so a
    jurisdiction added later is automatically covered), must be absent from
    every engine source file with comment-only lines removed — except the
    one narrowly-scoped, documented exception recorded above."""
    jurisdiction_ids = _collect_declared_jurisdiction_ids()
    assert jurisdiction_ids, "collected zero jurisdiction ids — the glob discipline above failed silently"

    engine_sources = _engine_source_files_without_comment_only_lines()

    violations: list[str] = []
    for jurisdiction_id in sorted(jurisdiction_ids):
        for path, source in engine_sources.items():
            if path in _JURISDICTION_ID_ALLOWED_FILES:
                continue
            if jurisdiction_id in source:
                violations.append(f"{jurisdiction_id!r} found in {path}")

    assert not violations, (
        "engine/ must dispatch only on declared field values, never a jurisdiction "
        f"identifier string (JUR-05) — found: {violations}"
    )


def test_engine_cost_localizer_dispatch_carries_no_jurisdiction_identifier():
    """The narrow exclusion above must never extend to the actual
    cost-pricing dispatch code. `engine/cost_localizer.py` (Phase 4,
    plan 04-01) must remain fully clean of every declared jurisdiction
    identifier, comment-only lines removed — this is Task 1's own
    acceptance criterion, re-asserted here as a permanent structural
    guard alongside the rest of the JUR-05 suite."""
    jurisdiction_ids = _collect_declared_jurisdiction_ids()
    assert jurisdiction_ids, "collected zero jurisdiction ids — the glob discipline above failed silently"

    engine_sources = _engine_source_files_without_comment_only_lines()
    cost_localizer_path = str(Path(ENGINE_DIR) / "cost_localizer.py")
    assert cost_localizer_path in engine_sources, (
        f"expected {cost_localizer_path!r} to exist under engine/ — has it moved?"
    )

    source = engine_sources[cost_localizer_path]
    violations = [
        jurisdiction_id for jurisdiction_id in sorted(jurisdiction_ids) if jurisdiction_id in source
    ]
    assert not violations, (
        f"engine/cost_localizer.py must dispatch only on declared CityCostProfile "
        f"data, never a jurisdiction identifier string (JUR-05/D-53) — found: {violations}"
    )


# ---------------------------------------------------------------------------
# 3. Concurrency/purity: pricing two jurisdictions in the same process, in
# both orderings, must not cross-contaminate their results — proving engine/
# holds no module-level mutable state.
# ---------------------------------------------------------------------------


def test_pricing_two_jurisdictions_in_one_process_does_not_cross_contaminate():
    """Price `zz-fixture-throwaway` and the committed New York rule file
    together in the same process, in both orderings, and assert each result
    is identical to pricing that jurisdiction alone in isolation — figure
    values AND derivation tuples, not merely totals."""
    throwaway_ruleset = load_ruleset(FIXTURE_PATH)
    ny_ruleset = load_ruleset("jurisdictions/us-ny.yaml")

    throwaway_spend = TOTAL_QUALIFIED_SPEND
    ny_spend = Decimal("3964760")  # Anora's disclosed qualified spend (SOURCE-TRUTH.md SRC-01)

    # Pricing each alone, in isolation.
    throwaway_alone = price_jurisdiction(throwaway_ruleset, throwaway_spend)
    ny_alone = price_jurisdiction(ny_ruleset, ny_spend)

    # Ordering A: throwaway then New York, in the same process.
    throwaway_first_a = price_jurisdiction(throwaway_ruleset, throwaway_spend)
    ny_second_a = price_jurisdiction(ny_ruleset, ny_spend)

    # Ordering B: New York then throwaway, in the same process (reversed).
    ny_first_b = price_jurisdiction(ny_ruleset, ny_spend)
    throwaway_second_b = price_jurisdiction(throwaway_ruleset, throwaway_spend)

    def _assert_identical(a, b, *, label: str) -> None:
        assert a.total_net_cash.value == b.total_net_cash.value, label
        assert a.total_net_cash.derivation == b.total_net_cash.derivation, label
        assert len(a.programmes) == len(b.programmes), label
        for pp_a, pp_b in zip(a.programmes, b.programmes, strict=True):
            assert pp_a.programme_id == pp_b.programme_id, label
            assert pp_a.gross_credit.value == pp_b.gross_credit.value, label
            assert pp_a.gross_credit.derivation == pp_b.gross_credit.derivation, label
            assert pp_a.net_cash.point.value == pp_b.net_cash.point.value, label
            assert pp_a.net_cash.point.derivation == pp_b.net_cash.point.derivation, label

    _assert_identical(throwaway_alone, throwaway_first_a, label="throwaway: alone vs. ordering A")
    _assert_identical(ny_alone, ny_second_a, label="new york: alone vs. ordering A")
    _assert_identical(ny_alone, ny_first_b, label="new york: alone vs. ordering B")
    _assert_identical(throwaway_alone, throwaway_second_b, label="throwaway: alone vs. ordering B")
