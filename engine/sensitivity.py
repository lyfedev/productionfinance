"""OUT-03 — which single declared input most moves the gap, found by
actually moving it, one input at a time, through the real pipeline
(D-67). Never a calculus-based slope estimate or a linear extrapolation:
the model is full of cliffs (the minimum-spend threshold, tiered rate
bands, the ceiling split, the per-project cap's strictly-greater-than
boundary, crew tier bands, dated union rate rows) and a slope estimate
cannot see a cliff it did not cross.

`data/sensitivity_steps.yaml` (D-68) declares every perturbable input and
its step size, in that input's own natural unit — a new row is a table
addition, mirroring `tests/mutation_targets.yaml`'s precedent (D-51).
There is DELIBERATELY no shared scale across rows: a step of one shoot
day and a step of one imported crew member are not comparable
magnitudes, and this module never invents a normalisation to declare a
single winner.

**The generic-vs-special-case step-application split, stated plainly.**
Most declared rows are a plain integer field on `ProductionSpec`
(`shoot_days_stage`, `shoot_days_location`, `principal_cast_count`) —
these apply through `_apply_generic_numeric_step`, which reads the
field name and step size from the declared row alone. Adding a NEW row
for a plain integer field requires zero code changes here.

Four field names are the disclosed exception: perturbing them naively
would produce an INVALID `ProductionSpec` (a validator failure), because
each is coupled to another field by one of `ProductionSpec`'s own
`model_validator`s:

- `crew_size` — must keep `crew_imported_count + crew_hired_locally_count
  == crew_size` (INP-03/INP-05); the increment is applied to
  locally-hired crew, disclosed on the row's own `step_text`.
- `crew_imported_count` — a genuine composition SWAP (imported for
  locally-hired) that holds `crew_size` fixed, so it isolates the
  travel-only cost effect (COST-04/COST-05) from the crew-size row's
  labour-cost effect.
- `principal_cast_imported_count` — must keep `principal_cast_imported
  _count <= principal_cast_count` (INP-04); converts a non-imported cast
  member when one exists, otherwise adds a new one (both are disclosed
  on the row).
- `start_quarter` — an enum, not an integer; advancing it can also roll
  `start_year` forward (INP-06).

`_regime_signature`/`_diff_regime_signatures` (Task 2, D-69) build a
frozen, comparable record of every discrete branch the chain took for a
spec, by READING the values and derivation text the chain already
produced (dated union rate row ids, the resolved crew tier, the
minimum-spend/tiered-band/per-project-cap derivation lines) — never by
re-deriving them independently, so a signature can never drift from what
actually happened.

JURISDICTION-AGNOSTIC by construction (JUR-05/D-53): a jurisdiction's
rule file is located generically from `CityCostProfile.jurisdiction_id`
(data already resolved by `engine.cost_profile.load_cost_profile`) joined
to the SAME `jurisdictions/{jurisdiction_id}.yaml` naming convention this
repo's other committed rule files already use — never a hard-coded
jurisdiction identifier string anywhere in this module's own source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from engine.budget import _infer_department_tier, build_canonical_budget
from engine.cost_localizer import LocalizedBudget, localize, quarter_start_date
from engine.cost_profile import COST_PROFILES_DIR, CityCostProfile, load_cost_profile
from engine.figure import Figure
from engine.gap import decompose_gap
from engine.models import JurisdictionRuleSet, load_ruleset
from engine.ranker import rank
from engine.rounding import quantize_money
from engine.spec import CrewHeadcount, ProductionSpec, resolve_crew_tier

__all__ = [
    "JURISDICTIONS_DIR",
    "SENSITIVITY_STEPS_PATH",
    "RegimeSignature",
    "SensitivityRow",
    "SensitivityStep",
    "StepNotApplicable",
    "load_sensitivity_steps",
    "most_moving_row",
    "sensitivity_rows",
]

# Module-anchored, never CWD-relative (T-04-01/D-46 convention) — the
# systemd unit and pytest run from different working directories.
SENSITIVITY_STEPS_PATH = Path(__file__).resolve().parents[1] / "data" / "sensitivity_steps.yaml"

# The SAME directory `app/services/_paths.py::RULESET_PATH_BY_JURISDICTION`
# points into — built generically from a `jurisdiction_id` VALUE (data),
# never a literal jurisdiction id, so this module never dispatches on one
# (JUR-05/D-53).
JURISDICTIONS_DIR = Path(__file__).resolve().parents[1] / "jurisdictions"

_STATUS_VALUES = ("active", "inactive")


class StrictModel(BaseModel):
    """Local mirror of `engine.spec.StrictModel` / `engine.cost_profile
    .StrictModel` (forbids unrecognised fields) — the same two-line
    convention, not imported, per that precedent's own stated reasoning."""

    model_config = ConfigDict(extra="forbid")


