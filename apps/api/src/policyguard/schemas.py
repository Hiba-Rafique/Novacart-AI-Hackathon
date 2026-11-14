from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal["ANSWER", "CLARIFY", "PARTIAL", "NOT_COVERED"]


class ConversationFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region: str | None = Field(default=None, max_length=40)
    country: str | None = Field(default=None, max_length=40)
    category: str | None = Field(default=None, max_length=40)
    payment_method: str | None = Field(default=None, max_length=40)
    promo_code: str | None = Field(default=None, max_length=20)
    return_type: str | None = Field(default=None, max_length=60)
    item_prices: list[Decimal] | None = Field(default=None, max_length=50)
    delivery_date: date | None = None
    order_date: date | None = None
    contact_date: date | None = None
    opened: bool | None = None
    first_order: bool | None = None
    tech500_used_this_month: bool | None = None
    express: bool | None = None
    cod: bool | None = None
    claimed_amount: Decimal | None = None

    @field_validator("item_prices")
    @classmethod
    def _prices_non_negative(cls, prices: list[Decimal] | None) -> list[Decimal] | None:
        if prices is not None and any(price < 0 for price in prices):
            raise ValueError("item prices must not be negative")
        return prices

    @field_validator("claimed_amount")
    @classmethod
    def _claimed_non_negative(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("claimed_amount must not be negative")
        return value


class ConversationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_question: str | None = Field(default=None, max_length=2_000)
    facts: ConversationFacts = Field(default_factory=ConversationFacts)
    last_asked_field: str | None = Field(default=None, max_length=60)


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2_000)
    conversation: ConversationState | None = None

    @field_validator("question")
    @classmethod
    def _question_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must not be blank")
        return stripped


class CitationResponse(BaseModel):
    id: str
    filename: str
    section: str
    heading: str
    supporting_quote: str


class AnswerPartResponse(BaseModel):
    text: str
    citations: list[str] = Field(default_factory=list)


class CalculationStep(BaseModel):
    description: str
    value: str


class CalculationResponse(BaseModel):
    currency: str = "PKR"
    amount: str
    steps: list[CalculationStep] = Field(default_factory=list)


class AskResponse(BaseModel):
    status: Status
    answer: str
    parts: list[AnswerPartResponse] = Field(default_factory=list)
    citations: list[CitationResponse] = Field(default_factory=list)
    calculation: CalculationResponse | None = None
    clarifying_question: str | None = None
    conversation: ConversationState
    resolved_contact_date: date
    request_id: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
