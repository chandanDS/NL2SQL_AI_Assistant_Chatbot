"""Idempotent, visibly synthetic personal-loan model outputs for the POC."""

import asyncio
from datetime import date
from decimal import Decimal

from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from backend.db.session import get_session_factory
from backend.models.ml_leads import CampaignLead, PropensityLead, RiskMismatchLead, RiskReviewLead, UnderwritingLead
from backend.models.organization import OfficeType, OrganizationUnit


AS_OF_DATE = date(2026, 9, 1)
BATCH_SIZE = 1000
METRO_CITIES = frozenset({
    "Mumbai", "New Delhi", "Bengaluru", "Chennai", "Hyderabad",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur",
})
TIER_2_CITIES = frozenset({
    "Chandigarh", "Kochi", "Bhubaneswar", "Patna", "Bhopal", "Indore",
    "Nagpur", "Lucknow", "Kanpur", "Jodhpur", "Guwahati",
})
TIER_3_CITIES = frozenset({
    "Dehradun", "Panaji", "Ranchi", "Raipur", "Varanasi", "Prayagraj",
    "Udaipur", "Kota",
})
RATE_BY_UNIT = {
    "TIER_1": Decimal("10.75"), "TIER_2": Decimal("11.25"),
    "TIER_3": Decimal("12.00"), "TIER_4": Decimal("12.75"),
    "PLTB": Decimal("11.50"), "SALPL": Decimal("10.50"),
}


def calculate_aa_based_offer(offer_amount: int, credits_6m: int, debits_6m: int) -> int:
    """Demo-only uplift when six-month credits exceed debits; never a credit decision."""
    positive_net_inflow = max(credits_6m - debits_6m, 0)
    return offer_amount + min(2 * positive_net_inflow, 200_000)


def propensity_band(score: int) -> str:
    """Exclusive bands: >90 very high, 75-90 high, 60-74 medium, <60 low."""
    if not 0 <= score <= 100:
        raise ValueError("Propensity score must be between 0 and 100")
    if score > 90:
        return "VERY_HIGH"
    if score >= 75:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    return "LOW"


def _business_unit(branch: OrganizationUnit, number: int) -> str:
    # Demo-only segmentation: PLTB and SALPL supersede geographic city tiers.
    if number % 13 == 0:
        return "SALPL"
    if number % 11 == 0:
        return "PLTB"
    if branch.city in METRO_CITIES:
        return "TIER_1"
    if branch.city in TIER_2_CITIES:
        return "TIER_2"
    if branch.city in TIER_3_CITIES:
        return "TIER_3"
    return "TIER_4"


def _customer_number(branch: OrganizationUnit, number: int) -> int:
    branch_number = int(branch.code.removeprefix("BR"))
    offset = (branch_number - 1) * 12 if branch_number <= 33 else 12_384 + (branch_number - 34) * 12
    return offset + number


def _identity(branch: OrganizationUnit, number: int, names: dict[int, str], fake: Faker) -> dict:
    customer_number = _customer_number(branch, number)
    if customer_number not in names:
        names[customer_number] = fake.name()
    business_unit = _business_unit(branch, number)
    return {
        "organization_unit_id": branch.id,
        "customer_ref": f"CUST{customer_number:09d}",
        "customer_name": names[customer_number],
        "as_of_date": AS_OF_DATE,
        "business_unit": business_unit,
        "interest_rate_pct": RATE_BY_UNIT[business_unit] + Decimal(number % 5) * Decimal("0.25"),
    }


