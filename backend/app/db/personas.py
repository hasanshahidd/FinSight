"""Persona definitions for mock-bank seed data.

Each persona is a deliberate scenario the agent can reason about. Demos can
switch personas to demonstrate range. The seeded RNG makes generation
deterministic, so amounts and timestamps reproduce exactly.
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class MerchantSpec:
    name: str
    amount_min: float
    amount_max: float
    subcategory: str = ""


@dataclass(frozen=True)
class SubscriptionSpec:
    merchant: str
    category: str
    amount: float
    day_of_month: int
    starts_offset_days: int = 0  # negative = relative to dataset start; 0 = present from day 1
    ends_offset_days: int | None = None


@dataclass(frozen=True)
class AccountSpec:
    name: str
    type: Literal["checking", "savings", "credit"]
    starting_balance: float


@dataclass(frozen=True)
class IncomeSpec:
    merchant: str
    amount: float
    cadence_days: int  # 14 = bi-weekly, 30 = monthly


@dataclass(frozen=True)
class StorySpec:
    """A 'story' is a deterministic event the data generator splices into the
    timeline. Story handlers in seed.py read these and inject extra
    transactions, modify income, etc."""
    kind: str  # one of: subscription_creep | medical_bill | vacation | raise | annual_insurance | dining_drift | overdraft | tax_refund
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    email: str
    description: str
    rng_seed: int
    accounts: tuple[AccountSpec, ...]
    incomes: tuple[IncomeSpec, ...]
    rent_amount: float
    rent_day_of_month: int
    category_weights: dict[str, int]  # daily-spend selection weights
    merchants_by_category: dict[str, tuple[MerchantSpec, ...]]
    subscriptions: tuple[SubscriptionSpec, ...]
    monthly_budgets: dict[str, float]
    stories: tuple[StorySpec, ...] = ()


# ---------------------------------------------------------------------------
# Shared merchant pools (re-used across personas to keep variety realistic)
# ---------------------------------------------------------------------------

_MERCHANTS = {
    "Groceries": (
        MerchantSpec("Whole Foods Market", 35, 180),
        MerchantSpec("Trader Joe's", 22, 90),
        MerchantSpec("Safeway", 28, 140),
        MerchantSpec("Costco Wholesale", 80, 320, "bulk"),
        MerchantSpec("Aldi", 18, 75, "discount"),
        MerchantSpec("Local Farmers Market", 12, 60, "fresh"),
        MerchantSpec("Kroger", 25, 130),
    ),
    "Dining": (
        MerchantSpec("Chipotle", 11, 24, "fast_casual"),
        MerchantSpec("Sweetgreen", 13, 22, "fast_casual"),
        MerchantSpec("Blue Bottle Coffee", 5, 12, "coffee"),
        MerchantSpec("Starbucks", 4, 9, "coffee"),
        MerchantSpec("Local Diner", 14, 38, "restaurant"),
        MerchantSpec("Sushi Bar", 28, 95, "restaurant"),
        MerchantSpec("Five Guys", 14, 28, "fast_food"),
        MerchantSpec("Olive Garden", 32, 78, "restaurant"),
        MerchantSpec("Dunkin'", 4, 10, "coffee"),
        MerchantSpec("Pho House", 16, 34, "restaurant"),
        MerchantSpec("Domino's Pizza", 18, 42, "delivery"),
        MerchantSpec("Uber Eats", 22, 58, "delivery"),
        MerchantSpec("DoorDash", 24, 65, "delivery"),
    ),
    "Transit": (
        MerchantSpec("Uber", 7, 38, "rideshare"),
        MerchantSpec("Lyft", 8, 32, "rideshare"),
        MerchantSpec("Metro Transit", 2.75, 5.5, "public"),
        MerchantSpec("Shell Gas", 38, 78, "gas"),
        MerchantSpec("Chevron Gas", 35, 72, "gas"),
        MerchantSpec("Citi Bike", 4, 18, "bike"),
        MerchantSpec("Amtrak", 38, 180, "rail"),
    ),
    "Subscriptions": (
        MerchantSpec("Netflix", 15.99, 15.99),
        MerchantSpec("Spotify", 10.99, 10.99),
        MerchantSpec("ChatGPT Plus", 20.00, 20.00),
        MerchantSpec("YouTube Premium", 13.99, 13.99),
        MerchantSpec("Disney+", 13.99, 13.99),
        MerchantSpec("Equinox Gym", 215.00, 215.00),
        MerchantSpec("Planet Fitness", 24.99, 24.99),
        MerchantSpec("iCloud+", 2.99, 2.99),
        MerchantSpec("Notion", 10.00, 10.00),
        MerchantSpec("New York Times", 17.00, 17.00),
        MerchantSpec("Adobe CC", 54.99, 54.99),
    ),
    "Utilities": (
        MerchantSpec("ConEd Electric", 78, 195, "electric"),
        MerchantSpec("PG&E", 65, 165, "electric"),
        MerchantSpec("Verizon Wireless", 65, 95, "phone"),
        MerchantSpec("AT&T Internet", 70, 80, "internet"),
        MerchantSpec("Comcast Xfinity", 80, 110, "internet"),
        MerchantSpec("National Grid Gas", 45, 130, "gas"),
    ),
    "Rent": (MerchantSpec("Landlord", 1200, 4200),),
    "Entertainment": (
        MerchantSpec("AMC Theatres", 14, 45, "movies"),
        MerchantSpec("Steam", 8, 65, "games"),
        MerchantSpec("Concert Tickets", 45, 220, "live"),
        MerchantSpec("Bowling Alley", 22, 55, "activity"),
        MerchantSpec("Apple App Store", 1, 30, "apps"),
        MerchantSpec("Live Nation", 65, 250, "live"),
    ),
    "Shopping": (
        MerchantSpec("Amazon", 12, 220, "online"),
        MerchantSpec("Target", 22, 145, "general"),
        MerchantSpec("Uniqlo", 28, 150, "apparel"),
        MerchantSpec("Best Buy", 45, 480, "electronics"),
        MerchantSpec("Etsy", 18, 95, "online"),
        MerchantSpec("REI", 65, 320, "outdoor"),
        MerchantSpec("Nike", 55, 220, "apparel"),
        MerchantSpec("IKEA", 35, 380, "home"),
    ),
    "Health": (
        MerchantSpec("CVS Pharmacy", 8, 75, "pharmacy"),
        MerchantSpec("Walgreens", 7, 65, "pharmacy"),
        MerchantSpec("Doctor Copay", 25, 60, "medical"),
        MerchantSpec("Dental Cleaning", 0, 180, "dental"),
        MerchantSpec("Optometrist", 0, 180, "vision"),
    ),
    "Travel": (
        MerchantSpec("Delta Airlines", 180, 720, "flight"),
        MerchantSpec("United Airlines", 200, 680, "flight"),
        MerchantSpec("Marriott", 140, 380, "hotel"),
        MerchantSpec("Airbnb", 95, 420, "lodging"),
        MerchantSpec("Hertz Rent-a-Car", 55, 220, "car"),
    ),
    "Personal Care": (
        MerchantSpec("Hair Salon", 35, 95),
        MerchantSpec("Sephora", 28, 145, "cosmetics"),
        MerchantSpec("Massage Envy", 75, 130, "spa"),
    ),
    "Education": (
        MerchantSpec("Coursera", 49, 49, "course"),
        MerchantSpec("University Bookstore", 65, 320, "textbooks"),
        MerchantSpec("Library Late Fee", 5, 18, "fee"),
        MerchantSpec("Stationery Store", 8, 35, "supplies"),
    ),
    "Kids": (
        MerchantSpec("Soccer Club", 120, 180, "sports"),
        MerchantSpec("School Lunch Program", 45, 90, "school"),
        MerchantSpec("Toys R Us", 25, 110, "toys"),
        MerchantSpec("Children's Place", 22, 95, "apparel"),
        MerchantSpec("Crayola Store", 12, 45, "supplies"),
    ),
}


# ---------------------------------------------------------------------------
# Personas
# ---------------------------------------------------------------------------

ALEX = Persona(
    id="user_1",
    name="Alex Chen",
    email="alex@finsight.demo",
    description="NYC software engineer, 28, single. High rent, dining-heavy lifestyle.",
    rng_seed=42,
    accounts=(
        AccountSpec("Chase Checking", "checking", 4200.00),
        AccountSpec("Marcus HYSA", "savings", 9800.00),
        AccountSpec("Chase Sapphire", "credit", 0.00),
    ),
    incomes=(IncomeSpec("Acme Corp Payroll", 3650.00, 14),),
    rent_amount=2400.00,
    rent_day_of_month=1,
    category_weights={
        "Groceries": 3, "Dining": 7, "Transit": 4, "Entertainment": 2,
        "Shopping": 3, "Health": 1, "Personal Care": 1,
    },
    merchants_by_category={k: _MERCHANTS[k] for k in [
        "Groceries", "Dining", "Transit", "Subscriptions", "Utilities", "Rent",
        "Entertainment", "Shopping", "Health", "Personal Care", "Travel",
    ]},
    subscriptions=(
        SubscriptionSpec("Netflix", "Subscriptions", 15.99, 5),
        SubscriptionSpec("Spotify", "Subscriptions", 10.99, 5),
        SubscriptionSpec("ChatGPT Plus", "Subscriptions", 20.00, 12, starts_offset_days=-120),
        SubscriptionSpec("Equinox Gym", "Subscriptions", 215.00, 1, starts_offset_days=-60),
        SubscriptionSpec("YouTube Premium", "Subscriptions", 13.99, 18, starts_offset_days=-30),
    ),
    monthly_budgets={
        "Groceries": 450, "Dining": 400, "Transit": 200, "Subscriptions": 280,
        "Utilities": 200, "Rent": 2400, "Entertainment": 150, "Shopping": 250,
        "Health": 80, "Personal Care": 80,
    },
    stories=(
        StorySpec("subscription_creep", {"description": "AI tool + gym + streaming added gradually"}),
        StorySpec("dining_drift", {"start_offset": -150, "growth_pct_total": 60}),
        StorySpec("raise", {"offset_days": -90, "increase_pct": 14}),
    ),
)


SAM = Persona(
    id="user_2",
    name="Sam Patel",
    email="sam@finsight.demo",
    description="Suburban family of 4. Groceries and kids' activities dominate. One surprise medical bill in the dataset.",
    rng_seed=101,
    accounts=(
        AccountSpec("Wells Fargo Checking", "checking", 6800.00),
        AccountSpec("Family Savings", "savings", 22500.00),
        AccountSpec("Citi Double Cash", "credit", 0.00),
    ),
    incomes=(
        IncomeSpec("Northrop Engineering Payroll", 4900.00, 14),
        IncomeSpec("Spouse Consulting LLC", 2800.00, 30),
    ),
    rent_amount=2850.00,  # mortgage
    rent_day_of_month=1,
    category_weights={
        "Groceries": 8, "Dining": 3, "Transit": 4, "Kids": 5,
        "Shopping": 3, "Health": 2, "Entertainment": 1,
    },
    merchants_by_category={k: _MERCHANTS[k] for k in [
        "Groceries", "Dining", "Transit", "Subscriptions", "Utilities", "Rent",
        "Kids", "Shopping", "Health", "Entertainment",
    ]},
    subscriptions=(
        SubscriptionSpec("Disney+", "Subscriptions", 13.99, 8),
        SubscriptionSpec("Netflix", "Subscriptions", 15.99, 5),
        SubscriptionSpec("New York Times", "Subscriptions", 17.00, 22),
        SubscriptionSpec("iCloud+", "Subscriptions", 2.99, 14),
        SubscriptionSpec("Daycare Center", "Kids", 1450.00, 1),
    ),
    monthly_budgets={
        "Groceries": 1100, "Dining": 350, "Transit": 380, "Subscriptions": 70,
        "Utilities": 320, "Rent": 2850, "Entertainment": 120, "Shopping": 380,
        "Health": 200, "Kids": 1750,
    },
    stories=(
        StorySpec("medical_bill", {"offset_days": -90, "amount": 1820, "merchant": "Mt. Sinai Hospital"}),
        StorySpec("annual_insurance", {"offset_days": -180, "amount": 1250, "merchant": "Geico Auto Insurance"}),
    ),
)


JORDAN = Persona(
    id="user_3",
    name="Jordan Rivera",
    email="jordan@finsight.demo",
    description="Grad student. Variable income (assistantship + freelance gigs). Tight budget. Subscription creep.",
    rng_seed=2024,
    accounts=(
        AccountSpec("Ally Checking", "checking", 1450.00),
        AccountSpec("Ally Savings", "savings", 2100.00),
        AccountSpec("Discover It", "credit", 0.00),
    ),
    incomes=(
        IncomeSpec("University Assistantship", 1450.00, 30),
        IncomeSpec("Freelance Design", 0.0, 30),  # variable; story injector handles
    ),
    rent_amount=1100.00,
    rent_day_of_month=1,
    category_weights={
        "Groceries": 5, "Dining": 4, "Transit": 5, "Education": 3,
        "Shopping": 1, "Entertainment": 2, "Health": 1,
    },
    merchants_by_category={k: _MERCHANTS[k] for k in [
        "Groceries", "Dining", "Transit", "Subscriptions", "Utilities", "Rent",
        "Education", "Entertainment", "Shopping", "Health",
    ]},
    subscriptions=(
        SubscriptionSpec("Spotify", "Subscriptions", 10.99, 6),
        SubscriptionSpec("Notion", "Subscriptions", 10.00, 14, starts_offset_days=-150),
        SubscriptionSpec("Adobe CC", "Subscriptions", 54.99, 20, starts_offset_days=-90),
        SubscriptionSpec("Coursera", "Subscriptions", 49.00, 11, starts_offset_days=-60),
        SubscriptionSpec("University Tuition", "Education", 850.00, 15),
    ),
    monthly_budgets={
        "Groceries": 280, "Dining": 150, "Transit": 90, "Subscriptions": 150,
        "Utilities": 90, "Rent": 1100, "Education": 950, "Entertainment": 60,
        "Shopping": 80, "Health": 50,
    },
    stories=(
        StorySpec("tax_refund", {"offset_days": -55, "amount": 1400}),
        StorySpec("subscription_creep", {"description": "Notion + Adobe + Coursera over 5 months"}),
    ),
)


RILEY = Persona(
    id="user_4",
    name="Riley Morgan",
    email="riley@finsight.demo",
    description="High-earning consultant. Travel-heavy. Investment transfers monthly. Dines out 4–5x/week.",
    rng_seed=777,
    accounts=(
        AccountSpec("Chase Sapphire Banking", "checking", 18500.00),
        AccountSpec("Vanguard Brokerage Cash", "savings", 78000.00),
        AccountSpec("Amex Platinum", "credit", 0.00),
    ),
    incomes=(IncomeSpec("Bain & Co Payroll", 9200.00, 14),),
    rent_amount=4200.00,
    rent_day_of_month=1,
    category_weights={
        "Groceries": 1, "Dining": 8, "Transit": 4, "Travel": 4,
        "Shopping": 4, "Entertainment": 3, "Personal Care": 2,
    },
    merchants_by_category={k: _MERCHANTS[k] for k in [
        "Groceries", "Dining", "Transit", "Subscriptions", "Utilities", "Rent",
        "Travel", "Entertainment", "Shopping", "Personal Care", "Health",
    ]},
    subscriptions=(
        SubscriptionSpec("Netflix", "Subscriptions", 15.99, 5),
        SubscriptionSpec("Spotify", "Subscriptions", 10.99, 5),
        SubscriptionSpec("ChatGPT Plus", "Subscriptions", 20.00, 12),
        SubscriptionSpec("Equinox Gym", "Subscriptions", 215.00, 1),
        SubscriptionSpec("New York Times", "Subscriptions", 17.00, 22),
        SubscriptionSpec("Adobe CC", "Subscriptions", 54.99, 20),
    ),
    monthly_budgets={
        "Groceries": 220, "Dining": 1100, "Transit": 380, "Subscriptions": 360,
        "Utilities": 240, "Rent": 4200, "Travel": 1400, "Entertainment": 380,
        "Shopping": 850, "Personal Care": 220, "Health": 100,
    },
    stories=(
        StorySpec("vacation", {"offset_days": -75, "duration_days": 7, "destination": "Tokyo"}),
    ),
)


CASEY = Persona(
    id="user_5",
    name="Casey Brooks",
    email="casey@finsight.demo",
    description="Recovering from credit card debt. Tight budget, paying down avalanche-style. No savings yet.",
    rng_seed=314,
    accounts=(
        AccountSpec("Bank of America Checking", "checking", 850.00),
        AccountSpec("Emergency Starter", "savings", 320.00),
        AccountSpec("Chase Freedom (paying down)", "credit", -3200.00),
        AccountSpec("Capital One (paying down)", "credit", -1850.00),
    ),
    incomes=(IncomeSpec("Office Admin Payroll", 1900.00, 14),),
    rent_amount=1450.00,
    rent_day_of_month=1,
    category_weights={
        "Groceries": 5, "Dining": 2, "Transit": 4, "Health": 1,
        "Shopping": 1, "Entertainment": 1,
    },
    merchants_by_category={k: _MERCHANTS[k] for k in [
        "Groceries", "Dining", "Transit", "Subscriptions", "Utilities", "Rent",
        "Health", "Shopping", "Entertainment",
    ]},
    subscriptions=(
        SubscriptionSpec("Netflix", "Subscriptions", 15.99, 5),
        SubscriptionSpec("Planet Fitness", "Subscriptions", 24.99, 18),
    ),
    monthly_budgets={
        "Groceries": 320, "Dining": 80, "Transit": 140, "Subscriptions": 45,
        "Utilities": 150, "Rent": 1450, "Health": 60, "Shopping": 50, "Entertainment": 30,
    },
    stories=(
        StorySpec("overdraft", {"offset_days": -120, "amount": 35, "description": "checking briefly negative"}),
    ),
)


PERSONAS: tuple[Persona, ...] = (ALEX, SAM, JORDAN, RILEY, CASEY)


def get_persona(persona_id: str) -> Persona | None:
    for p in PERSONAS:
        if p.id == persona_id:
            return p
    return None
