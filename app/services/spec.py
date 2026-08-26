"""Route A business logic: budget refusal (D-35's two layers), spec
validation, per-city curated status (D-40), New York's cited rule terms
(D-37 item 3), and — from Phase 4 — a real, cited, basis-tagged dollar
landed cost per candidate city (D-71).

D-71 (Phase 4) deliberately REVERSES the boundary this module used to
enforce: Route A now DOES reach `engine.pipeline` / `engine.qualifying_base`
for every candidate city that resolves to a committed cost profile. The
figure it derives is a MODELLED qualified spend, built from the visitor's
own described production via the canonical budget — never a disclosed
government figure (that's Route B's job, `app/services/validate.py`,
untouched by this phase). `tests/test_route_a_basis_walk.py`'s D-63 gate
is what keeps this honest: it walks the whole recursive `Figure` tree this
module returns and fails if any node claims `confidence: "validated"`.

Every filesystem path is anchored to `REPO_ROOT`, matching
`app/services/validate.py`'s established convention — `deploy/prodfin.
service` sets `WorkingDirectory=/opt/prodfin` on the host, and pytest runs
from the repo root; only a module-anchored path is correct in both.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.services._paths import REPO_ROOT, RULESET_PATH_BY_JURISDICTION
from app.services.city_lookup import resolve_city_to_jurisdiction
from engine.budget import build_canonical_budget
from engine.city_profile_lookup import resolve_city_to_profile_stem
from engine.cost_localizer import localize, quarter_start_date
from engine.cost_profile import COST_PROFILES_DIR, load_cost_profile
from engine.figure import Figure
from engine.landed_cost import aggregate
from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction
from engine.spec import CrewHeadcount, CrewTier, ProductionSpec, resolve_crew_tier

__all__ = [
    "REFUSAL_REASON",
    "REPO_ROOT",
    "RULESET_PATH_BY_JURISDICTION",
    "SPEND_ORIGIN_STATEMENT",
    "CityAssessment",
    "CityCost",
    "RefusalResult",
    "RuleTerm",
    "SpecFormSubmission",
    "SpecResult",
    "handle_spec_submission",
]

# D-35's visible half — the exact sentence a visitor reads after typing a
# number into the "Total budget" field.
REFUSAL_REASON = (
    "cost is only ever an output; a fixed dollar amount buys a different "
    "production in each city, which makes the comparison circular"
)

# D-73/D-32: the one sentence that keeps Route A and Route B visibly
# distinct now that both return a credit figure. Rendered adjacent to the
# number, not in a footer — see app/templates/spec_result.html.
SPEND_ORIGIN_STATEMENT = (
    "This qualified spend is MODELLED from the production you described — "
    "it is not a figure any government has disclosed."
)

_RULE_TERM_BASIS = "quoted verbatim from the curated rule file; not a computed figure"


class SpecFormSubmission(BaseModel):
    """The raw incoming submission shape. Carries every INP-01..INP-07
    field plus one deliberately NAMED `total_budget` field — the two-layer
    enforcement of D-35 in one class: a posted field this schema does not
    name is a 422 from `extra="forbid"` itself, while the one field the
    form actually shows is named so it can be caught and answered with the
    real reason (Pitfall 2)."""

    model_config = ConfigDict(extra="forbid")

    production_type: Literal["feature", "limited_series", "episodic"]
    shoot_days_stage: int
    shoot_days_location: int
    crew_size: int | None = None
    crew_tier: CrewTier | None = None
    principal_cast_count: int
    principal_cast_imported_count: int
    crew_imported_count: int
    crew_hired_locally_count: int
    start_quarter: Literal["Q1", "Q2", "Q3", "Q4"]
    start_year: int
    candidate_cities: list[str]
    total_budget: str | None = None


@dataclass(frozen=True)
class RefusalResult:
    reason: str
    refused_field: str


@dataclass(frozen=True)
class CityAssessment:
    name: str
    jurisdiction_id: str | None
    status: str


@dataclass(frozen=True)
class RuleTerm:
    label: str
    value_text: str
    basis: str
    source_url: str | None
    source_title: str | None
    date_checked: date | None
    confidence: str | None


@dataclass(frozen=True)
class CityCost:
    """One candidate city's real, cited, basis-tagged landed cost (D-71).
    `incentive_state` is `"modelled"` only when a committed cost profile's
    `jurisdiction_id` also has a committed rule file — never a suggestion,
    never a fabricated $0 (D-56)."""

    city_id: str
    cost_total: Figure
    total_landed_cost: Figure
    not_priced: tuple[str, ...]
    permanent_exclusions: tuple[str, ...]
    incentive_state: Literal["modelled", "not_modelled"]
    incentive_state_reason: str


@dataclass(frozen=True)
class SpecResult:
    spec: ProductionSpec
    crew_headcount: CrewHeadcount
    city_assessments: tuple[CityAssessment, ...]
    rule_terms: tuple[RuleTerm, ...]
    city_costs: tuple[CityCost, ...]
    spend_origin: str


def handle_spec_submission(raw: SpecFormSubmission) -> SpecResult | RefusalResult:
    """D-35/D-37/D-40/D-71 in one ordered sequence:

    1. Budget refusal check — BEFORE any `ProductionSpec` is constructed,
       so the refusal is what the visitor sees rather than a schema error
       about an unrelated field.
    2. Validate into `ProductionSpec`.
    3. Resolve the crew headcount (explicit size, or a tier resolved to a
       range carrying its modelling-assumption basis — D-39).
    4. Resolve each candidate city to a curated status, never a suggestion.
    5. For any city resolving to `us-ny`, read New York's cited rule terms.
    6. Build the ONE canonical budget for this submission (COST-01 — never
       once per city), and for each candidate city that resolves to a
       committed cost profile, localize it and aggregate a landed cost —
       pricing the incentive too when a rule file is also committed for
       that profile's jurisdiction (D-71).
    7. Return the echoed spec, the resolved crew headcount, the per-city
       assessments, the rule terms, the per-city costs, and the D-73
       spend-origin statement.
    """
    if raw.total_budget not in (None, ""):
        return RefusalResult(reason=REFUSAL_REASON, refused_field="total_budget")

    spec = ProductionSpec.model_validate(raw.model_dump(exclude={"total_budget"}))

    if spec.crew_size is not None:
        crew_headcount = CrewHeadcount(
            low=spec.crew_size,
            high=spec.crew_size,
            basis="supplied by the visitor",
            provenance_note="an explicit headcount was supplied, not resolved from a tier",
        )
    else:
        crew_headcount = resolve_crew_tier(spec.crew_tier)

    city_assessments: list[CityAssessment] = []
    resolved_jurisdictions: set[str] = set()
    for raw_name in spec.candidate_cities:
        jurisdiction_id = resolve_city_to_jurisdiction(raw_name)
        if jurisdiction_id is not None:
            status = "curated validated model"
            resolved_jurisdictions.add(jurisdiction_id)
        else:
            status = "no curated model"
        city_assessments.append(
            CityAssessment(name=raw_name, jurisdiction_id=jurisdiction_id, status=status)
        )

    rule_terms: tuple[RuleTerm, ...] = ()
    if "us-ny" in resolved_jurisdictions:
        rule_terms = tuple(_new_york_rule_terms())

    city_costs = _price_candidate_cities(spec, crew_headcount)

    return SpecResult(
        spec=spec,
        crew_headcount=crew_headcount,
        city_assessments=tuple(city_assessments),
        rule_terms=rule_terms,
        city_costs=city_costs,
        spend_origin=SPEND_ORIGIN_STATEMENT,
    )


def _price_candidate_cities(
    spec: ProductionSpec, crew_headcount: CrewHeadcount
) -> tuple[CityCost, ...]:
    """D-71/COST-01: build the ONE canonical budget for this submission
    (lazily, and only once — never rebuilt per city), then localize it
    against every candidate city that resolves to a committed cost
    profile. A city with no committed cost profile keeps its Phase 3
    behaviour and produces no `CityCost` entry at all."""
    budget = None
    city_costs: list[CityCost] = []
    seen_profile_stems: set[str] = set()

    for raw_name in spec.candidate_cities:
        profile_stem = resolve_city_to_profile_stem(raw_name)
        if profile_stem is None or profile_stem in seen_profile_stems:
            continue
        seen_profile_stems.add(profile_stem)

        profile_path = COST_PROFILES_DIR / f"{profile_stem}.yaml"
        profile = load_cost_profile(profile_path)

        if budget is None:
            # Built exactly once for the whole submission — COST-01 made
            # structural, never rebuilt for the next candidate city.
            budget = build_canonical_budget(spec, crew_headcount)

        on_date = quarter_start_date(spec.start_quarter, spec.start_year)
        localized = localize(budget, profile, on_date=on_date)

        net_cash_figure: Figure | None = None
        if profile.jurisdiction_id is not None and (
            profile.jurisdiction_id in RULESET_PATH_BY_JURISDICTION
        ):
            ruleset = load_ruleset(RULESET_PATH_BY_JURISDICTION[profile.jurisdiction_id])
            priced = price_jurisdiction(
                ruleset,
                localized.spend_breakdown.total_spend,
                spend_breakdown=localized.spend_breakdown,
                # D-71/D-63: this qualified spend is MODELLED from the
                # visitor's described production, never reproduced against
                # a government disclosure — it must never be able to reach
                # "validated", however curated the jurisdiction's own
                # status is. See engine/pipeline.py::price_programme.
                spend_confidence="researched",
            )
            net_cash_figure = priced.total_net_cash
            incentive_state: Literal["modelled", "not_modelled"] = "modelled"
            incentive_reason = (
                "this incentive figure is MODELLED from the described production's "
                "localized spend, not a disclosed government figure"
            )
        else:
            incentive_state = "not_modelled"
            incentive_reason = (
                "no curated rule file is committed for this city's jurisdiction yet"
            )

        landed = aggregate(localized, net_cash_figure)

        city_costs.append(
            CityCost(
                city_id=profile.city_id,
                cost_total=landed.cost_total,
                total_landed_cost=landed.total_landed_cost,
                not_priced=landed.not_priced,
                permanent_exclusions=landed.permanent_exclusions,
                incentive_state=incentive_state,
                incentive_state_reason=incentive_reason,
            )
        )

    return tuple(city_costs)


def _new_york_rule_terms() -> list[RuleTerm]:
    """D-37 item 3: the rate, mechanism, minimum spend, per-project and
    annual cap status, audit-fee treatment and estimated payout lag — each
    carrying its own source URL, `date_checked` and confidence tier read
    straight off `jurisdictions/us-ny.yaml`. Where the rule file's value is
    null, the term states that fact in plain words rather than rendering a
    blank."""
    ruleset = load_ruleset(RULESET_PATH_BY_JURISDICTION["us-ny"])
    jurisdiction = ruleset.jurisdiction
    programme = ruleset.programmes[0]

    source = jurisdiction.sources[0]
    source_url = source.url
    source_title = source.title
    date_checked = jurisdiction.effective_dates.source_checked_date
    confidence = source.confidence

    def term(label: str, value_text: str) -> RuleTerm:
        return RuleTerm(
            label=label,
            value_text=value_text,
            basis=_RULE_TERM_BASIS,
            source_url=source_url,
            source_title=source_title,
            date_checked=date_checked,
            confidence=confidence,
        )

    rate_structure = programme.rate_structure
    if rate_structure.base_rate is not None:
        rate_text = f"{rate_structure.base_rate} ({rate_structure.type})"
    else:
        rate_text = f"no flat base rate on file ({rate_structure.type})"

    if programme.minimum_spend is not None:
        minimum_spend_text = f"{programme.minimum_spend.value} {programme.minimum_spend.currency}"
    else:
        minimum_spend_text = "no minimum spend on file"

    per_project_cap = programme.caps.per_project_cap
    if per_project_cap is not None:
        per_project_text = f"{per_project_cap.value} {per_project_cap.currency}"
    else:
        per_project_text = "no per-project cap on file"

    annual_cap = programme.caps.annual_programme_cap
    if annual_cap is not None and annual_cap.amount is not None:
        annual_text = f"{annual_cap.amount.value} {annual_cap.amount.currency} per {annual_cap.period}"
    else:
        annual_text = "no annual programme cap on file"

    if programme.audit.mandatory and not programme.audit.fee_schedule:
        audit_text = "audit is mandatory; no fee schedule on file"
    elif programme.audit.mandatory:
        audit_text = "audit is mandatory; fee schedule on file"
    else:
        audit_text = "audit is not mandatory"

    payout_lag = programme.timing.payout_lag
    if payout_lag.typical_days is not None:
        payout_text = f"{payout_lag.typical_days} days"
    else:
        payout_text = payout_lag.description

    return [
        term("Credit rate", rate_text),
        term("Mechanism", programme.mechanism),
        term("Minimum spend", minimum_spend_text),
        term("Per-project cap", per_project_text),
        term("Annual programme cap", annual_text),
        term("Audit-fee treatment", audit_text),
        term("Estimated payout lag", payout_text),
    ]
