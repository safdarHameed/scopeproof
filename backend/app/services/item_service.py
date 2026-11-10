import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InvoiceItem, Project
from app.models.analysis import ItemStatus
from app.schemas.item import ItemCreate, ItemUpdate


class ItemError(Exception):
    pass


async def list_for_project(db: AsyncSession, project_id: uuid.UUID) -> list[InvoiceItem]:
    result = await db.execute(
        select(InvoiceItem)
        .where(InvoiceItem.project_id == project_id)
        .order_by(InvoiceItem.position, InvoiceItem.created_at)
    )
    return list(result.scalars())


async def get(db: AsyncSession, project_id: uuid.UUID, item_id: uuid.UUID) -> InvoiceItem | None:
    item = await db.get(InvoiceItem, item_id)
    return item if item is not None and item.project_id == project_id else None


async def create_manual(db: AsyncSession, project: Project, data: ItemCreate) -> InvoiceItem:
    max_pos = await db.scalar(
        select(func.max(InvoiceItem.position)).where(InvoiceItem.project_id == project.id)
    )
    item = InvoiceItem(
        project_id=project.id,
        origin="manual",
        category=data.category,
        description=data.description,
        rationale=data.rationale,
        quantity=data.quantity,
        unit_price=data.unit_price,
        # Something the freelancer adds by hand is approved unless it still lacks a price.
        status=ItemStatus.APPROVED if data.unit_price is not None else ItemStatus.PENDING,
        flags=[],
        position=(max_pos if max_pos is not None else -1) + 1,
        evidence=[],
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update(db: AsyncSession, item: InvoiceItem, data: ItemUpdate) -> InvoiceItem:
    changes = data.model_dump(exclude_unset=True, exclude={"status", "acknowledge_flags"})
    for key, value in changes.items():
        if getattr(item, key) != value:
            setattr(item, key, value)
            if item.origin == "analysis":
                item.edited = True

    if data.status is not None:
        _set_status(item, data.status, data.acknowledge_flags)
    elif item.status == ItemStatus.APPROVED and item.unit_price is None:
        raise ItemError("An approved item needs a price.")

    await db.commit()
    await db.refresh(item)
    return item


def _set_status(item: InvoiceItem, status: str, acknowledge_flags: bool) -> None:
    if status == ItemStatus.APPROVED:
        if item.unit_price is None or item.quantity <= 0:
            raise ItemError("Set a price and quantity before approving this item.")
        if item.flags and not acknowledge_flags:
            raise ItemError(
                "This item has open review flags. Confirm you have checked them to approve it."
            )
        item.flags_acknowledged = bool(item.flags)
    else:
        item.flags_acknowledged = False
    item.status = status


async def approve_clear(db: AsyncSession, project_id: uuid.UUID) -> int:
    """Approve every pending item that has a price and no flags."""
    count = 0
    for item in await list_for_project(db, project_id):
        if item.status == ItemStatus.PENDING and not item.flags and item.unit_price is not None:
            item.status = ItemStatus.APPROVED
            count += 1
    await db.commit()
    return count


async def delete_item(db: AsyncSession, item: InvoiceItem) -> None:
    if item.origin != "manual":
        raise ItemError("Suggested items can't be deleted. Exclude them instead.")
    await db.delete(item)
    await db.commit()


def approved_total(items: list[InvoiceItem]) -> Decimal:
    return sum(
        (i.amount for i in items if i.status == ItemStatus.APPROVED and i.amount is not None),
        Decimal("0.00"),
    )
