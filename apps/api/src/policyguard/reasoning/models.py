from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Disposition = Literal["ANSWER", "CLARIFY", "PARTIAL", "NOT_COVERED"]


class ModelEvidence(BaseModel):
    chunk_id: str
    quote: str


class ModelClaim(BaseModel):
    claim: str
    evidence: list[ModelEvidence] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)


class CalculationProposal(BaseModel):
    calculation_type: str
    arguments: dict[str, str] = Field(default_factory=dict)


class ModelOutput(BaseModel):
    disposition: Disposition
    covered_parts: list[ModelClaim] = Field(default_factory=list)
    uncovered_parts: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    clarifying_question: str | None = None
    calculation: CalculationProposal | None = None
    conflicts: list[str] = Field(default_factory=list)


class Evidence:
    __slots__ = (
        "chunk_id",
        "doc_id",
        "filename",
        "section",
        "heading",
        "citation",
        "text",
        "scope",
        "effective_date",
    )

    def __init__(
        self,
        *,
        chunk_id: str,
        doc_id: str,
        filename: str,
        section: str,
        heading: str,
        citation: str,
        text: str,
        scope: str,
        effective_date: date,
    ) -> None:
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.filename = filename
        self.section = section
        self.heading = heading
        self.citation = citation
        self.text = text
        self.scope = scope
        self.effective_date = effective_date

    def prompt_block(self) -> str:
        return (
            f"[{self.chunk_id}]\n"
            f"{self.filename} — Section {self.section}\n"
            f"{self.heading}\n"
            f"Scope: {self.scope}; effective: {self.effective_date.isoformat()}\n"
            f"{self.text}"
        )
