import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AnalysisRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analysis_runs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    engine: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # running|completed|failed
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ItemStatus:
    PENDING = "pending"
    APPROVED = "approved"
    EXCLUDED = "excluded"
    ALL = (PENDING, APPROVED, EXCLUDED)


class InvoiceItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A suggested (or manually added) invoice line, reviewed before invoicing."""

    __tablename__ = "invoice_items"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="SET NULL")
    )
    origin: Mapped[str] = mapped_column(String(20), nullable=False)  # analysis|manual
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal(1), nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default=ItemStatus.PENDING, nullable=False)
    # [{"code": "missing_approval", "message": "..."}]
    flags: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    # Set when the user approves an item despite open flags.
    flags_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="item",
        order_by="Evidence.position",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def amount(self) -> Decimal | None:
        if self.unit_price is None:
            return None
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))


class Evidence(UUIDPrimaryKeyMixin, Base):
    """A quote from a source document that supports (or questions) an invoice item."""

    __tablename__ = "evidence"

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoice_items.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), index=True
    )
    # request|price|approval|completion|acceptance|contract_term|other
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    # True when the quote was found verbatim in the referenced document.
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    item: Mapped[InvoiceItem] = relationship(back_populates="evidence")
