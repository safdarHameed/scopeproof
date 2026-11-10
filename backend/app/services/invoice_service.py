import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Invoice, InvoiceLine, Project, User
from app.models.analysis import ItemStatus
from app.models.invoice import InvoiceStatus
from app.services import item_service
from app.services.payments import get_payment_provider
from app.services.payments.base import PROVIDER_STATUS_MAP, PaymentProviderError, ProviderInvoice


class InvoiceError(Exception):
    pass


DEFAULT_PAYMENT_TERMS_DAYS = 14


async def get_active(db: AsyncSession, project_id: uuid.UUID) -> Invoice | None:
    result = await db.execute(
        select(Invoice)
        .where(Invoice.project_id == project_id, Invoice.status.in_(InvoiceStatus.ACTIVE))
        .order_by(Invoice.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_for_project(db: AsyncSession, project_id: uuid.UUID) -> list[Invoice]:
    result = await db.execute(
        select(Invoice).where(Invoice.project_id == project_id).order_by(Invoice.created_at.desc())
    )
    return list(result.scalars())


async def ensure_unlocked(db: AsyncSession, project_id: uuid.UUID) -> None:
    invoice = await get_active(db, project_id)
    if invoice is not None:
        raise InvoiceError(
            f"Invoice {invoice.number} is {invoice.status}. "
            + (
                "Reopen it to make changes."
                if invoice.status == InvoiceStatus.CONFIRMED
                else "Cancel it to make changes."
            )
        )


async def _next_number(db: AsyncSession, owner_id: uuid.UUID) -> str:
    count = await db.scalar(
        select(func.count(Invoice.id))
        .join(Project, Project.id == Invoice.project_id)
        .where(Project.owner_id == owner_id)
    )
    return f"INV-{date.today().year}-{(count or 0) + 1:04d}"


async def confirm(
    db: AsyncSession, project: Project, due_date: date | None, note: str | None
) -> Invoice:
    await ensure_unlocked(db, project.id)
    items = await item_service.list_for_project(db, project.id)
    pending = [i for i in items if i.status == ItemStatus.PENDING]
    if pending:
        raise InvoiceError(
            f"{len(pending)} item(s) still need a decision. Approve or exclude every item first."
        )
    approved = [i for i in items if i.status == ItemStatus.APPROVED]
    if not approved:
        raise InvoiceError("Approve at least one item to create an invoice.")
    if any(i.amount is None for i in approved):
        raise InvoiceError("Every approved item needs a price.")

    issue = date.today()
    due = due_date or issue + timedelta(days=DEFAULT_PAYMENT_TERMS_DAYS)
    if due < issue:
        raise InvoiceError("The due date can't be before today.")

    invoice = Invoice(
        project_id=project.id,
        number=await _next_number(db, project.owner_id),
        status=InvoiceStatus.CONFIRMED,
        currency=project.currency,
        total=sum((i.amount for i in approved if i.amount is not None), Decimal("0.00")),
        issue_date=issue,
        due_date=due,
        note=note,
        client_name=project.client_name,
        client_email=project.client_email,
        client_company=project.client_company,
        lines=[
            InvoiceLine(
                item_id=i.id,
                description=i.description,
                quantity=i.quantity,
                unit_price=i.unit_price,
                amount=i.amount,
                evidence_count=sum(1 for e in i.evidence if e.verified),
                position=n,
            )
            for n, i in enumerate(approved)
        ],
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def reopen(db: AsyncSession, invoice: Invoice) -> None:
    """Throw away a confirmed (not yet sent) invoice so the items can be edited again."""
    if invoice.status != InvoiceStatus.CONFIRMED:
        raise InvoiceError("Only an invoice that hasn't been sent can be reopened.")
    await db.delete(invoice)
    await db.commit()


async def send(db: AsyncSession, invoice: Invoice, project: Project, sender: User) -> Invoice:
    if invoice.status != InvoiceStatus.CONFIRMED:
        raise InvoiceError("This invoice has already been sent.")
    provider = get_payment_provider()
    try:
        result = await provider.send_invoice(invoice, project, sender)
    except PaymentProviderError as exc:
        raise InvoiceError(f"{provider.label}: {exc}") from exc
    invoice.provider = provider.name
    invoice.sent_at = datetime.now(UTC)
    _apply(invoice, result)
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def sync_status(db: AsyncSession, invoice: Invoice) -> Invoice:
    if invoice.provider is None:
        return invoice
    provider = get_payment_provider()
    try:
        result = await provider.get_status(invoice)
    except PaymentProviderError as exc:
        raise InvoiceError(f"{provider.label}: {exc}") from exc
    _apply(invoice, result)
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def cancel(db: AsyncSession, invoice: Invoice) -> Invoice:
    if invoice.status != InvoiceStatus.SENT:
        raise InvoiceError("Only a sent, unpaid invoice can be cancelled.")
    provider = get_payment_provider()
    try:
        result = await provider.cancel_invoice(invoice)
    except PaymentProviderError as exc:
        raise InvoiceError(f"{provider.label}: {exc}") from exc
    _apply(invoice, result)
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def apply_provider_status(
    db: AsyncSession, invoice: Invoice, result: ProviderInvoice
) -> Invoice:
    """Entry point for webhooks: store a status pushed by the provider."""
    _apply(invoice, result)
    await db.commit()
    await db.refresh(invoice)
    return invoice


def _apply(invoice: Invoice, result: ProviderInvoice) -> None:
    invoice.provider_invoice_id = result.provider_invoice_id or invoice.provider_invoice_id
    invoice.provider_status = result.status
    invoice.payment_url = result.payment_url or invoice.payment_url
    invoice.last_synced_at = datetime.now(UTC)
    invoice.status = PROVIDER_STATUS_MAP.get(result.status, invoice.status)
    if invoice.status == InvoiceStatus.PAID and invoice.paid_at is None:
        invoice.paid_at = result.paid_at or datetime.now(UTC)
