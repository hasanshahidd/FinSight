"""Per-category z-score anomaly detection over a baseline window."""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import load_txns


async def find_unusual_transactions(
    session: AsyncSession,
    user_id: str,
    period: str = "last_30_days",
    z_threshold: float = 2.5,
    baseline_days: int = 180,
) -> dict:
    """Compare each transaction in `period` to its category's baseline distribution.

    Baseline = `baseline_days` of history (default 180). A transaction is flagged
    when |z| >= z_threshold against that distribution.
    """
    end = datetime.utcnow()
    if period == "last_7_days":
        start = end - timedelta(days=7)
    elif period == "last_14_days":
        start = end - timedelta(days=14)
    elif period == "last_30_days":
        start = end - timedelta(days=30)
    elif period == "last_90_days":
        start = end - timedelta(days=90)
    else:
        start = end - timedelta(days=30)

    base_start = end - timedelta(days=baseline_days)

    df_baseline = await load_txns(session, user_id, base_start, end)
    df_baseline = df_baseline[df_baseline["is_debit"]] if not df_baseline.empty else df_baseline

    if df_baseline.empty:
        return {"_summary": "Not enough history.", "period": period, "anomalies": []}

    stats = (
        df_baseline.groupby("category")["abs_amount"]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    stats_map = {row["category"]: (row["mean"], row["std"] or 1.0, row["count"]) for _, row in stats.iterrows()}

    df_window = df_baseline[(df_baseline["timestamp"] >= start) & (df_baseline["timestamp"] <= end)]

    anomalies = []
    for _, t in df_window.iterrows():
        if t["category"] not in stats_map:
            continue
        mu, sd, n = stats_map[t["category"]]
        if n < 5:  # not enough baseline
            continue
        z = (t["abs_amount"] - mu) / sd if sd else 0
        if abs(z) >= z_threshold:
            anomalies.append({
                "id": t["id"],
                "timestamp": t["timestamp"].isoformat(),
                "merchant": t["merchant"],
                "category": t["category"],
                "amount": round(float(t["amount"]), 2),
                "z_score": round(float(z), 2),
                "category_mean": round(float(mu), 2),
                "category_std": round(float(sd), 2),
                "reason": (
                    f"{abs(z):.1f}σ above {t['category']} mean of ${mu:,.2f}"
                ),
            })

    anomalies.sort(key=lambda a: abs(a["z_score"]), reverse=True)

    return {
        "_summary": (
            f"Found {len(anomalies)} unusual transaction(s) in {period}"
            + (f"; biggest: {anomalies[0]['merchant']} (${abs(anomalies[0]['amount']):,.2f}, z={anomalies[0]['z_score']:.1f})"
               if anomalies else "")
        ),
        "period": period,
        "z_threshold": z_threshold,
        "baseline_days": baseline_days,
        "anomalies": anomalies[:25],
    }
