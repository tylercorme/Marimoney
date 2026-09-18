"""
Normalize transaction CSVs from institutions into expected
transaction schema.

"""

import re
import csv
from datetime import date
from typing import Protocol, NamedTuple


def camel_to_words(camel_case_str):
    # Insert a space before each uppercase letter, then capitalize properly
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', camel_case_str)
    return result.title()


class ParsedTransaction(NamedTuple):
    amount: float
    notes: str
    date_: date


class Parser(Protocol):
    @staticmethod
    def parse(contents: str) -> list[ParsedTransaction]:
        ...

_AVAILABLE_INSTITUTIONS: dict[str, type[Parser]] = {}

def get_institutions() -> list[str]:
    return list(_AVAILABLE_INSTITUTIONS.keys())


def register(parser: type[Parser]):
    _AVAILABLE_INSTITUTIONS[camel_to_words(parser.__name__)] = parser
    return parser


@register
class Chase:
    @staticmethod
    def parse(contents: str) -> list[ParsedTransaction]:
        lines = contents.splitlines()
        if not lines:
            return []

        reader = csv.DictReader(lines)
        columns = reader.fieldnames or []
        if not all(col in columns for col in ["Transaction Date", "Description", "Category", "Type", "Amount"]):
            raise TypeError("Invalid CSV Format")

        transactions = []
        for row in reader:
            amount = -float(str(row["Amount"]))

            # TODO: inject logic to parse into custom categories based on Description, Amount, Etc.
            category = row["Category"]

            # TODO: inject logic to grab account id if there's matching transaction

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


@register
class CapitalOne:
    @staticmethod
    def parse(contents: str) -> list[ParsedTransaction]:
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

            # TODO: inject logic to parse into custom categories based on Description, Amount, Etc.
            category = row["Category"]

            # TODO: inject logic to grab account id if there's matching transaction

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

@register
class CollinsCommunityCreditUnion:

    @staticmethod
    def parser(contents: str) -> list[ParsedTransaction]:
        lines = contents.splitlines()
        if not lines:
            return []

        reader = csv.DictReader(lines)
        columns = reader.fieldnames or []
        if not all(col in columns for col in ["Date", "Description", "Amount"]):
            raise TypeError("Invalid CSV Format")

        transactions = []
        for row in reader:
            amount = -float(str(row["Amount"]))

            # TODO: inject logic to parse into custom categories based on Description, Amount, Etc.
            category = row["Category"]

            # TODO: inject logic to grab account id if there's matching transaction

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


def make_parser(institution: str) -> type[Parser]:
    return _AVAILABLE_INSTITUTIONS[institution]
