import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.api.deps import DbSession, ProjectDep
from app.core.config import settings
from app.schemas.document import (
    DocumentDetail,
    DocumentRead,
    DocumentUpdate,
    SkippedFile,
    UploadResult,
)
from app.services import document_service, storage
from app.services.document_service import IncomingFile

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])

CHUNK = 1024 * 1024


async def _read_limited(upload: UploadFile) -> bytes:
    limit = settings.MAX_UPLOAD_MB * CHUNK
    data = bytearray()
    while chunk := await upload.read(CHUNK):
        data.extend(chunk)
        if len(data) > limit:
            raise HTTPException(
                status.HTTP_413_CONTENT_TOO_LARGE,
                f"{upload.filename} is larger than {settings.MAX_UPLOAD_MB} MB",
            )
    return bytes(data)


@router.get("", response_model=list[DocumentRead])
async def list_documents(project: ProjectDep, db: DbSession) -> list[DocumentRead]:
    docs = await document_service.list_for_project(db, project.id)
    return [DocumentRead.model_validate(d) for d in docs]


@router.post("", response_model=UploadResult, status_code=status.HTTP_201_CREATED)
async def upload_documents(
    project: ProjectDep,
    db: DbSession,
    files: Annotated[list[UploadFile], File(description="ZIP, .eml, .txt, .md or .pdf")],
) -> UploadResult:
    if not files:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "No files uploaded")
    incoming = [IncomingFile(f.filename or "upload", await _read_limited(f)) for f in files]
    result = await document_service.ingest(db, project, incoming)
    return UploadResult(
        documents=[DocumentRead.model_validate(d) for d in result.documents],
        skipped=[SkippedFile(filename=s.filename, reason=s.reason) for s in result.skipped],
    )


async def _get_doc(project: ProjectDep, db: DbSession, document_id: uuid.UUID):
    doc = await document_service.get(db, project.id, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: uuid.UUID, project: ProjectDep, db: DbSession
) -> DocumentDetail:
    return DocumentDetail.model_validate(await _get_doc(project, db, document_id))


@router.get("/{document_id}/file")
async def download_document(document_id: uuid.UUID, project: ProjectDep, db: DbSession) -> Response:
    doc = await _get_doc(project, db, document_id)
    try:
        data = storage.read(doc.storage_key)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File is no longer stored") from None
    safe_name = doc.filename.replace('"', "")
    return Response(
        content=data,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.patch("/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: uuid.UUID, data: DocumentUpdate, project: ProjectDep, db: DbSession
) -> DocumentRead:
    doc = await _get_doc(project, db, document_id)
    doc.kind = data.kind
    await db.commit()
    await db.refresh(doc)
    return DocumentRead.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: uuid.UUID, project: ProjectDep, db: DbSession) -> None:
    await document_service.delete_document(db, await _get_doc(project, db, document_id))
