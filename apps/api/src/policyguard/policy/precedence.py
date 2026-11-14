from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

Scope = Literal["general", "specific", "regional"]
SCOPE_ORDER = {"general": 0, "specific": 1, "regional": 2}


@dataclass(frozen=True)
class PolicyRule:
    topic: str
    file_name: str
    citation: str
    scope: Scope
    effective_date: date
    value: Any
    region: str | None = None


@dataclass(frozen=True)
class PrecedenceOutcome:
    topic: str
    selected: PolicyRule | None
    candidates: list[PolicyRule] = field(default_factory=list)
    conflicts: list[PolicyRule] = field(default_factory=list)
    disclosures: list[str] = field(default_factory=list)
    reason: str = ""


def _highest_scope(rules: list[PolicyRule]) -> Scope:
    return max((rule.scope for rule in rules), key=lambda scope: SCOPE_ORDER[scope])


def _disclosure(selected: PolicyRule, others: list[PolicyRule]) -> list[str]:
    messages: list[str] = []
    for other in others:
        if other.file_name == selected.file_name:
            continue
        if other.effective_date != selected.effective_date:
            messages.append(
                f"{selected.file_name} and {other.file_name} differ; "
                f"{selected.file_name} has the later effective date "
                f"({selected.effective_date.isoformat()}) and was used."
            )
    return messages


def resolve_topic(
    topic: str,
    rules: list[PolicyRule],
    *,
    contact_date: date,
    region: str | None = None,
) -> PrecedenceOutcome:
    topic_rules = [rule for rule in rules if rule.topic == topic]
    in_force = [rule for rule in topic_rules if rule.effective_date <= contact_date]
    if not in_force:
        return PrecedenceOutcome(
            topic=topic,
            selected=None,
            reason="No rule for this topic is in force on the contact date.",
        )

    applicable: list[PolicyRule] = []
    for rule in in_force:
        if rule.scope != "regional" or (region is not None and rule.region == region):
            applicable.append(rule)

    if not applicable:
        return PrecedenceOutcome(
            topic=topic,
            selected=None,
            candidates=in_force,
            reason="No in-force rule applies to this region.",
        )

    regional = [rule for rule in applicable if rule.scope == "regional"]
    if regional:
        latest_regional = max(rule.effective_date for rule in regional)
        finalists = [rule for rule in regional if rule.effective_date == latest_regional]
        comparison_pool = applicable
        reason = "A regional rule overrides general and specific rules for its region."
    else:
        latest = max(rule.effective_date for rule in applicable)
        finalists = [rule for rule in applicable if rule.effective_date == latest]
        comparison_pool = applicable
        reason = "The in-force rule with the latest effective date applies."

    if len(finalists) > 1:
        highest_scope = _highest_scope(finalists)
        finalists = [rule for rule in finalists if rule.scope == highest_scope]
        reason = "The more specific scope applies when effective dates are equal."

    distinct_values = {repr(rule.value) for rule in finalists}
    if len(finalists) > 1 and len(distinct_values) > 1:
        return PrecedenceOutcome(
            topic=topic,
            selected=None,
            candidates=applicable,
            conflicts=finalists,
            reason=(
                "The in-force rules have the same effective date and scope but "
                "different values; NovaCart support must confirm."
            ),
        )

    selected = finalists[0]
    disclosures = _disclosure(selected, comparison_pool)
    if any(rule.scope == "regional" for rule in applicable):
        disclosures.append(
            f"{selected.file_name} is the regional rule for {region}; where it is silent, "
            "the general and specific files still apply."
        )
    return PrecedenceOutcome(
        topic=topic,
        selected=selected,
        candidates=applicable,
        disclosures=disclosures,
        reason=reason,
    )