class SensitivityStep(StrictModel):
    """One declared row of `data/sensitivity_steps.yaml` (D-68). Every
    numeric value is a quoted string (RD-01) — `step` is parsed with
    `Decimal()` by the caller, never as a bare YAML-native number."""

    id: str
    spec_field: str
    step: str
    unit_label: str
    requirement: str
    status: Literal["active", "inactive"]
    why: str

    @model_validator(mode="after")
    def _step_must_be_a_whole_number(self) -> SensitivityStep:
        """WR-03 (04-REVIEW.md): `_step_delta` applies every declared row
        as `int(Decimal(step.step))` — a plain truncating conversion. That
        is currently a no-op (every committed row's `step` is `"1"`), but
        this module's own docstring promises "a new row is a table
        addition ... zero code changes" for any plain-integer
        `spec_field` — a future row declaring a fractional step (e.g.
        `"0.5"` for some future fractional-unit field) would otherwise be
        silently truncated to `0`, a zero-effect step reported as a real
        perturbation, with no test or schema guard catching it. Raise at
        load time instead, naming the offending row and step."""
        try:
            step_value = Decimal(self.step)
        except InvalidOperation as exc:
            raise ValueError(
                f"sensitivity step {self.id!r} declares step={self.step!r}, which is "
                "not a valid decimal number"
            ) from exc
        if step_value % 1 != 0:
            raise ValueError(
                f"sensitivity step {self.id!r} declares a fractional step "
                f"({self.step!r}) — _step_delta() converts every step with "
                "int(Decimal(step.step)), which would silently TRUNCATE a "
                "fractional step to a zero-effect integer perturbation rather than "
                "raise. Every declared step must be a whole number until "
                "_apply_generic_numeric_step (and every _apply_*_step special case) "
                "is widened to perturb a non-integer ProductionSpec field."
            )
        return self


class StepNotApplicable(Exception):
    """Raised by an `_apply_*_step` function when `step` cannot be applied
    to `spec` without violating one of `ProductionSpec`'s own validators
    (or the field simply is not set on this spec). Caught by
    `sensitivity_rows`, which reports a row carrying the message as its
    `note` rather than letting the exception propagate — a step that
    cannot be applied is a reported fact, never a silent skip."""


def load_sensitivity_steps(path: Path | None = None) -> tuple[SensitivityStep, ...]:
    """Load every declared row of `data/sensitivity_steps.yaml` (or an
    explicit `path`, for tests), via `yaml.safe_load` only — matching
    every other committed-table reader in this repo
    (`engine.spec.resolve_crew_tier`, `engine.union_rates.load_union_rates`)."""
    if path is None:
        path = SENSITIVITY_STEPS_PATH
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return tuple(SensitivityStep.model_validate(row) for row in raw["sensitivity_steps"])


@dataclass(frozen=True)
class RegimeSignature:
    """A frozen, comparable record of every discrete branch the pricing
    chain took for one city, for one spec (D-69). Every field is read
    from a value or a derivation line the chain already produced — never
    re-derived independently, so the signature cannot drift from what
    actually happened. `None` means "not applicable for this city/spec"
    (e.g. no incentive is priced at all), never "unknown"."""

    crew_tier: str
    rate_row_ids: tuple[str, ...]
    per_diem_month_keys: tuple[str, ...]
    minimum_spend_state: str | None
    rate_tier_band: str | None
    per_project_cap_state: str | None


