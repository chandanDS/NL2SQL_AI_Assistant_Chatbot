import asyncio
import math
import random
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, insert, select

from backend.db.session import get_session_factory
from backend.models.banking import (
    AdvanceMonthlyFact,
    AdvanceProduct,
    AssetQualityClass,
    AssetQualityMonthlyFact,
    DepositMonthlyFact,
    DepositProduct,
    DigitalProduct,
    DigitalProductMonthlyFact,
)
from backend.models.organization import OfficeType, OrganizationUnit


START_MONTH = date(2023, 10, 1)
MONTH_COUNT = 36
BRANCH_COUNT = 256
EXPECTED_COUNTS = {
    DepositMonthlyFact: MONTH_COUNT * BRANCH_COUNT * len(DepositProduct),
    AdvanceMonthlyFact: MONTH_COUNT * BRANCH_COUNT * len(AdvanceProduct),
    AssetQualityMonthlyFact: MONTH_COUNT * BRANCH_COUNT * len(AssetQualityClass),
    DigitalProductMonthlyFact: MONTH_COUNT * BRANCH_COUNT * len(DigitalProduct),
}

ADVANCE_BASE = {
    AdvanceProduct.EL: (8_000_000, 80),
    AdvanceProduct.VL: (12_000_000, 110),
    AdvanceProduct.PL: (10_000_000, 160),
    AdvanceProduct.HL: (30_000_000, 95),
    AdvanceProduct.MSME: (45_000_000, 70),
    AdvanceProduct.AGRI: (22_000_000, 130),
}
ASSET_RATES = {
    AssetQualityClass.SMA0: 0.018,
    AssetQualityClass.SMA1: 0.012,
    AssetQualityClass.SMA2: 0.009,
    AssetQualityClass.SUBSTANDARD: 0.010,
    AssetQualityClass.DOUBTFUL: 0.006,
    AssetQualityClass.LOSS: 0.002,
}
DIGITAL_ELIGIBLE_RATIOS = {
    DigitalProduct.MOBILE_BANKING: 0.92,
    DigitalProduct.INTERNET_BANKING: 0.85,
    DigitalProduct.UPI: 0.90,
    DigitalProduct.DEBIT_CARD: 0.88,
    DigitalProduct.POS: 0.25,
    DigitalProduct.QR: 0.35,
    DigitalProduct.AEPS: 0.60,
}
DIGITAL_TRANSACTION_FACTORS = {
    DigitalProduct.MOBILE_BANKING: 8,
    DigitalProduct.INTERNET_BANKING: 4,
    DigitalProduct.UPI: 24,
    DigitalProduct.DEBIT_CARD: 6,
    DigitalProduct.POS: 10,
    DigitalProduct.QR: 14,
    DigitalProduct.AEPS: 3,
}


def add_months(start: date, offset: int) -> date:
    month_index = start.year * 12 + start.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def deposit_rows(
    rng: random.Random,
    period: date,
    month_index: int,
    branch_id: int,
    branch_index: int,
) -> tuple[list[dict], int]:
    rows: list[dict] = []
    total_accounts = 0
    branch_scale = 0.75 + (branch_index % 30) / 50
    seasonal = 1 + 0.015 * math.sin((month_index % 12) * math.pi / 6)

    for product, base_amount, base_accounts in (
        (DepositProduct.CA, 18_000_000, 220),
        (DepositProduct.SA, 42_000_000, 900),
    ):
        actual = base_amount * branch_scale * (1.0065**month_index) * seasonal * rng.uniform(0.96, 1.04)
        accounts = max(1, round(base_accounts * branch_scale * (1.0045**month_index) * rng.uniform(0.97, 1.03)))
        target = actual * rng.uniform(0.96, 1.10)
        target_accounts = max(1, round(accounts * rng.uniform(0.98, 1.08)))
        new_accounts = max(1, round(accounts * rng.uniform(0.008, 0.018)))
        closed_accounts = max(0, round(accounts * rng.uniform(0.002, 0.007)))
        total_accounts += accounts
        rows.append(
            {
                "period_month": period,
                "organization_unit_id": branch_id,
                "product_type": product.value,
                "business_amount": money(actual),
                "target_amount": money(target),
                "account_count": accounts,
                "target_account_count": target_accounts,
                "new_accounts": new_accounts,
                "closed_accounts": closed_accounts,
            }
        )
    return rows, total_accounts


def advance_rows(
    rng: random.Random,
    period: date,
    month_index: int,
    branch_id: int,
    branch_index: int,
) -> tuple[list[dict], Decimal, int]:
    rows: list[dict] = []
    total_outstanding = Decimal("0")
    total_accounts = 0
    branch_scale = 0.72 + (branch_index % 28) / 48
    seasonal = 1 + 0.02 * math.cos((month_index % 12) * math.pi / 6)

    for product, (base_amount, base_accounts) in ADVANCE_BASE.items():
        outstanding = base_amount * branch_scale * (1.007**month_index) * seasonal * rng.uniform(0.95, 1.05)
        accounts = max(1, round(base_accounts * branch_scale * (1.004**month_index) * rng.uniform(0.96, 1.04)))
        target = outstanding * rng.uniform(0.96, 1.11)
        sanctioned = outstanding * rng.uniform(0.035, 0.065)
        disbursed = sanctioned * rng.uniform(0.76, 0.98)
        overdue = outstanding * rng.uniform(0.01, 0.07)
        total_outstanding += money(outstanding)
        total_accounts += accounts
        rows.append(
            {
                "period_month": period,
                "organization_unit_id": branch_id,
                "product_type": product.value,
                "outstanding_amount": money(outstanding),
                "target_amount": money(target),
                "account_count": accounts,
                "target_account_count": max(1, round(accounts * rng.uniform(0.98, 1.09))),
                "sanctioned_amount": money(sanctioned),
                "disbursed_amount": money(disbursed),
                "overdue_amount": money(overdue),
            }
        )
    return rows, total_outstanding, total_accounts


