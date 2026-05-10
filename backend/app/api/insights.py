"""Insights endpoints: summary, trend, compare, forecast, category-drift."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.compare import compare_periods
from app.analytics.drift import analyze_category_drift
from app.analytics.forecast import forecast_spending
from app.analytics.summary import compute_summary
from app.analytics.trend import compute_trend
from app.core.security import current_user
from app.db.models import Transaction
from app.db.session import get_session

router = APIRouter()


@router.get("/suggestions/context")
async def suggestions_context(
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, list[str]]:
    """Return the user's top categories + merchants by spend, for autocomplete.

    The chat input uses these to expand templates like
    "How much did I spend on {category}?" into concrete suggestions.
    """
    # Expenses are stored as negative amounts; income as positive. We want
    # spending categories/merchants only - filter to amount < 0 and order by
    # absolute spend / frequency.
    cat_q = (
        select(Transaction.category, func.sum(func.abs(Transaction.amount)).label("total"))
        .where(Transaction.user_id == user_id)
        .where(Transaction.amount < 0)
        .group_by(Transaction.category)
        .order_by(func.sum(func.abs(Transaction.amount)).desc())
        .limit(8)
    )
    categories = [row[0] for row in (await session.execute(cat_q)).all() if row[0]]

    mer_q = (
        select(Transaction.merchant, func.count().label("n"))
        .where(Transaction.user_id == user_id)
        .where(Transaction.amount < 0)
        .group_by(Transaction.merchant)
        .order_by(func.count().desc())
        .limit(12)
    )
    merchants = [row[0] for row in (await session.execute(mer_q)).all() if row[0]]

    return {"categories": categories, "merchants": merchants}


@router.get("/summary")
async def summary(
    period: str = Query("last_7_days"),
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await compute_summary(session, user_id, period)


@router.get("/trend")
async def trend(
    period: str = Query("last_30_days"),
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await compute_trend(session, user_id, period)


@router.get("/compare")
async def compare(
    period_a: str = Query("this_week"),
    period_b: str = Query("last_week"),
    by: str = Query("category"),
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await compare_periods(session, user_id, period_a, period_b, by)


@router.get("/forecast")
async def forecast(
    period: str = Query("this_month"),
    method: str = Query("linear"),
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await forecast_spending(session, user_id, period, method)


@router.get("/category-drift")
async def category_drift(
    window_days: int = Query(90, ge=14, le=365),
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await analyze_category_drift(session, user_id, window_days)