@dataclass(frozen=True)
class SensitivityRow:
    """One perturbed input's effect on the gap between two cities (D-67).

    `step_text` names the step and, for a special-case field, discloses
    which companion field absorbed the compensating adjustment (D-68) —
    the step is displayed on every row, never implied. `cliff_crossings`
    is populated by `_diff_regime_signatures` (Task 2, D-69); empty for a
    row whose perturbation crossed no discrete branch. `note` carries the
    cannot-perturb reason or the not-priced disclosure — `None` otherwise.
    """

    step_id: str
    spec_field: str
    step_text: str
    baseline_gap: Decimal
    perturbed_gap: Decimal
    delta: Decimal
    direction: Literal["widened", "narrowed", "unchanged"]
    cliff_crossings: tuple[str, ...]
    note: str | None


def _resolve_crew_headcount(spec: ProductionSpec) -> CrewHeadcount:
    """Mirrors `app/services/spec.py::handle_spec_submission`'s own crew-
    headcount resolution exactly — an explicit `crew_size` is never routed
    through `resolve_crew_tier`."""
    if spec.crew_size is not None:
        return CrewHeadcount(
            low=spec.crew_size,
            high=spec.crew_size,
            basis="supplied by the visitor",
            provenance_note="an explicit headcount was supplied, not resolved from a tier",
        )
    return resolve_crew_tier(spec.crew_tier)


def _with_updates(spec: ProductionSpec, updates: dict[str, object]) -> ProductionSpec:
    """Apply `updates` to `spec` and re-validate the WHOLE spec (never
    `model_copy`, which does not re-run validators) — a step that leaves
    `ProductionSpec` invalid raises `StepNotApplicable` naming the
    violated rule, rather than propagating a raw `ValidationError`."""
    try:
        return ProductionSpec.model_validate({**spec.model_dump(), **updates})
    except ValidationError as exc:
        raise StepNotApplicable(str(exc)) from exc


def _step_delta(step: SensitivityStep) -> int:
    return int(Decimal(step.step))


def _apply_generic_numeric_step(
    spec: ProductionSpec, step: SensitivityStep
) -> tuple[ProductionSpec, str]:
    """The GENERIC path: increment a plain integer field by the declared
    step, touching no other field. Any `spec_field` not named in
    `_SPECIAL_STEP_APPLIERS` reaches this function — this is what lets a
    new declared row for a plain integer field appear in the output with
    zero code changes here (Task 1's own acceptance criterion)."""
    try:
        current = getattr(spec, step.spec_field)
    except AttributeError as exc:
        raise StepNotApplicable(
            f"ProductionSpec has no field named {step.spec_field!r}"
        ) from exc
    if current is None:
        raise StepNotApplicable(
            f"{step.spec_field!r} is not set on this production spec (it is None) — "
            "this row does not apply"
        )
    if not isinstance(current, int) or isinstance(current, bool):
        raise StepNotApplicable(
            f"{step.spec_field!r} is {type(current).__name__!r}, not a plain integer "
            "field — the generic increment mechanism only applies to integer fields"
        )
    delta = _step_delta(step)
    updated_value = current + delta
    perturbed = _with_updates(spec, {step.spec_field: updated_value})
    note = f"{step.spec_field} increased by {delta} ({current} -> {updated_value}); no other field adjusted"
    return perturbed, note


def _apply_crew_size_step(spec: ProductionSpec, step: SensitivityStep) -> tuple[ProductionSpec, str]:
    if spec.crew_size is None:
        raise StepNotApplicable(
            "crew_size is not set on this production spec (a crew_tier was supplied "
            "instead, INP-03) — this row does not apply"
        )
    delta = _step_delta(step)
    new_crew_size = spec.crew_size + delta
    new_locally_hired = spec.crew_hired_locally_count + delta
    perturbed = _with_updates(
        spec, {"crew_size": new_crew_size, "crew_hired_locally_count": new_locally_hired}
    )
    note = (
        f"crew_size increased by {delta} ({spec.crew_size} -> {new_crew_size}); the "
        f"increment is applied to LOCALLY-HIRED crew ({spec.crew_hired_locally_count} -> "
        f"{new_locally_hired}), not imported crew — this row's own declared choice"
    )
    return perturbed, note


