from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, literal, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from backend.analytics.catalog import KPI_DEFINITIONS, KpiDefinition
from backend.core.config import get_settings
from backend.models.catalog import KpiCatalog
from backend.rbac.scope import organization_ids_subquery, resolve_organization_scope
from backend.repositories.users import UserAccessRecord
from backend.schemas.analytics import AnalyticsQueryRequest, AnalyticsQueryResponse, ComparisonType


class AnalyticsValidationError(ValueError):
    pass


def _shift_months(value: date, months: int) -> date:
    absolute = value.year * 12 + value.month - 1 + months
    year, month_index = divmod(absolute, 12)
    month = month_index + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _decimal(value) -> Decimal:
    return Decimal(value or 0)


def _percent(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return ((numerator / denominator) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def _aggregate(
    session: AsyncSession,
    definition: KpiDefinition,
    start: date,
    end: date,
    root_id: int,
    products: list[str],
) -> tuple[Decimal, Decimal | None, int, str]:
    model = definition.model
    target = func.coalesce(func.sum(definition.target_column), 0) if definition.target_column is not None else literal(None)
    statement = select(
        func.coalesce(func.sum(definition.value_column), 0),
        target,
        func.count(model.id),
    ).where(
        model.period_month.between(start, end),
        model.organization_unit_id.in_(organization_ids_subquery(root_id)),
    )
    if definition.aggregation == "snapshot":
        statement = statement.where(model.period_month == end)
    if products:
        statement = statement.where(definition.dimension_column.in_(products))
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    row = (await session.execute(statement)).one()
    return _decimal(row[0]), (_decimal(row[1]) if row[1] is not None else None), int(row[2]), sql


async def execute_analytics_query(
    session: AsyncSession,
    access: UserAccessRecord,
    request: AnalyticsQueryRequest,
) -> AnalyticsQueryResponse:
    definition = KPI_DEFINITIONS.get(request.kpi_code)
    if definition is None:
        raise AnalyticsValidationError("KPI is not in the executable allowlist")

    catalogue = await session.scalar(
        select(KpiCatalog).where(KpiCatalog.code == request.kpi_code, KpiCatalog.is_active.is_(True))
    )
    if catalogue is None:
        raise AnalyticsValidationError("KPI is not approved or is inactive")

    invalid = set(request.products) - definition.allowed_dimensions
    if invalid:
        raise AnalyticsValidationError(f"Invalid product/classification values: {', '.join(sorted(invalid))}")

    scope = await resolve_organization_scope(session, access, request.organization_unit_id)
    actual, target, row_count, current_sql = await _aggregate(
        session, definition, request.period_start, request.period_end, scope.effective_root_id, request.products
    )
    generated_sql = [current_sql]

    comparison_value = None
    growth = None
    if request.comparison != ComparisonType.NONE:
        offset = -12 if request.comparison == ComparisonType.YOY else -3
        comparison_value, _, _, comparison_sql = await _aggregate(
            session,
            definition,
            _shift_months(request.period_start, offset),
            _shift_months(request.period_end, offset),
            scope.effective_root_id,
            request.products,
        )
        generated_sql.append(comparison_sql)
        growth = _percent(actual - comparison_value, comparison_value)

    gap = actual - target if target is not None else None
    shortfall = max(target - actual, Decimal(0)) if target is not None else None
    achievement = _percent(actual, target) if target is not None else None

    return AnalyticsQueryResponse(
        kpi_code=definition.code,
        module=definition.module,
        unit=definition.unit,
        period_start=request.period_start,
        period_end=request.period_end,
        effective_organization_id=scope.effective_root_id,
        organization_count=len(scope.organizations),
        products=request.products,
        actual_value=actual,
        target_value=target,
        gap_to_target=gap,
        shortfall_to_target=shortfall,
        achievement_percent=achievement,
        comparison=request.comparison,
        comparison_value=comparison_value,
        growth_percent=growth,
        row_count=row_count,
        formula_version=catalogue.version,
        generated_sql=generated_sql if get_settings().environment != "production" else None,
    )
