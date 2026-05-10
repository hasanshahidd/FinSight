"""Shared helpers: load transactions into a pandas DataFrame and resolve periods."""

from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction


PERIODS_DAYS = {
    "last_7_days": 7,
    "last_14_days": 14,
    "last_30_days": 30,
    "last_60_days": 60,
    "last_90_days": 90,
    "last_180_days": 180,
}


def resolve_period(period: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Resolve a named period to (start, end) datetimes."""
    n = (now or datetime.utcnow()).replace(microsecond=0)
    if period == "this_week":
        start = (n - timedelta(days=n.weekday())).replace(hour=0, minute=0, second=0)
    elif period == "this_month":
        start = n.replace(day=1, hour=0, minute=0, second=0)
    elif period == "last_month":
        first = n.replace(day=1, hour=0, minute=0, second=0)
        end = first - timedelta(seconds=1)
        start = end.replace(day=1, hour=0, minute=0, second=0)
        return start, end
    elif period == "ytd":
        start = n.replace(month=1, day=1, hour=0, minute=0, second=0)
    elif period in PERIODS_DAYS:
        start = n - timedelta(days=PERIODS_DAYS[period])
    else:
        # Unknown period — default to last 7 days
        start = n - timedelta(days=7)
    return start, n


async def load_txns(
    session: AsyncSession,
    user_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> pd.DataFrame:
    """Pull a user's transactions into a pandas DataFrame."""
    q = select(Transaction).where(Transaction.user_id == user_id)
    if start is not None:
        q = q.where(Transaction.timestamp >= start)
    if end is not None:
        q = q.where(Transaction.timestamp <= end)
    rows = (await session.execute(q)).scalars().all()
    if not rows:
        return pd.DataFrame(
            columns=[
                "id", "amount", "category", "subcategory", "merchant",
                "description", "timestamp", "account_id", "is_recurring",
                "anomaly_score",
            ]
        )
    df = pd.DataFrame([
        {
            "id": r.id,
            "amount": r.amount,
            "category": r.category,
            "subcategory": r.subcategory,
            "merchant": r.merchant,
            "description": r.description,
            "timestamp": r.timestamp,
            "account_id": r.account_id,
            "is_recurring": r.is_recurring,
            "anomaly_score": r.anomaly_score,
        }
        for r in rows
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["abs_amount"] = df["amount"].abs()
    df["is_debit"] = df["amount"] < 0
    return df
