"""LangChain tool catalog (13 tools) — the only knobs available to the agent.

Categories:
  Transactions:  get_transactions, search_transactions_semantic,
                 get_recurring_transactions, find_unusual_transactions
  Insights:      get_spending_summary, get_spending_trend, compare_periods,
                 forecast_spending, analyze_category_drift
  Knowledge:     search_financial_knowledge
  Budgets:       get_budgets, evaluate_budget_status, propose_budget

Caching is intentionally NOT applied as a decorator over @tool — wrapping
LangChain's @tool with another decorator risks introspection regressions.
Where caching pays off (e.g. RAG retrieval), it is added inside the tool
body via app.core.cache.
"""

from datetime import datetime
from typing import Annotated

from langchain_core.tools import tool
from sqlalchemy import and_, select

from app.analytics.compare import compare_periods as _compare_periods
from app.analytics.drift import analyze_category_drift as _analyze_drift
from app.analytics.forecast import forecast_spending as _forecast_spending
from app.analytics.recurring import get_recurring_transactions as _get_recurring
from app.analytics.summary import compute_summary as _compute_summary
from app.analytics.trend import compute_trend as _compute_trend
from app.analytics.anomaly import find_unusual_transactions as _find_unusual
from app.db.models import Budget, Transaction
from app.db.session import SessionLocal
from app.rag.retriever import retrieve as _rag_retrieve
from app.rag.transaction_index import semantic_search_transactions as _semantic_txn_search


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@tool
async def get_transactions(
    date_from: Annotated[str | None, "ISO date YYYY-MM-DD; inclusive lower bound"] = None,
    date_to: Annotated[str | None, "ISO date YYYY-MM-DD; inclusive upper bound"] = None,
    category: Annotated[str | None, "Category name e.g. Groceries, Dining"] = None,
    merchant: Annotated[str | None, "Substring filter on merchant name"] = None,
    limit: Annotated[int, "Max rows"] = 50,
    user_id: Annotated[str, "User id"] = "user_1",
) -> dict:
    """List the user's transactions filtered by date/category/merchant. Use for
    direct factual queries about spending."""
    df_dt = datetime.fromisoformat(date_from) if date_from else None
    dt_dt = datetime.fromisoformat(date_to) if date_to else None
    filters = [Transaction.user_id == user_id]
    if df_dt:
        filters.append(Transaction.timestamp >= df_dt)
    if dt_dt:
        filters.append(Transaction.timestamp <= dt_dt)
    if category:
        filters.append(Transaction.category == category)
    if merchant:
        filters.append(Transaction.merchant.ilike(f"%{merchant}%"))

    async with SessionLocal() as session:
        q = select(Transaction).where(and_(*filters)).order_by(Transaction.timestamp.desc()).limit(limit)
        rows = (await session.execute(q)).scalars().all()

    total = sum(-r.amount for r in rows if r.amount < 0)
    return {
        "_summary": (
            f"{len(rows)} txns"
            + (f" in {category}" if category else "")
            + (f" matching '{merchant}'" if merchant else "")
            + (f" — ${total:,.2f} debit total" if total else "")
        ),
        "count": len(rows),
        "transactions": [
            {
                "id": r.id, "amount": r.amount, "category": r.category,
                "subcategory": r.subcategory, "merchant": r.merchant,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in rows
        ],
    }


@tool
async def search_transactions_semantic(
    query: Annotated[str, "Natural-language description of what to find, e.g. 'coffee runs'"],
    k: Annotated[int, "Number of matches to return"] = 20,
    user_id: Annotated[str, "User id"] = "user_1",
) -> dict:
    """Semantic search over the user's transactions. Use when category/merchant
    filtering won't work — e.g. fuzzy concepts ('coffee', 'late-night spending')."""
    async with SessionLocal() as session:
        return await _semantic_txn_search(session, user_id, query, k=k)


@tool
async def get_recurring_transactions(
    user_id: Annotated[str, "User id"] = "user_1",
) -> dict:
    """List auto-detected recurring charges (subscriptions, rent, payroll).
    Use for 'what subscriptions do I have' or to find recurring drains."""
    async with SessionLocal() as session:
        return await _get_recurring(session, user_id)


@tool
async def find_unusual_transactions(
    period: Annotated[str, "last_7_days | last_14_days | last_30_days | last_90_days"] = "last_30_days",
    z_threshold: Annotated[float, "z-score cutoff; higher = more conservative"] = 2.5,
    user_id: Annotated[str, "User id"] = "user_1",
) -> dict:
    """Detect statistically unusual transactions (per-category z-score against
    a 180-day baseline). Use for 'is anything weird in my spending?'."""
    async with SessionLocal() as session:
        return await _find_unusual(session, user_id, period=period, z_threshold=z_threshold)


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------

@tool
async def get_spending_summary(
    period: Annotated[str, "this_week | this_month | last_7_days | last_30_days | last_90_days"] = "last_7_days",
    user_id: Annotated[str, "User id"] = "user_1",
) -> dict:
    """Total spent, total income, top categories for a period."""
    async with SessionLocal() as session:
        return await _compute_summary(session, user_id, period)


@tool
async def get_spending_trend(
    period: Annotated[str, "last_7_days | last_30_days | last_90_days"] = "last_30_days",
    user_id: Annotated[str, "User id"] = "user_1",
) -> dict:
    """Daily timeseries with % change vs prior equal-length window."""
    async with SessionLocal() as session:
        return await _compute_trend(session, user_id, period)


@tool
async def compare_periods(
    period_a: Annotated[str, "First period label"] = "this_week",
    period_b: Annotated[str, "Second period label or 'last_week' for the equal window before A"] = "last_week",
    by: Annotated[str, "Group key: 'category' or 'merchant'"] = "category",
    user_id: Annotated[str, "User id"] = "user_1",
) -> dict:
    """Side-by-side breakdown of two periods with deltas + percent changes."""
    async with SessionLocal() as session:
        return await _compare_periods(session, user_id, period_a, period_b, by)


@tool
async def forecast_spending(
    period: Annotated[str, "Forecast horizon: this_month | this_week"] = "this_month",
    method: Annotated[str, "linear | rolling_mean"] = "linear",
    user_id: Annotated[str, "User id"] = "user_1",
) -> dict:
    """Project end-of-period spend per category from current pace."""
    async with SessionLocal() as session:
        return await _forecast_spending(session, user_id, period, method)


@tool
async def analyze_category_drift(
    window_days: Annotated[int, "Window length (days). Compares to the same prior length."] = 90,
    user_id: Annotated[str, "User id"] = "user_1",
) -> dict:
    """Which categories grew/shrank most over the window vs prior."""
    async with SessionLocal() as session:
        return await _analyze_drift(session, user_id, window_days)


# ---------------------------------------------------------------------------
# Knowledge
# ---------------------------------------------------------------------------

@tool
async def search_financial_knowledge(
    query: Annotated[str, "The question or topic to search the knowledge base for"],
    k: Annotated[int, "Number of grounded chunks to return"] = 4,
) -> dict:
    """Hybrid retrieval (dense + BM25 + cross-encoder rerank) over the financial
    literacy corpus. Use for definitions, frameworks, advice, strategies. Always
    cite the `source` field of each chunk in your answer."""
    chunks = _rag_retrieve(query, k=k, use_reranker=True)
    return {
        "_summary": (
            f"Top {len(chunks)} chunks from sources: "
            + ", ".join(sorted({c["source"] for c in chunks}))
        ) if chunks else "No relevant knowledge-base chunks found.",
        "chunks": chunks,
    }


# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------

@tool
async def get_budgets(
    user_id: Annotated[str, "User id"] = "user_1",
) -> dict:
    """The user's category-level monthly budget targets."""
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Budget).where(Budget.user_id == user_id).order_by(Budget.monthly_limit.desc())
            )
        ).scalars().all()
    items = [{"category": r.category, "monthly_limit": r.monthly_limit} for r in rows]
    total = sum(i["monthly_limit"] for i in items)
    return {
        "_summary": f"{len(items)} budget categories — total ${total:,.2f}/mo",
        "items": items,
        "total_monthly": round(total, 2),
    }


