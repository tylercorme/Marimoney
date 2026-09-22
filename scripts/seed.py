import json
import random
import sqlite3
import uuid
from datetime import date, timedelta

RNG_SEED = 7


def _uid() -> str:
    return uuid.uuid4().hex


def seed_demo_data(conn: sqlite3.Connection) -> None:
    rng = random.Random(RNG_SEED)
    today = date.today()

    # ---- accounts ----------------------------------------------------
    accounts = [
        ("Checking", 250_000, 1),
        ("Savings", 1_500_000, 1),
        ("Credit Card", -42_000, 1),
        ("Investments", 8_200_000, 0),  # off-budget
    ]
    account_ids: dict[str, int] = {}
    for name, start_balance, on_budget in accounts:
        cur = conn.execute(
            "insert into accounts (name, start_balance, on_budget) values (?, ?, ?)",
            (name, start_balance, on_budget),
        )
        account_ids[name] = cur.lastrowid

    # ---- categories -----------------------------------------------------
    income_categories = ["Paycheck", "Side Income"]
    expense_categories = [
        "Rent",
        "Groceries",
        "Dining Out",
        "Utilities",
        "Transportation",
        "Entertainment",
        "Subscriptions",
        "Health",
        "Shopping",
        "Travel",
    ]
    category_ids: dict[str, int] = {}
    for name in income_categories:
        cur = conn.execute(
            "insert into categories (name, is_income) values (?, 1)", (name,)
        )
        category_ids[name] = cur.lastrowid
    for name in expense_categories:
        cur = conn.execute(
            "insert into categories (name, is_income) values (?, 0)", (name,)
        )
        category_ids[name] = cur.lastrowid

    # ---- budget items (last 3 months, incl. current) --------------------
    monthly_budget_cents = {
        "Rent": 180_000,
        "Groceries": 60_000,
        "Dining Out": 25_000,
        "Utilities": 22_000,
        "Transportation": 15_000,
        "Entertainment": 10_000,
        "Subscriptions": 6_000,
        "Health": 12_000,
        "Shopping": 15_000,
        "Travel": 20_000,
    }
    months = []
    y, m = today.year, today.month
    for _ in range(3):
        months.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    months.reverse()


    start_year, start_month = months[0]
    conn.execute(
        """
        insert into settings (key, value) values ('budget_start', ?)
        on conflict (key) do update set value = excluded.value
        """,
        (date(start_year, start_month, 1).isoformat(),),
    )

    for year, month in months:
        for cat_name, cents in monthly_budget_cents.items():
            # small month-to-month variation so it doesn't look robotic
            jitter = rng.randint(-2000, 2000)
            conn.execute(
                """
                insert or ignore into budget_items (month, year, category_id, budgeted_amount)
                values (?, ?, ?, ?)
                """,
                (month, year, category_ids[cat_name], max(0, cents + jitter)),
            )

    # ---- transactions over the last ~90 days -----------------------------
    def add_txn(
        account_name: str,
        amount_cents: int,
        d: date,
        category_name: str | None = None,
        notes: str = "",
        status: int = 1,
        transfer_account_name: str | None = None,
    ):
        conn.execute(
            """
            insert into transactions
                (account_id, transfer_account_id, category_id, amount, notes, date, status, original_json)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_ids[account_name],
                account_ids[transfer_account_name] if transfer_account_name else None,
                category_ids[category_name] if category_name else None,
                amount_cents,
                notes,
                d.isoformat(),
                status,
                json.dumps({"notes": "", "amount":0, "date": _uid()}), #json is only used for unique constraint
            ),
        )

    # recurring paychecks, every other Friday for ~90 days back
    d = today - timedelta(days=90)
    while d <= today:
        if d.weekday() == 4:  # Friday
            add_txn("Checking", 320_000, d, "Paycheck", "Biweekly paycheck")
        d += timedelta(days=1)

    # monthly rent
    for year, month in months:
        add_txn("Checking", -180_000, date(year, month, 1), "Rent", "Monthly rent")

    # everyday spending, spread across the window
    spending_templates = [
        ("Checking", "Groceries", (2_000, 9_000), "Groceries"),
        ("Credit Card", "Dining Out", (1_200, 6_500), "Restaurant"),
        ("Checking", "Utilities", (3_000, 12_000), "Utility bill"),
        ("Credit Card", "Transportation", (800, 5_000), "Gas / rideshare"),
        ("Credit Card", "Entertainment", (1_000, 7_000), "Movies / streaming event"),
        ("Credit Card", "Subscriptions", (500, 2_000), "Subscription"),
        ("Credit Card", "Shopping", (1_500, 12_000), "Retail"),
        ("Checking", "Health", (1_000, 8_000), "Pharmacy / clinic"),
    ]
    d = today - timedelta(days=90)
    while d <= today:
        for account_name, cat, (lo, hi), label in spending_templates:
            if rng.random() < 0.18:  # not every category every day
                add_txn(account_name, -rng.randint(lo, hi), d, cat, label)
        d += timedelta(days=1)

    # a transfer between accounts, to show off transfer handling
    add_txn(
        "Checking",
        -50_000,
        today - timedelta(days=10),
        None,
        "Transfer to savings",
        transfer_account_name="Savings",
    )
    add_txn(
        "Savings",
        50_000,
        today - timedelta(days=10),
        None,
        "Transfer from checking",
        transfer_account_name="Checking",
    )

    # a couple of unconfirmed transactions, so the "Needs Review" tab has content
    add_txn("Checking", -4_200, today - timedelta(days=1), None, "Coffee shop", status=0)
    add_txn("Credit Card", -8_900, today, None, "New shoes", status=0)

    conn.commit()