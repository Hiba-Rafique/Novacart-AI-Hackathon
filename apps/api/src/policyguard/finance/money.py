from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_ONE = Decimal("1")


class MoneyError(ValueError):
    pass


def as_amount(value: str | int | float | Decimal) -> Decimal:
    raw = str(value)
    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise MoneyError(f"invalid amount: {value!r}") from exc
    if not amount.is_finite():
        raise MoneyError("amount must be finite")
    if amount < 0:
        raise MoneyError("amount must not be negative")
    return amount.quantize(_ONE, rounding=ROUND_HALF_UP)


def round_half_up(value: Decimal) -> int:
    if not value.is_finite():
        raise MoneyError("value must be finite")
    return int(value.quantize(_ONE, rounding=ROUND_HALF_UP))


def percentage(base: str | int | Decimal, rate: str | int | Decimal) -> int:
    base_amount = as_amount(base)
    rate_amount = Decimal(str(rate))
    if not rate_amount.is_finite() or rate_amount < 0 or rate_amount > 100:
        raise MoneyError("rate must be between 0 and 100")
    return round_half_up(base_amount * rate_amount / Decimal("100"))


def gst_component(inclusive_price: str | int | Decimal) -> int:
    price = as_amount(inclusive_price)
    return round_half_up(price * Decimal("18") / Decimal("118"))


def export_price(listed_price: str | int | Decimal) -> int:
    price = as_amount(listed_price)
    return round_half_up(price / Decimal("1.18"))


def allocate(total: str | int | Decimal, bases: Iterable[str | int | Decimal]) -> list[int]:
    total_amount = as_amount(total)
    base_amounts = [as_amount(base) for base in bases]
    if not base_amounts:
        raise MoneyError("at least one base is required")

    base_sum = sum(base_amounts, Decimal("0"))
    if base_sum <= 0:
        raise MoneyError("base sum must be positive")
    if total_amount > base_sum:
        raise MoneyError("total must not exceed the sum of bases")

    shares = [
        round_half_up(total_amount * base / base_sum) if base > 0 else 0 for base in base_amounts
    ]
    residual = int(total_amount) - sum(shares)
    if residual:
        target = max(
            range(len(base_amounts)),
            key=lambda index: (base_amounts[index], -index),
        )
        shares[target] += residual
    if any(share < 0 for share in shares):
        raise MoneyError("allocation produced a negative share")
    if sum(shares) != int(total_amount):
        raise MoneyError("allocation did not conserve the total")
    return shares