def _apply_crew_imported_step(
    spec: ProductionSpec, step: SensitivityStep
) -> tuple[ProductionSpec, str]:
    delta = _step_delta(step)
    if spec.crew_hired_locally_count < delta:
        raise StepNotApplicable(
            f"cannot shift {delta} locally-hired crew member(s) to imported — only "
            f"{spec.crew_hired_locally_count} locally-hired crew member(s) exist on "
            "this spec"
        )
    new_imported = spec.crew_imported_count + delta
    new_locally_hired = spec.crew_hired_locally_count - delta
    perturbed = _with_updates(
        spec, {"crew_imported_count": new_imported, "crew_hired_locally_count": new_locally_hired}
    )
    note = (
        f"crew_imported_count increased by {delta} ({spec.crew_imported_count} -> "
        f"{new_imported}), crew_hired_locally_count decreased by the same amount "
        f"({spec.crew_hired_locally_count} -> {new_locally_hired}) to keep crew_size "
        "unchanged — a composition swap, not a headcount change"
    )
    return perturbed, note


def _apply_principal_cast_imported_step(
    spec: ProductionSpec, step: SensitivityStep
) -> tuple[ProductionSpec, str]:
    delta = _step_delta(step)
    new_imported = spec.principal_cast_imported_count + delta
    if new_imported <= spec.principal_cast_count:
        perturbed = _with_updates(spec, {"principal_cast_imported_count": new_imported})
        note = (
            f"principal_cast_imported_count increased by {delta} "
            f"({spec.principal_cast_imported_count} -> {new_imported}); "
            f"principal_cast_count is unchanged ({spec.principal_cast_count}) since a "
            "non-imported cast member is available to convert"
        )
        return perturbed, note

    new_total = spec.principal_cast_count + delta
    perturbed = _with_updates(
        spec,
        {"principal_cast_imported_count": new_imported, "principal_cast_count": new_total},
    )
    note = (
        f"principal_cast_imported_count increased by {delta} "
        f"({spec.principal_cast_imported_count} -> {new_imported}); no non-imported "
        f"cast member was available to convert, so principal_cast_count is ALSO "
        f"increased by {delta} ({spec.principal_cast_count} -> {new_total}) to add a "
        "new imported cast member rather than violate the imported-within-total rule"
    )
    return perturbed, note


_QUARTER_ORDER: tuple[str, ...] = ("Q1", "Q2", "Q3", "Q4")


def _apply_start_quarter_step(
    spec: ProductionSpec, step: SensitivityStep
) -> tuple[ProductionSpec, str]:
    delta = _step_delta(step)
    current_index = _QUARTER_ORDER.index(spec.start_quarter)
    new_index = (current_index + delta) % 4
    year_delta = (current_index + delta) // 4
    new_quarter = _QUARTER_ORDER[new_index]
    new_year = spec.start_year + year_delta
    perturbed = _with_updates(spec, {"start_quarter": new_quarter, "start_year": new_year})
    note = (
        f"start_quarter advanced by {delta} quarter(s): {spec.start_quarter} "
        f"{spec.start_year} -> {new_quarter} {new_year}"
    )
    return perturbed, note


# The disclosed, narrowly-scoped exception set — see this module's own
# docstring for why each of these four (and only these four) needs a
# compensating adjustment to stay a valid ProductionSpec. Every OTHER
# spec_field reaches `_apply_generic_numeric_step` with zero code changes.
_SPECIAL_STEP_APPLIERS = {
    "crew_size": _apply_crew_size_step,
    "crew_imported_count": _apply_crew_imported_step,
    "principal_cast_imported_count": _apply_principal_cast_imported_step,
    "start_quarter": _apply_start_quarter_step,
}


def _apply_step(spec: ProductionSpec, step: SensitivityStep) -> tuple[ProductionSpec, str]:
    """Apply `step` to `spec`, returning the perturbed spec and a
    disclosure note. Raises `StepNotApplicable` — never lets a bare
    `ValidationError`/`AttributeError` escape — when the step cannot be
    applied without producing an invalid `ProductionSpec`."""
    applier = _SPECIAL_STEP_APPLIERS.get(step.spec_field, _apply_generic_numeric_step)
    return applier(spec, step)


