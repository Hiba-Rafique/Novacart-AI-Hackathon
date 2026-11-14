from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Protocol

from rank_bm25 import BM25Okapi

from policyguard.ingest import PolicyChunk, load_chunks

from .tokenize import tokenize


class Retriever(Protocol):
    def search(
        self,
        query: str,
        top_k: int | None = None,
        max_effective_date: date | None = None,
    ) -> list[RetrievedChunk]: ...


class RetrievedChunk:
    def __init__(self, chunk: PolicyChunk, score: float, rank: int) -> None:
        self.chunk = chunk
        self.score = score
        self.rank = rank

    def __repr__(self) -> str:
        return f"RetrievedChunk({self.chunk.citation!r}, score={self.score:.4f}, rank={self.rank})"


class BM25Retriever:
    def __init__(self, chunks: list[PolicyChunk], default_top_k: int = 15) -> None:
        if not chunks:
            raise ValueError("cannot build a retriever with no chunks")
        self._chunks = chunks
        self._default_top_k = default_top_k
        self._corpus_tokens = [tokenize(chunk.retrieval_text) for chunk in chunks]
        self._bm25 = BM25Okapi(self._corpus_tokens)

    @classmethod
    def from_index(cls, index_dir: Path, default_top_k: int = 15) -> BM25Retriever:
        return cls(load_chunks(index_dir), default_top_k=default_top_k)

    def search(
        self,
        query: str,
        top_k: int | None = None,
        max_effective_date: date | None = None,
    ) -> list[RetrievedChunk]:
        query_tokens = tokenize(query, expand=True)
        if not query_tokens:
            return []

        limit = top_k if top_k is not None else self._default_top_k
        scores = self._bm25.get_scores(query_tokens)
        ranked = sorted(
            (
                (index, float(score))
                for index, score in enumerate(scores)
                if score > 0
                and (
                    max_effective_date is None
                    or self._chunks[index].effective_date <= max_effective_date
                )
            ),
            key=lambda pair: (-pair[1], self._chunks[pair[0]].chunk_id),
        )[:limit]
        return [
            RetrievedChunk(chunk=self._chunks[index], score=score, rank=rank)
            for rank, (index, score) in enumerate(ranked, start=1)
        ]
