"""Synthetic personal-loan model outputs. Each use case owns its own table."""

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class LeadIdentityMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_unit_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("organization_units.id", ondelete="RESTRICT"), nullable=False)
    customer_ref: Mapped[str] = mapped_column(String(24), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    business_unit: Mapped[str] = mapped_column(String(12), nullable=False)
    interest_rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)


class CampaignLead(LeadIdentityMixin, Base):
    __tablename__ = "ml_campaign_leads"
    __table_args__ = (
        UniqueConstraint("customer_ref", "as_of_date"),
        CheckConstraint("propensity_score BETWEEN 0 AND 100", name="campaign_score_range"),
        CheckConstraint("propensity_band IN ('VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW')", name="campaign_propensity_band_values"),
        Index("ix_ml_campaign_scope_status", "organization_unit_id", "lead_status"),
        Index("ix_ml_campaign_scope_band", "organization_unit_id", "propensity_band"),
    )
    campaign_name: Mapped[str] = mapped_column(String(80), nullable=False)
    lead_status: Mapped[str] = mapped_column(String(20), nullable=False)
    propensity_score: Mapped[int] = mapped_column(nullable=False)
    propensity_band: Mapped[str] = mapped_column(String(20), nullable=False)
    suggested_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)


class PropensityLead(LeadIdentityMixin, Base):
    __tablename__ = "ml_pl_propensity_leads"
    __table_args__ = (
        UniqueConstraint("customer_ref", "as_of_date"),
        CheckConstraint("propensity_score BETWEEN 0 AND 100", name="propensity_score_range"),
        CheckConstraint("propensity_band IN ('VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW')", name="propensity_band_values"),
        Index("ix_ml_propensity_scope_band", "organization_unit_id", "propensity_band"),
    )
    propensity_score: Mapped[int] = mapped_column(nullable=False)
    propensity_band: Mapped[str] = mapped_column(String(20), nullable=False)
    model_version: Mapped[str] = mapped_column(String(30), nullable=False)
    preferred_contact_time: Mapped[str] = mapped_column(String(20), nullable=False)
    preferred_contact_channel: Mapped[str] = mapped_column(String(20), nullable=False)
    aa_last_6m_avg_balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    aa_last_6m_debit_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    aa_last_6m_credit_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    bureau_enquiries_6m: Mapped[int] = mapped_column(nullable=False)
    bureau_active_external_loans: Mapped[int] = mapped_column(nullable=False)
    bureau_current_exposure: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    bureau_bounces_6m: Mapped[int] = mapped_column(nullable=False)
    bureau_max_dpd_6m: Mapped[int] = mapped_column(nullable=False)
    bureau_cibil_score: Mapped[int] = mapped_column(nullable=False)
    offer_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    aa_based_offer_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)


class UnderwritingLead(LeadIdentityMixin, Base):
    __tablename__ = "ml_pl_underwriting_leads"
    __table_args__ = (
        UniqueConstraint("customer_ref", "as_of_date"),
        CheckConstraint("underwriting_score BETWEEN 0 AND 100", name="underwriting_score_range"),
        Index("ix_ml_underwriting_scope_decision", "organization_unit_id", "eligibility_status"),
    )
    eligibility_status: Mapped[str] = mapped_column(String(24), nullable=False)
    underwriting_score: Mapped[int] = mapped_column(nullable=False)
    recommended_limit: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    model_version: Mapped[str] = mapped_column(String(30), nullable=False)


class RiskReviewLead(LeadIdentityMixin, Base):
    __tablename__ = "ml_pl_risk_review_leads"
    __table_args__ = (
        UniqueConstraint("customer_ref", "as_of_date"),
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="risk_score_range"),
        CheckConstraint("risk_segment IN ('Super Red', 'Red', 'Risk Review')", name="risk_segment_values"),
        Index("ix_ml_risk_scope_band", "organization_unit_id", "risk_band"),
    )
    risk_score: Mapped[int] = mapped_column(nullable=False)
    risk_band: Mapped[str] = mapped_column(String(20), nullable=False)
    portfolio_segment_risk_probability: Mapped[int] = mapped_column(nullable=False)
    risk_segment: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_team_tag: Mapped[str] = mapped_column(String(20), nullable=False)
    review_status: Mapped[str] = mapped_column(String(160), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(40), nullable=False)


class RiskMismatchLead(LeadIdentityMixin, Base):
    __tablename__ = "ml_pl_risk_mismatch_leads"
    __table_args__ = (
        UniqueConstraint("customer_ref", "as_of_date"),
        CheckConstraint("model_risk_score BETWEEN 0 AND 100", name="mismatch_score_range"),
        Index("ix_ml_mismatch_scope_review", "organization_unit_id", "review_status"),
    )
    model_risk_score: Mapped[int] = mapped_column(nullable=False)
    model_risk_band: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_team_tag: Mapped[str] = mapped_column(String(20), nullable=False)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(40), nullable=False)
