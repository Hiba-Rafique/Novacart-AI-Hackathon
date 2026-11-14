from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .domain import PolicyInputError, normalize_category, normalize_region
from .money import as_amount, percentage
from .timeutil import add_days

CURRENT_RETURN_POLICY = date(2026, 3, 1)
REGIONAL_EFFECTIVE = date(2026, 4, 1)

RETURN_WINDOWS_CURRENT = {
    "electronics": 7,
    "clothing": 30,
    "furniture/bulky": 14,
    "personal care": 14,
    "grocery/perishables": None,
}
RETURN_WINDOWS_OLD = {
    "electronics": 10,
    "clothing": 14,
    "furniture/bulky": 14,
    "personal care": 14,
    "grocery/perishables": None,
}


@dataclass(frozen=True)
class ReturnItem:
    name: str
    category: str
    paid_price: str | int | Decimal
    opened: bool = False
    nova_error: bool = False

    @property
    def category_value(self) -> str:
        return normalize_category(self.category)


@dataclass(frozen=True)
class RefundLine:
    name: str
    category: str
    paid_price: int
    restocking_fee: int
    item_refund: int
    restocking_source: str | None = None


@dataclass(frozen=True)
class ReturnRefund:
    lines: list[RefundLine]
    return_fee: int
    return_fee_reason: str
    total_refund: int
    policy_file: str
    sources: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ShippingRefund:
    standard_fee: int
    express_fee: int
    bulky_surcharge: int
    cod_fee: int
    total_refund: int
    reason: str


def return_policy_file(contact_date: date) -> str:
    if contact_date >= CURRENT_RETURN_POLICY:
        return "01_returns_policy.md"
    return "02_returns_policy_2025.md"


def _regional_applies(region: str, contact_date: date) -> bool:
    return (
        normalize_region(region) in {"remote", "international"}
        and contact_date >= REGIONAL_EFFECTIVE
    )


def return_window_days(category: str, *, region: str = "metro", contact_date: date) -> int | None:
    category_value = normalize_category(category)
    region_value = normalize_region(region)
    if region_value == "international" and _regional_applies(region_value, contact_date):
        return None if category_value == "grocery/perishables" else 10

    base = RETURN_WINDOWS_CURRENT if contact_date >= CURRENT_RETURN_POLICY else RETURN_WINDOWS_OLD
    days = base[category_value]
    if days is None:
        return None
    if region_value == "remote" and _regional_applies(region_value, contact_date):
        return days + 3
    return days


def is_return_in_window(
    *,
    category: str,
    delivery_date: date,
    request_date: date,
    region: str = "metro",
    contact_date: date | None = None,
) -> bool:
    effective_contact = contact_date or request_date
    days = return_window_days(category, region=region, contact_date=effective_contact)
    if days is None:
        return False
    return request_date <= add_days(delivery_date, days)


def restocking_fee(item: ReturnItem, contact_date: date) -> tuple[int, str | None]:
    if item.nova_error:
        return 0, None
    paid = int(as_amount(item.paid_price))
    category = item.category_value
    if category == "electronics" and item.opened:
        if contact_date >= CURRENT_RETURN_POLICY:
            return percentage(paid, 15), "01_returns_policy.md — Section 3.1"
        return percentage(paid, 10), "02_returns_policy_2025.md — Section 3.1"
    if category == "furniture/bulky":
        return percentage(paid, 10), "01_returns_policy.md — Section 3.3"
    return 0, None


def return_fee(
    items: list[ReturnItem],
    *,
    region: str = "metro",
    contact_date: date,
    request_is_nova_error: bool = False,
) -> tuple[int, str]:
    if not items:
        raise PolicyInputError("at least one return item is required")
    if request_is_nova_error:
        return 0, "No return fee is charged on a NovaCart error return."

    region_value = normalize_region(region)
    if region_value == "international" and _regional_applies(region_value, contact_date):
        return 0, "International customers arrange and pay their own return shipping."

    if region_value == "remote" and _regional_applies(region_value, contact_date):
        return 400, "Remote-area return label fee."

    if any(item.category_value == "furniture/bulky" for item in items):
        fee = 2_000 if contact_date >= CURRENT_RETURN_POLICY else 1_500
        return fee, "The request includes a furniture/bulky item, so the pickup fee applies."

    fee = 200 if contact_date >= CURRENT_RETURN_POLICY else 150
    return fee, "Return label fee."


def calculate_return_refund(
    items: list[ReturnItem],
    *,
    region: str = "metro",
    contact_date: date,
    request_is_nova_error: bool = False,
) -> ReturnRefund:
    if not items:
        raise PolicyInputError("at least one return item is required")

    lines: list[RefundLine] = []
    for item in items:
        paid = int(as_amount(item.paid_price))
        fee, source = restocking_fee(item, contact_date)
        lines.append(
            RefundLine(
                name=item.name,
                category=item.category_value,
                paid_price=paid,
                restocking_fee=fee,
                item_refund=max(0, paid - fee),
                restocking_source=source,
            )
        )

    fee, fee_reason = return_fee(
        items,
        region=region,
        contact_date=contact_date,
        request_is_nova_error=request_is_nova_error,
    )
    total = max(0, sum(line.item_refund for line in lines) - fee)
    policy = return_policy_file(contact_date)
    sources = [f"{policy} — Section 5"]
    if any(line.restocking_source for line in lines):
        sources.extend(sorted({line.restocking_source for line in lines if line.restocking_source}))
    if fee:
        sources.append(f"{policy} — Section 4")
    if normalize_region(region) == "remote" and _regional_applies(region, contact_date):
        sources.append("19_remote_areas_addendum.md — Section 4.2")
    if normalize_region(region) == "international" and _regional_applies(region, contact_date):
        sources.append("20_international_addendum.md — Section 6.3")

    return ReturnRefund(
        lines=lines,
        return_fee=fee,
        return_fee_reason=fee_reason,
        total_refund=total,
        policy_file=policy,
        sources=sources,
    )


def refundable_shipping_fees(
    *,
    standard_fee: int,
    express_fee: int = 0,
    bulky_surcharge: int = 0,
    cod_fee: int = 0,
    cancelled_before_dispatch: bool = False,
    lost_parcel: bool = False,
    all_items_returned_nova_error: bool = False,
    bulky_item_returned_nova_error: bool = False,
) -> ShippingRefund:
    core_refundable = cancelled_before_dispatch or lost_parcel or all_items_returned_nova_error
    bulky_refundable = cancelled_before_dispatch or lost_parcel or bulky_item_returned_nova_error
    standard = standard_fee if core_refundable else 0
    express = express_fee if core_refundable else 0
    bulky = bulky_surcharge if bulky_refundable else 0
    cod = cod_fee if core_refundable else 0
    if cancelled_before_dispatch:
        reason = "Cancellation before dispatch refunds every fee."
    elif lost_parcel:
        reason = "A lost parcel is refunded with every fee."
    elif all_items_returned_nova_error:
        reason = "Every item was returned because of a NovaCart error."
    elif bulky_item_returned_nova_error:
        reason = "The bulky item was returned because of a NovaCart error."
    else:
        reason = "Shipping, express, bulky and COD fees are not refunded."
    return ShippingRefund(
        standard_fee=standard,
        express_fee=express,
        bulky_surcharge=bulky,
        cod_fee=cod,
        total_refund=standard + express + bulky + cod,
        reason=reason,
    )
