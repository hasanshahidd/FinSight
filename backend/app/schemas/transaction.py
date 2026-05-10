"""Pydantic schemas for transactions."""

from datetime import datetime

from pydantic import BaseModel, Field


class TransactionOut(BaseModel):
    id: str
    user_id: str
    account_id: str
    amount: float
    currency: str
    category: str
    subcategory: str = ""
    merchant: str
    description: str
    timestamp: datetime
    is_recurring: bool = False
    anomaly_score: float = 0.0

    class Config:
        from_attributes = True


class TransactionFilter(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    category: str | None = None
    merchant: str | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    limit: int = Field(default=100, ge=1, le=1000)


class TransactionSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    k: int = Field(default=20, ge=1, le=100)
