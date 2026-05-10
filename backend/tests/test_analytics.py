"""Smoke tests for the analytics module.

These don't assert exact numbers — the seeded data has known shape, but the
goal is structural correctness (right keys, no exceptions, sane numbers)."""

import pytest

from app.analytics.anomaly import find_unusual_transactions
from app.analytics.compare import compare_periods
from app.analytics.drift import analyze_category_drift
from app.analytics.forecast import forecast_spending
from app.analytics.recurring import get_recurring_transactions
from app.analytics.summary import compute_summary
from app.analytics.trend import compute_trend
from app.db.session import SessionLocal


@pytest.mark.asyncio
async def test_summary(demo_user_id):
    async with SessionLocal() as s:
        out = await compute_summary(s, demo_user_id, period="last_30_days")
    assert "total_spent" in out and out["total_spent"] >= 0
    assert isinstance(out["top_categories"], list)
    assert "_summary" in out


@pytest.mark.asyncio
async def test_trend(demo_user_id):
    async with SessionLocal() as s:
        out = await compute_trend(s, demo_user_id, period="last_30_days")
    assert "points" in out and isinstance(out["points"], list)
    assert "pct_change_vs_previous" in out


@pytest.mark.asyncio
async def test_compare(demo_user_id):
    async with SessionLocal() as s:
        out = await compare_periods(s, demo_user_id, period_a="this_week", period_b="last_week")
    assert "a_total" in out and "b_total" in out
    assert isinstance(out["breakdown"], list)


@pytest.mark.asyncio
async def test_forecast(demo_user_id):
    async with SessionLocal() as s:
        out = await forecast_spending(s, demo_user_id, period="this_month")
    assert "projected_total" in out
    assert isinstance(out["by_category"], list)


@pytest.mark.asyncio
async def test_drift(demo_user_id):
    async with SessionLocal() as s:
        out = await analyze_category_drift(s, demo_user_id, window_days=60)
    assert "categories" in out and isinstance(out["categories"], list)


@pytest.mark.asyncio
async def test_anomalies(demo_user_id):
    async with SessionLocal() as s:
        out = await find_unusual_transactions(s, demo_user_id, period="last_90_days", z_threshold=2.0)
    assert "anomalies" in out and isinstance(out["anomalies"], list)


@pytest.mark.asyncio
async def test_recurring(demo_user_id):
    async with SessionLocal() as s:
        out = await get_recurring_transactions(s, demo_user_id)
    assert "rules" in out and isinstance(out["rules"], list)
    # The data generator pre-detects, so we expect SOME recurring rules:
    assert out["count"] > 0
