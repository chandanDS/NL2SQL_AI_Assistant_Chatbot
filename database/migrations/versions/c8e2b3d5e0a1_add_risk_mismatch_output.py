"""Separate risk-tag/model disagreement output from the risk scorecard.

Revision ID: c8e2b3d5e0a1
Revises: b7e1a2c4d9f0
"""

from alembic import op
import sqlalchemy as sa


revision = "c8e2b3d5e0a1"
down_revision = "b7e1a2c4d9f0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ml_pl_risk_mismatch_leads",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_unit_id", sa.BigInteger(), sa.ForeignKey("organization_units.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_ref", sa.String(24), nullable=False),
        sa.Column("customer_name", sa.String(120), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("model_risk_score", sa.Integer(), nullable=False),
        sa.Column("model_risk_band", sa.String(20), nullable=False),
        sa.Column("risk_team_tag", sa.String(20), nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False),
        sa.Column("reason_code", sa.String(40), nullable=False),
        sa.UniqueConstraint("customer_ref", "as_of_date"),
        sa.CheckConstraint("model_risk_score BETWEEN 0 AND 100", name="ck_ml_pl_risk_mismatch_leads_mismatch_score_range"),
    )
    op.create_index("ix_ml_mismatch_scope_review", "ml_pl_risk_mismatch_leads", ["organization_unit_id", "review_status"])


def downgrade():
    op.drop_index("ix_ml_mismatch_scope_review", table_name="ml_pl_risk_mismatch_leads")
    op.drop_table("ml_pl_risk_mismatch_leads")