def _step_text(step: SensitivityStep, application_note: str) -> str:
    return f"+{step.step} {step.unit_label} — {application_note}"


# ---------------------------------------------------------------------------
# The regime signature (D-69) — every pattern below reads text the chain
# ALREADY emitted (row ids, tier-band lookups, cap-clip lines), never
# re-derives a value independently.
# ---------------------------------------------------------------------------

_ROW_ID_PATTERN = re.compile(r"row '([^']+)'")
_MONTH_LINE_PATTERN = re.compile(r"^(\d{4}-\d{2}):")
_MIN_SPEND_BELOW_PATTERN = re.compile(r"is below the declared minimum-spend threshold")
_MIN_SPEND_MEETS_PATTERN = re.compile(r"meets the declared minimum-spend threshold")
_TIER_BAND_PATTERN = re.compile(r"falls in the band (\[[^)]*\))")
_CAP_CLIPPED_PATTERN = re.compile(r"exceeds the cap and is clipped to")
_CAP_NOT_BINDING_PATTERN = re.compile(r"is declared but not binding")


def _regime_signature(
    spec: ProductionSpec,
    localized: LocalizedBudget,
    programme_figures: tuple[Figure, ...],
) -> RegimeSignature:
    """Build the regime signature for one city, one spec (D-69).

    `programme_figures` is every declared programme's own contribution
    Figure (e.g. `RankedCity.incentive_figure.inputs` — `total_net_cash
    .inputs` is exactly the per-programme contribution figures
    `engine.pipeline.price_jurisdiction` built, each one carrying its
    FULL derivation history via `Figure.with_step`'s append-only
    chaining) — an empty tuple when no incentive is priced for this city
    at all.
    """
    crew_headcount = _resolve_crew_headcount(spec)
    crew_tier = _infer_department_tier(spec, crew_headcount)

    rate_row_ids: list[str] = []
    per_diem_month_keys: list[str] = []
    for figure in localized.lines:
        for line in figure.derivation:
            row_match = _ROW_ID_PATTERN.search(line)
            if row_match:
                rate_row_ids.append(f"{figure.label}: row {row_match.group(1)}")
            month_match = _MONTH_LINE_PATTERN.match(line)
            if month_match:
                per_diem_month_keys.append(f"{figure.label}: {month_match.group(1)}")

    minimum_spend_state: str | None = None
    rate_tier_band: str | None = None
    per_project_cap_state: str | None = None
    for programme_figure in programme_figures:
        for line in programme_figure.derivation:
            if _MIN_SPEND_BELOW_PATTERN.search(line):
                minimum_spend_state = "below the declared minimum spend"
            elif _MIN_SPEND_MEETS_PATTERN.search(line):
                minimum_spend_state = "meets the declared minimum spend"
            band_match = _TIER_BAND_PATTERN.search(line)
            if band_match:
                rate_tier_band = band_match.group(1)
            if _CAP_CLIPPED_PATTERN.search(line):
                per_project_cap_state = "clipped at the per-project cap"
            elif _CAP_NOT_BINDING_PATTERN.search(line):
                per_project_cap_state = "declared but not binding"

    return RegimeSignature(
        crew_tier=crew_tier,
        rate_row_ids=tuple(sorted(set(rate_row_ids))),
        per_diem_month_keys=tuple(sorted(set(per_diem_month_keys))),
        minimum_spend_state=minimum_spend_state,
        rate_tier_band=rate_tier_band,
        per_project_cap_state=per_project_cap_state,
    )


