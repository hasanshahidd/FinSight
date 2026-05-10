"""Pydantic schemas for spending insights."""

from pydantic import BaseModel


class CategoryTotal(BaseModel):
    category: str
    total: float
    transaction_count: int
    pct_of_total: float


class SpendingSummary(BaseModel):
    period: str  # e.g. "last_7_days"
    start_date: str
    end_date: str
    total_spent: float
    total_income: float
    net: float
    top_categories: list[CategoryTotal]
    transaction_count: int


class TrendPoint(BaseModel):
    label: str  # day/week label
    spent: float
    income: float


class TrendResponse(BaseModel):
    period: str
    points: list[TrendPoint]
    pct_change_vs_previous: float | None = None
