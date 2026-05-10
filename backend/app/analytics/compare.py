"""Side-by-side period comparison."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import load_txns, resolve_period


async def compare_periods(
    session: AsyncSession,
    user_id: str,
    period_a: str = "this_week",
    period_b: str = "last_week",
    by: str = "category",
) -> dict:
    a_start, a_end = resolve_period(period_a)
    if period_b == "last_week":
        # interpret as "the equal-length window immediately preceding A"
        span = a_end - a_start
        b_end = a_start
        b_start = b_end - span
    else:
        b_start, b_end = resolve_period(period_b)

    df_a = await load_txns(session, user_id, a_start, a_end)
    df_b = await load_txns(session, user_id, b_start, b_end)

    df_a_d = df_a[df_a["is_debit"]] if not df_a.empty else df_a
    df_b_d = df_b[df_b["is_debit"]] if not df_b.empty else df_b

    a_total = float(df_a_d["abs_amount"].sum()) if not df_a_d.empty else 0
    b_total = float(df_b_d["abs_amount"].sum()) if not df_b_d.empty else 0

    # By-group breakdown
    rows = []
    a_by = df_a_d.groupby(by)["abs_amount"].sum() if not df_a_d.empty else None
    b_by = df_b_d.groupby(by)["abs_amount"].sum() if not df_b_d.empty else None
    keys = set()
    if a_by is not None:
        keys.update(a_by.index)
    if b_by is not None:
        keys.update(b_by.index)
    for k in sorted(keys):
        a_v = float(a_by.get(k, 0)) if a_by is not None else 0
        b_v = float(b_by.get(k, 0)) if b_by is not None else 0
        delta = a_v - b_v
        pct = (delta / b_v * 100) if b_v else None
        rows.append({
            "key": str(k),
            "a_total": round(a_v, 2),
            "b_total": round(b_v, 2),
            "abs_delta": round(delta, 2),
            "pct_delta": round(pct, 2) if pct is not None else None,
        })

    rows.sort(key=lambda r: abs(r["abs_delta"]), reverse=True)

    grand_pct = ((a_total - b_total) / b_total * 100) if b_total else None
    return {
        "_summary": (
            f"{period_a}: ${a_total:,.2f} vs {period_b}: ${b_total:,.2f} - "
            f"{'+' if (grand_pct or 0) >= 0 else ''}{grand_pct:.1f}%"
            if grand_pct is not None
            else f"{period_a}: ${a_total:,.2f}; no comparable prior window"
        ),
        "period_a": period_a,
        "period_b": period_b,
        "a_total": round(a_total, 2),
        "b_total": round(b_total, 2),
        "abs_delta": round(a_total - b_total, 2),
        "pct_delta": round(grand_pct, 2) if grand_pct is not None else None,
        "by": by,
        "breakdown": rows,
    }
