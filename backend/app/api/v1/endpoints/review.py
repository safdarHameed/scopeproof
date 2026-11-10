import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, ProjectDep
from app.models.analysis import ItemStatus
from app.schemas.item import AnalysisRunRead, ItemCreate, ItemRead, ItemUpdate, ReviewState
from app.services import analysis_service, invoice_service, item_service
from app.services.analysis_service import AnalysisError
from app.services.invoice_service import InvoiceError
from app.services.item_service import ItemError

router = APIRouter(prefix="/projects/{project_id}", tags=["review"])


async def _state(db: DbSession, project) -> ReviewState:
    items = await item_service.list_for_project(db, project.id)
    run = await analysis_service.latest_run(db, project.id)
    pending = [i for i in items if i.status == ItemStatus.PENDING]
    return ReviewState(
        analysis=AnalysisRunRead.model_validate(run) if run else None,
        items=[ItemRead.model_validate(i) for i in items],
        approved_total=item_service.approved_total(items),
        pending_count=len(pending),
        flagged_count=sum(1 for i in pending if i.flags),
        locked=await invoice_service.get_active(db, project.id) is not None,
        currency=project.currency,
    )


async def _unlocked(db: DbSession, project) -> None:
    try:
        await invoice_service.ensure_unlocked(db, project.id)
    except InvoiceError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None


@router.get("/review", response_model=ReviewState)
async def get_review(project: ProjectDep, db: DbSession) -> ReviewState:
    return await _state(db, project)


@router.post("/analysis", response_model=ReviewState)
async def run_analysis(project: ProjectDep, db: DbSession) -> ReviewState:
    await _unlocked(db, project)
    try:
        run = await analysis_service.run(db, project)
    except AnalysisError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    if run.status == "failed":
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Analysis failed: {run.error}")
    return await _state(db, project)


@router.post("/items", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def add_item(data: ItemCreate, project: ProjectDep, db: DbSession) -> ItemRead:
    await _unlocked(db, project)
    return ItemRead.model_validate(await item_service.create_manual(db, project, data))


@router.post("/items/approve-clear", response_model=ReviewState)
async def approve_clear_items(project: ProjectDep, db: DbSession) -> ReviewState:
    await _unlocked(db, project)
    await item_service.approve_clear(db, project.id)
    return await _state(db, project)


async def _get_item(db: DbSession, project, item_id: uuid.UUID):
    item = await item_service.get(db, project.id, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.patch("/items/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: uuid.UUID, data: ItemUpdate, project: ProjectDep, db: DbSession
) -> ItemRead:
    await _unlocked(db, project)
    item = await _get_item(db, project, item_id)
    try:
        item = await item_service.update(db, item, data)
    except ItemError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    return ItemRead.model_validate(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: uuid.UUID, project: ProjectDep, db: DbSession) -> None:
    await _unlocked(db, project)
    try:
        await item_service.delete_item(db, await _get_item(db, project, item_id))
    except ItemError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
