import asyncio
from datetime import date

import pytest

from policyguard.config import APP_ROOT, REPO_ROOT, Settings
from policyguard.finance import FixedClock
from policyguard.reasoning import (
    Evidence,
    ExtractiveReasoner,
    ModelClaim,
    ModelEvidence,
    ModelOutput,
    ModelOutputError,
    PolicyService,
    build_evidence,
    validate_model_output,
)
from policyguard.retrieval import BM25Retriever
from policyguard.schemas import AskRequest, ConversationFacts, ConversationState


def _evidence() -> list[Evidence]:
    retriever = BM25Retriever.from_index(APP_ROOT / "data" / "index")
    return build_evidence(retriever.search("shipping fee Metro cities"), limit=5)


def _service() -> PolicyService:
    settings = Settings(
        gemini_api_key=None,
        policies_dir=REPO_ROOT / "policies",
        index_dir=APP_ROOT / "data" / "index",
    )
    retriever = BM25Retriever.from_index(settings.index_dir)
    return PolicyService(
        settings=settings,
        retriever=retriever,
        reasoner=ExtractiveReasoner(),
        clock=FixedClock(date(2026, 11, 14)),
    )


def test_validation_accepts_exact_quotes_and_builds_canonical_citation() -> None:
    evidence = _evidence()
    first = evidence[0]
    output = ModelOutput(
        disposition="ANSWER",
        covered_parts=[
            ModelClaim(
                claim="The policy states the relevant rule.",
                evidence=[ModelEvidence(chunk_id=first.chunk_id, quote=first.text)],
            )
        ],
    )

    result = validate_model_output(output, evidence)

    assert result.status == "ANSWER"
    assert result.citations[0].filename == first.filename
    assert result.citations[0].section == first.section
    assert result.citations[0].id.startswith("NC-POL-")


def test_validation_rejects_unknown_chunk_and_paraphrased_quote() -> None:
    evidence = _evidence()
    first = evidence[0]

    unknown = ModelOutput(
        disposition="ANSWER",
        covered_parts=[
            ModelClaim(
                claim="Unsupported.",
                evidence=[ModelEvidence(chunk_id="not-supplied", quote=first.text)],
            )
        ],
    )
    paraphrased = ModelOutput(
        disposition="ANSWER",
        covered_parts=[
            ModelClaim(
                claim="Unsupported.",
                evidence=[ModelEvidence(chunk_id=first.chunk_id, quote="A paraphrased rule.")],
            )
        ],
    )

    with pytest.raises(ModelOutputError):
        validate_model_output(unknown, evidence)
    with pytest.raises(ModelOutputError):
        validate_model_output(paraphrased, evidence)


def test_not_covered_uses_required_phrase() -> None:
    result = validate_model_output(
        ModelOutput(disposition="NOT_COVERED"),
        _evidence(),
    )

    assert result.answer == "This is not covered by the supplied NovaCart policy files."


def test_service_uses_resolved_date_and_citations() -> None:
    service = _service()
    request = AskRequest(question="What is the shipping fee for Metro cities?")

    response = asyncio.run(service.ask(request, request_id="req-1"))

    assert response.status == "ANSWER"
    assert response.resolved_contact_date == date(2026, 11, 14)
    assert response.citations
    filenames = {citation.filename for citation in response.citations}
    assert "06_shipping_fees_and_free_shipping.md" in filenames
    assert "21_shipping_fee_update_2027.md" not in filenames


def test_service_exposes_cod_conflict_in_offline_mode() -> None:
    service = _service()
    request = AskRequest(question="What is the maximum cash on delivery order amount?")

    response = asyncio.run(service.ask(request, request_id="req-2"))
    filenames = {citation.filename for citation in response.citations}

    assert response.status == "ANSWER"
    assert "Policy conflict" in response.answer
    assert "10_payments.md" in filenames
    assert "11_cod_and_failed_payments.md" in filenames


def test_service_returns_not_covered_for_unrelated_question() -> None:
    service = _service()
    request = AskRequest(question="What is the weather forecast on Mars?")

    response = asyncio.run(service.ask(request, request_id="req-3"))

    assert response.status == "NOT_COVERED"
    assert response.citations == []


def test_explicit_contact_date_unlocks_2027_shipping_rules() -> None:
    service = _service()
    request = AskRequest(
        question="What is the shipping fee for Metro cities?",
        conversation=ConversationState(
            facts=ConversationFacts(contact_date=date(2027, 2, 1)),
        ),
    )

    response = asyncio.run(service.ask(request, request_id="req-4"))

    assert response.resolved_contact_date == date(2027, 2, 1)
    filenames = {citation.filename for citation in response.citations}
    assert "21_shipping_fee_update_2027.md" in filenames
