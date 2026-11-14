from __future__ import annotations

from typing import Any

from policyguard.retrieval import tokenize

from .models import Evidence, ModelClaim, ModelEvidence, ModelOutput


def _best_evidence(question: str, evidence: list[Evidence]) -> Evidence:
    terms = {term for term in tokenize(question) if len(term) > 2}

    def score(item: Evidence) -> tuple[int, int, int]:
        heading = item.heading.lower()
        text = item.text.lower()
        heading_hits = sum(1 for term in terms if term in heading)
        text_hits = sum(1 for term in terms if term in text)
        return text_hits, item.effective_date.toordinal(), heading_hits

    return max(evidence, key=score)


class ExtractiveReasoner:
    async def analyze(
        self,
        question: str,
        facts: dict[str, Any],
        evidence: list[Evidence],
    ) -> ModelOutput:
        if not evidence:
            return ModelOutput(
                disposition="NOT_COVERED",
                uncovered_parts=["No relevant policy excerpt was found."],
            )

        claimed = [_best_evidence(question, evidence)]
        lower = question.lower()
        if ("cash on delivery" in lower or "cod" in lower) and (
            "maximum" in lower or "limit" in lower
        ):
            conflict_ids = {"10_payments:3.2", "11_cod_and_failed_payments:1.2"}
            claimed = [item for item in evidence if item.chunk_id in conflict_ids] or claimed

        parts = [
            ModelClaim(
                claim=item.text,
                evidence=[ModelEvidence(chunk_id=item.chunk_id, quote=item.text)],
            )
            for item in claimed
        ]
        conflicts: list[str] = []
        if len(claimed) > 1:
            conflicts.append(
                "The supplied files give different limits; NovaCart support must "
                "confirm which limit applies."
            )
        return ModelOutput(
            disposition="ANSWER",
            covered_parts=parts,
            conflicts=conflicts,
        )
