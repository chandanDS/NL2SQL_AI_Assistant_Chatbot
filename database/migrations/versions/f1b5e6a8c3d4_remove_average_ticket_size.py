"""Remove average ticket size from personal-loan prediction outputs.

Revision ID: f1b5e6a8c3d4
Revises: e0a4d5f7b2c3
"""

from alembic import op
import sqlalchemy as sa


revision = "f1b5e6a8c3d4"
down_revision = "e0a4d5f7b2c3"
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
        op.drop_column(table, "average_ticket_size")


def downgrade():
    for table in OUTPUT_TABLES:
        op.add_column(table, sa.Column("average_ticket_size", sa.Numeric(16, 2), nullable=False, server_default="0.00"))
