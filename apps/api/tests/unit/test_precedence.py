import json
from datetime import date

from policyguard.policy import (
    PolicyRule,
    precedence_context,
    resolve_bundle_promo,
    resolve_cod_limit,
    resolve_return_policy,
    resolve_shipping_update,
    resolve_topic,
)


def test_cod_conflict_is_left_unresolved() -> None:
    outcome = resolve_cod_limit(date(2026, 6, 1))

    assert outcome.selected is None
    assert {rule.value for rule in outcome.conflicts} == {40_000, 50_000}
    assert "support" in outcome.reason.lower()


def test_later_return_policy_wins_and_discloses_old_version() -> None:
    old = resolve_return_policy(date(2025, 7, 1))
    current = resolve_return_policy(date(2026, 6, 1))

    assert old.selected is not None and old.selected.value == "2025"
    assert current.selected is not None and current.selected.value == "2026"
    assert any("01_returns_policy.md" in note for note in current.disclosures)
    assert any("02_returns_policy_2025.md" in note for note in current.disclosures)


def test_shipping_update_only_applies_from_2027() -> None:
    before = resolve_shipping_update(date(2027, 1, 31))
    after = resolve_shipping_update(date(2027, 2, 1))

    assert before.selected is not None and before.selected.value == "2026"
    assert after.selected is not None and after.selected.value == "2027"
    assert any("later effective date" in note for note in after.disclosures)


def test_specific_bundle_rule_beats_general_promo_rule() -> None:
    outcome = resolve_bundle_promo(date(2026, 6, 1))

    assert outcome.selected is not None
    assert outcome.selected.file_name == "13_sales_and_bundles.md"
    assert "specific" in outcome.reason


def test_precedence_context_is_prompt_safe_and_date_aware() -> None:
    context = precedence_context(date(2027, 3, 1))

    json.dumps(context)
    assert context["shipping_fee_version"]["selected"]["value"] == "2027"
    assert context["returns_version"]["selected"]["value"] == "2026"
    assert len(context["cod_limit"]["conflicts"]) == 2


def test_regional_rule_overrides_regardless_of_date() -> None:
    rules = [
        PolicyRule(
            "shipping",
            "06_general.md",
            "06_general.md — Section 1",
            "general",
            date(2027, 1, 1),
            "general",
        ),
        PolicyRule(
            "shipping",
            "19_remote.md",
            "19_remote.md — Section 2",
            "regional",
            date(2026, 1, 1),
            "remote",
            region="remote",
        ),
    ]
    outcome = resolve_topic("shipping", rules, contact_date=date(2027, 6, 1), region="remote")

    assert outcome.selected is not None
    assert outcome.selected.value == "remote"
    assert any("regional rule" in note for note in outcome.disclosures)