@tool
async def evaluate_budget_status(
    period: Annotated[str, "this_month | this_week"] = "this_month",
    user_id: Annotated[str, "User id"] = "user_1",
) -> dict:
    """Per-category budget status with projected end-of-period spend.
    Returns each category as under | on_track | warning | over."""
    async with SessionLocal() as session:
        budgets = {
            b.category: b.monthly_limit
            for b in (await session.execute(select(Budget).where(Budget.user_id == user_id))).scalars()
        }
        if not budgets:
            return {"_summary": "No budgets set.", "items": [], "overall_status": "under"}
        forecast = await _forecast_spending(session, user_id, period=period)

    by_cat = {row["category"]: row for row in forecast["by_category"]}
    items = []
    over_count = warn_count = 0
    for cat, limit in budgets.items():
        row = by_cat.get(cat, {"actual_so_far": 0.0, "projected_eom": 0.0})
        actual = float(row["actual_so_far"])
        projected = float(row["projected_eom"])
        pct = (projected / limit * 100) if limit else 0
        if pct >= 100:
            status = "over"; over_count += 1
        elif pct >= 90:
            status = "warning"; warn_count += 1
        elif pct >= 50:
            status = "on_track"
        else:
            status = "under"
        items.append({
            "category": cat, "monthly_limit": limit,
            "actual": round(actual, 2), "projected_eom": round(projected, 2),
            "status": status, "pct_used": round(pct, 1),
        })
    items.sort(key=lambda i: i["pct_used"], reverse=True)
    overall = "over" if over_count else ("warning" if warn_count else "on_track")
    return {
        "_summary": (
            f"{over_count} over budget, {warn_count} warning"
            f" (overall: {overall})" if (over_count or warn_count)
            else f"All {len(items)} categories tracking under budget"
        ),
        "period": period,
        "items": items,
        "overall_status": overall,
    }


