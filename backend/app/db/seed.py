"""Deterministic data generator: 5 personas × 240 days × baked-in stories.

The output of this module:
  - User rows (one per persona)
  - Account rows (3 accounts per user, typically)
  - Transaction rows (~2,400 total across all personas)
  - Budget rows (one per category per user)
  - RecurringRule rows (auto-detected after generation)

All timestamps are deterministic from `persona.rng_seed`. Re-running drops
existing rows for that user_id and rewrites them.
"""

from __future__ import annotations

import random
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median, pstdev

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Budget, RecurringRule, Transaction, User
from app.db.personas import (
    PERSONAS,
    Persona,
    SubscriptionSpec,
)

DATASET_DAYS = 240


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


@dataclass
class _GeneratedTxn:
    timestamp: datetime
    account_id: str
    amount: float
    category: str
    subcategory: str
    merchant: str
    description: str
    is_recurring: bool = False


def _now_truncated() -> datetime:
    n = datetime.utcnow()
    return n.replace(hour=0, minute=0, second=0, microsecond=0)


def _account_for(persona: Persona, kind: str, accounts: dict[str, Account]) -> Account:
    """Pick an account for a transaction kind. Convention:
    rent/utils/subscriptions on checking; income on checking; everyday on credit
    if available (else checking); savings only for transfers."""
    if kind == "income":
        return accounts["checking"]
    if kind in ("rent", "utilities", "subscription"):
        return accounts["checking"]
    if kind == "transfer_savings":
        return accounts["savings"]
    return accounts.get("credit") or accounts["checking"]


