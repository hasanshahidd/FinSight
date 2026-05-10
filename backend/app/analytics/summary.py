"""Spending summary: totals, top categories, transaction count."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import load_txns, resolve_period


async def compute_summary(session: AsyncSession, user_id: str, period: str = "last_7_days") -> dict:
    start, end = resolve_period(period)
    df = await load_txns(session, user_id, start, end)

    if df.empty:
        return {
            "_summary": f"No transactions in {period}.",
            "period": period,
            "start_date": start.date().isoformat(),
            "end_date": end.date().isoformat(),
            "total_spent": 0.0,
            "total_income": 0.0,
            "net": 0.0,
            "top_categories": [],
            "transaction_count": 0,
        }

    debits = df[df["is_debit"]]
    credits = df[~df["is_debit"]]

    total_spent = float(debits["abs_amount"].sum())
    total_income = float(credits["amount"].sum())

    by_cat = (
        debits.groupby("category")["abs_amount"]
        .agg(["sum", "count"])
        .sort_values("sum", ascending=False)
    )
    top = []
    for cat, row in by_cat.iterrows():
        pct = (row["sum"] / total_spent * 100) if total_spent else 0
        top.append({
            "category": cat,
            "total": round(float(row["sum"]), 2),
            "transaction_count": int(row["count"]),
            "pct_of_total": round(float(pct), 2),
        })

    return {
        "_summary": (
            f"In {period}, spent ${total_spent:,.2f} across {len(df)} txns; "
            f"top: {top[0]['category']} (${top[0]['total']:,.2f})" if top else
            f"In {period}, no spending recorded."
        ),
        "period": period,
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "total_spent": round(total_spent, 2),
        "total_income": round(total_income, 2),
        "net": round(total_income - total_spent, 2),
        "top_categories": top[:5],
        "transaction_count": int(len(df)),
    }