@tool
async def propose_budget(
    months_lookback: Annotated[int, "Months of history to base proposal on"] = 3,
    target_savings_rate: Annotated[float, "Target savings rate (0.0–0.6)"] = 0.20,
    user_id: Annotated[str, "User id"] = "user_1",
) -> dict:
    """Generate a proposed budget from the user's recent spend pattern that
    targets a given savings rate. Returns category limits."""
    from datetime import timedelta
    from app.analytics.common import load_txns

    end = datetime.utcnow()
    start = end - timedelta(days=30 * months_lookback)
    async with SessionLocal() as session:
        df = await load_txns(session, user_id, start, end)
    debits = df[df["is_debit"]] if not df.empty else df
    if debits.empty:
        return {"_summary": "Not enough history to propose.", "suggested": []}

    monthly = debits.groupby("category")["abs_amount"].sum() / months_lookback
    total = float(monthly.sum())
    target_total = total * (1 - target_savings_rate)
    scale = (target_total / total) if total else 1.0
    suggested = [
        {"category": cat, "monthly_limit": round(float(amt * scale), 2)}
        for cat, amt in monthly.sort_values(ascending=False).items()
    ]
    return {
        "_summary": (
            f"Proposed {len(suggested)} budgets totaling "
            f"${target_total:,.2f}/mo (savings rate {target_savings_rate*100:.0f}%)"
        ),
        "based_on_months": months_lookback,
        "target_savings_rate": target_savings_rate,
        "suggested": suggested,
    }


# ---------------------------------------------------------------------------
# Tool subsets per specialist
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    get_transactions, search_transactions_semantic, get_recurring_transactions,
    find_unusual_transactions, get_spending_summary, get_spending_trend,
    compare_periods, forecast_spending, analyze_category_drift,
    search_financial_knowledge, get_budgets, evaluate_budget_status, propose_budget,
]

TRANSACTION_ANALYST_TOOLS = [
    get_transactions, search_transactions_semantic, get_recurring_transactions,
    get_spending_summary, get_spending_trend, compare_periods, analyze_category_drift,
]

KNOWLEDGE_ADVISOR_TOOLS = [search_financial_knowledge]

BUDGET_COACH_TOOLS = [
    get_spending_summary, get_budgets, evaluate_budget_status, propose_budget,
    forecast_spending, search_financial_knowledge,
]

ANOMALY_DETECTIVE_TOOLS = [
    find_unusual_transactions, get_recurring_transactions, get_transactions,
    analyze_category_drift,
]
