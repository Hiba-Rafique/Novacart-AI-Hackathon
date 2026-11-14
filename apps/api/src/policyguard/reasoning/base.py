from __future__ import annotations

from typing import Any, Protocol

from .models import Evidence, ModelOutput


class ReasonerError(RuntimeError):
    pass


class ReasonerUnavailable(ReasonerError):
    pass


class Reasoner(Protocol):
    async def analyze(
        self,
        question: str,
        facts: dict[str, Any],
        evidence: list[Evidence],
    ) -> ModelOutput: ...
