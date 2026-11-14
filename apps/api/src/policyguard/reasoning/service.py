from __future__ import annotations

from typing import Any

from policyguard.config import Settings
from policyguard.finance import resolve_contact_date
from policyguard.policy import precedence_context
from policyguard.retrieval import Retriever
from policyguard.schemas import (
    AnswerPartResponse,
    AskRequest,
    AskResponse,
    CitationResponse,
    ConversationFacts,
    ConversationState,
)

from .base import Reasoner
from .evidence import build_evidence
from .extractive import ExtractiveReasoner
from .facts import extract_contact_date
from .gemini import GeminiReasoner
from .validate import validate_model_output


class PolicyService:
    def __init__(
        self,
        *,
        settings: Settings,
        retriever: Retriever,
        reasoner: Reasoner,
    ) -> None:
        self._settings = settings
        self._retriever = retriever
        self._reasoner = reasoner

    async def ask(self, request: AskRequest, *, request_id: str) -> AskResponse:
        conversation = request.conversation or ConversationState()
        facts = conversation.facts
        try:
            message_contact_date = extract_contact_date(
                request.question,
                awaiting_contact_date=conversation.last_asked_field == "contact_date",
            )
            if message_contact_date is not None:
                facts = facts.model_copy(update={"contact_date": message_contact_date})
            resolution = resolve_contact_date(facts.contact_date)
        except ValueError as exc:
            question = str(exc)
            return AskResponse(
                status="CLARIFY",
                answer=question,
                clarifying_question=question,
                conversation=ConversationState(
                    original_question=conversation.original_question or request.question,
                    facts=facts.model_copy(update={"contact_date": None}),
                    last_asked_field="contact_date",
                ),
                resolved_contact_date=None,
                request_id=request_id,
            )

        question = request.question
        if conversation.original_question:
            question = f"{conversation.original_question}\nCustomer follow-up: {request.question}"

        results = self._retriever.search(
            question,
            self._settings.rag_top_k,
            max_effective_date=resolution.contact_date,
        )
        evidence = build_evidence(results, limit=12, region=facts.region)
        prompt_facts: dict[str, Any] = facts.model_dump(mode="json", exclude_none=True)
        prompt_facts["resolved_contact_date"] = resolution.contact_date.isoformat()
        prompt_facts["resolved_contact_date_source"] = resolution.source
        prompt_facts["policy_precedence"] = precedence_context(resolution.contact_date)

        output = await self._reasoner.analyze(question, prompt_facts, evidence)
        validated = validate_model_output(output, evidence)

        if validated.status == "CLARIFY":
            response_conversation = ConversationState(
                original_question=conversation.original_question or request.question,
                facts=facts,
                last_asked_field=(
                    validated.missing_fields[0] if validated.missing_fields else None
                ),
            )
        else:
            response_conversation = ConversationState(
                original_question=None,
                facts=facts,
                last_asked_field=None,
            )

        return AskResponse(
            status=validated.status,
            answer=validated.answer,
            parts=[
                AnswerPartResponse(text=part.text, citations=part.citations)
                for part in validated.parts
            ],
            citations=[
                CitationResponse(
                    id=citation.id,
                    filename=citation.filename,
                    section=citation.section,
                    heading=citation.heading,
                    supporting_quote=citation.supporting_quote,
                )
                for citation in validated.citations
            ],
            calculation=None,
            clarifying_question=validated.clarifying_question,
            conversation=response_conversation,
            resolved_contact_date=resolution.contact_date,
            request_id=request_id,
        )


def create_reasoner(settings: Settings) -> Reasoner:
    if settings.has_gemini:
        return GeminiReasoner(settings)
    return ExtractiveReasoner()


def create_service(settings: Settings, retriever: Retriever) -> PolicyService:
    return PolicyService(
        settings=settings,
        retriever=retriever,
        reasoner=create_reasoner(settings),
    )


def default_facts() -> ConversationFacts:
    return ConversationFacts()
