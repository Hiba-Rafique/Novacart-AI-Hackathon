from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .domain import NotApplicableError, normalize_category, normalize_region
from .money import as_amount, round_half_up
from .timeutil import full_months_between

WARRANTY_MONTHS = {
    "electronics": 12,
    "furniture/bulky": 24,
    "clothing": 0,
    "personal care": 0,
    "grocery/perishables": 0,
}


@dataclass(frozen=True)
class WarrantyRefund:
    paid_price: int
    warranty_months: int
    full_months_elapsed: int
    refund: int
    source: str = "08_warranty_policy.md — Section 4.3"


def warranty_months(category: str, *, separate_accessory: bool = False) -> int:
    category_value = normalize_category(category)
    if separate_accessory:
        return 6
    return WARRANTY_MONTHS[category_value]


def warranty_refund(
    paid_price: str | int | Decimal,
    *,
    category: str,
    delivery_date: date,
    claim_date: date,
    separate_accessory: bool = False,
) -> WarrantyRefund:
    months = warranty_months(category, separate_accessory=separate_accessory)
    if months <= 0:
        raise NotApplicableError(f"{category} has no NovaCart warranty")
    paid = int(as_amount(paid_price))
    elapsed = full_months_between(delivery_date, claim_date)
    if elapsed >= months:
        refund = 0
    else:
        refund = round_half_up(Decimal(paid) * Decimal(months - elapsed) / Decimal(months))
    return WarrantyRefund(
        paid_price=paid,
        warranty_months=months,
        full_months_elapsed=elapsed,
        refund=max(0, refund),
    )


def warranty_repair_days(region: str = "metro") -> int:
    return 21 if normalize_region(region) == "remote" else 14