def asset_quality_rows(
    rng: random.Random,
    period: date,
    branch_id: int,
    advance_amount: Decimal,
    advance_accounts: int,
) -> list[dict]:
    rows: list[dict] = []
    for classification, base_rate in ASSET_RATES.items():
        rate = base_rate * rng.uniform(0.82, 1.18)
        outstanding = float(advance_amount) * rate
        accounts = max(1, round(advance_accounts * rate * rng.uniform(0.8, 1.15)))
        recovery = outstanding * rng.uniform(0.025, 0.10)
        rows.append(
            {
                "period_month": period,
                "organization_unit_id": branch_id,
                "classification": classification.value,
                "outstanding_amount": money(outstanding),
                "account_count": accounts,
                "slippage_amount": money(outstanding * rng.uniform(0.01, 0.055)),
                "recovery_amount": money(recovery),
                "target_recovery_amount": money(recovery * rng.uniform(0.9, 1.3)),
            }
        )
    return rows


def digital_rows(
    rng: random.Random,
    period: date,
    month_index: int,
    branch_id: int,
    deposit_accounts: int,
) -> list[dict]:
    rows: list[dict] = []
    adoption_growth = min(0.18, month_index * 0.004)
    for product in DigitalProduct:
        eligible = max(1, round(deposit_accounts * DIGITAL_ELIGIBLE_RATIOS[product]))
        registration_ratio = min(0.92, 0.48 + adoption_growth + rng.uniform(-0.035, 0.035))
        registered = max(1, min(eligible, round(eligible * registration_ratio)))
        active = max(1, min(registered, round(registered * rng.uniform(0.58, 0.86))))
        transactions = max(active, round(active * DIGITAL_TRANSACTION_FACTORS[product] * rng.uniform(0.85, 1.15)))
        average_ticket = rng.uniform(700, 8_000)
        rows.append(
            {
                "period_month": period,
                "organization_unit_id": branch_id,
                "product_type": product.value,
                "eligible_customer_count": eligible,
                "registered_customer_count": registered,
                "active_customer_count": active,
                "transaction_count": transactions,
                "transaction_amount": money(transactions * average_ticket),
                "target_registered_count": min(eligible, max(registered, round(eligible * min(0.95, registration_ratio + rng.uniform(0.01, 0.08))))),
                "target_transaction_count": max(transactions, round(transactions * rng.uniform(1.02, 1.12))),
            }
        )
    return rows


async def seed() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session, session.begin():
        existing = {
            model.__tablename__: await session.scalar(select(func.count()).select_from(model))
            for model in EXPECTED_COUNTS
        }
        if all(existing[model.__tablename__] == expected for model, expected in EXPECTED_COUNTS.items()):
            print("Synthetic banking facts already exist; no changes made.")
            return
        if any(existing.values()):
            raise RuntimeError(f"Banking fact seed requires empty fact tables; found {existing}")

        branches = list(
            await session.scalars(
                select(OrganizationUnit)
                .where(OrganizationUnit.office_type == OfficeType.BRANCH, OrganizationUnit.is_active.is_(True))
                .order_by(OrganizationUnit.code)
            )
        )
        if len(branches) != BRANCH_COUNT:
            raise RuntimeError(f"Expected {BRANCH_COUNT} active branches, found {len(branches)}")

        rng = random.Random(20260913)
        for month_index in range(MONTH_COUNT):
            period = add_months(START_MONTH, month_index)
            deposits: list[dict] = []
            advances: list[dict] = []
            assets: list[dict] = []
            digital: list[dict] = []

            for branch_index, branch in enumerate(branches, start=1):
                branch_deposits, deposit_accounts = deposit_rows(
                    rng, period, month_index, branch.id, branch_index
                )
                branch_advances, advance_amount, advance_accounts = advance_rows(
                    rng, period, month_index, branch.id, branch_index
                )
                deposits.extend(branch_deposits)
                advances.extend(branch_advances)
                assets.extend(
                    asset_quality_rows(
                        rng, period, branch.id, advance_amount, advance_accounts
                    )
                )
                digital.extend(
                    digital_rows(
                        rng, period, month_index, branch.id, deposit_accounts
                    )
                )

            await session.execute(insert(DepositMonthlyFact), deposits)
            await session.execute(insert(AdvanceMonthlyFact), advances)
            await session.execute(insert(AssetQualityMonthlyFact), assets)
            await session.execute(insert(DigitalProductMonthlyFact), digital)

            if (month_index + 1) % 12 == 0:
                print(f"Generated {month_index + 1} of {MONTH_COUNT} months.")

    print("Synthetic banking dataset created successfully.")


if __name__ == "__main__":
    asyncio.run(seed())

