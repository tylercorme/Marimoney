"""
Pooled-income envelope budgeting
================================

Terms
-----
Start date:
    The budget start date setting. Transactions dated before it
    are ignored.

Confirmed:
    A transaction with status = 1. Status 0 means unconfirmed.

Categorized:
    A transaction whose category exists in `categories`.

Income category:
    An expense-free category (is_income = 1). Its confirmed transactions feed the pool.

Expense category / envelope:
    Any other category. Money is assigned to it each month and its spending draws it down.

Assigned/Budgeted:
    Money moved from the pool into an envelope for one month (a `budget_items` row).

Actual:
    Sum of a category's counted transactions. Spending is negative.

Pool:
    The single shared pile of income money not yet assigned to
    any envelope. Shown as "To Budget".

Rollover:
    What an envelope carries into the selected month from all
    earlier months.

Balance:
    What an envelope has left at the end of the selected month.

Notes:
Only transactions that are confirmed AND categorized AND dated
on or after the start date are counted.

Rules:
1. Income is pooled. Income categories are not budgeted individually; their
   actuals all flow into one pool.
2. To Budget = income actual from the start date through the end of the
   selected month, minus everything assigned to envelopes through the
   selected month.
3. Envelope balance = everything assigned to it through the selected month,
   plus its actual from the start date through the end of the selected month.
4. Rollover = the same sum through the end of the PREVIOUS month. Nothing
   resets: surpluses and deficits both carry forward indefinitely.
5. Spending only draws down its own envelope. It never touches the pool.

Invariant: To Budget + sum of envelope balances == counted income + counted
spending. If this fails, money is being created or lost.

Caveats:
- Overspending is not covered. A negative envelope stays negative and rolls
  forward; the pool is not reduced. To Budget can look healthy while
  envelopes are underwater.
- Rollover is recomputed from history, not stored. Editing a past month
  changes every later month. There are no caps, top-up targets, or resets.
- Flagging a category as income zeroes all its assignments, past months
  included. Unflagging does not restore them.
- Income rows show their actual in the "budgeted" column and have no balance.
"""


import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

_ENVELOPES_SQL = """
with budget as (
    select
        category_id,
        sum(case when year * 12 + month <  :ym then budgeted_amount else 0 end) as assigned_before,
        sum(case when year * 12 + month =  :ym then budgeted_amount else 0 end) as budgeted
    from budget_items
    where year * 12 + month <= :ym
        and year * 12 + month >= :start_ym
    group by category_id
),
actuals as (
    select
        category_id,
        sum(case when date <  :start then amount else 0 end) as actual_before,
        sum(case when date >= :start then amount else 0 end) as actual
    from transactions
    where status = 1
      and date >= :budget_start
      and date <  :end
    group by category_id
)
select
    c.id, c.name, c.is_income,
    coalesce(b.assigned_before, 0),
    coalesce(b.budgeted, 0),
    coalesce(a.actual_before, 0),
    coalesce(a.actual, 0)
from categories c
left join budget  b on b.category_id = c.id
left join actuals a on a.category_id = c.id
order by c.is_income desc, c.name
"""


@dataclass(frozen=True, slots=True)
class Envelope:
    id: int
    name: str
    is_income: bool
    assigned_before: int
    budgeted: int
    actual_before: int
    actual: int

    @property
    def rollover(self) -> int:
        return 0 if self.is_income else self.assigned_before + self.actual_before

    @property
    def balance(self) -> int | None:
        if self.is_income:
            return None
        return self.rollover + self.budgeted + self.actual

    @property
    def display_budgeted(self) -> int:
        return self.actual if self.is_income else self.budgeted


@dataclass(frozen=True)
class Budget:
    envelopes: list[Envelope]

    @property
    def _income(self) -> list[Envelope]:
        return [e for e in self.envelopes if e.is_income]

    @property
    def _expense(self) -> list[Envelope]:
        return [e for e in self.envelopes if not e.is_income]

    @property
    def income_actual(self) -> int:
        return sum(e.actual for e in self._income)

    @property
    def expense_actual(self) -> int:
        return sum(e.actual for e in self._expense)

    @property
    def expense_assigned(self) -> int:
        return sum(e.budgeted for e in self._expense)

    @property
    def net_actual(self) -> int:
        return self.income_actual + self.expense_actual

    @property
    def pool_rollover(self) -> int:
        """Pool balance at the start of the month."""
        return (sum(e.actual_before for e in self._income)
                - sum(e.assigned_before for e in self._expense))

    @property
    def to_budget(self) -> int:
        """Pool balance at the end of the month."""
        return self.pool_rollover + self.income_actual - self.expense_assigned

    @property
    def total_balance(self) -> int:
        return sum(e.balance for e in self._expense)


def month_bounds(year: int, month: int) -> tuple[str, str]:
    """First of this month and first of next month, ISO strings."""
    start = date(year, month, 1)
    end = date(year + month // 12, month % 12 + 1, 1)
    return start.isoformat(), end.isoformat()


def load_budget(conn: sqlite3.Connection, year: int, month: int,
                budget_start: date | None) -> Budget:
    if budget_start is None:
        return Budget([])
    start, end = month_bounds(year, month)
    rows = conn.execute(_ENVELOPES_SQL, {
        "ym": year * 12 + month,
        "start": start,
        "end": end,
        "budget_start": budget_start.isoformat(),
        "start_ym": budget_start.year * 12 + budget_start.month,
    }).fetchall()
    return Budget([Envelope(r[0], r[1], bool(r[2]), *r[3:]) for r in rows])


def dollars_to_cents(v: float | None) -> int:
    if v is None:
        return 0
    return int((Decimal(str(v)) * 100).quantize(Decimal(1), ROUND_HALF_UP))


def set_budgeted(conn: sqlite3.Connection, year: int, month: int,
                 category_id: int, cents: int) -> None:
    with conn:
        conn.execute(
            """insert into budget_items (month, year, category_id, budgeted_amount)
               values (?, ?, ?, ?)
               on conflict (month, year, category_id)
               do update set budgeted_amount = excluded.budgeted_amount""",
            (month, year, category_id, cents),
        )


def rename_category(conn: sqlite3.Connection, category_id: int, name: str) -> None:
    with conn:
        conn.execute("update categories set name = ? where id = ?", (name, category_id))


def set_is_income(conn: sqlite3.Connection, category_id: int, is_income: bool) -> None:
    with conn:
        conn.execute("update categories set is_income = ? where id = ?",
                     (int(is_income), category_id))
        if is_income:  # destructive, see docstring
            conn.execute("update budget_items set budgeted_amount = 0 where category_id = ?",
                         (category_id,))