def _diff_regime_signatures(
    before: RegimeSignature, after: RegimeSignature, *, city_id: str
) -> tuple[str, ...]:
    """Every difference between `before` and `after`, as a plain-words
    fact naming what changed — never a verb, never an evaluation of
    whether the change is good (D-70). `city_id` is a cost-profile city
    id (`CityCostProfile.city_id`), never a jurisdiction id — this module
    dispatches on neither (JUR-05/D-53)."""
    crossings: list[str] = []

    if before.crew_tier != after.crew_tier:
        crossings.append(
            f"{city_id!r}: crosses the crew-tier boundary used for department "
            f"crew-share lookup — {before.crew_tier!r} before, {after.crew_tier!r} after"
        )
    if before.rate_row_ids != after.rate_row_ids:
        crossings.append(
            f"{city_id!r}: the selected dated union rate row(s) change — "
            f"{before.rate_row_ids!r} before, {after.rate_row_ids!r} after"
        )
    if before.minimum_spend_state != after.minimum_spend_state:
        crossings.append(
            f"{city_id!r}: crosses the minimum-spend threshold — "
            f"{before.minimum_spend_state!r} before, {after.minimum_spend_state!r} after"
        )
    if before.rate_tier_band != after.rate_tier_band:
        crossings.append(
            f"{city_id!r}: crosses a tiered-rate band boundary — "
            f"{before.rate_tier_band!r} before, {after.rate_tier_band!r} after"
        )
    if before.per_project_cap_state != after.per_project_cap_state:
        crossings.append(
            f"{city_id!r}: crosses the per-project cap clip boundary — "
            f"{before.per_project_cap_state!r} before, {after.per_project_cap_state!r} after"
        )
    if before.per_diem_month_keys != after.per_diem_month_keys:
        crossings.append(
            f"{city_id!r}: the per-diem month band(s) covered by the shoot calendar "
            f"change — {before.per_diem_month_keys!r} before, "
            f"{after.per_diem_month_keys!r} after"
        )

    return tuple(crossings)


def _load_jurisdiction_rulesets(
    *profiles: CityCostProfile,
) -> dict[str, JurisdictionRuleSet]:
    """Resolve every distinct `jurisdiction_id` across `profiles` to a
    committed rule file, generically: `jurisdictions/{jurisdiction_id}
    .yaml` — the SAME naming convention this repo's other committed rule
    files already use, built from a runtime VALUE (`profile.jurisdiction
    _id`), never a literal jurisdiction id (JUR-05/D-53). A jurisdiction_id
    with no matching committed file is simply absent from the returned
    mapping — `engine.ranker.rank` already treats a missing entry as "no
    rule file exists yet" (D-56), never a raise."""
    rulesets: dict[str, JurisdictionRuleSet] = {}
    for profile in profiles:
        jurisdiction_id = profile.jurisdiction_id
        if jurisdiction_id is None or jurisdiction_id in rulesets:
            continue
        path = JURISDICTIONS_DIR / f"{jurisdiction_id}.yaml"
        if path.exists():
            rulesets[jurisdiction_id] = load_ruleset(path)
    return rulesets


def _price_pair(
    spec: ProductionSpec,
    profile_a: CityCostProfile,
    profile_b: CityCostProfile,
    ruleset_by_jurisdiction: dict[str, JurisdictionRuleSet],
    *,
    reporting_currency: str,
) -> tuple[Decimal, RegimeSignature, RegimeSignature]:
    """Run the WHOLE chain — build the canonical budget, localize both
    cities, rank (which prices the incentive when a rule file exists),
    decompose the gap — for `spec`, and return the headline gap value
    plus each city's regime signature. A literal re-run every time this
    is called, never a slope-based estimate or a scaled extrapolation of
    another call's result (D-67)."""
    crew_headcount = _resolve_crew_headcount(spec)
    budget = build_canonical_budget(spec, crew_headcount)
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)

    localized_a = localize(budget, profile_a, on_date=on_date, spec=spec)
    localized_b = localize(budget, profile_b, on_date=on_date, spec=spec)

    ranked = rank(
        {profile_a.city_id: localized_a, profile_b.city_id: localized_b},
        ruleset_by_jurisdiction,
        reporting_currency=reporting_currency,
    )
    ranked_by_id = {city.city_id: city for city in ranked}
    ranked_a = ranked_by_id[profile_a.city_id]
    ranked_b = ranked_by_id[profile_b.city_id]

    decomposition = decompose_gap(
        profile_a.city_id,
        ranked_a.landed_cost,
        profile_b.city_id,
        ranked_b.landed_cost,
        reporting_currency=reporting_currency,
    )
    gap_value = decomposition.headline_gap.value

    programme_figures_a = ranked_a.incentive_figure.inputs if ranked_a.incentive_figure else ()
    programme_figures_b = ranked_b.incentive_figure.inputs if ranked_b.incentive_figure else ()
    signature_a = _regime_signature(spec, localized_a, programme_figures_a)
    signature_b = _regime_signature(spec, localized_b, programme_figures_b)

    return gap_value, signature_a, signature_b


