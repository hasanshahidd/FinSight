"""Pytest configuration: spin up an in-memory SQLite seeded with one persona."""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Ensure the backend dir is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Use a separate in-memory-ish test DB
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/finsight_test.db")
os.environ.setdefault("CHROMA_PERSIST_DIR", "./chroma_db_test")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def _seed_test_db():
    """Initialize and seed the test DB with personas."""
    from app.db.session import SessionLocal, init_db
    from app.db.seed import seed_all

    async def _bootstrap():
        await init_db()
        async with SessionLocal() as session:
            await seed_all(session)

    asyncio.get_event_loop().run_until_complete(_bootstrap())
    yield
    # Teardown left to manual cleanup; test DB is small.


@pytest.fixture
def demo_user_id() -> str:
    return "user_1"
