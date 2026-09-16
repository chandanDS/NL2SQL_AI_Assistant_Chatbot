"""Add demo segmentation, pricing, contact, AA and bureau fields.

Revision ID: d9f3c4e6a1b2
Revises: c8e2b3d5e0a1
"""

from alembic import op
import sqlalchemy as sa


revision = "d9f3c4e6a1b2"
down_revision = "c8e2b3d5e0a1"
branch_labels = None
depends_on = None


OUTPUT_TABLES = (
    "ml_campaign_leads",
    "ml_pl_propensity_leads",
    "ml_pl_underwriting_leads",
    "ml_pl_risk_review_leads",
    "ml_pl_risk_mismatch_leads",
)


def upgrade():
    for table in OUTPUT_TABLES:
        op.add_column(table, sa.Column("business_unit", sa.String(12), nullable=False, server_default="TIER_3"))
        op.add_column(table, sa.Column("average_ticket_size", sa.Numeric(16, 2), nullable=False, server_default="250000.00"))
        op.add_column(table, sa.Column("interest_rate_pct", sa.Numeric(5, 2), nullable=False, server_default="12.50"))
    table = "ml_pl_propensity_leads"
    op.add_column(table, sa.Column("preferred_contact_time", sa.String(20), nullable=False, server_default="UNKNOWN"))
    op.add_column(table, sa.Column("preferred_contact_channel", sa.String(20), nullable=False, server_default="UNKNOWN"))
    for name in ("aa_last_6m_avg_balance", "aa_last_6m_debit_amount", "aa_last_6m_credit_amount", "bureau_current_exposure"):
        op.add_column(table, sa.Column(name, sa.Numeric(16, 2), nullable=False, server_default="0.00"))
    for name in ("bureau_enquiries_6m", "bureau_active_external_loans", "bureau_bounces_6m", "bureau_max_dpd_6m"):
        op.add_column(table, sa.Column(name, sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    table = "ml_pl_propensity_leads"
    for name in (
        "bureau_max_dpd_6m", "bureau_bounces_6m", "bureau_current_exposure",
        "bureau_active_external_loans", "bureau_enquiries_6m", "aa_last_6m_credit_amount",
        "aa_last_6m_debit_amount", "aa_last_6m_avg_balance", "preferred_contact_channel",
        "preferred_contact_time",
    ):
        op.drop_column(table, name)
    for table in reversed(OUTPUT_TABLES):
        for name in ("interest_rate_pct", "average_ticket_size", "business_unit"):
            op.drop_column(table, name)
