from __future__ import annotations

from policyguard.retrieval import RetrievedChunk

from .models import Evidence


def _region_matches(filename: str, region: str | None) -> bool:
    if filename.startswith("19_remote_areas"):
        return region == "remote"
    if filename.startswith("20_international"):
        return region == "international"
    return True


def build_evidence(
    results: list[RetrievedChunk],
    limit: int = 12,
    *,
    region: str | None = None,
) -> list[Evidence]:
    evidence: list[Evidence] = []
    seen: set[str] = set()
    for result in results:
        chunk = result.chunk
        if chunk.chunk_id in seen:
            continue
        if chunk.scope == "regional" and not _region_matches(chunk.file_name, region):
            continue
        seen.add(chunk.chunk_id)
        section = chunk.item_numbers[0] if chunk.item_numbers else chunk.section_number
        evidence.append(
            Evidence(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                filename=chunk.file_name,
                section=section,
                heading=f"{chunk.section_number}. {chunk.section_title}",
                citation=chunk.citation,
                text=chunk.text,
                scope=chunk.scope,
                effective_date=chunk.effective_date,
            )
        )
        if len(evidence) >= limit:
            break
    return evidence
