from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .models import CorpusManifest, PolicyChunk
from .parser import parse_corpus

SCHEMA_VERSION = 1
CHUNKS_FILE = "chunks.jsonl"
MANIFEST_FILE = "manifest.json"


def _corpus_hash(policies_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(policies_dir.glob("*.md")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_index(policies_dir: Path, index_dir: Path) -> CorpusManifest:
    documents, chunks, quarantined = parse_corpus(policies_dir)
    manifest = CorpusManifest(
        schema_version=SCHEMA_VERSION,
        generated_at=datetime.now(UTC),
        corpus_hash=_corpus_hash(policies_dir),
        document_count=len(documents),
        chunk_count=len(chunks),
        quarantined_lines=quarantined,
        documents=documents,
    )

    index_dir.mkdir(parents=True, exist_ok=True)
    chunk_lines = "\n".join(
        json.dumps(chunk.model_dump(mode="json"), ensure_ascii=False) for chunk in chunks
    )
    (index_dir / CHUNKS_FILE).write_text(chunk_lines + "\n", encoding="utf-8")
    _write_json(index_dir / MANIFEST_FILE, manifest.model_dump(mode="json"))
    return manifest


def load_chunks(index_dir: Path) -> list[PolicyChunk]:
    path = index_dir / CHUNKS_FILE
    if not path.is_file():
        raise FileNotFoundError(f"index not found: {path}. Run `python -m policyguard.ingest.cli`.")
    return [
        PolicyChunk.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_manifest(index_dir: Path) -> CorpusManifest:
    path = index_dir / MANIFEST_FILE
    if not path.is_file():
        raise FileNotFoundError(
            f"manifest not found: {path}. Run `python -m policyguard.ingest.cli`."
        )
    return CorpusManifest.model_validate_json(path.read_text(encoding="utf-8"))
