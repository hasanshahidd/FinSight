"""Smoke tests against the FastAPI app - verifies routes wire up + return JSON."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_users(client):
    r = await client.get("/api/users")
    assert r.status_code == 200
    users = r.json()
    assert any(u["id"] == "user_1" for u in users)


@pytest.mark.asyncio
async def test_transactions(client):
    r = await client.get("/api/transactions?limit=5")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) <= 5


@pytest.mark.asyncio
async def test_categories(client):
    r = await client.get("/api/transactions/categories")
    assert r.status_code == 200
    cats = r.json()
    assert "Rent" in cats or len(cats) > 0


@pytest.mark.asyncio
async def test_recurring(client):
    r = await client.get("/api/transactions/recurring")
    assert r.status_code == 200
    body = r.json()
    assert "rules" in body


@pytest.mark.asyncio
async def test_anomalies(client):
    r = await client.get("/api/transactions/anomalies?period=last_90_days")
    assert r.status_code == 200
    body = r.json()
    assert "anomalies" in body


@pytest.mark.asyncio
async def test_summary(client):
    r = await client.get("/api/insights/summary?period=last_30_days")
    assert r.status_code == 200
    body = r.json()
    assert "total_spent" in body


@pytest.mark.asyncio
async def test_compare(client):
    r = await client.get("/api/insights/compare?period_a=this_week&period_b=last_week")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_forecast(client):
    r = await client.get("/api/insights/forecast?period=this_month")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_drift(client):
    r = await client.get("/api/insights/category-drift?window_days=60")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_budgets(client):
    r = await client.get("/api/budgets")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) > 0


@pytest.mark.asyncio
async def test_budget_status(client):
    r = await client.get("/api/budgets/status?period=this_month")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "overall_status" in body
