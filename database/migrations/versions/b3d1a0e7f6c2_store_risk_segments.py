"""Store synthetic portfolio-relative risk segments in the scorecard table.

Revision ID: b3d1a0e7f6c2
Revises: a2c6f7b9d4e5
"""

from alembic import op
import sqlalchemy as sa


revision = "b3d1a0e7f6c2"
down_revision = "a2c6f7b9d4e5"
branch_labels = None
depends_on = None

TABLE = "ml_pl_risk_review_leads"


def upgrade():
    op.add_column(TABLE, sa.Column("portfolio_segment_risk_probability", sa.Integer(), nullable=True))
    op.add_column(TABLE, sa.Column("risk_segment", sa.String(20), nullable=True))
    op.alter_column(TABLE, "review_status", existing_type=sa.String(30), type_=sa.String(160), existing_nullable=False)

    op.execute(sa.text("""
        UPDATE ml_pl_risk_review_leads
        SET portfolio_segment_risk_probability = CASE business_unit
            WHEN 'TIER_1' THEN 40
            WHEN 'TIER_2' THEN 45
            WHEN 'TIER_3' THEN 50
            WHEN 'TIER_4' THEN 55
            WHEN 'PLTB' THEN 52
            WHEN 'SALPL' THEN 48
            ELSE NULL
        END
    """))
    op.execute(sa.text("""
        UPDATE ml_pl_risk_review_leads
        SET risk_segment = CASE
            WHEN risk_score > 80 AND risk_score >= 2 * portfolio_segment_risk_probability THEN 'Super Red'
            WHEN risk_score > 80 AND risk_score >= 1.5 * portfolio_segment_risk_probability THEN 'Red'
            ELSE 'Risk Review'
        END
    """))
    op.execute(sa.text("""
        UPDATE ml_pl_risk_review_leads
        SET review_status = CASE
            WHEN risk_score <= 80 THEN
                'Risk probability ' || risk_score || '% does not exceed the 80% threshold.'
            WHEN risk_segment = 'Super Red' THEN
                'Risk probability ' || risk_score || '% exceeds 80% and is at least 2x the '
                || business_unit || ' portfolio baseline (' || portfolio_segment_risk_probability || '%): Super Red.'
            WHEN risk_segment = 'Red' THEN
                'Risk probability ' || risk_score || '% exceeds 80% and is at least 1.5x the '
                || business_unit || ' portfolio baseline (' || portfolio_segment_risk_probability || '%): Red.'
            ELSE
                'Risk probability ' || risk_score || '% exceeds 80%, but is below 1.5x the '
                || business_unit || ' portfolio baseline (' || portfolio_segment_risk_probability || '%).'
        END
    """))
    op.alter_column(TABLE, "portfolio_segment_risk_probability", existing_type=sa.Integer(), nullable=False)
    op.alter_column(TABLE, "risk_segment", existing_type=sa.String(20), nullable=False)
    op.create_check_constraint("risk_segment_values", TABLE,
                               "risk_segment IN ('Super Red', 'Red', 'Risk Review')")


def downgrade():
    op.drop_constraint("ck_ml_pl_risk_review_leads_risk_segment_values", TABLE, type_="check")
    op.execute(sa.text("UPDATE ml_pl_risk_review_leads SET review_status = 'AVOID_PENDING_REVIEW'"))
    op.alter_column(TABLE, "review_status", existing_type=sa.String(160), type_=sa.String(30), existing_nullable=False)
    op.drop_column(TABLE, "risk_segment")
    op.drop_column(TABLE, "portfolio_segment_risk_probability")
