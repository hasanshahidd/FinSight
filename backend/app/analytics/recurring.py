"""Auto-detected recurring charges. Reads from RecurringRule (pre-computed at seed
time) and the live transactions to refresh/adjust."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RecurringRule


async def get_recurring_transactions(
    session: AsyncSession,
    user_id: str,
    min_confidence: float = 0.6,
) -> dict:
    q = (
        select(RecurringRule)
        .where(RecurringRule.user_id == user_id)
        .where(RecurringRule.confidence >= min_confidence)
        .order_by(RecurringRule.typical_amount.desc())
    )
    rules = (await session.execute(q)).scalars().all()

    rows = [
        {
            "merchant": r.merchant,
            "category": r.category,
            "typical_amount": round(r.typical_amount, 2),
            "cadence_days": r.cadence_days,
            "occurrences": r.occurrence_count,
            "last_seen_at": r.last_seen_at.isoformat(),
            "confidence": round(r.confidence, 2),
            "monthly_estimate": round(r.typical_amount * (30 / r.cadence_days), 2),
        }
        for r in rules
    ]
    monthly_total = sum(r["monthly_estimate"] for r in rows)

    return {
        "_summary": (
            f"{len(rows)} recurring charge(s) identified - about ${monthly_total:,.2f}/month"
            if rows else "No recurring charges detected."
        ),
        "count": len(rows),
        "monthly_estimated_total": round(monthly_total, 2),
        "rules": rows,
    }
