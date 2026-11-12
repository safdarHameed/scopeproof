import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models import Invoice, InvoiceLine, Project, User
from app.models.invoice import InvoiceStatus
from app.services.payments.base import PaymentProviderError
from app.services.payments.paypal import (
    PayPalAuthManager,
    PayPalProvider,
    build_invoice_payload,
    extract_payment_url,
)


def _mock_transport(handler):
    return httpx.MockTransport(handler)


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="freelancer@example.com",
        full_name="Jane Doe",
        company_name="Acme Studio",
        hashed_password="hashed_pw_test",
        is_active=True,
    )


@pytest.fixture
def test_project(test_user):
    return Project(
        id=uuid.uuid4(),
        owner_id=test_user.id,
        name="Branding Campaign",
        currency="USD",
        client_name="Bob Smith",
        client_email="bob@client.com",
        client_company="Client Corp",
    )


@pytest.fixture
def test_invoice(test_project):
    inv = Invoice(
        id=uuid.uuid4(),
        project_id=test_project.id,
        number="INV-2026-0001",
        status=InvoiceStatus.CONFIRMED,
        currency="USD",
        total=Decimal("350.00"),
        issue_date=date(2026, 11, 12),
        due_date=date(2026, 11, 26),
        note="Thank you for your business.",
        client_name=test_project.client_name,
        client_email=test_project.client_email,
        client_company=test_project.client_company,
        lines=[
            InvoiceLine(
                id=uuid.uuid4(),
                description="Logo Design",
                quantity=Decimal("1.00"),
                unit_price=Decimal("200.00"),
                amount=Decimal("200.00"),
                position=0,
            ),
            InvoiceLine(
                id=uuid.uuid4(),
                description="Brand Guidelines",
                quantity=Decimal("1.50"),
                unit_price=Decimal("100.00"),
                amount=Decimal("150.00"),
                position=1,
            ),
        ],
    )
    return inv


# -------------------------------------------------------------------------
# 1. OAuth success, failure and expiration
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_oauth_success_and_caching():
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        assert request.url.path == "/v1/oauth2/token"
        assert "Basic " in request.headers["Authorization"]
        return httpx.Response(200, json={"access_token": "token-xyz-123", "expires_in": 3600})

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    auth = PayPalAuthManager("client_id_val", "client_sec_val", "https://api-m.sandbox.paypal.com")

    t1 = await auth.get_access_token(client)
    assert t1 == "token-xyz-123"
    assert call_count == 1

    # Second call uses cache without hitting HTTP
    t2 = await auth.get_access_token(client)
    assert t2 == "token-xyz-123"
    assert call_count == 1


@pytest.mark.asyncio
async def test_oauth_failure_handling():
    def handler(request: httpx.Request):
        return httpx.Response(
            401, json={"error": "invalid_client", "error_description": "Bad credentials"}
        )

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    auth = PayPalAuthManager("bad_client", "bad_sec", "https://api-m.sandbox.paypal.com")

    with pytest.raises(PaymentProviderError) as exc:
        await auth.get_access_token(client)
    assert "PayPal OAuth error (HTTP 401)" in str(exc.value)


@pytest.mark.asyncio
async def test_oauth_token_expiration_refresh():
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"access_token": f"token-{call_count}", "expires_in": 10})

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    auth = PayPalAuthManager("cid", "csec", "https://api-m.sandbox.paypal.com")

    # Initial call
    t1 = await auth.get_access_token(client)
    assert t1 == "token-1"

    # Manually expire token
    auth._expires_at = 0.0

    t2 = await auth.get_access_token(client)
    assert t2 == "token-2"
    assert call_count == 2


