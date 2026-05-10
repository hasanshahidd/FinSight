"""End-of-month spending projection per category."""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import load_txns, resolve_period


async def forecast_spending(
    session: AsyncSession,
    user_id: str,
    period: str = "this_month",
    method: str = "linear",
) -> dict:
    start, end = resolve_period(period)
    df = await load_txns(session, user_id, start, end)

    # Determine total period span (this_month → calendar month)
    if period == "this_month":
        # span to end of this month
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        period_end = next_month - timedelta(seconds=1)
    elif period == "this_week":
        period_end = start + timedelta(days=6, hours=23, minutes=59)
    else:
        period_end = end  # cannot meaningfully forecast non-bounded periods

    elapsed_days = (datetime.utcnow() - start).days or 1
    total_days = (period_end - start).days or 1
    progress = min(1.0, elapsed_days / total_days)

    if df.empty:
        return {
            "_summary": "Not enough data to forecast.",
            "period": period,
            "method": method,
            "elapsed_days": elapsed_days,
            "total_days": total_days,
            "progress": round(progress, 3),
            "by_category": [],
            "projected_total": 0.0,
            "actual_so_far": 0.0,
        }

    debits = df[df["is_debit"]]
    by_cat = debits.groupby("category")["abs_amount"].agg(["sum", "count"]).reset_index()

    out = []
    for _, row in by_cat.iterrows():
        actual = float(row["sum"])
        if method == "linear" and progress > 0:
            projected = actual / progress
        else:
            projected = actual  # no extrapolation
        out.append({
            "category": row["category"],
            "actual_so_far": round(actual, 2),
            "projected_eom": round(projected, 2),
            "transaction_count": int(row["count"]),
        })

    out.sort(key=lambda r: r["projected_eom"], reverse=True)

    actual_total = float(debits["abs_amount"].sum())
    projected_total = actual_total / progress if progress > 0 else actual_total

    return {
        "_summary": (
            f"At {progress*100:.0f}% through {period}: "
            f"${actual_total:,.2f} actual, projected ${projected_total:,.2f} by period end"
        ),
        "period": period,
        "method": method,
        "elapsed_days": elapsed_days,
        "total_days": total_days,
        "progress": round(progress, 3),
        "by_category": out,
        "actual_so_far": round(actual_total, 2),
        "projected_total": round(projected_total, 2),
    }
