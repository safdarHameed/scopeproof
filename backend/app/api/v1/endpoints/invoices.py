from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, ProjectDep
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoice import InvoiceConfirm, InvoiceRead, InvoiceState
from app.services import invoice_service
from app.services.invoice_service import InvoiceError
from app.services.payments import get_payment_provider

router = APIRouter(prefix="/projects/{project_id}/invoice", tags=["invoices"])


async def _state(db: DbSession, project) -> InvoiceState:
    invoices = await invoice_service.list_for_project(db, project.id)
    active = next((i for i in invoices if i.status in InvoiceStatus.ACTIVE), None)
    provider = get_payment_provider()
    return InvoiceState(
        invoice=InvoiceRead.model_validate(active) if active else None,
        history=[InvoiceRead.model_validate(i) for i in invoices if i is not active],
        provider=provider.name,
        provider_label=provider.label,
    )


async def _active(db: DbSession, project) -> Invoice:
    invoice = await invoice_service.get_active(db, project.id)
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No invoice yet. Confirm the draft first.")
    return invoice


def _conflict(exc: InvoiceError) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("", response_model=InvoiceState)
async def get_invoice(project: ProjectDep, db: DbSession) -> InvoiceState:
    return await _state(db, project)


@router.post("", response_model=InvoiceState, status_code=status.HTTP_201_CREATED)
async def confirm_invoice(data: InvoiceConfirm, project: ProjectDep, db: DbSession) -> InvoiceState:
    try:
        await invoice_service.confirm(db, project, data.due_date, data.note)
    except InvoiceError as exc:
        raise _conflict(exc) from None
    return await _state(db, project)


@router.post("/reopen", response_model=InvoiceState)
async def reopen_invoice(project: ProjectDep, db: DbSession) -> InvoiceState:
    try:
        await invoice_service.reopen(db, await _active(db, project))
    except InvoiceError as exc:
        raise _conflict(exc) from None
    return await _state(db, project)


@router.post("/send", response_model=InvoiceState)
async def send_invoice(project: ProjectDep, db: DbSession, user: CurrentUser) -> InvoiceState:
    try:
        await invoice_service.send(db, await _active(db, project), project, user)
    except InvoiceError as exc:
        raise _conflict(exc) from None
    return await _state(db, project)


@router.post("/refresh", response_model=InvoiceState)
async def refresh_invoice_status(project: ProjectDep, db: DbSession) -> InvoiceState:
    try:
        await invoice_service.sync_status(db, await _active(db, project))
    except InvoiceError as exc:
        raise _conflict(exc) from None
    return await _state(db, project)


@router.post("/cancel", response_model=InvoiceState)
async def cancel_invoice(project: ProjectDep, db: DbSession) -> InvoiceState:
    try:
        await invoice_service.cancel(db, await _active(db, project))
    except InvoiceError as exc:
        raise _conflict(exc) from None
    return await _state(db, project)
