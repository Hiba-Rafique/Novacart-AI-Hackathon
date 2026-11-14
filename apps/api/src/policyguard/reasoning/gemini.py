from __future__ import annotations

import asyncio
import re
from typing import Any

from google import genai
from google.genai import types

from policyguard.config import Settings

from .base import ReasonerUnavailable
from .models import Evidence, ModelOutput
from .prompt import SYSTEM_PROMPT, build_user_prompt

_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


class GeminiReasoner:
    def __init__(self, settings: Settings) -> None:
        if not settings.has_gemini:
            raise ReasonerUnavailable("GEMINI_API_KEY is not configured")
        self._settings = settings
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def analyze(
        self,
        question: str,
        facts: dict[str, Any],
        evidence: list[Evidence],
    ) -> ModelOutput:
        user_prompt = build_user_prompt(question, facts, evidence)
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            max_output_tokens=2_048,
            response_mime_type="application/json",
            response_schema=ModelOutput,
        )
        try:
            async with asyncio.timeout(self._settings.model_timeout_seconds):
                response = await self._client.aio.models.generate_content(
                    model=self._settings.gemini_model,
                    contents=user_prompt,
                    config=config,
                )
        except TimeoutError as exc:
            raise ReasonerUnavailable("model request timed out") from exc
        except Exception as exc:
            raise ReasonerUnavailable("model request failed") from exc

        parsed = response.parsed
        if isinstance(parsed, ModelOutput):
            return parsed
        if isinstance(parsed, dict):
            return ModelOutput.model_validate(parsed)

        text = (response.text or "").strip()
        fenced = _FENCE.match(text)
        if fenced:
            text = fenced.group(1)
        try:
            return ModelOutput.model_validate_json(text)
        except Exception as exc:
            raise ReasonerUnavailable("model returned invalid structured output") from exc
