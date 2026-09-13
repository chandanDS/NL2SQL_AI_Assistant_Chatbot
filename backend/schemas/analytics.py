from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class ComparisonType(StrEnum):
    NONE = "none"
    YOY = "yoy"
    QOQ = "qoq"


class AnalyticsQueryRequest(BaseModel):
    kpi_code: str = Field(min_length=3, max_length=80)
    period_start: date
    period_end: date
    organization_unit_id: int | None = Field(default=None, gt=0)
    products: list[str] = Field(default_factory=list, max_length=10)
    comparison: ComparisonType = ComparisonType.NONE

    @field_validator("kpi_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("products")
    @classmethod
    def normalize_products(cls, values: list[str]) -> list[str]:
        return sorted({value.strip().upper() for value in values if value.strip()})

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_start.day != 1 or self.period_end.day != 1:
            raise ValueError("period_start and period_end must be the first day of a month")
        if self.period_start > self.period_end:
            raise ValueError("period_start must not be after period_end")
        return self


class AnalyticsQueryResponse(BaseModel):
    kpi_code: str
    module: str
    unit: str
    period_start: date
    period_end: date
    effective_organization_id: int
    organization_count: int
    products: list[str]
    actual_value: Decimal
    target_value: Decimal | None
    gap_to_target: Decimal | None
    shortfall_to_target: Decimal | None
    achievement_percent: Decimal | None
    comparison: ComparisonType
    comparison_value: Decimal | None
    growth_percent: Decimal | None
    row_count: int
    formula_version: int
    read_only: bool = True
    generated_sql: list[str] | None = None
