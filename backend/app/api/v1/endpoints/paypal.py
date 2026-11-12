import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession
from app.core.config import settings
from app.models.webhook import WebhookEvent, WebhookEventStatus
from app.services import invoice_service
from app.services.payments.paypal import PayPalProvider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["paypal"])

SUPPORTED_INVOICE_EVENTS = {
    "INVOICING.INVOICE.CREATED",
    "INVOICING.INVOICE.SENT",
    "INVOICING.INVOICE.UPDATED",
    "INVOICING.INVOICE.SCHEDULED",
    "INVOICING.INVOICE.CANCELLED",
    "INVOICING.INVOICE.PAID",
    "INVOICING.INVOICE.REFUNDED",
}


async def _handle_paypal_webhook(request: Request, db: DbSession):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body"
        ) from None

    headers = dict(request.headers)
    event_id = body.get("id")
    event_type = body.get("event_type")

    if not event_id or not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event 'id' or 'event_type' in webhook payload.",
        )

    # 1. Mandatory Security: require configured webhook ID (fail closed)
    if not settings.PAYPAL_WEBHOOK_ID:
        logger.error("PayPal webhook received but PAYPAL_WEBHOOK_ID is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PAYPAL_WEBHOOK_ID is not configured.",
        )

    # 2. Check for required signature headers
    required_sig_headers = [
        "paypal-auth-algo",
        "paypal-cert-url",
        "paypal-transmission-id",
        "paypal-transmission-sig",
        "paypal-transmission-time",
    ]
    for h in required_sig_headers:
        if h not in headers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required PayPal signature header: {h}",
            )

    # 3. Verify signature against PayPal's verification endpoint
    provider = PayPalProvider()
    try:
        is_valid = await provider.verify_webhook_signature(headers, body)
    except Exception as exc:
        logger.warning("Error during PayPal webhook signature verification: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PayPal webhook signature verification failed: {exc}",
        ) from exc

    if not is_valid:
        logger.warning("PayPal webhook signature verification failed for event %s", event_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PayPal webhook signature verification failed.",
        )

    # 4. Enforce persistent deduplication with database-level uniqueness
    existing_event = await db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == event_id))
    if existing_event:
        logger.info(
            "Duplicate PayPal webhook event %s already processed; acknowledging safely.", event_id
        )
        return {"status": "ok", "message": "Duplicate event already received."}

    webhook_event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        provider="paypal",
        status=WebhookEventStatus.PROCESSING,
    )
    db.add(webhook_event)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.info(
            "Duplicate PayPal webhook event %s received concurrently; acknowledging safely.",
            event_id,
        )
        return {"status": "ok", "message": "Duplicate event already received."}

    # 5. Extract provider invoice ID
    resource = body.get("resource") or {}
    paypal_invoice_id = resource.get("id") or (resource.get("invoice") or {}).get("id")
    webhook_event.provider_invoice_id = paypal_invoice_id

    if event_type not in SUPPORTED_INVOICE_EVENTS:
        webhook_event.status = WebhookEventStatus.IGNORED
        webhook_event.error = f"Unsupported event type: {event_type}"
        webhook_event.processed_at = datetime.now(UTC)
        await db.commit()
        return {"status": "ok", "message": f"Ignored event type: {event_type}"}

    if not paypal_invoice_id:
        webhook_event.status = WebhookEventStatus.IGNORED
        webhook_event.error = "No PayPal invoice ID found in resource."
        webhook_event.processed_at = datetime.now(UTC)
        await db.commit()
        return {"status": "ok", "message": "Ignored: no invoice ID in resource."}

    # 6. Locate local invoice
    invoice = await invoice_service.get_by_provider_invoice_id(db, paypal_invoice_id)
    if not invoice:
        webhook_event.status = WebhookEventStatus.IGNORED
        webhook_event.error = f"No local invoice matches PayPal ID: {paypal_invoice_id}"
        webhook_event.processed_at = datetime.now(UTC)
        await db.commit()
        return {"status": "ok", "message": "Ignored: no matching local invoice."}

    # 7. Retrieve authoritative PayPal invoice status to prevent trusting raw event payload blindly
    try:
        provider_invoice = await provider.get_status(invoice)
        await invoice_service.apply_provider_status(db, invoice, provider_invoice)
        webhook_event.status = WebhookEventStatus.PROCESSED
        webhook_event.processed_at = datetime.now(UTC)
        await db.commit()
    except Exception as exc:
        logger.exception("Failed to apply PayPal status for event %s: %s", event_id, exc)
        webhook_event.status = WebhookEventStatus.FAILED
        webhook_event.error = str(exc)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook synchronization failed: {exc}",
        ) from exc

    return {
        "status": "ok",
        "invoice_id": str(invoice.id),
        "invoice_status": invoice.status,
        "provider_status": invoice.provider_status,
    }


@router.post("/webhooks/paypal", status_code=status.HTTP_200_OK)
async def paypal_webhook_endpoint(request: Request, db: DbSession):
    return await _handle_paypal_webhook(request, db)


@router.post("/paypal/webhooks", status_code=status.HTTP_200_OK)
async def paypal_webhook_alias(request: Request, db: DbSession):
    return await _handle_paypal_webhook(request, db)
