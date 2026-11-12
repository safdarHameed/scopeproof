"""Placeholder payment provider used until the PayPal integration is ready.

Sending records a local reference and marks the invoice as sent, without contacting any
payment service or producing a payment link. Replace it by setting PAYMENT_PROVIDER=paypal.
"""

import secrets

from app.models import Invoice, Project, User
from app.services.payments.base import PaymentProviderError, ProviderInvoice


class PlaceholderPaymentProvider:
    name = "placeholder"
    label = "Not connected (PayPal coming soon)"

    async def create_draft(
        self, invoice: Invoice, project: Project, sender: User
    ) -> ProviderInvoice:
        return ProviderInvoice(
            provider_invoice_id=f"LOCAL-{secrets.token_urlsafe(12)}", status="DRAFT"
        )

    async def send_invoice(
        self, invoice: Invoice, project: Project, sender: User
    ) -> ProviderInvoice:
        provider_id = invoice.provider_invoice_id or f"LOCAL-{secrets.token_urlsafe(12)}"
        return ProviderInvoice(provider_invoice_id=provider_id, status="SENT")

    async def get_status(self, invoice: Invoice) -> ProviderInvoice:
        if not invoice.provider_invoice_id:
            raise PaymentProviderError("Invoice was never sent")
        return ProviderInvoice(
            provider_invoice_id=invoice.provider_invoice_id,
            status=invoice.provider_status or "SENT",
            payment_url=invoice.payment_url,
            paid_at=invoice.paid_at,
        )

    async def cancel_invoice(self, invoice: Invoice) -> ProviderInvoice:
        if invoice.provider_status in {"PAID", "MARKED_AS_PAID"}:
            raise PaymentProviderError("A paid invoice can't be cancelled")
        return ProviderInvoice(
            provider_invoice_id=invoice.provider_invoice_id or "",
            status="CANCELLED",
            payment_url=invoice.payment_url,
        )
