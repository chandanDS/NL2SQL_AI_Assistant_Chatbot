from datetime import date
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class SemanticOperation(StrEnum):
    AGGREGATE = "aggregate"
    RATIO = "ratio"
    DIFFERENCE = "difference"


class SemanticAggregation(StrEnum):
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"


class SemanticDimension(StrEnum):
    PERIOD = "period_month"
    PRODUCT = "product"
    ORGANIZATION = "organization"


class SemanticQueryPlan(BaseModel):
    module: Literal["DEPOSITS", "ADVANCES", "NPA_SMA", "DIGITAL"]
    operation: SemanticOperation
    measure: str = Field(min_length=2, max_length=60)
    secondary_measure: str | None = Field(default=None, max_length=60)
    aggregation: SemanticAggregation = SemanticAggregation.SUM
    as_percentage: bool = False
    group_by: list[SemanticDimension] = Field(default_factory=list, max_length=3)
    period_start: date
    period_end: date
    products: list[str] = Field(default_factory=list, max_length=10)
    organization_unit_id: int | None = Field(default=None, gt=0)
    sort_descending: bool = True
    limit: int = Field(default=20, ge=1, le=50)
    interpretation: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def validate_plan(self):
        if self.operation in {SemanticOperation.RATIO, SemanticOperation.DIFFERENCE} and not self.secondary_measure:
            raise ValueError("secondary_measure is required for ratio or difference")
        if self.as_percentage and self.operation != SemanticOperation.RATIO:
            raise ValueError("as_percentage is valid only for ratio calculations")
        self.period_start = self.period_start.replace(day=1)
        self.period_end = self.period_end.replace(day=1)
        if self.period_start > self.period_end:
            raise ValueError("Semantic query period_start must not be after period_end")
        self.measure = self.measure.strip().lower()
        self.secondary_measure = self.secondary_measure.strip().lower() if self.secondary_measure else None
        product_aliases = {
            "SAVINGS": "SA", "SAVINGS_ACCOUNT": "SA", "SAVING_ACCOUNT": "SA",
            "CURRENT_ACCOUNT": "CA", "EDUCATION_LOAN": "EL", "VEHICLE_LOAN": "VL",
            "PERSONAL_LOAN": "PL", "HOME_LOAN": "HL", "HOUSING_LOAN": "HL",
            "AGRICULTURE": "AGRI", "AGRICULTURE_LOAN": "AGRI", "AGRICULTURAL_LOAN": "AGRI",
        }
        normalized_products = {
            item.strip().upper().replace(" ", "_").replace("-", "_")
            for item in self.products
            if item.strip()
        }
        self.products = sorted({product_aliases.get(item, item) for item in normalized_products})
        self.group_by = list(dict.fromkeys(self.group_by))
        return self


class SemanticQueryRequest(BaseModel):
    plan: SemanticQueryPlan
    session_id: UUID | None = None


class SemanticQueryResponse(BaseModel):
    interpretation: str
    module: str
    operation: SemanticOperation
    unit: str
    effective_organization_id: int
    columns: list[str]
    rows: list[dict]
    row_count: int
    insights: list[str] = Field(default_factory=list)
    insight_usage: dict[str, int] = Field(
        default_factory=lambda: {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    )
    insight_fallback_used: bool = False
    generated_sql: str | None = None
    read_only: bool = True
