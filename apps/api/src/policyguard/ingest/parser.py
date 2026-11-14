from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .models import CrossReference, PolicyChunk, PolicyDocument, QuarantinedLine
from .sanitize import sanitize_line

_FRONTMATTER_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$")
_SECTION = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")
_ITEM = re.compile(r"^\*\*(\d+\.\d+)\*\*\s*(.*)$")
_CROSS_REFERENCE = re.compile(r"\[file\s+(\d{2})(?:,\s*Section\s+([0-9.]+))?\]")
_FILE_NUMBER = re.compile(r"^(\d{2})_")

_REQUIRED_FRONTMATTER = {
    "doc_id",
    "title",
    "version",
    "effective_date",
    "last_updated",
    "scope",
}


class PolicyParseError(ValueError):
    pass


@dataclass
class _Section:
    number: str
    title: str
    line_start: int
    preamble: list[tuple[int, str]] = field(default_factory=list)
    items: list[_Item] = field(default_factory=list)


@dataclass
class _Item:
    number: str
    line_start: int
    lines: list[tuple[int, str]] = field(default_factory=list)


@dataclass
class ParsedDocument:
    document: PolicyDocument
    chunks: list[PolicyChunk]
    quarantined: list[QuarantinedLine]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _split_frontmatter(lines: list[str]) -> tuple[dict[str, str], list[str], int]:
    if not lines or lines[0].strip() != "---":
        raise PolicyParseError("missing YAML frontmatter")

    try:
        closing = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration as exc:
        raise PolicyParseError("unterminated YAML frontmatter") from exc

    metadata: dict[str, str] = {}
    for line in lines[1:closing]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _FRONTMATTER_KEY.match(line)
        if not match:
            raise PolicyParseError(f"unsupported frontmatter line: {line!r}")
        metadata[match.group(1)] = match.group(2)

    missing = _REQUIRED_FRONTMATTER.difference(metadata)
    if missing:
        raise PolicyParseError(f"missing frontmatter keys: {sorted(missing)}")

    return metadata, lines[closing + 1 :], closing + 2


def _resolve_cross_references(text: str, file_names: dict[str, str]) -> list[CrossReference]:
    references: list[CrossReference] = []
    seen: set[str] = set()
    for match in _CROSS_REFERENCE.finditer(text):
        raw = match.group(0)
        if raw in seen:
            continue
        seen.add(raw)
        number = match.group(1)
        references.append(
            CrossReference(
                file_number=number,
                file_name=file_names.get(number, f"{number}_unknown.md"),
                section=match.group(2),
                raw=raw,
            )
        )
    return references


def _chunk_text(lines: list[tuple[int, str]]) -> tuple[str, bool]:
    cleaned = [line.rstrip() for _, line in lines]
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()
    text = "\n".join(cleaned)
    return text, any(line.lstrip().startswith("|") for line in cleaned)


def _build_chunk(
    *,
    file_name: str,
    metadata: dict[str, str],
    section: _Section,
    item: _Item | None,
    lines: list[tuple[int, str]],
    file_names: dict[str, str],
) -> PolicyChunk | None:
    text, has_table = _chunk_text(lines)
    if not text:
        return None

    item_numbers = [item.number] if item else []
    start = item.line_start if item else section.line_start
    end = lines[-1][0] if lines else start
    citation_section = item.number if item else section.number
    return PolicyChunk(
        chunk_id=f"{Path(file_name).stem}:{citation_section}",
        doc_id=metadata["doc_id"],
        file_name=file_name,
        doc_title=metadata["title"],
        scope=metadata["scope"],
        effective_date=date.fromisoformat(metadata["effective_date"]),
        last_updated=date.fromisoformat(metadata["last_updated"]),
        section_number=section.number,
        section_title=section.title,
        item_numbers=item_numbers,
        text=text,
        citation=f"{file_name} — Section {citation_section}",
        line_start=start,
        line_end=end,
        has_table=has_table,
        cross_references=_resolve_cross_references(text, file_names),
    )


def _iter_sections(entries: list[tuple[int, str]]) -> list[_Section]:
    sections: list[_Section] = []
    current: _Section | None = None
    current_item: _Item | None = None

    for line_number, line in entries:
        section_match = _SECTION.match(line)
        if section_match:
            current = _Section(
                number=section_match.group(1),
                title=section_match.group(2),
                line_start=line_number,
            )
            sections.append(current)
            current_item = None
            continue

        if current is None:
            continue

        item_match = _ITEM.match(line)
        if item_match:
            current_item = _Item(number=item_match.group(1), line_start=line_number)
            current_item.lines.append((line_number, line))
            current.items.append(current_item)
            continue

        target = current_item.lines if current_item is not None else current.preamble
        target.append((line_number, line))

    return sections


def parse_document(path: Path, file_names: dict[str, str]) -> ParsedDocument:
    raw = _read_text(path)
    lines = raw.splitlines()
    metadata, body, first_line_number = _split_frontmatter(lines)

    file_number_match = _FILE_NUMBER.match(path.name)
    if not file_number_match:
        raise PolicyParseError(f"unexpected policy file name: {path.name}")

    sanitized: list[tuple[int, str]] = []
    quarantined: list[QuarantinedLine] = []
    for offset, line in enumerate(body):
        line_number = first_line_number + offset
        kept, event = sanitize_line(path.name, line_number, line)
        if event is not None:
            quarantined.append(event)
        if kept is not None:
            sanitized.append((line_number, kept))

    sections = _iter_sections(sanitized)
    chunks: list[PolicyChunk] = []
    for section in sections:
        if section.preamble:
            preamble_chunk = _build_chunk(
                file_name=path.name,
                metadata=metadata,
                section=section,
                item=None,
                lines=section.preamble,
                file_names=file_names,
            )
            if preamble_chunk is not None:
                chunks.append(preamble_chunk)
        for item in section.items:
            chunk = _build_chunk(
                file_name=path.name,
                metadata=metadata,
                section=section,
                item=item,
                lines=item.lines,
                file_names=file_names,
            )
            if chunk is not None:
                chunks.append(chunk)

    all_cross_references: list[CrossReference] = []
    seen_refs: set[str] = set()
    for chunk in chunks:
        for reference in chunk.cross_references:
            if reference.raw not in seen_refs:
                seen_refs.add(reference.raw)
                all_cross_references.append(reference)

    checksum = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    document = PolicyDocument(
        doc_id=metadata["doc_id"],
        file_name=path.name,
        title=metadata["title"],
        version=metadata["version"],
        effective_date=date.fromisoformat(metadata["effective_date"]),
        last_updated=date.fromisoformat(metadata["last_updated"]),
        scope=metadata["scope"],
        checksum=checksum,
        line_count=len(lines),
        section_count=len(sections),
        item_count=sum(len(section.items) for section in sections),
        cross_references=all_cross_references,
    )
    return ParsedDocument(document=document, chunks=chunks, quarantined=quarantined)


def parse_corpus(
    policies_dir: Path,
) -> tuple[list[PolicyDocument], list[PolicyChunk], list[QuarantinedLine]]:
    paths = sorted(policies_dir.glob("*.md"))
    if not paths:
        raise PolicyParseError(f"no policy Markdown files found in {policies_dir}")

    file_names = {"".join(path.name[:2]): path.name for path in paths}
    documents: list[PolicyDocument] = []
    chunks: list[PolicyChunk] = []
    quarantined: list[QuarantinedLine] = []

    for path in paths:
        parsed = parse_document(path, file_names)
        documents.append(parsed.document)
        chunks.extend(parsed.chunks)
        quarantined.extend(parsed.quarantined)

    return documents, chunks, quarantined
