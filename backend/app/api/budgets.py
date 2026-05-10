"""Budgets: read, propose, evaluate status."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import load_txns, resolve_period
from app.analytics.forecast import forecast_spending
from app.core.security import current_user
from app.db.models import Budget
from app.db.session import get_session
from app.schemas.budget import (
    BudgetItem,
    BudgetProposal,
    BudgetStatusItem,
    BudgetStatusResponse,
)

router = APIRouter()


@router.get("", response_model=list[BudgetItem])
async def list_budgets(
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BudgetItem]:
    q = select(Budget).where(Budget.user_id == user_id).order_by(Budget.monthly_limit.desc())
    rows = (await session.execute(q)).scalars().all()
    return [BudgetItem(category=r.category, monthly_limit=r.monthly_limit) for r in rows]


@router.get("/status", response_model=BudgetStatusResponse)
async def budget_status(
    period: str = Query("this_month"),
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> BudgetStatusResponse:
    budgets = {
        b.category: b.monthly_limit
        for b in (await session.execute(select(Budget).where(Budget.user_id == user_id))).scalars()
    }
    if not budgets:
        return BudgetStatusResponse(period=period, items=[], overall_status="under")

    forecast = await forecast_spending(session, user_id, period=period)
    by_cat = {row["category"]: row for row in forecast["by_category"]}

    items: list[BudgetStatusItem] = []
    over_count = warn_count = 0
    for cat, limit in budgets.items():
        row = by_cat.get(cat, {"actual_so_far": 0.0, "projected_eom": 0.0})
        actual = float(row["actual_so_far"])
        projected = float(row["projected_eom"])
        pct = (projected / limit * 100) if limit else 0
        if pct >= 100:
            status = "over"
            over_count += 1
        elif pct >= 90:
            status = "warning"
            warn_count += 1
        elif pct >= 50:
            status = "on_track"
        else:
            status = "under"
        items.append(BudgetStatusItem(
            category=cat,
            monthly_limit=limit,
            actual=round(actual, 2),
            projected_eom=round(projected, 2),
            status=status,
            pct_used=round(pct, 1),
        ))

    overall = "over" if over_count else ("warning" if warn_count else "on_track")
    items.sort(key=lambda i: i.pct_used, reverse=True)
    return BudgetStatusResponse(period=period, items=items, overall_status=overall)


@router.post("/propose", response_model=BudgetProposal)
async def propose_budget(
    months_lookback: int = Query(3, ge=1, le=12),
    target_savings_rate: float = Query(0.20, ge=0, le=0.6),
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> BudgetProposal:
    end = datetime.utcnow()
    start = end - timedelta(days=30 * months_lookback)
    df = await load_txns(session, user_id, start, end)
    debits = df[df["is_debit"]] if not df.empty else df
    if debits.empty:
        return BudgetProposal(
            based_on_months=months_lookback,
            target_savings_rate=target_savings_rate,
            suggested=[],
        )

    monthly = debits.groupby("category")["abs_amount"].sum() / months_lookback
    # Apply a savings-rate haircut proportional to category share
    total = float(monthly.sum())
    target_total = total * (1 - target_savings_rate)
    scale = (target_total / total) if total else 1.0

    suggested = [
        BudgetItem(category=cat, monthly_limit=round(float(amt * scale), 2))
        for cat, amt in monthly.sort_values(ascending=False).items()
    ]
    return BudgetProposal(
        based_on_months=months_lookback,
        target_savings_rate=target_savings_rate,
        suggested=suggested,
    )
