import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import uuid4


class CreateTable(Protocol):
    def create_table(self): ...


@dataclass
class Transaction(CreateTable):
    _id: uuid.UUID
    account: Account
    amount: Decimal
    name: str
    notes: str

    created: datetime
    updated: datetime


@dataclass
class Account(CreateTable):
    _id: uuid.UUID
    name: str
    on_budget: bool

    transactions: list[Transaction]
