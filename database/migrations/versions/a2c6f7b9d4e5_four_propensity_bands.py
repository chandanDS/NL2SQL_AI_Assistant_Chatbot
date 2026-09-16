"""Classify every scored campaign/propensity row into four exclusive bands.

Revision ID: a2c6f7b9d4e5
Revises: f1b5e6a8c3d4
"""

from alembic import op
import sqlalchemy as sa


revision = "a2c6f7b9d4e5"
down_revision = "f1b5e6a8c3d4"
branch_labels = None
depends_on = None


def _band_case():
    return "CASE WHEN propensity_score > 90 THEN 'VERY_HIGH' " \
           "WHEN propensity_score >= 75 THEN 'HIGH' " \
           "WHEN propensity_score >= 60 THEN 'MEDIUM' ELSE 'LOW' END"


def upgrade():
    op.add_column("ml_campaign_leads", sa.Column("propensity_band", sa.String(20), nullable=False, server_default="MEDIUM"))
    for table in ("ml_campaign_leads", "ml_pl_propensity_leads"):
        op.execute(sa.text(f"UPDATE {table} SET propensity_band = {_band_case()}"))
    op.alter_column("ml_campaign_leads", "propensity_band", server_default=None)
    op.create_check_constraint("campaign_propensity_band_values", "ml_campaign_leads",
                               "propensity_band IN ('VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW')")
    op.create_check_constraint("propensity_band_values", "ml_pl_propensity_leads",
                               "propensity_band IN ('VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW')")
    op.create_index("ix_ml_campaign_scope_band", "ml_campaign_leads", ["organization_unit_id", "propensity_band"])


def downgrade():
    op.drop_index("ix_ml_campaign_scope_band", table_name="ml_campaign_leads")
    op.drop_constraint("ck_ml_pl_propensity_leads_propensity_band_values", "ml_pl_propensity_leads", type_="check")
    op.drop_constraint("ck_ml_campaign_leads_campaign_propensity_band_values", "ml_campaign_leads", type_="check")
    op.execute(sa.text("UPDATE ml_pl_propensity_leads SET propensity_band = CASE WHEN propensity_score >= 80 THEN 'HIGH' ELSE 'MEDIUM' END"))
    op.drop_column("ml_campaign_leads", "propensity_band")
