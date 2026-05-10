"""Daily spending timeseries with WoW/MoM-style delta vs prior window."""

from datetime import timedelta

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import load_txns, resolve_period


async def compute_trend(session: AsyncSession, user_id: str, period: str = "last_30_days") -> dict:
    start, end = resolve_period(period)
    span = end - start
    prev_start, prev_end = start - span, start

    df_cur = await load_txns(session, user_id, start, end)
    df_prev = await load_txns(session, user_id, prev_start, prev_end)

    points = []
    if not df_cur.empty:
        df_cur = df_cur.copy()
        df_cur["day"] = df_cur["timestamp"].dt.floor("D")
        agg = df_cur.groupby("day").apply(
            lambda g: pd.Series({
                "spent": g.loc[g["is_debit"], "abs_amount"].sum(),
                "income": g.loc[~g["is_debit"], "amount"].sum(),
            })
        )
        # Reindex to fill missing days
        all_days = pd.date_range(start.date(), end.date(), freq="D")
        agg = agg.reindex(all_days, fill_value=0)
        for day, row in agg.iterrows():
            points.append({
                "label": day.date().isoformat(),
                "spent": round(float(row["spent"]), 2),
                "income": round(float(row["income"]), 2),
            })

    cur_total = float(df_cur.loc[df_cur["is_debit"], "abs_amount"].sum()) if not df_cur.empty else 0
    prev_total = float(df_prev.loc[df_prev["is_debit"], "abs_amount"].sum()) if not df_prev.empty else 0
    pct_change = ((cur_total - prev_total) / prev_total * 100) if prev_total else None

    return {
        "_summary": (
            f"Spent ${cur_total:,.2f} in {period}; "
            f"{'+' if (pct_change or 0) >= 0 else ''}{pct_change:.1f}% vs prior {span.days} days"
            if pct_change is not None
            else f"Spent ${cur_total:,.2f} in {period}; no comparable prior window"
        ),
        "period": period,
        "points": points,
        "total_spent": round(cur_total, 2),
        "prev_total_spent": round(prev_total, 2),
        "pct_change_vs_previous": round(pct_change, 2) if pct_change is not None else None,
    }
