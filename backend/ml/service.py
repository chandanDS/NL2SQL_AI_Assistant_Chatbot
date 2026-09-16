"""Intent routing and RBAC-safe reads over synthetic model-output tables."""

import re
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.ml_leads import CampaignLead, PropensityLead, RiskMismatchLead, RiskReviewLead, UnderwritingLead
from backend.models.organization import OfficeType, OrganizationUnit
from backend.rbac.scope import (
    OrganizationAccessDenied,
    organization_ids_subquery,
    requests_bank_wide_scope,
    resolve_organization_scope,
)
from backend.repositories.users import UserAccessRecord


class LeadIntentError(ValueError):
    pass


SYNTHETIC_PORTFOLIO_RISK_PROBABILITY = {
    "TIER_1": 40,
    "TIER_2": 45,
    "TIER_3": 50,
    "TIER_4": 55,
    "PLTB": 52,
    "SALPL": 48,
}


def risk_segment(risk_probability: int, business_unit: str) -> str:
    """Classify synthetic customer risk against its business-unit portfolio baseline."""
    baseline = SYNTHETIC_PORTFOLIO_RISK_PROBABILITY.get(business_unit)
    if baseline is None or risk_probability <= 80:
        return "Risk Review"
    if risk_probability >= 2 * baseline:
        return "Super Red"
    if risk_probability >= 1.5 * baseline:
        return "Red"
    return "Risk Review"


def risk_review_reason(risk_probability: int, business_unit: str) -> str:
    """Explain the synthetic segment comparison in the review-status column."""
    baseline = SYNTHETIC_PORTFOLIO_RISK_PROBABILITY.get(business_unit)
    if baseline is None:
        return "No synthetic portfolio baseline is configured for this business unit."
    if risk_probability <= 80:
        return f"Risk probability {risk_probability}% does not exceed the 80% threshold."
    segment = risk_segment(risk_probability, business_unit)
    if segment == "Super Red":
        return (f"Risk probability {risk_probability}% exceeds 80% and is at least 2x "
                f"the {business_unit} portfolio baseline ({baseline}%): Super Red.")
    if segment == "Red":
        return (f"Risk probability {risk_probability}% exceeds 80% and is at least 1.5x "
                f"the {business_unit} portfolio baseline ({baseline}%): Red.")
    return (f"Risk probability {risk_probability}% exceeds 80%, but is below 1.5x "
            f"the {business_unit} portfolio baseline ({baseline}%).")


@dataclass(frozen=True)
class LeadIntent:
    use_case: str
    label: str
    model: type
    filters: tuple[tuple[str, str], ...]
    guidance: str


def identify_lead_intent(question: str) -> LeadIntent:
    text = re.sub(r"\s+", " ", question.strip().lower())
    if not text or len(text) > 2000:
        raise LeadIntentError("Ask a lead question of up to 2,000 characters")
    if re.search(r"good.{0,35}(?:tagged|marked|flagged).{0,20}bad|false.?positive|risk.{0,15}mismatch", text):
        return LeadIntent("risk_mismatch", "Good customers flagged by risk", RiskMismatchLead,
                          (("risk_team_tag", "BAD"), ("model_risk_band", "LOW")),
                          "Model/tag disagreement only. Obtain risk-team clearance before any offer or disbursal.")
    if re.search(r"risky|high.?risk|avoid.{0,30}(?:loan|disburs|customer)|risk scorecard", text):
        return LeadIntent("risk_review", "High-risk customers", RiskReviewLead,
                          (("risk_band", "HIGH"),),
                          "Risk segments use illustrative portfolio risk-probability baselines by business unit "
                          "(Tier 1: 40%, Tier 2: 45%, Tier 3: 50%, Tier 4: 55%, PLTB: 52%, SALPL: 48%). "
                          "For customer risk probability above 80%, at least 2x baseline is Super Red; "
                          "at least 1.5x baseline is Red. Follow the bank's credit policy and risk-team decision.")
    if re.search(r"pre.?approved|underwrit|eligib", text):
        return LeadIntent("underwriting", "Pre-approved personal-loan candidates", UnderwritingLead,
                          (("eligibility_status", "PRE_APPROVED"),),
                          "Synthetic model output; final offer and disbursal require current policy checks and human approval.")
    if re.search(r"propensity|likely to (?:take|buy)|conversion score", text):
        band = None
        if re.search(r"\bvery[\s-]+high\b", text):
            band = "VERY_HIGH"
        elif re.search(r"\bhigh\b", text):
            band = "HIGH"
        elif re.search(r"\bmedium\b", text):
            band = "MEDIUM"
        elif re.search(r"\blow\b", text):
            band = "LOW"
        label = f"{band.replace('_', ' ').title()}-propensity personal-loan candidates" if band else "Personal-loan propensity candidates across all bands"
        return LeadIntent("propensity", label, PropensityLead,
                          (("propensity_band", band),) if band else (),
                          "Propensity, contact preferences, Account Aggregator and bureau fields are synthetic; verify consent and credit policy before use. This is not a credit approval.")
    if re.search(r"hot lead|campaign|personal loan lead|pl lead", text):
        return LeadIntent("campaign", "Hot personal-loan campaign leads", CampaignLead,
                          (("lead_status", "HOT"),),
                          "Campaign leads are outreach candidates, not approved loans.")
    raise LeadIntentError(
        "I can show hot campaign leads, very-high/high/medium/low PL propensity, pre-approved underwriting candidates, "
        "high-risk customers, or good customers flagged by the risk team."
    )


