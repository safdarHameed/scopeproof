import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InvoiceStatus:
    CONFIRMED = "confirmed"  # locked draft, not sent yet
    SENT = "sent"  # sent through the payment provider, awaiting payment
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    ACTIVE = (CONFIRMED, SENT, PAID, REFUNDED)


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "invoices"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    # Snapshot of who the invoice is addressed to at confirmation time.
    client_name: Mapped[str] = mapped_column(String(200), nullable=False)
    client_email: Mapped[str] = mapped_column(String(320), nullable=False)
    client_company: Mapped[str | None] = mapped_column(String(200))

    # Payment provider state
    provider: Mapped[str | None] = mapped_column(String(30))
    provider_invoice_id: Mapped[str | None] = mapped_column(String(100), index=True)
    provider_status: Mapped[str | None] = mapped_column(String(40))
    payment_url: Mapped[str | None] = mapped_column(String(1000))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice",
        order_by="InvoiceLine.position",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class InvoiceLine(UUIDPrimaryKeyMixin, Base):
    """Immutable copy of an approved item, taken when the invoice is confirmed."""

    __tablename__ = "invoice_lines"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=False
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invoice_items.id", ondelete="SET NULL")
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")
