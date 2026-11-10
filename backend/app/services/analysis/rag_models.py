"""Strict LLM output contracts, separate from the public review API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Candidates(StrictModel):
    work_items: list[str] = Field(description="Distinct work names, including unapproved requests")


class Citation(StrictModel):
    chunk_id: str
    quote: str
    role: Literal[
        "contract_term", "request", "price", "approval", "completion", "acceptance", "other"
    ]


class Decision(StrictModel):
    description: str
    category: Literal["milestone", "extra", "fixed", "hourly", "expense", "other"]
    quantity: str = Field(description="Positive decimal string, never a float")
    unit_price: str | None = Field(description="Nonnegative decimal string, null if unclear")
    currency: str | None
    rationale: str
    price_approved: bool
    ready_to_invoice: bool
    conflicting_price: bool
    confidence: float
    evidence: list[Citation]
