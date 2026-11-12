import asyncio
import base64
import logging
import time
from datetime import datetime
from decimal import Decimal

import httpx

from app.core.config import settings
from app.models import Invoice, Project, User
from app.services.payments.base import PaymentProviderError, ProviderInvoice

logger = logging.getLogger(__name__)


def extract_payment_url(data: dict) -> str | None:
    """Extract customer-facing hosted invoice payment URL from PayPal response."""
    detail = data.get("detail") or {}
    metadata = detail.get("metadata") or {}
    if metadata.get("recipient_view_url"):
        return metadata["recipient_view_url"]
    if metadata.get("payer_view_url"):
        return metadata["payer_view_url"]

    links = data.get("links") or []
    for link in links:
        if link.get("rel") in ("payer-view", "recipient-view"):
            return link.get("href")
    return None


def extract_paid_at(data: dict) -> datetime | None:
    """Extract paid_at timestamp from PayPal invoice payments data if present."""
    payments = data.get("payments") or {}
    transactions = payments.get("transactions") or []
    for tx in transactions:
        payment_date_str = tx.get("payment_date")
        if payment_date_str:
            try:
                # Handle ISO timestamps like 2026-11-12T01:00:00Z
                clean_ts = payment_date_str.replace("Z", "+00:00")
                return datetime.fromisoformat(clean_ts)
            except Exception:
                continue
    return None


def build_invoice_payload(invoice: Invoice, project: Project, sender: User) -> dict:
    """Build the official PayPal Invoicing v2 draft payload from confirmed invoice."""
    if not invoice.lines:
        raise PaymentProviderError("Cannot create a PayPal invoice with no line items.")

    currency = (invoice.currency or "").strip().upper()
    if len(currency) != 3:
        raise PaymentProviderError(f"Invalid currency code: '{invoice.currency}'.")

    if not invoice.client_email or "@" not in invoice.client_email:
        raise PaymentProviderError("A valid client email is required to send a PayPal invoice.")
    if not invoice.client_name or not invoice.client_name.strip():
        raise PaymentProviderError("Client name is required to send a PayPal invoice.")

    # 1. Decimal calculation and verification
    recalculated_total = Decimal("0.00")
    items = []
    for line in invoice.lines:
        qty = Decimal(str(line.quantity))
        unit_price = Decimal(str(line.unit_price))
        line_amount = (qty * unit_price).quantize(Decimal("0.01"))
        recalculated_total += line_amount

        desc = (line.description or "").strip()
        if not desc:
            raise PaymentProviderError("Each invoice line must have a description.")

        # Exclude internal RAG quotes or conversations; only send clear item descriptions
        formatted_qty = (
            f"{qty:.2f}".rstrip("0").rstrip(".") if qty == qty.to_integral() else f"{qty:.2f}"
        ) or "0"

        items.append(
            {
                "name": desc[:300],
                "quantity": formatted_qty,
                "unit_amount": {
                    "currency_code": currency,
                    "value": f"{unit_price:.2f}",
                },
                "unit_of_measure": "QUANTITY",
            }
        )

    inv_total = Decimal(str(invoice.total)).quantize(Decimal("0.01"))
    if recalculated_total != inv_total:
        raise PaymentProviderError(
            f"Invoice total mismatch: calculated {recalculated_total} {currency} "
            f"does not match confirmed total {inv_total} {currency}."
        )

    # 2. Invoicer details
    invoicer_name_parts = (sender.full_name or "ScopeProof User").strip().split(" ", 1)
    given_name = invoicer_name_parts[0]
    surname = invoicer_name_parts[1] if len(invoicer_name_parts) > 1 else ""

    invoicer: dict = {
        "name": {
            "given_name": given_name,
        },
        "email_address": sender.email,
    }
    if surname:
        invoicer["name"]["surname"] = surname
    if sender.company_name:
        invoicer["business_name"] = sender.company_name.strip()

    # 3. Recipient details
    client_name_parts = invoice.client_name.strip().split(" ", 1)
    client_given = client_name_parts[0]
    client_surname = client_name_parts[1] if len(client_name_parts) > 1 else ""

    billing_info: dict = {
        "name": {
            "given_name": client_given,
        },
        "email_address": invoice.client_email.strip(),
    }
    if client_surname:
        billing_info["name"]["surname"] = client_surname
    if invoice.client_company:
        billing_info["business_name"] = invoice.client_company.strip()

    # 4. Detail
    detail: dict = {
        "invoice_number": invoice.number[:25],
        "invoice_date": invoice.issue_date.isoformat(),
        "currency_code": currency,
        "payment_term": {
            "term_type": "DUE_ON_DATE_SPECIFIED",
            "due_date": invoice.due_date.isoformat(),
        },
    }
    if invoice.note:
        detail["note"] = invoice.note[:4000]

    return {
        "detail": detail,
        "invoicer": invoicer,
        "primary_recipients": [
            {
                "billing_info": billing_info,
            }
        ],
        "items": items,
        "amount": {
            "currency_code": currency,
            "value": f"{inv_total:.2f}",
            "breakdown": {
                "item_total": {
                    "currency_code": currency,
                    "value": f"{inv_total:.2f}",
                }
            },
        },
    }


