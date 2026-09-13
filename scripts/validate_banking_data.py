import asyncio

from sqlalchemy import text

from backend.db.session import get_engine


VALIDATIONS = {
    "exact_month_count": """
        SELECT COUNT(DISTINCT period_month) = 36
        FROM fact_deposits_monthly
    """,
    "all_facts_are_branch_level": """
        SELECT COUNT(*) = 0 FROM (
            SELECT organization_unit_id FROM fact_deposits_monthly
            UNION SELECT organization_unit_id FROM fact_advances_monthly
            UNION SELECT organization_unit_id FROM fact_asset_quality_monthly
            UNION SELECT organization_unit_id FROM fact_digital_products_monthly
        ) facts
        JOIN organization_units o ON o.id = facts.organization_unit_id
        WHERE o.office_type <> 'BRANCH'
    """,
    "asset_amount_within_advances": """
        SELECT COUNT(*) = 0
        FROM vw_asset_quality_monthly_summary aq
        JOIN vw_advance_monthly_summary adv USING (period_month, organization_unit_id)
        WHERE aq.stressed_amount > adv.actual_amount
    """,
    "asset_accounts_within_advances": """
        SELECT COUNT(*) = 0
        FROM vw_asset_quality_monthly_summary aq
        JOIN vw_advance_monthly_summary adv USING (period_month, organization_unit_id)
        WHERE aq.stressed_account_count > adv.account_count
    """,
    "digital_funnel_valid": """
        SELECT COUNT(*) = 0
        FROM fact_digital_products_monthly
        WHERE active_customer_count > registered_customer_count
           OR registered_customer_count > eligible_customer_count
    """,
    "advance_relationships_valid": """
        SELECT COUNT(*) = 0
        FROM fact_advances_monthly
        WHERE disbursed_amount > sanctioned_amount
           OR overdue_amount > outstanding_amount
    """,
    "deposit_view_totals_match": """
        SELECT
            (SELECT SUM(business_amount) FROM fact_deposits_monthly)
            =
            (SELECT SUM(actual_amount) FROM vw_deposit_monthly_summary)
    """,
    "advance_view_totals_match": """
        SELECT
            (SELECT SUM(outstanding_amount) FROM fact_advances_monthly)
            =
            (SELECT SUM(actual_amount) FROM vw_advance_monthly_summary)
    """,
}


async def main() -> None:
    engine = get_engine()
    try:
        async with engine.connect() as connection:
            period = (
                await connection.execute(
                    text("""
                        SELECT MIN(period_month), MAX(period_month), COUNT(DISTINCT period_month)
                        FROM fact_deposits_monthly
                    """)
                )
            ).one()
            print(f"Period: {period[0]} to {period[1]} ({period[2]} months)")

            yearly_rows = (
                await connection.execute(
                    text("""
                        SELECT module, reporting_year, records FROM (
                            SELECT 'deposits' module, EXTRACT(YEAR FROM period_month)::int reporting_year, COUNT(*) records FROM fact_deposits_monthly GROUP BY 2
                            UNION ALL
                            SELECT 'advances', EXTRACT(YEAR FROM period_month)::int, COUNT(*) FROM fact_advances_monthly GROUP BY 2
                            UNION ALL
                            SELECT 'asset_quality', EXTRACT(YEAR FROM period_month)::int, COUNT(*) FROM fact_asset_quality_monthly GROUP BY 2
                            UNION ALL
                            SELECT 'digital_products', EXTRACT(YEAR FROM period_month)::int, COUNT(*) FROM fact_digital_products_monthly GROUP BY 2
                        ) counts
                        ORDER BY module, reporting_year
                    """)
                )
            ).all()
            for row in yearly_rows:
                if row.records < 1_000:
                    raise RuntimeError(
                        f"Insufficient records: {row.module} {row.reporting_year}={row.records}"
                    )
                print(f"{row.module} {row.reporting_year}: {row.records} records")

            for name, sql in VALIDATIONS.items():
                passed = await connection.scalar(text(sql))
                if not passed:
                    raise RuntimeError(f"Validation failed: {name}")
                print(f"PASS: {name}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
