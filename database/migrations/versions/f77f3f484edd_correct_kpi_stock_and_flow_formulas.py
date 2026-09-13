"""correct KPI stock and flow formulas

Revision ID: f77f3f484edd
Revises: 3388099bd02f
Create Date: 2026-09-13 00:36:38.597078

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f77f3f484edd'
down_revision: Union[str, Sequence[str], None] = '3388099bd02f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.text("""
        UPDATE kpi_catalog
        SET actual_formula = 'SUM(value) for period_end month (point-in-time balance/count)'
        WHERE code IN ('DEPOSIT_BUSINESS_AMOUNT', 'DEPOSIT_ACCOUNT_COUNT',
                       'ADVANCE_OUTSTANDING_AMOUNT', 'ADVANCE_ACCOUNT_COUNT',
                       'ASSET_QUALITY_OUTSTANDING_AMOUNT', 'ASSET_QUALITY_ACCOUNT_COUNT',
                       'DIGITAL_REGISTERED_CUSTOMERS', 'DIGITAL_ACTIVE_CUSTOMERS')
    """))
    op.execute(sa.text("""
        UPDATE kpi_catalog
        SET actual_formula = 'SUM(value) from period_start through period_end (period activity)'
        WHERE code NOT IN ('DEPOSIT_BUSINESS_AMOUNT', 'DEPOSIT_ACCOUNT_COUNT',
                           'ADVANCE_OUTSTANDING_AMOUNT', 'ADVANCE_ACCOUNT_COUNT',
                           'ASSET_QUALITY_OUTSTANDING_AMOUNT', 'ASSET_QUALITY_ACCOUNT_COUNT',
                           'DIGITAL_REGISTERED_CUSTOMERS', 'DIGITAL_ACTIVE_CUSTOMERS')
    """))


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE kpi_catalog SET actual_formula = 'SUM(value)' ")
