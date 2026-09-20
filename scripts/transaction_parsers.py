"""
Normalize transaction CSVs from institutions into expected
transaction schema.

"""

import re
import csv
from datetime import date
from typing import NamedTuple
from collections.abc import Callable

class ParsedTransaction(NamedTuple):
    amount: float
    notes: str
    date_: date

type ParseFunction = Callable[[str], list[ParsedTransaction]]

_AVAILABLE_INSTITUTIONS: dict[str, ParseFunction] = {}

def get_institutions() -> list[str]:
    return list(_AVAILABLE_INSTITUTIONS.keys())

def get_parser(institution: str) -> ParseFunction:
    return _AVAILABLE_INSTITUTIONS[institution]

def register(key: str):
    def inner(parser: ParseFunction):
        _AVAILABLE_INSTITUTIONS[key] = parser
        return parser
    return inner


@register("Chase")
def _(contents: str) -> list[ParsedTransaction]:
    lines = contents.splitlines()
    if not lines:
        return []

    reader = csv.DictReader(lines)
    columns = reader.fieldnames or []
    if not all(col in columns for col in ["Transaction Date", "Description", "Category", "Type", "Amount"]):
        raise TypeError("Invalid CSV Format")

    transactions = []
    for row in reader:
        amount = float(str(row["Amount"]))
        category = row["Category"]
        date_ = date.strptime(row["Transaction Date"], r"%m/%d/%Y")
        description = re.sub(r"\s+", " ", row["Description"])
        transactions.append(
            ParsedTransaction(
                amount=float(amount),
                notes=description,
                date_=date_,
            )
        )

    return transactions


@register("Capital One")
def _(contents: str) -> list[ParsedTransaction]:
    lines = contents.splitlines()
    if not lines:
        return []

    reader = csv.DictReader(lines)
    columns = reader.fieldnames or []
    if not all(col in columns for col in ["Transaction Date", "Description", "Category", "Debit", "Credit"]):
        raise TypeError("Invalid CSV Format")

    transactions = []
    for row in reader:
        if row["Debit"]:
            amount = -float(str(row["Debit"]))
        elif row["Credit"]:
            amount = +float(str(row["Credit"]))
        else:
            continue

        category = row["Category"]
        date_ = date.strptime(row["Transaction Date"], r"%Y-%m-%d")
        description = re.sub(r"\s+", " ", row["Description"])
        transactions.append(
            ParsedTransaction(
                amount=float(amount),
                notes=description,
                date_=date_,
            )
        )

    return transactions


@register("CCCU")
def _(contents: str) -> list[ParsedTransaction]:
    lines = contents.splitlines()
    if not lines:
        return []

    reader = csv.DictReader(lines)
    columns = reader.fieldnames or []
    if not all(col in columns for col in ["Date", "Description", "Amount"]):
        raise TypeError("Invalid CSV Format")

    transactions = []
    for row in reader:
        amount = float(str(row["Amount"]).replace("$","").replace(',',''))


        date_ = date.strptime(row["Date"], r"%m/%d/%Y")
        description = re.sub(r"\s+", " ", row["Description"])
        transactions.append(
            ParsedTransaction(
                amount=amount,
                notes=description,
                date_=date_,
            )
        )

    return transactions
