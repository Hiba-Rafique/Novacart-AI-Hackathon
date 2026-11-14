from datetime import date

import pytest

from policyguard.finance import (
    MissingFactError,
    MoneyError,
    PolicyInputError,
    PromoItem,
    ReturnItem,
    add_business_days,
    add_days,
    allocate,
    calculate_return_refund,
    calculate_shipping,
    cod_limit_candidates,
    credit_expiry,
    evaluate_discount,
    evaluate_freeship,
    export_price,
    full_months_between,
    gst_component,
    is_return_in_window,
    is_within_days,
    percentage,
    refundable_shipping_fees,
    resolve_contact_date,
    return_window_days,
    split_refund_with_store_credit,
    store_credit_bonus,
    warranty_refund,
    warranty_repair_days,
)


def test_money_rounding_and_allocation() -> None:
    assert gst_component(11_800) == 1_800
    assert export_price(11_800) == 10_000
    assert percentage(6_000, 15) == 900
    assert allocate(500, [5_000, 5_000, 5_500]) == [161, 161, 178]
    assert allocate(3_333, [2_500, 1_000, 500]) == [2_083, 833, 417]
    assert allocate(1, [10, 10, 10]) == [1, 0, 0]

    with pytest.raises(MoneyError):
        allocate(101, [100])
    with pytest.raises(MoneyError):
        percentage(100, 101)


def test_date_rules() -> None:
    assert full_months_between(date(2026, 1, 10), date(2026, 4, 9)) == 2
    assert full_months_between(date(2026, 1, 10), date(2026, 4, 10)) == 3
    assert add_business_days(date(2026, 1, 2), 1) == date(2026, 1, 5)
    assert is_within_days(date(2026, 1, 1), date(2026, 1, 11), 10)
    assert not is_within_days(date(2026, 1, 1), date(2026, 1, 12), 10)
    assert add_days(date(2026, 1, 1), 5) == date(2026, 1, 6)


def test_contact_date_requires_an_explicit_customer_date() -> None:
    explicit = resolve_contact_date(date(2026, 5, 1))

    assert explicit.contact_date == date(2026, 5, 1)
    assert explicit.source == "explicit"
    with pytest.raises(MissingFactError, match="contact date"):
        resolve_contact_date(None)


def test_style15_worked_example() -> None:
    items = [
        PromoItem("shirt", "clothing", 2_400),
        PromoItem("trousers", "clothing", 3_600),
    ]
    result = evaluate_discount("STYLE15", items, order_date=date(2026, 6, 1))

    assert result.applied
    assert result.eligible_subtotal == 6_000
    assert result.discount == 900


def test_discount_excludes_bundles_marketplace_and_final_sale() -> None:
    items = [
        PromoItem("bundle shirt", "clothing", 5_000, in_bundle=True),
        PromoItem("seller shirt", "clothing", 5_000, marketplace=True),
        PromoItem("final shirt", "clothing", 5_000, final_sale=True),
        PromoItem("normal shirt", "clothing", 4_000),
    ]
    result = evaluate_discount("STYLE15", items, order_date=date(2026, 6, 1))

    assert result.eligible_subtotal == 4_000
    assert result.discount == 600


def test_welcome10_grocery_exclusion() -> None:
    result = evaluate_discount(
        "WELCOME10",
        [PromoItem("rice", "grocery", 5_000)],
        order_date=date(2026, 6, 1),
        first_order=True,
    )

    assert not result.applied
    assert result.eligible_subtotal == 0


def test_tech500_requirements_and_expiry() -> None:
    items = [PromoItem("phone", "electronics", 15_500)]
    result = evaluate_discount(
        "TECH500",
        items,
        order_date=date(2026, 6, 1),
        tech500_used_this_month=False,
    )
    assert result.discount == 500

    with pytest.raises(MissingFactError):
        evaluate_discount("TECH500", items, order_date=date(2026, 6, 1))

    expired = evaluate_discount(
        "TECH500",
        items,
        order_date=date(2027, 2, 1),
        tech500_used_this_month=False,
    )
    assert not expired.applied


def test_freeship_rules() -> None:
    valid = evaluate_freeship(
        requested=True,
        region="metro",
        subtotal_after_discount=2_500,
        order_date=date(2026, 6, 1),
    )
    remote = evaluate_freeship(
        requested=True,
        region="remote",
        subtotal_after_discount=12_000,
        order_date=date(2026, 6, 1),
    )

    assert valid.applied
    assert not remote.applied


def test_shipping_schedules_and_express() -> None:
    assert calculate_shipping("metro", 6_000, date(2026, 6, 1)).standard_fee == 0
    assert calculate_shipping("metro", 4_680, date(2026, 6, 1)).standard_fee == 250
    assert calculate_shipping("metro", 5_999, date(2027, 2, 1)).standard_fee == 300
    assert calculate_shipping("rest_of_pakistan", 7_499, date(2026, 6, 1)).standard_fee == 350

    express = calculate_shipping("metro", 6_000, date(2026, 6, 1), express=True)
    assert express.standard_fee == 0
    assert express.express_fee == 500
    assert express.total_shipping == 500

    bulky = calculate_shipping(
        "metro",
        10_000,
        date(2027, 2, 1),
        bulky_item_count=2,
    )
    assert bulky.bulky_surcharge == 3_600


