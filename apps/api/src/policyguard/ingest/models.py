from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class CrossReference(BaseModel):
    file_number: str
    file_name: str
    section: str | None = None
    raw: str


class PolicyDocument(BaseModel):
    doc_id: str
    file_name: str
    title: str
    version: str
    effective_date: date
    last_updated: date
    scope: str
    checksum: str
    line_count: int
    section_count: int
    item_count: int
    cross_references: list[CrossReference] = Field(default_factory=list)


class PolicyChunk(BaseModel):
    chunk_id: str
    doc_id: str
    file_name: str
    doc_title: str
    scope: str
    effective_date: date
    last_updated: date
    section_number: str
    section_title: str
    item_numbers: list[str] = Field(default_factory=list)
    text: str
    citation: str
    line_start: int
    line_end: int
    has_table: bool = False
    cross_references: list[CrossReference] = Field(default_factory=list)

    @property
    def retrieval_text(self) -> str:
        items = ", ".join(self.item_numbers) if self.item_numbers else "section"
        return (
            f"{self.file_name}\n{self.doc_title}\n"
            f"Section {self.section_number}: {self.section_title}\n"
            f"Items: {items}\n{self.text}"
        )


class QuarantinedLine(BaseModel):
    file_name: str
    line_number: int
    reason: str


class CorpusManifest(BaseModel):
    schema_version: int = 1
    generated_at: datetime
    corpus_hash: str
    document_count: int
    chunk_count: int
    quarantined_lines: list[QuarantinedLine] = Field(default_factory=list)
    documents: list[PolicyDocument] = Field(default_factory=list)
