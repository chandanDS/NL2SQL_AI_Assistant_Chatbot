from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from backend.analytics.semantic_catalog import SEMANTIC_DATASETS
from backend.core.config import get_settings
from backend.rbac.scope import organization_ids_subquery, resolve_organization_scope
from backend.repositories.users import UserAccessRecord
from backend.models.organization import OrganizationUnit
from backend.schemas.semantic import SemanticAggregation, SemanticDimension, SemanticOperation, SemanticQueryPlan, SemanticQueryResponse


class SemanticValidationError(ValueError):
    pass


TWO_DECIMAL_PLACES = Decimal("0.01")


def _response_value(value):
    """Round calculated decimal output without reducing database precision."""
    if isinstance(value, Decimal):
        return float(value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP))
    return value


def _format_calculated_value(value, unit: str) -> str:
    number = Decimal(str(value))
    if unit == "INR":
        return f"₹{number / Decimal('10000000'):,.2f} crore"
    if unit == "INR_PER_ACCOUNTS":
        return f"₹{number:,.2f} per account"
    if unit == "PERCENT":
        return f"{number:,.2f}%"
    return f"{number:,.2f} {unit.lower().replace('_', ' ')}"


def _aggregate(column, aggregation: SemanticAggregation):
    return {
        SemanticAggregation.SUM: func.sum,
        SemanticAggregation.AVG: func.avg,
        SemanticAggregation.MIN: func.min,
        SemanticAggregation.MAX: func.max,
    }[aggregation](column)


def validate_semantic_plan(plan: SemanticQueryPlan):
    dataset = SEMANTIC_DATASETS.get(plan.module)
    if dataset is None:
        raise SemanticValidationError("Module is not available in the semantic layer")
    if plan.measure not in dataset.measures:
        raise SemanticValidationError(f"Measure '{plan.measure}' is not allowed for {plan.module}")
    if plan.secondary_measure and plan.secondary_measure not in dataset.measures:
        raise SemanticValidationError(f"Secondary measure '{plan.secondary_measure}' is not allowed for {plan.module}")
    invalid_products = set(plan.products) - dataset.allowed_products
    if invalid_products:
        raise SemanticValidationError(f"Invalid product/classification values: {', '.join(sorted(invalid_products))}")
    if SemanticDimension.ORGANIZATION in plan.group_by and SemanticDimension.PERIOD in plan.group_by and SemanticDimension.PRODUCT in plan.group_by:
        raise SemanticValidationError("A maximum of two grouping dimensions is allowed for a single query")
    return dataset


async def execute_semantic_query(
    session: AsyncSession, access: UserAccessRecord, plan: SemanticQueryPlan
) -> SemanticQueryResponse:
    dataset = validate_semantic_plan(plan)
    model = dataset.model
    scope = await resolve_organization_scope(session, access, plan.organization_unit_id)

    primary = _aggregate(dataset.measures[plan.measure].column, plan.aggregation)
    unit = dataset.measures[plan.measure].unit
    if plan.operation == SemanticOperation.RATIO:
        secondary = _aggregate(dataset.measures[plan.secondary_measure].column, plan.aggregation)
        ratio = primary / func.nullif(secondary, 0)
        value_expression = ((ratio * 100) if plan.as_percentage else ratio).label("value")
        unit = "PERCENT" if plan.as_percentage else f"{unit}_PER_{dataset.measures[plan.secondary_measure].unit}"
    elif plan.operation == SemanticOperation.DIFFERENCE:
        secondary = _aggregate(dataset.measures[plan.secondary_measure].column, plan.aggregation)
        value_expression = (primary - secondary).label("value")
    else:
        value_expression = primary.label("value")

    dimensions = []
    labels = []
    group_by_organization = False
    for dimension in plan.group_by:
        if dimension == SemanticDimension.PERIOD:
            dimensions.append(model.period_month)
            labels.append("period_month")
        elif dimension == SemanticDimension.PRODUCT:
            dimensions.append(dataset.product_column)
            labels.append("product")
        else:
            dimensions.extend([OrganizationUnit.code, OrganizationUnit.name])
            labels.extend(["organization_code", "organization_name"])
            group_by_organization = True

    statement = select(*dimensions, value_expression).where(
        model.period_month.between(plan.period_start, plan.period_end),
        model.organization_unit_id.in_(organization_ids_subquery(scope.effective_root_id)),
    )
    if group_by_organization:
        statement = statement.join(OrganizationUnit, OrganizationUnit.id == model.organization_unit_id)
    if plan.products:
        statement = statement.where(dataset.product_column.in_(plan.products))
    if dimensions:
        statement = statement.group_by(*dimensions).order_by(value_expression.desc() if plan.sort_descending else value_expression.asc())
        statement = statement.limit(plan.limit)

    result = await session.execute(statement)
    rows = []
    for row in result.all():
        mapping = dict(zip([*labels, "value"], row, strict=True))
        rows.append({key: _response_value(value) for key, value in mapping.items()})

    sql = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    if not rows:
        insights = ["No records matched the selected period, products, and permitted organization scope."]
    elif len(rows) == 1:
        insights = [f"The calculated result is {_format_calculated_value(rows[0]['value'], unit)}."]
    else:
        group = ", ".join(f"{key}={rows[0][key]}" for key in labels)
        insights = [f"The leading result is {group}, at {_format_calculated_value(rows[0]['value'], unit)}."]
    return SemanticQueryResponse(
        interpretation=plan.interpretation,
        module=plan.module,
        operation=plan.operation,
        unit=unit,
        effective_organization_id=scope.effective_root_id,
        columns=[*labels, "value"],
        rows=rows,
        row_count=len(rows),
        insights=insights,
        generated_sql=sql if get_settings().environment != "production" else None,
    )