def make_rows(branches: list[OrganizationUnit]) -> dict[type, list[dict]]:
    fake = Faker("en_IN")
    fake.seed_instance(20260916)
    names: dict[int, str] = {}
    output: dict[type, list[dict]] = {model: [] for model in (CampaignLead, PropensityLead, UnderwritingLead, RiskReviewLead, RiskMismatchLead)}
    for branch in branches:
        campaign_count = 12_000 if branch.code == "BR0033" else 8
        for number in range(1, campaign_count + 1):
            hot = branch.code == "BR0033" or number <= 3
            output[CampaignLead].append({
                **_identity(branch, number, names, fake),
                "campaign_name": "PL Growth September 2026",
                "lead_status": "HOT" if hot else "WARM",
                "propensity_score": 82 + number % 18 if hot else 55 + number % 20,
                "propensity_band": propensity_band(82 + number % 18 if hot else 55 + number % 20),
                "suggested_amount": Decimal(100000 + (number % 15) * 25000),
            })
        for number in range(1, 13):
            score = 50 + (number * 4) % 50
            avg_balance = 25_000 + (number % 20) * 12_500
            debit_amount = 120_000 + (number % 30) * 35_000
            credit_amount = 150_000 + (number % 30) * 38_000
            if number % 4 == 0:
                credit_amount = debit_amount - (20_000 + (number % 5) * 5_000)
            dpd = 30 if number % 11 == 0 else 0
            bounces = 1 if number % 7 == 0 or dpd > 0 else 0
            cibil_score = 640 + (number * 17) % 220 - 30 * bool(dpd) - 10 * bounces
            offer_amount = 150_000 + score * 3_000
            aa_offer_amount = calculate_aa_based_offer(offer_amount, credit_amount, debit_amount)
            output[PropensityLead].append({
                **_identity(branch, number, names, fake),
                "propensity_score": score,
                "propensity_band": propensity_band(score),
                "model_version": "pl-propensity-demo-v1",
                "preferred_contact_time": ("09:00-12:00", "12:00-16:00", "16:00-19:00")[number % 3],
                "preferred_contact_channel": ("CALL", "SMS", "EMAIL", "WHATSAPP")[number % 4],
                "aa_last_6m_avg_balance": Decimal(avg_balance),
                "aa_last_6m_debit_amount": Decimal(debit_amount),
                "aa_last_6m_credit_amount": Decimal(credit_amount),
                "bureau_enquiries_6m": number % 6,
                "bureau_active_external_loans": number % 4,
                "bureau_current_exposure": Decimal((number % 4) * 125_000 + (number % 7) * 15_000),
                "bureau_bounces_6m": bounces,
                "bureau_max_dpd_6m": dpd,
                "bureau_cibil_score": cibil_score,
                "offer_amount": Decimal(offer_amount),
                "aa_based_offer_amount": Decimal(aa_offer_amount),
            })
            output[UnderwritingLead].append({
                **_identity(branch, number, names, fake),
                "eligibility_status": "PRE_APPROVED" if number <= 5 else "REVIEW",
                "underwriting_score": 72 + (number * 2) % 28,
                "recommended_limit": Decimal(150000 + number * 30000),
                "model_version": "pl-underwriting-demo-v1",
            })
            output[RiskReviewLead].append({
                **_identity(branch, number, names, fake),
                "risk_score": 70 + number,
                "risk_band": "HIGH",
                "risk_team_tag": "HIGH_RISK",
                "review_status": "AVOID_PENDING_REVIEW",
                "reason_code": "ELEVATED_RISK_SCORE",
            })
            if number <= 3:
                output[RiskMismatchLead].append({
                    **_identity(branch, number, names, fake),
                    "model_risk_score": 18 + number,
                    "model_risk_band": "LOW",
                    "risk_team_tag": "BAD",
                    "review_status": "RISK_REVIEW_REQUIRED",
                    "reason_code": "TAG_MODEL_MISMATCH",
                })
    return output


async def seed() -> None:
    factory = get_session_factory()
    async with factory() as session:
        branches = (await session.scalars(
            select(OrganizationUnit)
            .where(OrganizationUnit.office_type == OfficeType.BRANCH)
            .order_by(OrganizationUnit.code)
        )).all()
        if not branches or not any(branch.code == "BR0033" and branch.name == "Mumbai Branch 01" for branch in branches):
            raise RuntimeError("Seed the organization hierarchy before AI/ML outputs")
        rows_by_model = make_rows(branches)
        for model, rows in rows_by_model.items():
            for start in range(0, len(rows), BATCH_SIZE):
                batch = rows[start:start + BATCH_SIZE]
                statement = insert(model).values(batch)
                updates = {key: getattr(statement.excluded, key) for key in batch[0] if key not in ("customer_ref", "as_of_date")}
                await session.execute(statement.on_conflict_do_update(
                    index_elements=["customer_ref", "as_of_date"], set_=updates,
                ))
                await session.commit()
            count = await session.scalar(select(func.count()).select_from(model))
            print(f"{model.__tablename__}: {count:,} rows")


if __name__ == "__main__":
    asyncio.run(seed())
