"""Seed the SQLite mock-banking database with demo data.

Usage:  python scripts/seed_db.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.seed import seed_demo_user
from app.db.session import SessionLocal, init_db


async def main() -> None:
    await init_db()
    async with SessionLocal() as session:
        await seed_demo_user(session)
    print("Seeded demo user 'user_1' with mock transactions.")


if __name__ == "__main__":
    asyncio.run(main())
