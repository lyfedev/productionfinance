"""Route A business logic: budget refusal (D-35's two layers), spec
validation, per-city curated status (D-40), New York's cited rule terms
(D-37 item 3), and the explicit not-yet-derived statement (D-36).

This module must never import `engine.pipeline` or
`engine.qualifying_base`, and must never call `price_jurisdiction` or
`compute_qualifying_base` directly or through a module alias — Route A
returns no dollar figure derived from the visitor's spec (D-36). It only
ever reads the New York rule file's TERMS via `engine.models.load_ruleset`,
never prices anything through it.

Every filesystem path is anchored to `REPO_ROOT`, matching
`app/services/validate.py`'s established convention — `deploy/prodfin.
service` sets `WorkingDirectory=/opt/prodfin` on the host, and pytest runs
from the repo root; only a module-anchored path is correct in both.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.services.city_lookup import resolve_city_to_jurisdiction
from engine.models import load_ruleset
from engine.spec import CrewHeadcount, CrewTier, ProductionSpec, resolve_crew_tier

__all__ = [
    "REFUSAL_REASON",
    "REPO_ROOT",
    "RULESET_PATH_BY_JURISDICTION",
    "SPEND_NOT_DERIVED",
    "CityAssessment",
    "RefusalResult",
    "RuleTerm",
    "SpecFormSubmission",
    "SpecResult",
    "handle_spec_submission",
]

REPO_ROOT = Path(__file__).resolve().parents[2]

# New York only in Phase 3 — matches app/services/validate.py's identical
# jurisdiction scoping.
RULESET_PATH_BY_JURISDICTION: dict[str, Path] = {
    "us-ny": REPO_ROOT / "jurisdictions" / "us-ny.yaml",
}

# D-35's visible half — the exact sentence a visitor reads after typing a
# number into the "Total budget" field.
REFUSAL_REASON = (
    "cost is only ever an output; a fixed dollar amount buys a different "
    "production in each city, which makes the comparison circular"
)

# D-36 — the honest terminal state of Route A. Never replaced by a
# spinner, a progress bar, a delay, or a number with an asterisk.
SPEND_NOT_DERIVED = (
    "Qualified spend is not derived from a described production in this phase. "
    "Cost localization against each city's real local costs is Phase 4's goal. "
    "This system reports that as a stated boundary, not an estimated placeholder."
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
class SpecResult:
    spec: ProductionSpec
    crew_headcount: CrewHeadcount
    city_assessments: tuple[CityAssessment, ...]
    rule_terms: tuple[RuleTerm, ...]
    spend_not_derived: str


def handle_spec_submission(raw: SpecFormSubmission) -> SpecResult | RefusalResult:
    """D-35/D-36/D-37/D-40 in one ordered sequence:

    1. Budget refusal check — BEFORE any `ProductionSpec` is constructed,
       so the refusal is what the visitor sees rather than a schema error
       about an unrelated field.
    2. Validate into `ProductionSpec`.
    3. Resolve the crew headcount (explicit size, or a tier resolved to a
       range carrying its modelling-assumption basis — D-39).
    4. Resolve each candidate city to a curated status, never a suggestion.
    5. For any city resolving to `us-ny`, read New York's cited rule terms.
    6. Return the echoed spec, the resolved crew headcount, the per-city
       assessments, the rule terms, and the not-yet-derived statement.
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

    return SpecResult(
        spec=spec,
        crew_headcount=crew_headcount,
        city_assessments=tuple(city_assessments),
        rule_terms=rule_terms,
        spend_not_derived=SPEND_NOT_DERIVED,
    )


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
