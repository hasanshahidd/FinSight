"""Category drift: which categories grew/shrank most over a window vs prior window."""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import load_txns


async def analyze_category_drift(
    session: AsyncSession,
    user_id: str,
    window_days: int = 90,
) -> dict:
    end = datetime.utcnow()
    cur_start = end - timedelta(days=window_days)
    prev_start = cur_start - timedelta(days=window_days)

    df_cur = await load_txns(session, user_id, cur_start, end)
    df_prev = await load_txns(session, user_id, prev_start, cur_start)

    cur_d = df_cur[df_cur["is_debit"]] if not df_cur.empty else df_cur
    prev_d = df_prev[df_prev["is_debit"]] if not df_prev.empty else df_prev

    cur_by = cur_d.groupby("category")["abs_amount"].sum() if not cur_d.empty else None
    prev_by = prev_d.groupby("category")["abs_amount"].sum() if not prev_d.empty else None

    keys = set()
    if cur_by is not None:
        keys.update(cur_by.index)
    if prev_by is not None:
        keys.update(prev_by.index)

    out = []
    for k in keys:
        c = float(cur_by.get(k, 0)) if cur_by is not None else 0
        p = float(prev_by.get(k, 0)) if prev_by is not None else 0
        delta = c - p
        pct = (delta / p * 100) if p else None
        out.append({
            "category": k,
            "current": round(c, 2),
            "prior": round(p, 2),
            "abs_delta": round(delta, 2),
            "pct_delta": round(pct, 2) if pct is not None else None,
            "direction": "up" if delta > 0 else ("down" if delta < 0 else "flat"),
        })

    out.sort(key=lambda r: abs(r["abs_delta"]), reverse=True)

    top = out[0] if out else None
    summary = (
        f"Biggest drift over last {window_days}d: {top['category']} "
        f"({'+' if top['abs_delta'] >= 0 else ''}${top['abs_delta']:,.2f}"
        + (f", {top['pct_delta']:+.1f}%" if top["pct_delta"] is not None else "")
        + ")"
        if top
        else "No drift to report."
    )

    return {
        "_summary": summary,
        "window_days": window_days,
        "categories": out,
    }
