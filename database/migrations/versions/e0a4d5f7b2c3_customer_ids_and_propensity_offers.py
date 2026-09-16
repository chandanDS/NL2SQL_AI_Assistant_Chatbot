"""Add synthetic CIBIL/offer fields and migrate legacy demo customer refs.

Revision ID: e0a4d5f7b2c3
Revises: d9f3c4e6a1b2
"""

from alembic import op
import sqlalchemy as sa


revision = "e0a4d5f7b2c3"
down_revision = "d9f3c4e6a1b2"
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
    table = "ml_pl_propensity_leads"
    op.add_column(table, sa.Column("bureau_cibil_score", sa.Integer(), nullable=False, server_default="700"))
    op.add_column(table, sa.Column("offer_amount", sa.Numeric(16, 2), nullable=False, server_default="0.00"))
    op.add_column(table, sa.Column("aa_based_offer_amount", sa.Numeric(16, 2), nullable=False, server_default="0.00"))
    op.create_check_constraint("cibil_score_range", table, "bureau_cibil_score BETWEEN 300 AND 900")

    # Existing demo refs are C-BR0033-00001, P-BR0033-00001, etc.
    # Reserve 12 IDs per branch except Mumbai Branch 01, which has 12,000.
    # This gives the same CUST ID for the same synthetic branch/customer number
    # across use-case tables without deleting or duplicating existing rows.
    for output_table in OUTPUT_TABLES:
        op.execute(sa.text(f"""
            UPDATE {output_table}
            SET customer_ref = 'CUST' || lpad((
                CASE
                    WHEN substring(split_part(customer_ref, '-', 2) from 3)::int <= 33
                    THEN (substring(split_part(customer_ref, '-', 2) from 3)::int - 1) * 12
                    ELSE 384 + 12000 + (substring(split_part(customer_ref, '-', 2) from 3)::int - 34) * 12
                END + split_part(customer_ref, '-', 3)::int
            )::text, 9, '0')
            WHERE customer_ref ~ '^[CPURM]-BR[0-9]{{4}}-[0-9]{{5}}$'
              AND as_of_date = DATE '2026-09-01'
        """))


def downgrade():
    # Generated IDs cannot be reversed without the original branch/reference
    # mapping; only the additive columns are removed on downgrade.
    table = "ml_pl_propensity_leads"
    op.drop_constraint("ck_ml_pl_propensity_leads_cibil_score_range", table, type_="check")
    op.drop_column(table, "aa_based_offer_amount")
    op.drop_column(table, "offer_amount")
    op.drop_column(table, "bureau_cibil_score")