# -------------------------------------------------------------------------
# 2. Correct invoice payload mapping
# -------------------------------------------------------------------------
def test_invoice_payload_mapping(test_invoice, test_project, test_user):
    payload = build_invoice_payload(test_invoice, test_project, test_user)

    assert payload["detail"]["invoice_number"] == "INV-2026-0001"
    assert payload["detail"]["currency_code"] == "USD"
    assert payload["detail"]["invoice_date"] == "2026-11-12"
    assert payload["detail"]["payment_term"]["due_date"] == "2026-11-26"
    assert payload["invoicer"]["email_address"] == "freelancer@example.com"
    assert payload["invoicer"]["name"]["given_name"] == "Jane"
    assert payload["invoicer"]["name"]["surname"] == "Doe"
    assert payload["invoicer"]["business_name"] == "Acme Studio"
    assert payload["primary_recipients"][0]["billing_info"]["name"]["given_name"] == "Bob"
    assert payload["primary_recipients"][0]["billing_info"]["email_address"] == "bob@client.com"
    assert len(payload["items"]) == 2
    assert payload["items"][0]["name"] == "Logo Design"
    assert payload["items"][0]["unit_amount"]["value"] == "200.00"
    assert payload["amount"]["value"] == "350.00"
    assert payload["amount"]["breakdown"]["item_total"]["value"] == "350.00"


# -------------------------------------------------------------------------
# 3. Decimal and currency validation
# -------------------------------------------------------------------------
def test_decimal_and_currency_validation(test_invoice, test_project, test_user):
    # Invalid currency
    test_invoice.currency = "TOOLONG"
    with pytest.raises(PaymentProviderError) as exc:
        build_invoice_payload(test_invoice, test_project, test_user)
    assert "Invalid currency" in str(exc.value)

    # Mismatch in total calculation
    test_invoice.currency = "USD"
    test_invoice.total = Decimal("999.99")
    with pytest.raises(PaymentProviderError) as exc:
        build_invoice_payload(test_invoice, test_project, test_user)
    assert "Invoice total mismatch" in str(exc.value)


# -------------------------------------------------------------------------
# 4. Unapproved items excluded
# -------------------------------------------------------------------------
def test_unapproved_items_not_in_payload(test_invoice, test_project, test_user):
    # Only items present in test_invoice.lines are used (confirm() only copies approved items)
    payload = build_invoice_payload(test_invoice, test_project, test_user)
    assert len(payload["items"]) == len(test_invoice.lines)


# -------------------------------------------------------------------------
# 5. Missing recipient/invoicer information returns actionable error
# -------------------------------------------------------------------------
def test_missing_client_info(test_invoice, test_project, test_user):
    test_invoice.client_email = ""
    with pytest.raises(PaymentProviderError) as exc:
        build_invoice_payload(test_invoice, test_project, test_user)
    assert "A valid client email is required" in str(exc.value)

    test_invoice.client_email = "bob@client.com"
    test_invoice.client_name = ""
    with pytest.raises(PaymentProviderError) as exc:
        build_invoice_payload(test_invoice, test_project, test_user)
    assert "Client name is required" in str(exc.value)


# -------------------------------------------------------------------------
# 5b. PAYPAL_INVOICER_EMAIL overrides sender email in payload
# -------------------------------------------------------------------------
def test_invoicer_email_override(test_invoice, test_project, test_user):
    """PAYPAL_INVOICER_EMAIL must be used as invoicer email, not the sender's login email."""
    from app.services.payments.paypal import build_invoice_payload

    # Without override — sender email used
    payload_no_override = build_invoice_payload(test_invoice, test_project, test_user)
    assert payload_no_override["invoicer"]["email_address"] == test_user.email

    # With an explicit invoicer_email — that email is used instead
    business_email = "sb-seller123@business.example.com"
    payload_with_override = build_invoice_payload(
        test_invoice, test_project, test_user, invoicer_email=business_email
    )
    assert payload_with_override["invoicer"]["email_address"] == business_email
    # The sender's email must NOT appear as the invoicer email when overridden
    assert payload_with_override["invoicer"]["email_address"] != test_user.email

    # Whitespace-only override falls back to sender email
    payload_blank = build_invoice_payload(
        test_invoice, test_project, test_user, invoicer_email="   "
    )
    assert payload_blank["invoicer"]["email_address"] == test_user.email


