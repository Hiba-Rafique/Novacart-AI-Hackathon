from __future__ import annotations

from datetime import date

from .precedence import PolicyRule, PrecedenceOutcome, resolve_topic

COD_LIMIT_RULES = [
    PolicyRule(
        topic="cod_limit",
        file_name="10_payments.md",
        citation="10_payments.md — Section 3.2",
        scope="general",
        effective_date=date(2026, 5, 1),
        value=40_000,
    ),
    PolicyRule(
        topic="cod_limit",
        file_name="11_cod_and_failed_payments.md",
        citation="11_cod_and_failed_payments.md — Section 1.2",
        scope="general",
        effective_date=date(2026, 5, 1),
        value=50_000,
    ),
]

RETURN_POLICY_RULES = [
    PolicyRule(
        topic="returns",
        file_name="02_returns_policy_2025.md",
        citation="02_returns_policy_2025.md — Section 2",
        scope="general",
        effective_date=date(2025, 6, 1),
        value="2025",
    ),
    PolicyRule(
        topic="returns",
        file_name="01_returns_policy.md",
        citation="01_returns_policy.md — Section 2",
        scope="general",
        effective_date=date(2026, 3, 1),
        value="2026",
    ),
]

SHIPPING_UPDATE_RULES = [
    PolicyRule(
        topic="shipping_fees",
        file_name="06_shipping_fees_and_free_shipping.md",
        citation="06_shipping_fees_and_free_shipping.md — Section 1",
        scope="general",
        effective_date=date(2026, 1, 15),
        value="2026",
    ),
    PolicyRule(
        topic="shipping_fees",
        file_name="21_shipping_fee_update_2027.md",
        citation="21_shipping_fee_update_2027.md — Section 1",
        scope="general",
        effective_date=date(2027, 2, 1),
        value="2027",
    ),
]

BUNDLE_PROMO_RULES = [
    PolicyRule(
        topic="bundle_promo",
        file_name="12_promo_code_rules.md",
        citation="12_promo_code_rules.md — Section 1.5",
        scope="general",
        effective_date=date(2026, 6, 1),
        value="bundle items are eligible for discount codes",
    ),
    PolicyRule(
        topic="bundle_promo",
        file_name="13_sales_and_bundles.md",
        citation="13_sales_and_bundles.md — Section 4.2",
        scope="specific",
        effective_date=date(2026, 6, 1),
        value="bundle items are not eligible for discount codes",
    ),
]


def resolve_cod_limit(contact_date: date) -> PrecedenceOutcome:
    return resolve_topic("cod_limit", COD_LIMIT_RULES, contact_date=contact_date)


def resolve_return_policy(contact_date: date) -> PrecedenceOutcome:
    return resolve_topic("returns", RETURN_POLICY_RULES, contact_date=contact_date)


def resolve_shipping_update(contact_date: date) -> PrecedenceOutcome:
    return resolve_topic("shipping_fees", SHIPPING_UPDATE_RULES, contact_date=contact_date)


def resolve_bundle_promo(contact_date: date) -> PrecedenceOutcome:
    return resolve_topic("bundle_promo", BUNDLE_PROMO_RULES, contact_date=contact_date)
