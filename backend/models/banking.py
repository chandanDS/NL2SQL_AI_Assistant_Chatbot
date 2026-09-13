from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


AMOUNT = Numeric(20, 2)


class DepositProduct(StrEnum):
    CA = "CA"
    SA = "SA"


class AdvanceProduct(StrEnum):
    EL = "EL"
    VL = "VL"
    PL = "PL"
    HL = "HL"
    MSME = "MSME"
    AGRI = "AGRI"


class AssetQualityClass(StrEnum):
    SMA0 = "SMA0"
    SMA1 = "SMA1"
    SMA2 = "SMA2"
    SUBSTANDARD = "SUBSTANDARD"
    DOUBTFUL = "DOUBTFUL"
    LOSS = "LOSS"


class DigitalProduct(StrEnum):
    MOBILE_BANKING = "MOBILE_BANKING"
    INTERNET_BANKING = "INTERNET_BANKING"
    UPI = "UPI"
    DEBIT_CARD = "DEBIT_CARD"
    POS = "POS"
    QR = "QR"
    AEPS = "AEPS"


class DepositMonthlyFact(Base):
    __tablename__ = "fact_deposits_monthly"
    __table_args__ = (
        UniqueConstraint("period_month", "organization_unit_id", "product_type"),
        CheckConstraint("product_type IN ('CA', 'SA')", name="deposit_valid_product"),
        CheckConstraint("business_amount >= 0 AND target_amount >= 0", name="deposit_non_negative_amounts"),
        CheckConstraint(
            "account_count >= 0 AND target_account_count >= 0 AND new_accounts >= 0 AND closed_accounts >= 0",
            name="deposit_non_negative_counts",
        ),
        Index("ix_fact_deposits_org_period", "organization_unit_id", "period_month"),
        Index("ix_fact_deposits_product_period", "product_type", "period_month"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    period_month: Mapped[date] = mapped_column(Date, nullable=False)
    organization_unit_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organization_units.id", ondelete="RESTRICT"), nullable=False
    )
    product_type: Mapped[str] = mapped_column(String(10), nullable=False)
    business_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    account_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_account_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    new_accounts: Mapped[int] = mapped_column(BigInteger, nullable=False)
    closed_accounts: Mapped[int] = mapped_column(BigInteger, nullable=False)


class AdvanceMonthlyFact(Base):
    __tablename__ = "fact_advances_monthly"
    __table_args__ = (
        UniqueConstraint("period_month", "organization_unit_id", "product_type"),
        CheckConstraint(
            "product_type IN ('EL', 'VL', 'PL', 'HL', 'MSME', 'AGRI')",
            name="advance_valid_product",
        ),
        CheckConstraint(
            "outstanding_amount >= 0 AND target_amount >= 0 AND sanctioned_amount >= 0 "
            "AND disbursed_amount >= 0 AND overdue_amount >= 0",
            name="advance_non_negative_amounts",
        ),
        CheckConstraint("disbursed_amount <= sanctioned_amount", name="advance_disbursed_within_sanction"),
        CheckConstraint("overdue_amount <= outstanding_amount", name="advance_overdue_within_outstanding"),
        CheckConstraint("account_count >= 0 AND target_account_count >= 0", name="advance_non_negative_counts"),
        Index("ix_fact_advances_org_period", "organization_unit_id", "period_month"),
        Index("ix_fact_advances_product_period", "product_type", "period_month"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    period_month: Mapped[date] = mapped_column(Date, nullable=False)
    organization_unit_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organization_units.id", ondelete="RESTRICT"), nullable=False
    )
    product_type: Mapped[str] = mapped_column(String(10), nullable=False)
    outstanding_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    account_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_account_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sanctioned_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    disbursed_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    overdue_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)


class AssetQualityMonthlyFact(Base):
    __tablename__ = "fact_asset_quality_monthly"
    __table_args__ = (
        UniqueConstraint("period_month", "organization_unit_id", "classification"),
        CheckConstraint(
            "classification IN ('SMA0', 'SMA1', 'SMA2', 'SUBSTANDARD', 'DOUBTFUL', 'LOSS')",
            name="asset_quality_valid_class",
        ),
        CheckConstraint(
            "outstanding_amount >= 0 AND slippage_amount >= 0 AND recovery_amount >= 0 "
            "AND target_recovery_amount >= 0",
            name="asset_quality_non_negative_amounts",
        ),
        CheckConstraint("account_count >= 0", name="asset_quality_non_negative_accounts"),
        CheckConstraint("recovery_amount <= outstanding_amount", name="asset_quality_recovery_within_outstanding"),
        Index("ix_fact_asset_quality_org_period", "organization_unit_id", "period_month"),
        Index("ix_fact_asset_quality_class_period", "classification", "period_month"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    period_month: Mapped[date] = mapped_column(Date, nullable=False)
    organization_unit_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organization_units.id", ondelete="RESTRICT"), nullable=False
    )
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    outstanding_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    account_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    slippage_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    recovery_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    target_recovery_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)


class DigitalProductMonthlyFact(Base):
    __tablename__ = "fact_digital_products_monthly"
    __table_args__ = (
        UniqueConstraint("period_month", "organization_unit_id", "product_type"),
        CheckConstraint(
            "product_type IN ('MOBILE_BANKING', 'INTERNET_BANKING', 'UPI', "
            "'DEBIT_CARD', 'POS', 'QR', 'AEPS')",
            name="digital_valid_product",
        ),
        CheckConstraint(
            "eligible_customer_count >= 0 AND registered_customer_count >= 0 "
            "AND active_customer_count >= 0 AND transaction_count >= 0 "
            "AND target_registered_count >= 0 AND target_transaction_count >= 0",
            name="digital_non_negative_counts",
        ),
        CheckConstraint(
            "active_customer_count <= registered_customer_count "
            "AND registered_customer_count <= eligible_customer_count",
            name="digital_customer_funnel",
        ),
        CheckConstraint("transaction_amount >= 0", name="digital_non_negative_amount"),
        Index("ix_fact_digital_org_period", "organization_unit_id", "period_month"),
        Index("ix_fact_digital_product_period", "product_type", "period_month"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    period_month: Mapped[date] = mapped_column(Date, nullable=False)
    organization_unit_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organization_units.id", ondelete="RESTRICT"), nullable=False
    )
    product_type: Mapped[str] = mapped_column(String(30), nullable=False)
    eligible_customer_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    registered_customer_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    active_customer_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    transaction_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    transaction_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    target_registered_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_transaction_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