# -------------------------------------------------------------------------
# 6. Draft creation and invoice sending (separate operations)
#    Asserts Prefer: return=representation on the POST /v2/invoicing/invoices
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_draft_creation_and_send(test_invoice, test_project, test_user):
    created_id = "INV2-ABC1-DEF2-GHI3-JKL4"
    status_state = {"status": "DRAFT"}

    def handler(request: httpx.Request):
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "token-123", "expires_in": 3600})
        if request.url.path == "/v2/invoicing/invoices" and request.method == "POST":
            # Assert Prefer header is sent only on draft creation
            assert request.headers.get("Prefer") == "return=representation"
            return httpx.Response(
                201,
                json={
                    "id": created_id,
                    "status": "DRAFT",
                    "links": [
                        {
                            "rel": "payer-view",
                            "href": "https://www.sandbox.paypal.com/invoice/p/#draft",
                        }
                    ],
                },
            )
        if request.url.path == f"/v2/invoicing/invoices/{created_id}" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": created_id,
                    "status": status_state["status"],
                    "links": [
                        {
                            "rel": "payer-view",
                            "href": "https://www.sandbox.paypal.com/invoice/p/#draft",
                        }
                    ],
                },
            )
        if request.url.path == f"/v2/invoicing/invoices/{created_id}/send":
            # Simulate PayPal transitioning draft to UNPAID after send
            status_state["status"] = "UNPAID"
            return httpx.Response(200, json={})
        return httpx.Response(404, json={})

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    provider = PayPalProvider("cid", "csec", "https://api-m.sandbox.paypal.com", client=client)

    # 1. Create draft
    draft = await provider.create_draft(test_invoice, test_project, test_user)
    assert draft.provider_invoice_id == created_id
    assert draft.status == "DRAFT"

    # 2. Send invoice
    test_invoice.provider_invoice_id = created_id
    sent = await provider.send_invoice(test_invoice, test_project, test_user)
    assert sent.provider_invoice_id == created_id
    assert sent.status == "UNPAID"


# -------------------------------------------------------------------------
# 7. Hosted URL extraction
# -------------------------------------------------------------------------
def test_hosted_url_extraction():
    data_with_recipient_view = {
        "detail": {
            "metadata": {"recipient_view_url": "https://www.sandbox.paypal.com/invoice/p/#recip"}
        }
    }
    assert (
        extract_payment_url(data_with_recipient_view)
        == "https://www.sandbox.paypal.com/invoice/p/#recip"
    )

    data_with_links = {
        "links": [{"rel": "payer-view", "href": "https://www.sandbox.paypal.com/invoice/p/#link"}]
    }
    assert extract_payment_url(data_with_links) == "https://www.sandbox.paypal.com/invoice/p/#link"

    assert extract_payment_url({}) is None


# -------------------------------------------------------------------------
# 8. Timeouts and API errors
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_api_timeout_and_errors(test_invoice, test_project, test_user):
    def timeout_handler(request: httpx.Request):
        raise httpx.ReadTimeout("Connection timed out")

    client = httpx.AsyncClient(transport=_mock_transport(timeout_handler))
    provider = PayPalProvider("cid", "csec", "https://api-m.sandbox.paypal.com", client=client)

    with pytest.raises(PaymentProviderError) as exc:
        await provider.create_draft(test_invoice, test_project, test_user)
    assert "PayPal OAuth connection failed" in str(exc.value)


# -------------------------------------------------------------------------
# 9. Duplicate invoice protection / reuse existing draft
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reuse_existing_draft_id(test_invoice, test_project, test_user):
    existing_id = "INV2-EXISTING-DRAFT"
    test_invoice.provider_invoice_id = existing_id
    get_called = False

    def handler(request: httpx.Request):
        nonlocal get_called
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "token-123", "expires_in": 3600})
        if request.url.path == f"/v2/invoicing/invoices/{existing_id}" and request.method == "GET":
            get_called = True
            return httpx.Response(200, json={"id": existing_id, "status": "DRAFT"})
        return httpx.Response(500, json={})

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    provider = PayPalProvider("cid", "csec", "https://api-m.sandbox.paypal.com", client=client)

    draft = await provider.create_draft(test_invoice, test_project, test_user)
    assert draft.provider_invoice_id == existing_id
    assert get_called is True


# -------------------------------------------------------------------------
# 10. Cancellation flow
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cancel_invoice(test_invoice):
    test_invoice.provider_invoice_id = "INV2-TO-CANCEL"

    def handler(request: httpx.Request):
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "token-123", "expires_in": 3600})
        if request.url.path == "/v2/invoicing/invoices/INV2-TO-CANCEL/cancel":
            return httpx.Response(204)
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    provider = PayPalProvider("cid", "csec", "https://api-m.sandbox.paypal.com", client=client)

    res = await provider.cancel_invoice(test_invoice)
    assert res.status == "CANCELLED"


