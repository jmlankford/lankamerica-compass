"""
models.py — Dataclasses for LankAmerica Compass
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    id: int
    username: str
    display_name: str
    color: str = '#1565C0'
    db_path: Optional[str] = None


@dataclass
class Account:
    id: int
    name: str
    type: str
    owner_user_id: int
    opening_balance: float = 0.0
    notes: str = ''
    is_archived: int = 0


@dataclass
class Transaction:
    id: int
    account_id: int
    date: str
    type: str
    check_number: str
    description: str
    memo: str
    category_id: Optional[int]
    category_name: str
    reconciled: int
    debit: float
    credit: float
    balance: float
    created_by_user_id: Optional[int]


@dataclass
class Category:
    id: int
    name: str
    category_type: str  # 'expense' or 'income'
    is_default: int = 0
    sort_order: int = 0


@dataclass
class Budget:
    id: int
    category_id: int
    monthly_amount: float
    user_id: int
