"""The complete ``JurisdictionRuleSet`` Pydantic v2 schema.

Implements every field in ``.planning/research/ARCHITECTURE.md`` Q2's
concrete field list, including where New York (this plan's only curated
jurisdiction) does not exercise a given field — the four wave-2 plans extend
*behaviour* against this schema without needing to touch it.

**RD-01 (deliberate, recorded deviation from ARCHITECTURE.md Q2's literal
schema listing):** every money, rate, percentage and threshold field here is
typed ``Decimal``, never ``float``. ARCHITECTURE.md Q2 types several such
fields ``float`` as shorthand for "this is a fractional number" — verified by
execution (``02-RESEARCH.md`` Finding 1, against this repo's locked
``pydantic==2.13.4``) that an unquoted YAML value like ``0.263`` parses as a
native Python ``float``, and naive ``Decimal(x)`` conversion of that float
corrupts it past the fifteenth significant digit. Every such value in every
committed rule file is therefore written as a quoted YAML string, and every
matching Pydantic field is ``Decimal`` — Pydantic v2's ``Decimal`` validator
safely converts the value via its string representation even when the raw
input is a bare float.

**RD-02 (two confidence vocabularies, never conflated):**
``Source.confidence`` here uses the four-tier *source-document-reliability*
vocabulary already established in ``tests/test_source_truth.py``
(``LEGAL_CONFIDENCE_TIERS = {"LOW", "MEDIUM", "MEDIUM-HIGH", "HIGH"}``). This
is a different axis from ``engine.figure.Figure.confidence`` (closed to
exactly ``{"validated", "researched"}``, measuring whether a *computed
figure* has been checked against a real government disclosure) — the two
scales are never unified.

**RD-05 (five extensions to ARCHITECTURE.md Q2's schema):**
1. Decimal-typing + quoted-string YAML convention (RD-01, above).
2. ``Jurisdiction.status`` gains a fourth literal, ``synthetic_fixture``, so
   the real-vs-test-fixture split is schema-enforced, not a directory
   convention a reader has to notice.
3. ``Programme.corporation_tax_rate: Decimal | None``, required when
   ``taxable`` is true (INC-07 needs a rate; Q2 only supplies the boolean).
4. ``RateStructure.source_note: str | None``, mirroring
   ``TransferDiscount.source_note``, for a rate schedule derived empirically
   from a government dataset.
5. ``Validation.validation_pair_fixture_glob: str | None`` replaces Q2's
   inline ``validation_pairs`` list — Phase 1's already-committed fixtures
   under ``tests/fixtures/validation_pairs/`` stay the single source of
   truth instead of being duplicated into the rule file where the two
   copies could diverge.

Every classification field (``mechanism``, ``base_definition.type``,
``rate_structure.type``, ``jurisdiction.status``, and the other closed
enums below) is a ``Literal`` type, and every model forbids extra fields
(``model_config = ConfigDict(extra="forbid")``) — an unrecognised value or an
unexpected key raises ``pydantic.ValidationError`` on load rather than
silently defaulting or being ignored (T-02-02).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

__all__ = [
    "AnnualProgrammeCap",
    "Audit",
    "AuditFeeTier",
    "BaseDefinition",
    "CapConsumptionCheck",
    "Caps",
    "CeilingSplit",
    "EffectiveDates",
    "EscalatorStep",
    "HeadcountScaleStep",
    "Jurisdiction",
    "JurisdictionRuleSet",
    "Money",
    "PayoutLag",
    "PerPersonCeiling",
    "PerPersonCeilingTier",
    "Programme",
    "RateStructure",
    "ResidencyRules",
    "Source",
    "Tier",
    "Timing",
    "TransferDiscount",
    "Uplift",
    "Validation",
    "load_ruleset",
]


class StrictModel(BaseModel):
    """Base for every schema model: forbids unrecognised fields (T-02-02)."""

    model_config = ConfigDict(extra="forbid")


class Money(StrictModel):
    value: Decimal
    currency: str


class Source(StrictModel):
    url: str
    title: str
    accessed_date: date
    # RD-02: the four-tier *source-document-reliability* vocabulary already
    # established by tests/test_source_truth.py's LEGAL_CONFIDENCE_TIERS —
    # not to be confused with engine.figure.Figure.confidence's closed
    # two-value {"validated", "researched"} scale (a different axis).
    confidence: Literal["HIGH", "MEDIUM", "MEDIUM-HIGH", "LOW"]


class EffectiveDates(StrictModel):
    rule_version_effective_from: date
    rule_version_effective_to: date | None = None
    source_checked_date: date


class Jurisdiction(StrictModel):
    id: str
    name: str
    country_code: str
    level: Literal["national", "state", "provincial", "city"]
    parent_id: str | None = None
    currency: str
    # RD-05 extension #2: synthetic_fixture is new relative to Q2's
    # three-value listing — makes the curated-vs-test-fixture split
    # machine-checkable.
    status: Literal[
        "curated_validated",
        "live_researched",
        "no_programme_found",
        "synthetic_fixture",
    ]
    effective_dates: EffectiveDates
    sources: list[Source]


class BaseDefinition(StrictModel):
    type: Literal[
        "total_qualified_spend",
        "labour_only",
        "lesser_of_pct_core_or_actual_local",
        "local_hires_only",
        "custom",
    ]
    pct_core_cap: Decimal | None = None
    excluded_line_items: list[str] = []
    custom_handler_id: str | None = None


class PerPersonCeilingTier(StrictModel):
    """One band of a loan-out-withholding schedule, keyed by effective date.

    SCOPE-FREEZE item 2: a per-person ceiling's loan-out withholding rate is
    modelled as a *schedule*, not a scalar — Georgia's confirmed five-tier
    declining schedule (SOURCE-TRUTH.md SRC-05) is the concrete proof this
    must be a lookup-by-effective-date table.
    """

    effective_from: date
    effective_to: date | None = None
    loanout_withholding_rate: Decimal


class PerPersonCeiling(StrictModel):
    applies: bool
    note: str | None = None
    w2_cap_amount: Money | None = None
    loanout_exempt: bool | None = None
    # Scalar fallback for a jurisdiction with a single confirmed rate and no
    # published schedule; loanout_withholding_schedule (RD-05-adjacent
    # extension) is the multi-tier lookup table a schedule-bearing
    # jurisdiction (e.g. Georgia, plan 02-05) populates instead.
    loanout_withholding_rate: Decimal | None = None
    loanout_withholding_confirmed: bool | None = None
    loanout_withholding_schedule: list[PerPersonCeilingTier] = []


class Tier(StrictModel):
    threshold_low: Decimal
    threshold_high: Decimal | None = None
    rate: Decimal


class Uplift(StrictModel):
    id: str
    name: str
    additional_rate: Decimal
    stackable: bool
    conditions: str | None = None
    requires_separate_application: bool = False


class CeilingSplit(StrictModel):
    enhanced_threshold: Money | None = None
    enhanced_rate: Decimal | None = None
    standard_rate: Decimal | None = None


class HeadcountScaleStep(StrictModel):
    budget_threshold: Decimal
    max_headcount: int


class RateStructure(StrictModel):
    type: Literal[
        "flat",
        "tiered_by_spend",
        "blended_by_ceiling_split",
        "headcount_scaled",
    ]
    base_rate: Decimal | None = None
    tiers: list[Tier] = []
    uplifts: list[Uplift] = []
    ceiling_split: CeilingSplit | None = None
    headcount_scale: list[HeadcountScaleStep] | None = None
    # RD-05 extension #4, mirroring TransferDiscount.source_note.
    source_note: str | None = None


class EscalatorStep(StrictModel):
    period_label: str
    amount: Decimal


class AnnualProgrammeCap(StrictModel):
    amount: Money | None = None
    period: Literal["calendar_year", "fiscal_year"] | None = None
    escalator_schedule: list[EscalatorStep] | None = None


class CapConsumptionCheck(StrictModel):
    method: Literal["live_research", "official_dashboard", "manual", "not_applicable"]
    source_url: str | None = None


class Caps(StrictModel):
    per_project_cap: Money | None = None
    annual_programme_cap: AnnualProgrammeCap | None = None
    cap_consumption_check: CapConsumptionCheck | None = None


class AuditFeeTier(StrictModel):
    spend_threshold_low: Decimal
    spend_threshold_high: Decimal | None = None
    fee_primary: Decimal
    fee_third_party_auditor: Decimal | None = None


class Audit(StrictModel):
    mandatory: bool
    fee_schedule: list[AuditFeeTier] = []


class PayoutLag(StrictModel):
    description: str
    typical_days: int | None = None
    interest_paid: bool | None = None


class Timing(StrictModel):
    terms_lock_at: Literal["application", "start_of_principal_photography", "completion"]
    application_window: str | None = None
    decision_sla_days: int | None = None
    payout_lag: PayoutLag


class TransferDiscount(StrictModel):
    applies: bool
    typical_rate_low: Decimal | None = None
    typical_rate_high: Decimal | None = None
    source_note: str | None = None


class ResidencyRules(StrictModel):
    resident_definition: str | None = None
    nonresident_treatment: str | None = None
    custom_handler_id: str | None = None


class Validation(StrictModel):
    validated: bool
    # RD-05 extension #5: replaces Q2's inline validation_pairs list. Phase
    # 1's committed tests/fixtures/validation_pairs/*.yaml stay the single
    # source of truth instead of being duplicated into the rule file.
    validation_pair_fixture_glob: str | None = None
    mean_error_pct: Decimal | None = None
    last_checked_against_disclosure: date | None = None


class Programme(StrictModel):
    id: str
    name: str
    requires_separate_application: bool = False
    stacks_with: list[str] = []
    mutually_exclusive_with: list[str] = []
    mechanism: Literal["refundable", "transferable", "rebate_grant", "nonrefundable_credit"]
    taxable: bool
    # RD-05 extension #3: required when taxable is true (INC-07).
    corporation_tax_rate: Decimal | None = None
    base_definition: BaseDefinition
    per_person_ceiling: PerPersonCeiling
    rate_structure: RateStructure
    minimum_spend: Money | None = None
    caps: Caps
    audit: Audit
    timing: Timing
    transfer_discount: TransferDiscount
    residency_rules: ResidencyRules | None = None
    validation: Validation

    @model_validator(mode="after")
    def _corporation_tax_rate_required_when_taxable(self) -> "Programme":
        if self.taxable and self.corporation_tax_rate is None:
            raise ValueError(
                "corporation_tax_rate is required when taxable is true (RD-05 #3, INC-07)"
            )
        return self


class JurisdictionRuleSet(StrictModel):
    jurisdiction: Jurisdiction
    programmes: list[Programme]

    @model_validator(mode="after")
    def _programme_edges_resolve_to_declared_ids(self) -> JurisdictionRuleSet:
        """WR-01/WR-02 (INC-03): every `stacks_with` and `mutually_exclusive_with`
        entry, on every declared programme, must name a DIFFERENT programme
        that is actually declared in this ruleset — checked here, once, so
        the two edge kinds cannot drift apart (that single-place requirement
        is WR-02's substance, not a style preference).

        Ids are compared with plain Python string equality on exactly the
        values PyYAML returned: no whitespace trimming, no case folding,
        no fuzzy matching. An id differing only by case or surrounding
        whitespace from a declared id is a DIFFERENT id — silently coercing
        it into a match would be the same class of failure as silently
        dropping the programme it was meant to reference (T-02-02).

        A self-reference (a programme naming its own id in either field) and
        a dangling reference (an id no declared programme carries) both
        raise `ValueError`, because an unresolvable edge must never be
        silently dropped from a jurisdiction's summed total — a dropped
        programme is indistinguishable from one that was never modelled.
        """
        declared_ids = {programme.id for programme in self.programmes}
        for programme in self.programmes:
            for field_name in ("stacks_with", "mutually_exclusive_with"):
                for other_id in getattr(programme, field_name):
                    if other_id == programme.id:
                        raise ValueError(
                            f"programme {programme.id!r} declares itself in its own "
                            f"{field_name!r} list — a programme cannot be mutually "
                            "exclusive with, or stack with, itself"
                        )
                    if other_id not in declared_ids:
                        raise ValueError(
                            f"programme {programme.id!r} declares {field_name}="
                            f"{other_id!r}, which is not a declared programme id in "
                            f"this ruleset (declared ids: {sorted(declared_ids)})"
                        )
        return self


def load_ruleset(path: str | Path) -> JurisdictionRuleSet:
    """The single rule-file read path in the codebase.

    Opens ``path``, parses it with PyYAML's *safe* loader only (never
    ``yaml.load``/``yaml.unsafe_load`` — V5 input-validation control, T-02-01)
    and returns a validated ``JurisdictionRuleSet``. An unrecognised
    classification value or an unexpected key raises
    ``pydantic.ValidationError`` rather than silently defaulting.
    """
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return JurisdictionRuleSet.model_validate(raw)
