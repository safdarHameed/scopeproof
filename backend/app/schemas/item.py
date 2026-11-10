import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["milestone", "extra", "fixed", "hourly", "expense", "other"]
Status = Literal["pending", "approved", "excluded"]


class FlagRead(BaseModel):
    code: str
    message: str


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID | None
    role: str
    quote: str
    location: str | None
    verified: bool


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    origin: str
    category: str
    description: str
    rationale: str | None
    quantity: Decimal
    unit_price: Decimal | None
    amount: Decimal | None
    status: str
    flags: list[FlagRead]
    flags_acknowledged: bool
    confidence: float | None
    edited: bool
    position: int
    evidence: list[EvidenceRead]
    created_at: datetime
    updated_at: datetime


class ItemCreate(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    category: Category = "other"
    rationale: str | None = Field(default=None, max_length=5000)
    quantity: Decimal = Field(default=Decimal(1), gt=0, max_digits=10, decimal_places=2)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class ItemUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=500)
    category: Category | None = None
    rationale: str | None = Field(default=None, max_length=5000)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    status: Status | None = None
    # Required to approve an item that still has review flags.
    acknowledge_flags: bool = False


class AnalysisRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engine: str
    status: str
    document_count: int
    item_count: int
    error: str | None
    created_at: datetime
    finished_at: datetime | None


class ReviewState(BaseModel):
    """Everything the review screen needs in one response."""

    analysis: AnalysisRunRead | None
    items: list[ItemRead]
    approved_total: Decimal
    pending_count: int
    flagged_count: int
    locked: bool  # true while an invoice is confirmed/sent/paid
    currency: str
