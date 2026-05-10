"""Mock-banking endpoints: list, search, recurring, anomalies."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.anomaly import find_unusual_transactions
from app.analytics.recurring import get_recurring_transactions
from app.core.security import current_user
from app.db.models import Transaction
from app.db.session import get_session
from app.schemas.transaction import TransactionOut, TransactionSearchRequest

router = APIRouter()


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    user_id: str = Depends(current_user),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    category: str | None = Query(None),
    subcategory: str | None = Query(None),
    merchant: str | None = Query(None),
    min_amount: float | None = Query(None),
    max_amount: float | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> list[TransactionOut]:
    filters = [Transaction.user_id == user_id]
    if date_from:
        filters.append(Transaction.timestamp >= date_from)
    if date_to:
        filters.append(Transaction.timestamp <= date_to)
    if category:
        filters.append(Transaction.category == category)
    if subcategory:
        filters.append(Transaction.subcategory == subcategory)
    if merchant:
        filters.append(Transaction.merchant.ilike(f"%{merchant}%"))
    if min_amount is not None:
        filters.append(Transaction.amount >= min_amount)
    if max_amount is not None:
        filters.append(Transaction.amount <= max_amount)

    q = (
        select(Transaction)
        .where(and_(*filters))
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
    )
    rows = (await session.execute(q)).scalars().all()
    return [TransactionOut.model_validate(r) for r in rows]


@router.get("/categories", response_model=list[str])
async def list_categories(
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    q = select(Transaction.category).where(Transaction.user_id == user_id).distinct()
    rows = (await session.execute(q)).scalars().all()
    return sorted(rows)


@router.get("/recurring")
async def recurring(
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await get_recurring_transactions(session, user_id)


@router.get("/anomalies")
async def anomalies(
    period: str = Query("last_30_days"),
    z_threshold: float = Query(2.5, ge=1.0, le=5.0),
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await find_unusual_transactions(session, user_id, period=period, z_threshold=z_threshold)


@router.post("/search")
async def search(
    body: TransactionSearchRequest,
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Semantic search over merchant + description."""
    from app.rag.transaction_index import semantic_search_transactions
    return await semantic_search_transactions(session, user_id, body.query, k=body.k)
