"""Contract between the app and an analysis engine (placeholder now, RAG later).

An engine receives the project's processed documents and returns suggested invoice items,
each with the quotes that support it. The app takes care of everything else: storing the
items, checking that every quote really appears in its document, and the review flow.

To plug in the RAG engine:
  1. Implement `Analyzer` in app/services/analysis/rag.py
  2. Register it in `get_analyzer()` in app/services/analysis/__init__.py
  3. Set ANALYZER=rag in backend/.env
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol


class FlagCode:
    MISSING_APPROVAL = "missing_approval"  # price/work never approved by the client
    CONFLICTING_PRICE = "conflicting_price"  # sources disagree on the price
    UNCLEAR_PRICE = "unclear_price"  # no usable price found
    NOT_READY = "not_ready"  # work not delivered/accepted yet
    LOW_CONFIDENCE = "low_confidence"  # engine is unsure; a human should check
    UNSUPPORTED = "unsupported"  # no quote could be verified in the documents (set by the app)


class EvidenceRole:
    CONTRACT_TERM = "contract_term"
    REQUEST = "request"
    PRICE = "price"
    APPROVAL = "approval"
    COMPLETION = "completion"
    ACCEPTANCE = "acceptance"
    OTHER = "other"


class Category:
    MILESTONE = "milestone"
    EXTRA = "extra"
    FIXED = "fixed"
    HOURLY = "hourly"
    EXPENSE = "expense"
    OTHER = "other"
    ALL = (MILESTONE, EXTRA, FIXED, HOURLY, EXPENSE, OTHER)


@dataclass(frozen=True)
class SourceDocument:
    id: uuid.UUID
    filename: str
    kind: str  # contract | email | note
    text: str
    title: str | None = None
    author: str | None = None
    recipients: str | None = None
    sent_at: datetime | None = None


@dataclass(frozen=True)
class ProjectContext:
    name: str
    currency: str
    client_name: str
    client_email: str
    client_company: str | None = None
    description: str | None = None


@dataclass
class Flag:
    code: str
    message: str


@dataclass
class EvidenceSuggestion:
    document_id: uuid.UUID | None
    quote: str  # should be copied verbatim from the document
    role: str = EvidenceRole.OTHER
    location: str | None = None  # e.g. "§3.1" or "paragraph 2"


@dataclass
class ItemSuggestion:
    description: str
    category: str = Category.OTHER
    quantity: Decimal = Decimal(1)
    unit_price: Decimal | None = None  # None when no price could be determined
    rationale: str | None = None
    confidence: float | None = None  # 0..1
    flags: list[Flag] = field(default_factory=list)
    evidence: list[EvidenceSuggestion] = field(default_factory=list)


class Analyzer(Protocol):
    name: str

    async def analyze(
        self, project: ProjectContext, documents: list[SourceDocument]
    ) -> list[ItemSuggestion]: ...
