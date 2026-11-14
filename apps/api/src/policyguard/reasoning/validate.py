from __future__ import annotations

from dataclasses import dataclass, field

from .models import Evidence, ModelOutput


class ModelOutputError(RuntimeError):
    pass


@dataclass(frozen=True)
class Citation:
    id: str
    filename: str
    section: str
    heading: str
    supporting_quote: str


@dataclass(frozen=True)
class AnswerPart:
    text: str
    citations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ValidatedAnswer:
    status: str
    answer: str
    parts: list[AnswerPart]
    citations: list[Citation]
    clarifying_question: str | None
    missing_fields: list[str]
    conflicts: list[str]


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _citation_id(evidence: Evidence) -> str:
    return f"{evidence.doc_id}-{evidence.section}"


def validate_model_output(
    output: ModelOutput,
    evidence: list[Evidence],
) -> ValidatedAnswer:
    evidence_by_chunk = {item.chunk_id: item for item in evidence}
    citations: dict[str, Citation] = {}
    parts: list[AnswerPart] = []

    if output.disposition == "CLARIFY" and not output.clarifying_question:
        raise ModelOutputError("CLARIFY output requires a clarifying question")
    if output.disposition == "ANSWER" and not output.covered_parts:
        raise ModelOutputError("ANSWER output requires supported claims")
    if output.disposition == "NOT_COVERED" and output.covered_parts:
        raise ModelOutputError("NOT_COVERED output must not contain supported claims")

    for claim in output.covered_parts:
        if not claim.claim.strip():
            raise ModelOutputError("empty claim")
        if not claim.evidence:
            raise ModelOutputError("claim has no evidence")
        part_citations: list[str] = []
        for cited in claim.evidence:
            evidence_item = evidence_by_chunk.get(cited.chunk_id)
            if evidence_item is None:
                raise ModelOutputError("model cited a chunk outside the supplied evidence")
            if not cited.quote.strip():
                raise ModelOutputError("empty supporting quote")
            if _normalize(cited.quote) not in _normalize(evidence_item.text):
                raise ModelOutputError("supporting quote is not an exact policy substring")
            citation_id = _citation_id(evidence_item)
            if citation_id not in citations:
                citations[citation_id] = Citation(
                    id=citation_id,
                    filename=evidence_item.filename,
                    section=evidence_item.section,
                    heading=evidence_item.heading,
                    supporting_quote=cited.quote,
                )
            if citation_id not in part_citations:
                part_citations.append(citation_id)
        parts.append(AnswerPart(text=claim.claim.strip(), citations=part_citations))

    if output.disposition == "ANSWER":
        answer = "Based on the supplied policies, " + " ".join(part.text for part in parts)
    elif output.disposition == "PARTIAL":
        covered = " ".join(part.text for part in parts) or "Some requested points are covered."
        uncovered = " ".join(output.uncovered_parts) or "A complete determination is not supported."
        answer = f"Covered: {covered}\nNot covered: {uncovered}"
    elif output.disposition == "CLARIFY":
        answer = output.clarifying_question or ""
    else:
        answer = "This is not covered by the supplied NovaCart policy files."

    if output.conflicts:
        answer = f"{answer}\nPolicy conflict: {' '.join(output.conflicts)}"
    if citations:
        sources = "; ".join(citation.id for citation in citations.values())
        answer = f"{answer}\nSources: {sources}."

    return ValidatedAnswer(
        status=output.disposition,
        answer=answer.strip(),
        parts=parts,
        citations=list(citations.values()),
        clarifying_question=output.clarifying_question,
        missing_fields=output.missing_fields,
        conflicts=output.conflicts,
    )