def test_shipping_freeship_and_cod() -> None:
    freeship = calculate_shipping(
        "metro",
        2_500,
        date(2026, 6, 1),
        freeship=True,
        order_date=date(2026, 6, 1),
    )
    assert freeship.standard_fee == 0
    assert freeship.freeship_applied

    cod = calculate_shipping("metro", 4_680, date(2026, 6, 1), cod=True)
    assert cod.cod_fee == 100
    assert cod.total_shipping == 350


def test_regional_shipping_rules() -> None:
    assert calculate_shipping("remote", 11_999, date(2026, 6, 1)).standard_fee == 600
    assert calculate_shipping("remote", 12_000, date(2026, 6, 1)).standard_fee == 0
    international = calculate_shipping("international", 99_000, date(2026, 6, 1), country="UAE")
    assert international.standard_fee == 3_500

    with pytest.raises(PolicyInputError):
        calculate_shipping("remote", 12_000, date(2026, 6, 1), express=True)
    with pytest.raises(PolicyInputError):
        calculate_shipping("international", 12_000, date(2026, 6, 1), country="UK", cod=True)


def test_cod_limit_conflict_is_exposed_not_resolved() -> None:
    limits = {item["limit"] for item in cod_limit_candidates()}

    assert limits == {40_000, 50_000}


def test_return_refund_worked_example() -> None:
    result = calculate_return_refund(
        [ReturnItem("shirt", "clothing", 2_040)],
        contact_date=date(2026, 6, 1),
    )

    assert result.lines[0].item_refund == 2_040
    assert result.return_fee == 200
    assert result.total_refund == 1_840


def test_restocking_and_error_exemptions() -> None:
    electronics = calculate_return_refund(
        [ReturnItem("headphones", "electronics", 1_000, opened=True)],
        contact_date=date(2026, 6, 1),
    )
    error = calculate_return_refund(
        [ReturnItem("headphones", "electronics", 1_000, opened=True, nova_error=True)],
        contact_date=date(2026, 6, 1),
        request_is_nova_error=True,
    )
    bulky = calculate_return_refund(
        [ReturnItem("sofa", "furniture/bulky", 5_000)],
        contact_date=date(2026, 6, 1),
    )

    assert electronics.lines[0].restocking_fee == 150
    assert electronics.total_refund == 650
    assert error.lines[0].restocking_fee == 0
    assert error.total_refund == 1_000
    assert bulky.lines[0].restocking_fee == 500
    assert bulky.return_fee == 2_000
    assert bulky.total_refund == 2_500


def test_old_return_policy_and_windows() -> None:
    old = calculate_return_refund(
        [ReturnItem("headphones", "electronics", 1_000, opened=True)],
        contact_date=date(2026, 2, 1),
    )
    assert old.lines[0].restocking_fee == 100
    assert old.return_fee == 150

    assert return_window_days("electronics", region="metro", contact_date=date(2026, 6, 1)) == 7
    assert return_window_days("electronics", region="remote", contact_date=date(2026, 6, 1)) == 10
    international_window = return_window_days(
        "electronics", region="international", contact_date=date(2026, 6, 1)
    )
    assert international_window == 10
    assert is_return_in_window(
        category="electronics",
        delivery_date=date(2026, 6, 1),
        request_date=date(2026, 6, 8),
        region="metro",
        contact_date=date(2026, 6, 8),
    )
    assert not is_return_in_window(
        category="electronics",
        delivery_date=date(2026, 6, 1),
        request_date=date(2026, 6, 9),
        region="metro",
        contact_date=date(2026, 6, 9),
    )


def test_shipping_fee_refund_conditions() -> None:
    full = refundable_shipping_fees(
        standard_fee=250,
        express_fee=500,
        bulky_surcharge=1_500,
        cod_fee=100,
        cancelled_before_dispatch=True,
    )
    partial_error = refundable_shipping_fees(
        standard_fee=250,
        express_fee=500,
        bulky_surcharge=1_500,
        cod_fee=100,
        bulky_item_returned_nova_error=True,
    )

    assert full.total_refund == 2_350
    assert partial_error.standard_fee == 0
    assert partial_error.bulky_surcharge == 1_500


def test_warranty_proration() -> None:
    result = warranty_refund(
        24_000,
        category="electronics",
        delivery_date=date(2026, 1, 10),
        claim_date=date(2026, 4, 12),
    )

    assert result.full_months_elapsed == 3
    assert result.refund == 18_000
    assert warranty_repair_days("remote") == 21


def test_store_credit_bonus_split_and_expiry() -> None:
    bonus = store_credit_bonus(8_000)
    capped = store_credit_bonus(30_000)
    split = split_refund_with_store_credit(8_000, 3_000)

    assert bonus.bonus == 400
    assert bonus.total_credit == 8_400
    assert capped.bonus == 1_000
    assert split.to_original_method == 3_000
    assert split.to_store_credit == 5_000
    assert credit_expiry(date(2026, 2, 28)) == date(2027, 2, 28)