async def resolve_lead_scope(session: AsyncSession, access: UserAccessRecord, question: str):
    text = question.lower()
    if requests_bank_wide_scope(question) and access.role_code != "HO_USER":
        raise OrganizationAccessDenied
    branches = (await session.scalars(
        select(OrganizationUnit).where(OrganizationUnit.office_type == OfficeType.BRANCH)
    )).all()
    cities = sorted({branch.city for branch in branches if branch.city}, key=len, reverse=True)
    mentioned_city = next((city for city in cities if re.search(rf"\b{re.escape(city.lower())}\b", text)), None)
    requested_id = None
    if mentioned_city:
        city_branches = [branch for branch in branches if branch.city == mentioned_city]
        branch_match = re.search(r"\bbranch\s*(\d{1,2})\b", text)
        if "branches" in text or "all branches" in text:
            requested_id = city_branches[0].parent_id
        elif branch_match:
            number = int(branch_match.group(1))
            matching = next((branch for branch in city_branches if branch.name.endswith(f"Branch {number:02d}")), None)
            if matching is None:
                raise LeadIntentError(f"No Branch {number:02d} exists in {mentioned_city}")
            requested_id = matching.id
        else:
            own = next((branch for branch in city_branches if branch.id == access.organization_unit_id), None)
            requested_id = own.id if own else city_branches[0].id
    return await resolve_organization_scope(session, access, requested_id)


def _serialize(record, branch_name: str) -> dict:
    values = {
        "customer_ref": record.customer_ref,
        "customer_name": record.customer_name,
        "branch": branch_name,
        "as_of_date": record.as_of_date.isoformat(),
        "business_unit": record.business_unit,
        "interest_rate_pct": float(record.interest_rate_pct),
    }
    for key in (
        "campaign_name", "lead_status", "propensity_score", "propensity_band",
        "suggested_amount", "eligibility_status", "underwriting_score",
        "recommended_limit", "model_version", "risk_score", "risk_band",
        "portfolio_segment_risk_probability", "risk_segment", "review_status", "model_risk_score", "model_risk_band",
        "preferred_contact_time", "preferred_contact_channel", "aa_last_6m_avg_balance",
        "aa_last_6m_debit_amount", "aa_last_6m_credit_amount", "bureau_enquiries_6m",
        "bureau_active_external_loans", "bureau_current_exposure", "bureau_bounces_6m",
        "bureau_max_dpd_6m", "bureau_cibil_score", "offer_amount", "aa_based_offer_amount",
    ):
        if hasattr(record, key):
            value = getattr(record, key)
            display_key = key.upper() if key.startswith("aa_") else key
            values[display_key] = float(value) if key in (
                "suggested_amount", "recommended_limit", "aa_last_6m_avg_balance",
                "aa_last_6m_debit_amount", "aa_last_6m_credit_amount", "bureau_current_exposure",
                "offer_amount", "aa_based_offer_amount",
            ) else value
    return values


async def query_leads(
    session: AsyncSession, access: UserAccessRecord, question: str, *,
    limit: int = 100, offset: int = 0, export: bool = False,
) -> dict:
    intent = identify_lead_intent(question)
    scope = await resolve_lead_scope(session, access, question)
    model = intent.model
    scope_condition = model.organization_unit_id.in_(organization_ids_subquery(scope.effective_root_id))
    condition = scope_condition
    for column_name, value in intent.filters:
        condition = condition & (getattr(model, column_name) == value)
    total = int(await session.scalar(select(func.count()).select_from(model).where(condition)) or 0)
    band_counts = {}
    if intent.use_case == "propensity" and not intent.filters:
        rows = (await session.execute(
            select(model.propensity_band, func.count()).where(scope_condition).group_by(model.propensity_band)
        )).all()
        observed = {band: int(count) for band, count in rows}
        band_counts = {band: observed.get(band, 0) for band in ("VERY_HIGH", "HIGH", "MEDIUM", "LOW")}
    if export and total > 50_000:
        raise LeadIntentError("Export is limited to 50,000 records; narrow the organization scope")
    statement = select(model).where(condition).order_by(model.organization_unit_id, model.customer_ref)
    if not export:
        statement = statement.limit(limit).offset(offset)
    records = (await session.scalars(statement)).all()
    branch_names = {org.id: org.name for org in scope.organizations}
    selected_name = scope.organizations[0].name if scope.organizations else "Assigned scope"
    return {
        "use_case": intent.use_case,
        "title": intent.label,
        "source_table": model.__tablename__,
        "organization": selected_name,
        "organization_id": scope.effective_root_id,
        "total_count": total,
        "band_counts": band_counts,
        "limit": limit,
        "offset": offset,
        "records": [_serialize(row, branch_names.get(row.organization_unit_id, "Unknown branch")) for row in records],
        "guidance": f"{intent.guidance} Interest rates and offer amounts are illustrative demo estimates, not loan offers.",
        "synthetic": True,
    }