# -------------------------------------------------------------------------
# 11. Webhook signature verification (valid vs invalid)
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_webhook_signature_verification():
    def handler(request: httpx.Request):
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        if request.url.path == "/v1/notifications/verify-webhook-signature":
            data = request.read()
            if b"GOOD_SIG" in data:
                return httpx.Response(200, json={"verification_status": "SUCCESS"})
            return httpx.Response(200, json={"verification_status": "FAILURE"})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    provider = PayPalProvider(
        "cid", "csec", "https://api-m.sandbox.paypal.com", webhook_id="WH-123", client=client
    )

    valid_headers = {
        "paypal-auth-algo": "SHA256withRSA",
        "paypal-cert-url": "https://api.sandbox.paypal.com/cert",
        "paypal-transmission-id": "trans-1",
        "paypal-transmission-sig": "GOOD_SIG",
        "paypal-transmission-time": "2026-11-12T01:00:00Z",
    }
    assert await provider.verify_webhook_signature(valid_headers, {"id": "EVT-1"}) is True

    invalid_headers = dict(valid_headers)
    invalid_headers["paypal-transmission-sig"] = "BAD_SIG"
    assert await provider.verify_webhook_signature(invalid_headers, {"id": "EVT-1"}) is False


# -------------------------------------------------------------------------
# 12. Missing webhook ID and invalid signatures fail closed
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_webhook_missing_webhook_id_fails_closed(client: httpx.AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "PAYPAL_WEBHOOK_ID", "")

    headers = {
        "paypal-auth-algo": "SHA256withRSA",
        "paypal-cert-url": "https://api.sandbox.paypal.com/cert",
        "paypal-transmission-id": "trans-1",
        "paypal-transmission-sig": "sig-1",
        "paypal-transmission-time": "2026-11-12T01:00:00Z",
    }
    body = {"id": "EVT-999", "event_type": "INVOICING.INVOICE.PAID"}

    res = await client.post("/api/v1/webhooks/paypal", json=body, headers=headers)
    assert res.status_code == 500
    assert "PAYPAL_WEBHOOK_ID is not configured" in res.json()["detail"]


# -------------------------------------------------------------------------
# 13. Duplicate and concurrent webhook events deduplication
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_webhook_deduplication(client: httpx.AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "PAYPAL_WEBHOOK_ID", "WH-TEST-123")

    async def _mock_verify(self, headers, body):
        return True

    monkeypatch.setattr(PayPalProvider, "verify_webhook_signature", _mock_verify)

    headers = {
        "paypal-auth-algo": "algo",
        "paypal-cert-url": "url",
        "paypal-transmission-id": "tx",
        "paypal-transmission-sig": "sig",
        "paypal-transmission-time": "time",
    }
    body = {
        "id": "EVT-DEDUPE-1",
        "event_type": "INVOICING.INVOICE.PAID",
        "resource": {"id": "NON-EXISTENT-INV"},
    }

    # First request
    res1 = await client.post("/api/v1/webhooks/paypal", json=body, headers=headers)
    assert res1.status_code == 200

    # Second identical request (duplicate event_id)
    res2 = await client.post("/api/v1/webhooks/paypal", json=body, headers=headers)
    assert res2.status_code == 200
    assert "Duplicate event" in res2.json()["message"]


