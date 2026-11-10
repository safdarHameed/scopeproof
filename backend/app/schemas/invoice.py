import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InvoiceLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_id: uuid.UUID | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    evidence_count: int


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    number: str
    status: str
    currency: str
    total: Decimal
    issue_date: date
    due_date: date
    note: str | None
    client_name: str
    client_email: str
    client_company: str | None
    provider: str | None
    provider_invoice_id: str | None
    provider_status: str | None
    payment_url: str | None
    sent_at: datetime | None
    paid_at: datetime | None
    last_synced_at: datetime | None
    created_at: datetime
    lines: list[InvoiceLineRead]


class InvoiceConfirm(BaseModel):
    due_date: date | None = None
    note: str | None = Field(default=None, max_length=2000)


class InvoiceState(BaseModel):
    invoice: InvoiceRead | None
    history: list[InvoiceRead]  # earlier cancelled invoices
    provider: str
    provider_label: str
