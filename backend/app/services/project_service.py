import uuid
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalysisRun, Document, Evidence, Invoice, InvoiceItem, InvoiceLine, Project
from app.models.analysis import ItemStatus
from app.models.invoice import InvoiceStatus
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services import storage


@dataclass
class ProjectStats:
    document_count: int = 0
    item_count: int = 0
    pending_count: int = 0
    flagged_count: int = 0
    approved_total: float = 0.0
    invoice_status: str | None = None
    invoice_number: str | None = None


async def list_for_owner(db: AsyncSession, owner_id: uuid.UUID) -> list[Project]:
    result = await db.execute(
        select(Project).where(Project.owner_id == owner_id).order_by(Project.created_at.desc())
    )
    return list(result.scalars())


async def get_for_owner(
    db: AsyncSession, project_id: uuid.UUID, owner_id: uuid.UUID
) -> Project | None:
    project = await db.get(Project, project_id)
    if project is None or project.owner_id != owner_id:
        return None
    return project


async def create(db: AsyncSession, owner_id: uuid.UUID, data: ProjectCreate) -> Project:
    project = Project(owner_id=owner_id, **data.model_dump())
    project.client_email = project.client_email.lower()
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update(db: AsyncSession, project: Project, data: ProjectUpdate) -> Project:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(project, key, value.lower() if key == "client_email" and value else value)
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project: Project) -> None:
    # Explicit deletes keep this working on SQLite (tests) where FK cascades are off.
    item_ids = select(InvoiceItem.id).where(InvoiceItem.project_id == project.id)
    invoice_ids = select(Invoice.id).where(Invoice.project_id == project.id)
    await db.execute(delete(Evidence).where(Evidence.item_id.in_(item_ids)))
    await db.execute(delete(InvoiceLine).where(InvoiceLine.invoice_id.in_(invoice_ids)))
    await db.execute(delete(Invoice).where(Invoice.project_id == project.id))
    await db.execute(delete(InvoiceItem).where(InvoiceItem.project_id == project.id))
    await db.execute(delete(AnalysisRun).where(AnalysisRun.project_id == project.id))
    await db.execute(delete(Document).where(Document.project_id == project.id))
    await db.delete(project)
    await db.commit()
    storage.delete_project(project.id)


async def stats_for(
    db: AsyncSession, project_ids: list[uuid.UUID]
) -> dict[uuid.UUID, ProjectStats]:
    stats = {pid: ProjectStats() for pid in project_ids}
    if not project_ids:
        return stats

    docs = await db.execute(
        select(Document.project_id, func.count())
        .where(Document.project_id.in_(project_ids))
        .group_by(Document.project_id)
    )
    for pid, count in docs.all():
        stats[pid].document_count = count

    items = await db.execute(select(InvoiceItem).where(InvoiceItem.project_id.in_(project_ids)))
    for item in items.scalars():
        s = stats[item.project_id]
        s.item_count += 1
        if item.status == ItemStatus.PENDING:
            s.pending_count += 1
            if item.flags:
                s.flagged_count += 1
        elif item.status == ItemStatus.APPROVED and item.amount is not None:
            s.approved_total += float(item.amount)

    invoices = await db.execute(
        select(Invoice)
        .where(Invoice.project_id.in_(project_ids), Invoice.status.in_(InvoiceStatus.ACTIVE))
        .order_by(Invoice.created_at)
    )
    for invoice in invoices.scalars():
        stats[invoice.project_id].invoice_status = invoice.status
        stats[invoice.project_id].invoice_number = invoice.number
    return stats