def sensitivity_rows(
    spec: ProductionSpec,
    city_a_id: str,
    city_b_id: str,
    *,
    reporting_currency: str,
) -> tuple[SensitivityRow, ...]:
    """OUT-03 — every active declared row in `data/sensitivity_steps.yaml`,
    perturbed one at a time through a real re-run of the whole pipeline
    (D-67), sorted by absolute `delta` descending.

    `city_a_id`/`city_b_id` are cost-profile city ids (`RankedCity.city_id`
    / `LandedCost`'s own city identity — `CityCostProfile.city_id`) — the
    same ids `engine.gap.decompose_gap`'s own `city_a_id`/`city_b_id`
    parameters take, resolved to a committed `CityCostProfile` at
    `engine.cost_profile.COST_PROFILES_DIR / f"{city_id}.yaml"`.
    """
    profile_a = load_cost_profile(COST_PROFILES_DIR / f"{city_a_id}.yaml")
    profile_b = load_cost_profile(COST_PROFILES_DIR / f"{city_b_id}.yaml")
    ruleset_by_jurisdiction = _load_jurisdiction_rulesets(profile_a, profile_b)

    baseline_gap, baseline_signature_a, baseline_signature_b = _price_pair(
        spec, profile_a, profile_b, ruleset_by_jurisdiction, reporting_currency=reporting_currency
    )

    rows: list[SensitivityRow] = []
    for step in load_sensitivity_steps():
        if step.status != "active":
            continue

        try:
            perturbed_spec, application_note = _apply_step(spec, step)
        except StepNotApplicable as exc:
            rows.append(
                SensitivityRow(
                    step_id=step.id,
                    spec_field=step.spec_field,
                    step_text=f"+{step.step} {step.unit_label} (not applicable to this spec)",
                    baseline_gap=baseline_gap,
                    perturbed_gap=baseline_gap,
                    delta=Decimal("0"),
                    direction="unchanged",
                    cliff_crossings=(),
                    note=f"this step cannot be applied to this production spec: {exc}",
                )
            )
            continue

        perturbed_gap, perturbed_signature_a, perturbed_signature_b = _price_pair(
            perturbed_spec,
            profile_a,
            profile_b,
            ruleset_by_jurisdiction,
            reporting_currency=reporting_currency,
        )
        delta = quantize_money(perturbed_gap - baseline_gap)

        if delta > 0:
            direction: Literal["widened", "narrowed", "unchanged"] = "widened"
        elif delta < 0:
            direction = "narrowed"
        else:
            direction = "unchanged"

        cliff_crossings = (
            *_diff_regime_signatures(baseline_signature_a, perturbed_signature_a, city_id=city_a_id),
            *_diff_regime_signatures(baseline_signature_b, perturbed_signature_b, city_id=city_b_id),
        )

        note = None
        if delta == Decimal("0"):
            note = (
                f"{step.spec_field!r} does not enter any priced line for either city — "
                "this step moves the production spec but the gap is unchanged"
            )

        rows.append(
            SensitivityRow(
                step_id=step.id,
                spec_field=step.spec_field,
                step_text=_step_text(step, application_note),
                baseline_gap=baseline_gap,
                perturbed_gap=perturbed_gap,
                delta=delta,
                direction=direction,
                cliff_crossings=cliff_crossings,
                note=note,
            )
        )

    return tuple(sorted(rows, key=lambda row: abs(row.delta), reverse=True))


def most_moving_row(rows: tuple[SensitivityRow, ...]) -> SensitivityRow:
    """The row with the greatest absolute `delta` — a purely descriptive
    fact (no verb, no "you should", D-70). `rows` is expected to already
    be sorted by `sensitivity_rows` (absolute delta descending); this
    function does not re-sort, it only asserts there is a row to return."""
    if not rows:
        raise ValueError("most_moving_row() received no rows to compare")
    return rows[0]
