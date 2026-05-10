"""Pydantic schemas for budgets."""

from typing import Literal

from pydantic import BaseModel


class BudgetItem(BaseModel):
    category: str
    monthly_limit: float
    currency: str = "USD"


class BudgetStatusItem(BaseModel):
    category: str
    monthly_limit: float
    actual: float
    projected_eom: float
    status: Literal["under", "on_track", "warning", "over"]
    pct_used: float


class BudgetStatusResponse(BaseModel):
    period: str
    items: list[BudgetStatusItem]
    overall_status: Literal["under", "on_track", "warning", "over"]


class BudgetProposal(BaseModel):
    based_on_months: int
    target_savings_rate: float
    suggested: list[BudgetItem]