class PayPalAuthManager:
    """Manages OAuth 2.0 client credentials token acquisition, caching and thread-safety."""

    def __init__(self, client_id: str, client_secret: str, base_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self._access_token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get_access_token(self, client: httpx.AsyncClient) -> str:
        # Buffer of 60 seconds before actual token expiry
        if self._access_token and time.time() < (self._expires_at - 60):
            return self._access_token

        async with self._lock:
            if self._access_token and time.time() < (self._expires_at - 60):
                return self._access_token

            if not self.client_id or not self.client_secret:
                raise PaymentProviderError(
                    "PayPal credentials (PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET) are missing."
                )

            auth_str = f"{self.client_id}:{self.client_secret}"
            b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")
            headers = {
                "Authorization": f"Basic {b64_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            try:
                res = await client.post(
                    f"{self.base_url}/v1/oauth2/token",
                    data={"grant_type": "client_credentials"},
                    headers=headers,
                    timeout=15.0,
                )
            except httpx.RequestError as exc:
                raise PaymentProviderError(f"PayPal OAuth connection failed: {exc}") from exc

            if res.status_code != 200:
                raise PaymentProviderError(
                    f"PayPal OAuth error (HTTP {res.status_code}): {res.text}"
                )

            data = res.json()
            token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            if not token:
                raise PaymentProviderError("PayPal OAuth response missing access_token.")

            self._access_token = token
            self._expires_at = time.time() + float(expires_in)
            return self._access_token


class PayPalProvider:
    """Production-grade PayPal Invoicing API v2 provider for ScopeProof."""

    name = "paypal"
    label = "PayPal Sandbox"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str | None = None,
        webhook_id: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.client_id = client_id or settings.PAYPAL_CLIENT_ID
        if client_secret:
            self.client_secret = client_secret
        elif hasattr(settings.PAYPAL_CLIENT_SECRET, "get_secret_value"):
            self.client_secret = settings.PAYPAL_CLIENT_SECRET.get_secret_value()
        else:
            self.client_secret = str(settings.PAYPAL_CLIENT_SECRET or "")
        self.base_url = (base_url or settings.PAYPAL_BASE_URL).rstrip("/")
        self.webhook_id = webhook_id or settings.PAYPAL_WEBHOOK_ID
        self._injected_client = client
        self.auth_manager = PayPalAuthManager(self.client_id, self.client_secret, self.base_url)

    def _get_client_context(self):
        if self._injected_client is not None:
            return _DummyAsyncContextManager(self._injected_client)
        return httpx.AsyncClient(timeout=30.0)

    async def _request(
        self,
        method: str,
        path: str,
        client: httpx.AsyncClient,
        json_body: dict | None = None,
        extra_headers: dict | None = None,
    ) -> httpx.Response:
        token = await self.auth_manager.get_access_token(client)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        url = f"{self.base_url}{path}"
        try:
            res = await client.request(method, url, json=json_body, headers=headers)
        except httpx.RequestError as exc:
            raise PaymentProviderError(f"PayPal API request failed ({path}): {exc}") from exc

        return res

    def _format_error(self, res: httpx.Response) -> str:
        try:
            data = res.json()
            msg = data.get("message") or res.text
            details = data.get("details")
            if details and isinstance(details, list) and len(details) > 0:
                first = details[0]
                issue = first.get("issue")
                desc = first.get("description")
                field = first.get("field")
                extra = f" [{issue}: {desc or field}]" if issue else ""
                return f"{msg}{extra}"
            return msg
        except Exception:
            return res.text

    async def create_draft(
        self, invoice: Invoice, project: Project, sender: User
    ) -> ProviderInvoice:
        """Create draft invoice in PayPal and return draft ProviderInvoice without sending."""
        async with self._get_client_context() as client:
            # If provider_invoice_id is already present, verify existing invoice
            if invoice.provider_invoice_id:
                res = await self._request(
                    "GET", f"/v2/invoicing/invoices/{invoice.provider_invoice_id}", client
                )
                if res.status_code == 200:
                    data = res.json()
                    status = data.get("status", "DRAFT")
                    return ProviderInvoice(
                        provider_invoice_id=invoice.provider_invoice_id,
                        status=status,
                        payment_url=extract_payment_url(data),
                        paid_at=extract_paid_at(data),
                    )

            payload = build_invoice_payload(invoice, project, sender)
            headers = {
                "PayPal-Request-Id": f"create-{invoice.id}",
                "Prefer": "return=representation",
            }

            res = await self._request(
                "POST", "/v2/invoicing/invoices", client, json_body=payload, extra_headers=headers
            )
            if res.status_code not in (200, 201):
                err = self._format_error(res)
                raise PaymentProviderError(f"Failed to create PayPal draft invoice: {err}")

            data = res.json()
            provider_id = data.get("id")
            if not provider_id:
                raise PaymentProviderError("PayPal did not return an invoice ID.")

            return ProviderInvoice(
                provider_invoice_id=provider_id,
                status=data.get("status", "DRAFT"),
                payment_url=extract_payment_url(data),
            )

    async def send_invoice(
        self, invoice: Invoice, project: Project, sender: User
    ) -> ProviderInvoice:
        """Send the PayPal invoice. If draft was already created, reuse it idempotently."""
        async with self._get_client_context() as client:
            provider_id = invoice.provider_invoice_id
            if not provider_id:
                draft = await self.create_draft(invoice, project, sender)
                provider_id = draft.provider_invoice_id

            # Establish authoritative state before sending to prevent redundant duplicate sends
            check_res = await self._request("GET", f"/v2/invoicing/invoices/{provider_id}", client)
            if check_res.status_code == 200:
                current = check_res.json()
                cur_status = current.get("status", "")
                if cur_status in ("SENT", "PAID", "MARKED_AS_PAID", "PARTIALLY_PAID", "SCHEDULED"):
                    return ProviderInvoice(
                        provider_invoice_id=provider_id,
                        status=cur_status,
                        payment_url=extract_payment_url(current),
                        paid_at=extract_paid_at(current),
                    )

            # Send the invoice
            headers = {"PayPal-Request-Id": f"send-{provider_id}"}
            send_body = {"send_to_recipient": True}
            send_res = await self._request(
                "POST",
                f"/v2/invoicing/invoices/{provider_id}/send",
                client,
                json_body=send_body,
                extra_headers=headers,
            )

            if send_res.status_code not in (200, 202, 204):
                err = self._format_error(send_res)
                raise PaymentProviderError(f"Failed to send PayPal invoice: {err}")

            # Retrieve authoritative invoice details to get the hosted payment URL
            detail_res = await self._request("GET", f"/v2/invoicing/invoices/{provider_id}", client)
            if detail_res.status_code == 200:
                data = detail_res.json()
                return ProviderInvoice(
                    provider_invoice_id=provider_id,
                    status=data.get("status", "SENT"),
                    payment_url=extract_payment_url(data),
                    paid_at=extract_paid_at(data),
                )

            return ProviderInvoice(provider_invoice_id=provider_id, status="SENT")

    async def get_status(self, invoice: Invoice) -> ProviderInvoice:
        """Fetch current authoritative status and details for an invoice from PayPal."""
        if not invoice.provider_invoice_id:
            raise PaymentProviderError("Invoice was never sent to PayPal.")

        async with self._get_client_context() as client:
            res = await self._request(
                "GET", f"/v2/invoicing/invoices/{invoice.provider_invoice_id}", client
            )
            if res.status_code != 200:
                err = self._format_error(res)
                raise PaymentProviderError(f"Failed to get PayPal invoice status: {err}")

            data = res.json()
            raw_status = data.get("status", "SENT")

            # Check due amount for partial payment
            due_amount = data.get("due_amount") or {}
            due_val_str = due_amount.get("value")
            if due_val_str is not None:
                try:
                    due_val = Decimal(str(due_val_str))
                    total_amount = Decimal(str(data.get("amount", {}).get("value", "0.00")))
                    if raw_status == "PAID" and due_val > 0:
                        raw_status = "PARTIALLY_PAID"
                    elif raw_status in ("SENT", "UNPAID") and 0 < due_val < total_amount:
                        raw_status = "PARTIALLY_PAID"
                except Exception:
                    pass

            # Check refunds
            refunds = data.get("refunds") or {}
            refund_amount = refunds.get("refund_amount") or {}
            refund_val_str = refund_amount.get("value")
            if refund_val_str is not None:
                try:
                    ref_val = Decimal(str(refund_val_str))
                    total_val = Decimal(str(data.get("amount", {}).get("value", "0.00")))
                    if 0 < ref_val < total_val:
                        raw_status = "PARTIALLY_REFUNDED"
                    elif ref_val >= total_val and ref_val > 0:
                        raw_status = "REFUNDED"
                except Exception:
                    pass

            return ProviderInvoice(
                provider_invoice_id=invoice.provider_invoice_id,
                status=raw_status,
                payment_url=extract_payment_url(data),
                paid_at=extract_paid_at(data),
            )

    async def cancel_invoice(self, invoice: Invoice) -> ProviderInvoice:
        """Cancel an invoice on PayPal."""
        if not invoice.provider_invoice_id:
            raise PaymentProviderError("Invoice was never sent to PayPal.")

        async with self._get_client_context() as client:
            headers = {"PayPal-Request-Id": f"cancel-{invoice.provider_invoice_id}"}
            body = {
                "subject": f"Invoice {invoice.number} cancelled",
                "note": "Invoice cancelled by sender in ScopeProof",
                "send_to_invoicer": False,
                "send_to_recipient": True,
            }
            res = await self._request(
                "POST",
                f"/v2/invoicing/invoices/{invoice.provider_invoice_id}/cancel",
                client,
                json_body=body,
                extra_headers=headers,
            )

            if res.status_code in (200, 204):
                return ProviderInvoice(
                    provider_invoice_id=invoice.provider_invoice_id,
                    status="CANCELLED",
                    payment_url=invoice.payment_url,
                )

            # Check if invoice is already cancelled
            err = self._format_error(res)
            if "ALREADY_CANCELLED" in err or "CANNOT_CANCEL" in err:
                status_res = await self._request(
                    "GET", f"/v2/invoicing/invoices/{invoice.provider_invoice_id}", client
                )
                if status_res.status_code == 200 and status_res.json().get("status") == "CANCELLED":
                    return ProviderInvoice(
                        provider_invoice_id=invoice.provider_invoice_id,
                        status="CANCELLED",
                        payment_url=invoice.payment_url,
                    )

            raise PaymentProviderError(f"Failed to cancel PayPal invoice: {err}")

    async def verify_webhook_signature(self, headers: dict[str, str], raw_body_dict: dict) -> bool:
        """Verify incoming webhook signature using official PayPal verification endpoint."""
        if not self.webhook_id:
            raise PaymentProviderError("PAYPAL_WEBHOOK_ID is not configured.")

        # Normalize header keys to lowercase
        h_lower = {k.lower(): v for k, v in headers.items()}

        verify_payload = {
            "auth_algo": h_lower.get("paypal-auth-algo"),
            "cert_url": h_lower.get("paypal-cert-url"),
            "transmission_id": h_lower.get("paypal-transmission-id"),
            "transmission_sig": h_lower.get("paypal-transmission-sig"),
            "transmission_time": h_lower.get("paypal-transmission-time"),
            "webhook_id": self.webhook_id,
            "webhook_event": raw_body_dict,
        }

        async with self._get_client_context() as client:
            res = await self._request(
                "POST",
                "/v1/notifications/verify-webhook-signature",
                client,
                json_body=verify_payload,
            )
            if res.status_code != 200:
                logger.warning("PayPal webhook verification HTTP error: %s", res.text)
                return False

            result = res.json()
            return result.get("verification_status") == "SUCCESS"


class _DummyAsyncContextManager:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
