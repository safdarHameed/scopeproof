"""Contract between the app and a payment provider (placeholder now, PayPal next).

The invoice service calls the provider to send, refresh and cancel an invoice and stores
what comes back. Statuses use PayPal's invoice status names so the PayPal implementation
can pass them through unchanged.

To plug in PayPal:
  1. Implement `PaymentProvider` in app/services/payments/paypal.py
  2. Register it in `get_payment_provider()` in app/services/payments/__init__.py
  3. Set PAYMENT_PROVIDER=paypal (plus your PayPal sandbox credentials) in backend/.env
  4. Optional: a webhook endpoint can call invoice_service.apply_provider_status(...)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.models import Invoice, Project, User
from app.models.invoice import InvoiceStatus

# PayPal invoice statuses -> our invoice status
PROVIDER_STATUS_MAP = {
    "DRAFT": InvoiceStatus.CONFIRMED,
    "SENT": InvoiceStatus.SENT,
    "SCHEDULED": InvoiceStatus.SENT,
    "UNPAID": InvoiceStatus.SENT,
    "PAYMENT_PENDING": InvoiceStatus.SENT,
    "PARTIALLY_PAID": InvoiceStatus.SENT,
    "PAID": InvoiceStatus.PAID,
    "MARKED_AS_PAID": InvoiceStatus.PAID,
    "CANCELLED": InvoiceStatus.CANCELLED,
    "REFUNDED": InvoiceStatus.REFUNDED,
    "PARTIALLY_REFUNDED": InvoiceStatus.PAID,
    "MARKED_AS_REFUNDED": InvoiceStatus.REFUNDED,
}


class PaymentProviderError(Exception):
    pass


@dataclass
class ProviderInvoice:
    provider_invoice_id: str
    status: str  # PayPal-style status, e.g. "SENT", "PAID"
    payment_url: str | None = None
    paid_at: datetime | None = None


class PaymentProvider(Protocol):
    name: str
    label: str  # shown in the UI, e.g. "PayPal sandbox"

    async def send_invoice(
        self, invoice: Invoice, project: Project, sender: User
    ) -> ProviderInvoice:
        """Create the invoice at the provider and send it to the client."""
        ...

    async def get_status(self, invoice: Invoice) -> ProviderInvoice: ...

    async def cancel_invoice(self, invoice: Invoice) -> ProviderInvoice: ...
