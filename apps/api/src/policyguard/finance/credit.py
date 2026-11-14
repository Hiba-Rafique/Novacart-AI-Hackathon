from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .money import as_amount, percentage
from .timeutil import add_months

STORE_CREDIT_BONUS_RATE = 5
STORE_CREDIT_BONUS_CAP = 1_000


@dataclass(frozen=True)
class StoreCreditBonus:
    refund_amount: int
    bonus: int
    total_credit: int
    source: str = "14_store_credit.md — Section 3.1"


@dataclass(frozen=True)
class CreditSplit:
    refund_amount: int
    to_original_method: int
    to_store_credit: int
    source: str = "14_store_credit.md — Section 6.1"


def store_credit_bonus(refund_amount: str | int | Decimal) -> StoreCreditBonus:
    refund = int(as_amount(refund_amount))
    bonus = min(percentage(refund, STORE_CREDIT_BONUS_RATE), STORE_CREDIT_BONUS_CAP)
    return StoreCreditBonus(
        refund_amount=refund,
        bonus=bonus,
        total_credit=refund + bonus,
    )


def split_refund_with_store_credit(
    refund_amount: str | int | Decimal,
    other_method_paid: str | int | Decimal,
) -> CreditSplit:
    refund = int(as_amount(refund_amount))
    other = int(as_amount(other_method_paid))
    to_other = min(refund, other)
    return CreditSplit(
        refund_amount=refund,
        to_original_method=to_other,
        to_store_credit=refund - to_other,
    )


def credit_expiry(issue_date: date) -> date:
    return add_months(issue_date, 12)
