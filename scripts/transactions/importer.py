from typing import NamedTuple
import sqlite3
from collections import Counter
import json

from .parsers import ParsedTransaction


class ImportResult(NamedTuple):
    inserted: int
    skipped: int


def import_(
    conn: sqlite3.Connection,
    account_id: int,
    parsed_transactions: list[ParsedTransaction],
) -> ImportResult:
    """Import one or more parsed statements in a single transaction.

    Each statement gets its own duplicate counter: identical rows within one
    file get increasing `count` values (so real repeats survive), while the
    same transaction appearing in two overlapping files is stored once.
    Relies on a unique index over (account_id, date, amount, notes, count).
    """
    inserted = 0
    total = 0
    with conn:
        seen = Counter()
        for amount, notes, d in parsed_transactions:
            cents = round(amount * 100)
            iso = d.isoformat()
            key = (iso, cents, notes)
            seen[key] += 1
            cur = conn.execute(
                """insert or ignore into transactions
                   (account_id, notes, amount, date, count, status, original_json)
                   values (?, ?, ?, ?, ?, 1, ?)""",
                (account_id, notes, cents, iso, seen[key],
                 json.dumps({"amount": cents, "notes": notes, "date": iso})),
            )
            inserted += cur.rowcount
            total += 1
    return ImportResult(inserted, total - inserted)
