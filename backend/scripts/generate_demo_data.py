"""Generate the full demo dataset: 5 personas × 240 days × stories.

Usage:  python scripts/generate_demo_data.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.seed import seed_all
from app.db.session import SessionLocal, init_db


async def main() -> None:
    await init_db()
    async with SessionLocal() as session:
        results = await seed_all(session)
    total_txns = sum(r["transactions"] for r in results)
    print("=" * 64)
    print(f"Seeded {len(results)} personas, {total_txns} transactions total")
    print("=" * 64)
    for r in results:
        print(
            f"  {r['user']:<8}  txns={r['transactions']:>4}  "
            f"accts={r['accounts']}  budgets={r['budgets']}  "
            f"recurring={r['recurring_rules']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