# -------------------------------------------------------------------------
# 14. Partial payment versus full payment
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_partial_payment_vs_full_payment(test_invoice):
    test_invoice.provider_invoice_id = "INV2-PARTIAL"

    def handler(request: httpx.Request):
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        if request.url.path == "/v2/invoicing/invoices/INV2-PARTIAL":
            # Paid event, but due_amount is still 50.00
            return httpx.Response(
                200,
                json={
                    "id": "INV2-PARTIAL",
                    "status": "PAID",
                    "amount": {"currency_code": "USD", "value": "200.00"},
                    "due_amount": {"currency_code": "USD", "value": "50.00"},
                },
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    provider = PayPalProvider("cid", "csec", "https://api-m.sandbox.paypal.com", client=client)

    status_partial = await provider.get_status(test_invoice)
    assert status_partial.status == "PARTIALLY_PAID"


# -------------------------------------------------------------------------
# 15. Payment pending
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_payment_pending(test_invoice):
    test_invoice.provider_invoice_id = "INV2-PENDING"

    def handler(request: httpx.Request):
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        if request.url.path == "/v2/invoicing/invoices/INV2-PENDING":
            return httpx.Response(200, json={"id": "INV2-PENDING", "status": "PAYMENT_PENDING"})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    provider = PayPalProvider("cid", "csec", "https://api-m.sandbox.paypal.com", client=client)

    status_pending = await provider.get_status(test_invoice)
    assert status_pending.status == "PAYMENT_PENDING"


# -------------------------------------------------------------------------
# 16. Partial refund versus full refund
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_partial_refund_vs_full_refund(test_invoice):
    test_invoice.provider_invoice_id = "INV2-REFUND"

    def handler(request: httpx.Request):
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        if request.url.path == "/v2/invoicing/invoices/INV2-REFUND":
            return httpx.Response(
                200,
                json={
                    "id": "INV2-REFUND",
                    "status": "PARTIALLY_REFUNDED",
                    "amount": {"currency_code": "USD", "value": "200.00"},
                    "refunds": {"refund_amount": {"currency_code": "USD", "value": "50.00"}},
                },
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    provider = PayPalProvider("cid", "csec", "https://api-m.sandbox.paypal.com", client=client)

    status_refund = await provider.get_status(test_invoice)
    assert status_refund.status == "PARTIALLY_REFUNDED"


# -------------------------------------------------------------------------
# 17. Live integration via webhook sync with DB
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_webhook_updates_invoice_status_in_db(client: httpx.AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "PAYPAL_WEBHOOK_ID", "WH-TEST-123")

    async def _mock_verify(self, headers, body):
        return True

    monkeypatch.setattr(PayPalProvider, "verify_webhook_signature", _mock_verify)

    paypal_inv_id = "INV2-SYNC-TEST-99"

    async def mock_get_status(self, invoice):
        from app.services.payments.base import ProviderInvoice

        return ProviderInvoice(
            provider_invoice_id=paypal_inv_id,
            status="PAID",
            payment_url="https://www.sandbox.paypal.com/invoice/p/#paid",
            paid_at=datetime(2026, 11, 12, 1, 30, tzinfo=UTC),
        )

    monkeypatch.setattr(PayPalProvider, "get_status", mock_get_status)

    from tests.conftest import TestSession

    async with TestSession() as db:
        user = User(
            id=uuid.uuid4(),
            email="seller@example.com",
            hashed_password="hashed_pw_test",
            is_active=True,
        )
        db.add(user)
        project = Project(
            id=uuid.uuid4(),
            owner_id=user.id,
            name="Test Proj",
            currency="USD",
            client_name="Buyer",
            client_email="buyer@example.com",
        )
        db.add(project)
        inv = Invoice(
            id=uuid.uuid4(),
            project_id=project.id,
            number="INV-2026-0099",
            status=InvoiceStatus.SENT,
            currency="USD",
            total=Decimal("100.00"),
            issue_date=date(2026, 11, 12),
            due_date=date(2026, 11, 26),
            client_name="Buyer",
            client_email="buyer@example.com",
            provider="paypal",
            provider_invoice_id=paypal_inv_id,
            provider_status="SENT",
        )
        db.add(inv)
        await db.commit()

    headers = {
        "paypal-auth-algo": "algo",
        "paypal-cert-url": "url",
        "paypal-transmission-id": "tx",
        "paypal-transmission-sig": "sig",
        "paypal-transmission-time": "time",
    }
    body = {
        "id": "EVT-PAID-SUCCESS-1",
        "event_type": "INVOICING.INVOICE.PAID",
        "resource": {"id": paypal_inv_id},
    }

    res = await client.post("/api/v1/webhooks/paypal", json=body, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["invoice_status"] == InvoiceStatus.PAID
    assert data["provider_status"] == "PAID"

    async with TestSession() as db:
        updated = await db.scalar(
            select(Invoice).where(Invoice.provider_invoice_id == paypal_inv_id)
        )
        assert updated.status == InvoiceStatus.PAID
        assert updated.paid_at is not None
