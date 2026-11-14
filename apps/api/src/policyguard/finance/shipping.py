from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .domain import (
    MissingFactError,
    PolicyInputError,
    normalize_country,
    normalize_region,
)
from .money import as_amount
from .promotions import evaluate_freeship

SHIPPING_2026 = {
    "metro": (250, 5_000),
    "rest_of_pakistan": (350, 7_500),
}
SHIPPING_2027 = {
    "metro": (300, 6_000),
    "rest_of_pakistan": (400, 8_500),
}
REMOTE_SHIPPING = (600, 12_000)
INTERNATIONAL_SHIPPING = {
    "UAE": 3_500,
    "UK": 5_500,
    "USA": 6_500,
}
EXPRESS_2026 = 500
EXPRESS_2027 = 600
BULKY_2026 = {"metro": 1_500, "rest_of_pakistan": 2_500}
BULKY_2027 = {"metro": 1_800, "rest_of_pakistan": 3_000}
COD_FEE = 100


@dataclass(frozen=True)
class ShippingBreakdown:
    region: str
    country: str | None
    standard_fee: int
    express_fee: int
    bulky_surcharge: int
    cod_fee: int
    total_shipping: int
    free_standard_shipping: bool
    freeship_applied: bool
    notes: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "region": self.region,
            "country": self.country,
            "standard_fee": self.standard_fee,
            "express_fee": self.express_fee,
            "bulky_surcharge": self.bulky_surcharge,
            "cod_fee": self.cod_fee,
            "total_shipping": self.total_shipping,
            "free_standard_shipping": self.free_standard_shipping,
            "freeship_applied": self.freeship_applied,
            "notes": list(self.notes),
            "sources": list(self.sources),
        }


def _shipping_version(contact_date: date) -> str:
    return "2027" if contact_date >= date(2027, 2, 1) else "2026"


def calculate_shipping(
    region: str,
    subtotal_after_discount: str | int | Decimal,
    contact_date: date,
    *,
    country: str | None = None,
    bulky_item_count: int = 0,
    contains_grocery: bool = False,
    express: bool = False,
    cod: bool = False,
    freeship: bool = False,
    order_date: date | None = None,
) -> ShippingBreakdown:
    region_value = normalize_region(region)
    subtotal = int(as_amount(subtotal_after_discount))
    if bulky_item_count < 0:
        raise PolicyInputError("bulky_item_count must not be negative")

    if region_value == "international":
        if country is None:
            raise MissingFactError("country is required for an international order")
        country_value = normalize_country(country)
        if contains_grocery:
            raise PolicyInputError("grocery/perishables cannot be delivered internationally")
        if bulky_item_count:
            raise PolicyInputError("furniture/bulky items cannot be delivered internationally")
        if express:
            raise PolicyInputError("express delivery is not available internationally")
        if cod:
            raise PolicyInputError("cash on delivery is not available internationally")
        fee = INTERNATIONAL_SHIPPING[country_value]
        notes = ["No free-shipping threshold and no FREESHIP for International orders."]
        if freeship:
            notes.append("FREESHIP is not valid for International orders.")
        return ShippingBreakdown(
            region=region_value,
            country=country_value,
            standard_fee=fee,
            express_fee=0,
            bulky_surcharge=0,
            cod_fee=0,
            total_shipping=fee,
            free_standard_shipping=False,
            freeship_applied=False,
            notes=notes,
            sources=["20_international_addendum.md — Section 4.1"],
        )

    if region_value == "remote":
        if contains_grocery:
            raise PolicyInputError("grocery/perishables are not available in Remote areas")
        if bulky_item_count:
            raise PolicyInputError("bulky items are not available in Remote areas")
        if express:
            raise PolicyInputError("express delivery is not available in Remote areas")
        if cod:
            raise PolicyInputError("cash on delivery is not available in Remote areas")
        fee, threshold = REMOTE_SHIPPING
        free = subtotal >= threshold
        notes = ["Remote-area fees are unchanged by the 2027 update."]
        if freeship:
            notes.append("FREESHIP is not valid for Remote areas.")
        return ShippingBreakdown(
            region=region_value,
            country=None,
            standard_fee=0 if free else fee,
            express_fee=0,
            bulky_surcharge=0,
            cod_fee=0,
            total_shipping=0 if free else fee,
            free_standard_shipping=free,
            freeship_applied=False,
            notes=notes,
            sources=["19_remote_areas_addendum.md — Section 2.1"],
        )

    if express and region_value != "metro":
        raise PolicyInputError("express delivery is available in Metro cities only")

    version = _shipping_version(contact_date)
    schedule = SHIPPING_2027 if version == "2027" else SHIPPING_2026
    fee, threshold = schedule[region_value]
    free = subtotal >= threshold
    freeship_result = evaluate_freeship(
        requested=freeship,
        region=region_value,
        subtotal_after_discount=subtotal,
        order_date=order_date,
    )

    standard_fee = 0 if free or freeship_result.applied else fee
    if express:
        standard_fee = 0
        express_fee = EXPRESS_2027 if version == "2027" else EXPRESS_2026
    else:
        express_fee = 0

    bulky_rate = (BULKY_2027 if version == "2027" else BULKY_2026)[region_value]
    bulky_surcharge = bulky_rate * bulky_item_count
    cod_fee = COD_FEE if cod else 0
    total = standard_fee + express_fee + bulky_surcharge + cod_fee

    sources = [
        "21_shipping_fee_update_2027.md — Section 1.1"
        if version == "2027"
        else "06_shipping_fees_and_free_shipping.md — Section 1.1"
    ]
    if express:
        sources.append("06_shipping_fees_and_free_shipping.md — Section 2.3")
    if bulky_item_count:
        sources.append("06_shipping_fees_and_free_shipping.md — Section 2.4")
    if cod:
        sources.append("11_cod_and_failed_payments.md — Section 2.1")

    notes = []
    if free and not express:
        notes.append("The post-discount subtotal meets the standard free-shipping threshold.")
    if freeship_result.requested:
        notes.append(freeship_result.reason)

    return ShippingBreakdown(
        region=region_value,
        country=None,
        standard_fee=standard_fee,
        express_fee=express_fee,
        bulky_surcharge=bulky_surcharge,
        cod_fee=cod_fee,
        total_shipping=total,
        free_standard_shipping=free or freeship_result.applied,
        freeship_applied=freeship_result.applied,
        notes=notes,
        sources=sources,
    )


def cod_limit_candidates() -> list[dict[str, int | str]]:
    return [
        {
            "limit": 40_000,
            "source": "10_payments.md — Section 3.2",
        },
        {
            "limit": 50_000,
            "source": "11_cod_and_failed_payments.md — Section 1.2",
        },
    ]
