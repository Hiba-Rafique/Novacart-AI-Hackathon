from __future__ import annotations

from datetime import date
from typing import Any

from .known_issues import (
    resolve_bundle_promo,
    resolve_cod_limit,
    resolve_return_policy,
    resolve_shipping_update,
)
from .precedence import PrecedenceOutcome


def _outcome_summary(outcome: PrecedenceOutcome) -> dict[str, Any]:
    return {
        "topic": outcome.topic,
        "selected": (
            {
                "citation": outcome.selected.citation,
                "value": outcome.selected.value,
                "scope": outcome.selected.scope,
                "effective_date": outcome.selected.effective_date.isoformat(),
            }
            if outcome.selected is not None
            else None
        ),
        "conflicts": [
            {
                "citation": rule.citation,
                "value": rule.value,
                "effective_date": rule.effective_date.isoformat(),
            }
            for rule in outcome.conflicts
        ],
        "disclosures": outcome.disclosures,
        "reason": outcome.reason,
    }


def precedence_context(contact_date: date) -> dict[str, Any]:
    return {
        "cod_limit": _outcome_summary(resolve_cod_limit(contact_date)),
        "returns_version": _outcome_summary(resolve_return_policy(contact_date)),
        "shipping_fee_version": _outcome_summary(resolve_shipping_update(contact_date)),
        "bundle_vs_promo": _outcome_summary(resolve_bundle_promo(contact_date)),
    }
