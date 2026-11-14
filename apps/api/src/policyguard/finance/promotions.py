from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .domain import (
    Category,
    MissingFactError,
    NotApplicableError,
    PolicyInputError,
    normalize_category,
)
from .money import allocate, as_amount, percentage

PROMO_SOURCE = "12_promo_code_rules.md"


@dataclass(frozen=True)
class PromoItem:
    name: str
    category: str
    price: str | int | Decimal
    quantity: int = 1
    marketplace: bool = False
    final_sale: bool = False
    in_bundle: bool = False

    @property
    def category_value(self) -> Category:
        return normalize_category(self.category)

    @property
    def subtotal(self) -> Decimal:
        return as_amount(self.price) * self.quantity


@dataclass(frozen=True)
class DiscountEvaluation:
    code: str
    applied: bool
    eligible_subtotal: int
    discount: int
    reason: str
    source: str = PROMO_SOURCE


@dataclass(frozen=True)
class FreeShippingEvaluation:
    requested: bool
    applied: bool
    subtotal_after_discount: int
    reason: str
    source: str = PROMO_SOURCE


@dataclass(frozen=True)
class DiscountSpec:
    code: str
    kind: str
    rate: int | None
    fixed: int | None
    minimum: int
    cap: int
    last_order_date: date
    categories: tuple[Category, ...] | None
    excludes_grocery: bool = False
    first_order_only: bool = False
    monthly_limit: bool = False


CODES: dict[str, DiscountSpec] = {
    "WELCOME10": DiscountSpec(
        code="WELCOME10",
        kind="percentage",
        rate=10,
        fixed=None,
        minimum=3_000,
        cap=1_000,
        last_order_date=date(2026, 12, 31),
        categories=None,
        excludes_grocery=True,
        first_order_only=True,
    ),
    "STYLE15": DiscountSpec(
        code="STYLE15",
        kind="percentage",
        rate=15,
        fixed=None,
        minimum=4_000,
        cap=1_500,
        last_order_date=date(2026, 8, 31),
        categories=("clothing",),
    ),
    "TECH500": DiscountSpec(
        code="TECH500",
        kind="fixed",
        rate=None,
        fixed=500,
        minimum=15_000,
        cap=500,
        last_order_date=date(2027, 1, 31),
        categories=("electronics",),
        monthly_limit=True,
    ),
}


def _eligible_items(code: str, items: list[PromoItem]) -> list[PromoItem]:
    spec = CODES[code]
    eligible: list[PromoItem] = []
    for item in items:
        if item.marketplace or item.final_sale or item.in_bundle:
            continue
        if spec.categories is not None and item.category_value not in spec.categories:
            continue
        if spec.excludes_grocery and item.category_value == "grocery/perishables":
            continue
        eligible.append(item)
    return eligible


def evaluate_discount(
    code: str,
    items: list[PromoItem],
    *,
    order_date: date | None,
    first_order: bool | None = None,
    tech500_used_this_month: bool | None = None,
) -> DiscountEvaluation:
    normalized = code.strip().upper()
    if normalized == "FREESHIP":
        raise PolicyInputError("FREESHIP is a shipping code, not a discount code")

    try:
        spec = CODES[normalized]
    except KeyError as exc:
        raise NotApplicableError(f"unknown promo code: {code}") from exc

    if order_date is None:
        raise MissingFactError("order_date is required to check a promo code")
    if order_date > spec.last_order_date:
        return DiscountEvaluation(
            code=normalized,
            applied=False,
            eligible_subtotal=0,
            discount=0,
            reason=f"code expired after {spec.last_order_date.isoformat()}",
        )
    if spec.first_order_only:
        if first_order is None:
            raise MissingFactError("first_order is required for WELCOME10")
        if not first_order:
            return DiscountEvaluation(
                code=normalized,
                applied=False,
                eligible_subtotal=0,
                discount=0,
                reason="WELCOME10 is limited to a customer's first order",
            )
    if spec.monthly_limit:
        if tech500_used_this_month is None:
            raise MissingFactError("TECH500 monthly usage is required")
        if tech500_used_this_month:
            return DiscountEvaluation(
                code=normalized,
                applied=False,
                eligible_subtotal=0,
                discount=0,
                reason="TECH500 can be used only once per customer per calendar month",
            )

    eligible = _eligible_items(normalized, items)
    eligible_subtotal = int(sum((item.subtotal for item in eligible), Decimal("0")))
    if eligible_subtotal < spec.minimum:
        return DiscountEvaluation(
            code=normalized,
            applied=False,
            eligible_subtotal=eligible_subtotal,
            discount=0,
            reason=f"eligible subtotal is below the Rs. {spec.minimum:,} minimum",
        )

    if spec.kind == "percentage":
        assert spec.rate is not None
        discount = min(percentage(eligible_subtotal, spec.rate), spec.cap)
    else:
        assert spec.fixed is not None
        discount = min(spec.fixed, eligible_subtotal, spec.cap)

    return DiscountEvaluation(
        code=normalized,
        applied=True,
        eligible_subtotal=eligible_subtotal,
        discount=discount,
        reason=f"{normalized} applied to {len(eligible)} eligible item(s)",
    )


def evaluate_freeship(
    *,
    requested: bool,
    region: str,
    subtotal_after_discount: str | int | Decimal,
    order_date: date | None,
) -> FreeShippingEvaluation:
    subtotal = int(as_amount(subtotal_after_discount))
    if not requested:
        return FreeShippingEvaluation(
            requested=False,
            applied=False,
            subtotal_after_discount=subtotal,
            reason="FREESHIP was not requested",
        )
    if order_date is None:
        raise MissingFactError("order_date is required to check FREESHIP")
    if order_date > date(2026, 12, 31):
        return FreeShippingEvaluation(
            requested=True,
            applied=False,
            subtotal_after_discount=subtotal,
            reason="FREESHIP expired after 2026-12-31",
        )
    if region not in {"metro", "rest_of_pakistan"}:
        return FreeShippingEvaluation(
            requested=True,
            applied=False,
            subtotal_after_discount=subtotal,
            reason="FREESHIP is not valid for Remote areas or International orders",
        )
    if subtotal < 2_000:
        return FreeShippingEvaluation(
            requested=True,
            applied=False,
            subtotal_after_discount=subtotal,
            reason="FREESHIP needs a post-discount merchandise subtotal of at least Rs. 2,000",
        )
    return FreeShippingEvaluation(
        requested=True,
        applied=True,
        subtotal_after_discount=subtotal,
        reason="FREESHIP removes the standard shipping fee",
    )


def allocate_discount(discount: int, eligible_items: list[PromoItem]) -> list[int]:
    return allocate(discount, [item.subtotal for item in eligible_items])


def bundle_shares(
    bundle_price: str | int | Decimal,
    list_prices: list[str | int | Decimal],
) -> list[int]:
    return allocate(bundle_price, list_prices)