def _generate_persona_txns(persona: Persona, accounts: dict[str, Account]) -> list[_GeneratedTxn]:
    rng = random.Random(persona.rng_seed)
    now = _now_truncated()
    start = now - timedelta(days=DATASET_DAYS)
    rows: list[_GeneratedTxn] = []

    # 1) Income - bi-weekly (or as configured)
    for income in persona.incomes:
        if income.amount <= 0:
            continue
        d = start + timedelta(days=income.cadence_days // 2)  # offset first paycheck
        while d <= now:
            rows.append(_GeneratedTxn(
                timestamp=d.replace(hour=8),
                account_id=accounts["checking"].id,
                amount=income.amount,
                category="Income",
                subcategory="payroll",
                merchant=income.merchant,
                description=f"Direct deposit - {income.merchant}",
                is_recurring=True,
            ))
            d += timedelta(days=income.cadence_days)

    # 2) Rent - monthly
    if persona.rent_amount > 0:
        d = start.replace(day=min(persona.rent_day_of_month, 28))
        if d < start:
            d = (d + timedelta(days=32)).replace(day=min(persona.rent_day_of_month, 28))
        while d <= now:
            rows.append(_GeneratedTxn(
                timestamp=d.replace(hour=9),
                account_id=accounts["checking"].id,
                amount=-persona.rent_amount,
                category="Rent",
                subcategory="housing",
                merchant="Landlord ACH",
                description="Monthly rent",
                is_recurring=True,
            ))
            d = (d + timedelta(days=32)).replace(day=min(persona.rent_day_of_month, 28))

    # 3) Subscriptions - recurring monthly with optional start offsets
    for sub in persona.subscriptions:
        sub_start = start + timedelta(days=max(sub.starts_offset_days, 0))
        if sub.starts_offset_days < 0:
            # the offset is relative-to-now; but since start_offset_days < 0 typically
            # means "started before dataset", we shift to dataset start
            sub_start = start
        # offset for subscription_creep: start later in dataset
        if sub.starts_offset_days > 0:
            sub_start = start + timedelta(days=sub.starts_offset_days)
        elif sub.starts_offset_days < 0 and abs(sub.starts_offset_days) < DATASET_DAYS:
            # subscription started after dataset start - splice in mid-dataset
            sub_start = now + timedelta(days=sub.starts_offset_days)
            if sub_start < start:
                sub_start = start
        d = sub_start.replace(day=min(sub.day_of_month, 28))
        if d < sub_start:
            d = (d + timedelta(days=32)).replace(day=min(sub.day_of_month, 28))
        end_at = sub.ends_offset_days and (now + timedelta(days=sub.ends_offset_days)) or now
        while d <= end_at:
            rows.append(_GeneratedTxn(
                timestamp=d.replace(hour=11),
                account_id=accounts["checking"].id,
                amount=-sub.amount,
                category=sub.category,
                subcategory="recurring",
                merchant=sub.merchant,
                description=f"{sub.merchant} subscription",
                is_recurring=True,
            ))
            d = (d + timedelta(days=32)).replace(day=min(sub.day_of_month, 28))

    # 4) Utilities - twice-monthly variable
    if "Utilities" in persona.merchants_by_category:
        for day_in_month in (10, 25):
            d = start.replace(day=min(day_in_month, 28))
            if d < start:
                d = (d + timedelta(days=32)).replace(day=min(day_in_month, 28))
            while d <= now:
                ms = persona.merchants_by_category["Utilities"]
                m = ms[rng.randint(0, len(ms) - 1)]
                amt = -round(rng.uniform(m.amount_min, m.amount_max), 2)
                rows.append(_GeneratedTxn(
                    timestamp=d.replace(hour=10),
                    account_id=accounts["checking"].id,
                    amount=amt,
                    category="Utilities",
                    subcategory=m.subcategory,
                    merchant=m.name,
                    description=f"{m.name}",
                    is_recurring=True,
                ))
                d = (d + timedelta(days=32)).replace(day=min(day_in_month, 28))

    # 5) Daily discretionary spending - drawn from category weights
    cat_pool: list[str] = []
    for cat, w in persona.category_weights.items():
        cat_pool.extend([cat] * w)

    for day in range(DATASET_DAYS, 0, -1):
        d = now - timedelta(days=day)
        n_today = rng.choices([0, 1, 2, 3, 4], weights=[1, 3, 4, 3, 1])[0]
        for _ in range(n_today):
            cat = rng.choice(cat_pool)
            ms = persona.merchants_by_category.get(cat)
            if not ms:
                continue
            m = ms[rng.randint(0, len(ms) - 1)]
            amt = -round(rng.uniform(m.amount_min, m.amount_max), 2)
            ts = d.replace(hour=rng.randint(7, 21), minute=rng.randint(0, 59))
            rows.append(_GeneratedTxn(
                timestamp=ts,
                account_id=_account_for(persona, "spend", accounts).id,
                amount=amt,
                category=cat,
                subcategory=m.subcategory,
                merchant=m.name,
                description=f"{m.name}",
            ))

    # 6) Apply story injectors
    rows = _apply_stories(persona, rows, accounts, start, now, rng)

    return rows


# ---------------------------------------------------------------------------
# Story injectors
# ---------------------------------------------------------------------------


def _apply_stories(
    persona: Persona,
    rows: list[_GeneratedTxn],
    accounts: dict[str, Account],
    start: datetime,
    now: datetime,
    rng: random.Random,
) -> list[_GeneratedTxn]:
    for story in persona.stories:
        if story.kind == "subscription_creep":
            # Already encoded via SubscriptionSpec.starts_offset_days; nothing to do here.
            pass

        elif story.kind == "medical_bill":
            offset = story.params["offset_days"]
            ts = (now + timedelta(days=offset)).replace(hour=14)
            rows.append(_GeneratedTxn(
                timestamp=ts,
                account_id=accounts.get("credit", accounts["checking"]).id,
                amount=-float(story.params["amount"]),
                category="Health",
                subcategory="medical",
                merchant=story.params["merchant"],
                description="ER visit + diagnostics",
            ))

        elif story.kind == "annual_insurance":
            offset = story.params["offset_days"]
            ts = (now + timedelta(days=offset)).replace(hour=10)
            rows.append(_GeneratedTxn(
                timestamp=ts,
                account_id=accounts["checking"].id,
                amount=-float(story.params["amount"]),
                category="Utilities",
                subcategory="insurance",
                merchant=story.params["merchant"],
                description="Annual auto insurance premium",
            ))

        elif story.kind == "vacation":
            offset = story.params["offset_days"]
            duration = story.params.get("duration_days", 7)
            destination = story.params.get("destination", "Trip")
            base_ts = (now + timedelta(days=offset))
            # 2 flights, 4 hotels, 8 dining, ~3 transit
            travel_pool = persona.merchants_by_category.get("Travel") or ()
            dining_pool = persona.merchants_by_category.get("Dining") or ()
            transit_pool = persona.merchants_by_category.get("Transit") or ()
            for kind_ms, count, cat in (
                (travel_pool[:2], 2, "Travel"),  # outbound + return
                (travel_pool[2:4], duration - 2, "Travel"),  # hotel nights
                (dining_pool, duration, "Dining"),
                (transit_pool, duration, "Transit"),
            ):
                if not kind_ms:
                    continue
                for i in range(count):
                    m = kind_ms[i % len(kind_ms)] if isinstance(kind_ms, tuple) else rng.choice(kind_ms)
                    amt = -round(rng.uniform(m.amount_min, m.amount_max) * 1.4, 2)
                    ts = (base_ts + timedelta(days=i % duration, hours=rng.randint(8, 22)))
                    rows.append(_GeneratedTxn(
                        timestamp=ts,
                        account_id=accounts.get("credit", accounts["checking"]).id,
                        amount=amt,
                        category=cat,
                        subcategory=getattr(m, "subcategory", "") or "vacation",
                        merchant=m.name,
                        description=f"{destination} trip - {m.name}",
                    ))

        elif story.kind == "raise":
            offset = story.params["offset_days"]
            cutoff = now + timedelta(days=offset)
            inc_pct = float(story.params["increase_pct"]) / 100.0
            for r in rows:
                if r.category == "Income" and r.timestamp >= cutoff:
                    r.amount = round(r.amount * (1 + inc_pct), 2)

        elif story.kind == "dining_drift":
            # Rescale dining transactions over a window so the latest months are higher.
            window_start = now + timedelta(days=story.params["start_offset"])
            growth = float(story.params["growth_pct_total"]) / 100.0
            window_days = (now - window_start).days or 1
            for r in rows:
                if r.category == "Dining" and r.timestamp >= window_start:
                    progress = (r.timestamp - window_start).days / window_days
                    r.amount = round(r.amount * (1 + growth * progress), 2)

        elif story.kind == "tax_refund":
            offset = story.params["offset_days"]
            ts = (now + timedelta(days=offset)).replace(hour=9)
            rows.append(_GeneratedTxn(
                timestamp=ts,
                account_id=accounts["checking"].id,
                amount=float(story.params["amount"]),
                category="Income",
                subcategory="refund",
                merchant="IRS Tax Refund",
                description="Federal tax refund",
            ))

        elif story.kind == "overdraft":
            offset = story.params["offset_days"]
            ts = (now + timedelta(days=offset)).replace(hour=15)
            rows.append(_GeneratedTxn(
                timestamp=ts,
                account_id=accounts["checking"].id,
                amount=-float(story.params["amount"]),
                category="Utilities",
                subcategory="bank_fee",
                merchant="Bank of America Overdraft Fee",
                description=story.params.get("description", "overdraft"),
            ))

    return rows


# ---------------------------------------------------------------------------
# Anomaly + recurring annotation (writes back into Transaction rows)
# ---------------------------------------------------------------------------


def _annotate_anomaly_scores(rows: list[_GeneratedTxn]) -> None:
    """Compute z-score per (category) over abs amounts; write into row.anomaly_score."""
    by_cat: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        if r.amount < 0:
            by_cat[r.category].append(abs(r.amount))

    stats = {}
    for cat, amts in by_cat.items():
        if len(amts) >= 5:
            mu = sum(amts) / len(amts)
            sd = pstdev(amts) or 1.0
            stats[cat] = (mu, sd)

    for r in rows:
        if r.amount < 0 and r.category in stats:
            mu, sd = stats[r.category]
            z = (abs(r.amount) - mu) / sd
            r._anomaly_score = round(float(z), 3)
        else:
            r._anomaly_score = 0.0  # type: ignore[attr-defined]


def _detect_recurring(rows: list[_GeneratedTxn], user_id: str) -> list[RecurringRule]:
    """Group by (merchant, sign), find repeats with consistent cadence."""
    groups: dict[tuple[str, str, int], list[_GeneratedTxn]] = defaultdict(list)
    for r in rows:
        sign = "credit" if r.amount > 0 else "debit"
        groups[(r.merchant, sign, 0)].append(r)

    rules: list[RecurringRule] = []
    for (merchant, _sign, _), txns in groups.items():
        if len(txns) < 3:
            continue
        txns.sort(key=lambda t: t.timestamp)
        gaps = [
            (txns[i + 1].timestamp - txns[i].timestamp).days
            for i in range(len(txns) - 1)
        ]
        if not gaps:
            continue
        med_gap = int(median(gaps))
        if med_gap < 5:
            continue
        # consistency: most gaps within 25% of median
        consistent = sum(1 for g in gaps if abs(g - med_gap) <= max(2, med_gap * 0.25))
        confidence = consistent / len(gaps)
        if confidence < 0.6:
            continue
        amts = [abs(t.amount) for t in txns]
        rules.append(RecurringRule(
            id=str(uuid.uuid4()),
            user_id=user_id,
            merchant=merchant,
            category=txns[-1].category,
            typical_amount=round(median(amts), 2),
            cadence_days=med_gap,
            last_seen_at=txns[-1].timestamp,
            occurrence_count=len(txns),
            confidence=round(confidence, 3),
        ))
        # Mark the source rows as recurring
        for t in txns:
            t.is_recurring = True
    return rules


# ---------------------------------------------------------------------------
# Top-level seeding
# ---------------------------------------------------------------------------


async def seed_persona(session: AsyncSession, persona: Persona) -> dict[str, int]:
    """Drop and re-seed all data for a single persona. Returns counts."""
    # Drop existing data for this user (in dependency order)
    for table_cls in (Transaction, Budget, RecurringRule, Account, User):
        await session.execute(delete(table_cls).where(getattr(table_cls, "user_id" if table_cls is not User else "id") == persona.id))

    user = User(
        id=persona.id,
        email=persona.email,
        name=persona.name,
        persona=persona.id,
        description=persona.description,
    )
    session.add(user)

    # Accounts - keyed by type so we can reference them
    accounts_by_type: dict[str, Account] = {}
    for spec in persona.accounts:
        acc = Account(
            id=str(uuid.uuid4()),
            user_id=persona.id,
            name=spec.name,
            type=spec.type,
            starting_balance=spec.starting_balance,
        )
        session.add(acc)
        # Only the *first* account of each type is the canonical one for routing
        accounts_by_type.setdefault(spec.type, acc)

    # Budgets
    for cat, limit in persona.monthly_budgets.items():
        session.add(Budget(
            id=str(uuid.uuid4()),
            user_id=persona.id,
            category=cat,
            monthly_limit=limit,
        ))

    # Transactions (generation + annotation)
    txn_rows = _generate_persona_txns(persona, accounts_by_type)
    _annotate_anomaly_scores(txn_rows)
    rules = _detect_recurring(txn_rows, persona.id)

    for r in txn_rows:
        session.add(Transaction(
            id=str(uuid.uuid4()),
            user_id=persona.id,
            account_id=r.account_id,
            amount=r.amount,
            currency="USD",
            category=r.category,
            subcategory=r.subcategory,
            merchant=r.merchant,
            description=r.description,
            timestamp=r.timestamp,
            is_recurring=r.is_recurring,
            anomaly_score=getattr(r, "_anomaly_score", 0.0),
        ))

    for rule in rules:
        session.add(rule)

    await session.commit()
    return {
        "user": persona.id,
        "transactions": len(txn_rows),
        "accounts": len(persona.accounts),
        "budgets": len(persona.monthly_budgets),
        "recurring_rules": len(rules),
    }


async def seed_all(session: AsyncSession) -> list[dict]:
    """Seed every persona in PERSONAS."""
    out = []
    for p in PERSONAS:
        out.append(await seed_persona(session, p))
    return out


# Backward compat for older imports
seed_demo_user = seed_all
