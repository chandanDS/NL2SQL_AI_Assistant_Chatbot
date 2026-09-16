"""Create separate synthetic personal-loan model-output tables.

Revision ID: b7e1a2c4d9f0
Revises: d3fc32489655
"""

from alembic import op
import sqlalchemy as sa

revision = "b7e1a2c4d9f0"
down_revision = "d3fc32489655"
branch_labels = None
depends_on = None


def _identity_columns():
    return [
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_unit_id", sa.BigInteger(), sa.ForeignKey("organization_units.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_ref", sa.String(24), nullable=False),
        sa.Column("customer_name", sa.String(120), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.UniqueConstraint("customer_ref", "as_of_date"),
    ]


def upgrade():
    op.create_table(
        "ml_campaign_leads", *_identity_columns(),
        sa.Column("campaign_name", sa.String(80), nullable=False),
        sa.Column("lead_status", sa.String(20), nullable=False),
        sa.Column("propensity_score", sa.Integer(), nullable=False),
        sa.Column("suggested_amount", sa.Numeric(16, 2), nullable=False),
        sa.CheckConstraint("propensity_score BETWEEN 0 AND 100", name="ck_ml_campaign_leads_campaign_score_range"),
    )
    op.create_index("ix_ml_campaign_scope_status", "ml_campaign_leads", ["organization_unit_id", "lead_status"])
    op.create_table(
        "ml_pl_propensity_leads", *_identity_columns(),
        sa.Column("propensity_score", sa.Integer(), nullable=False),
        sa.Column("propensity_band", sa.String(20), nullable=False),
        sa.Column("model_version", sa.String(30), nullable=False),
        sa.CheckConstraint("propensity_score BETWEEN 0 AND 100", name="ck_ml_pl_propensity_leads_propensity_score_range"),
    )
    op.create_index("ix_ml_propensity_scope_band", "ml_pl_propensity_leads", ["organization_unit_id", "propensity_band"])
    op.create_table(
        "ml_pl_underwriting_leads", *_identity_columns(),
        sa.Column("eligibility_status", sa.String(24), nullable=False),
        sa.Column("underwriting_score", sa.Integer(), nullable=False),
        sa.Column("recommended_limit", sa.Numeric(16, 2), nullable=False),
        sa.Column("model_version", sa.String(30), nullable=False),
        sa.CheckConstraint("underwriting_score BETWEEN 0 AND 100", name="ck_ml_pl_underwriting_leads_underwriting_score_range"),
    )
    op.create_index("ix_ml_underwriting_scope_decision", "ml_pl_underwriting_leads", ["organization_unit_id", "eligibility_status"])
    op.create_table(
        "ml_pl_risk_review_leads", *_identity_columns(),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_band", sa.String(20), nullable=False),
        sa.Column("risk_team_tag", sa.String(20), nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False),
        sa.Column("reason_code", sa.String(40), nullable=False),
        sa.CheckConstraint("risk_score BETWEEN 0 AND 100", name="ck_ml_pl_risk_review_leads_risk_score_range"),
    )
    op.create_index("ix_ml_risk_scope_band", "ml_pl_risk_review_leads", ["organization_unit_id", "risk_band"])


def downgrade():
    for table, index in (
        ("ml_pl_risk_review_leads", "ix_ml_risk_scope_band"),
        ("ml_pl_underwriting_leads", "ix_ml_underwriting_scope_decision"),
        ("ml_pl_propensity_leads", "ix_ml_propensity_scope_band"),
        ("ml_campaign_leads", "ix_ml_campaign_scope_status"),
    ):
        op.drop_index(index, table_name=table)
        op.drop_table(table)
