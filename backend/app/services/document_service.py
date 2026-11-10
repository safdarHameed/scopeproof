import hashlib
import io
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentKind, DocumentStatus
from app.models.project import Project
from app.services import storage
from app.services.extraction import (
    CONTENT_TYPES,
    SUPPORTED_EXTENSIONS,
    ExtractionError,
    extension,
    extract,
)

MB = 1024 * 1024


@dataclass
class IncomingFile:
    path: str  # path inside the ZIP, or the uploaded filename
    data: bytes


@dataclass
class Skipped:
    filename: str
    reason: str


@dataclass
class IngestResult:
    documents: list[Document] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)


def expand_upload(filename: str, data: bytes) -> tuple[list[IncomingFile], list[Skipped]]:
    """Unpack ZIP uploads (in memory, with size and count limits); pass other files through."""
    if extension(filename) != ".zip":
        return [IncomingFile(filename, data)], []

    files: list[IncomingFile] = []
    skipped: list[Skipped] = []
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return [], [Skipped(filename, "Not a valid ZIP file")]

    entries = [
        info
        for info in archive.infolist()
        if not info.is_dir()
        and not info.filename.startswith("__MACOSX/")
        and not PurePosixPath(info.filename).name.startswith(".")
    ]
    if len(entries) > settings.MAX_ZIP_ENTRIES:
        return [], [Skipped(filename, f"ZIP has more than {settings.MAX_ZIP_ENTRIES} files")]

    per_file_limit = settings.MAX_UPLOAD_MB * MB
    budget = settings.MAX_EXTRACTED_MB * MB
    for info in entries:
        name = info.filename
        if info.flag_bits & 0x1:
            skipped.append(Skipped(name, "File is password protected"))
            continue
        if extension(name) == ".zip":
            skipped.append(Skipped(name, "Nested ZIP files are not supported"))
            continue
        if extension(name) not in SUPPORTED_EXTENSIONS:
            skipped.append(Skipped(name, _unsupported_reason(name)))
            continue
        # Don't trust the size in the header: read at most limit + 1 bytes.
        with archive.open(info) as fh:
            content = fh.read(min(per_file_limit, budget) + 1)
        if len(content) > per_file_limit:
            skipped.append(Skipped(name, f"File is larger than {settings.MAX_UPLOAD_MB} MB"))
            continue
        if len(content) > budget:
            skipped.append(Skipped(name, "ZIP contents are too large"))
            break
        budget -= len(content)
        files.append(IncomingFile(name, content))
    return files, skipped


def _unsupported_reason(name: str) -> str:
    return f"Unsupported file type '{extension(name) or PurePosixPath(name).name}'"


async def ingest(db: AsyncSession, project: Project, uploads: list[IncomingFile]) -> IngestResult:
    result = IngestResult()
    existing = await db.execute(select(Document.sha256).where(Document.project_id == project.id))
    seen = set(existing.scalars())

    for upload in uploads:
        files, skipped = expand_upload(upload.path, upload.data)
        result.skipped.extend(skipped)
        for incoming in files:
            ext = extension(incoming.path)
            if ext not in SUPPORTED_EXTENSIONS:
                result.skipped.append(Skipped(incoming.path, _unsupported_reason(incoming.path)))
                continue
            digest = hashlib.sha256(incoming.data).hexdigest()
            if digest in seen:
                result.skipped.append(Skipped(incoming.path, "Already uploaded to this project"))
                continue
            seen.add(digest)
            result.documents.append(_create_document(db, project, incoming, ext, digest))

    await db.commit()
    for doc in result.documents:
        await db.refresh(doc)
    return result


def _create_document(
    db: AsyncSession, project: Project, incoming: IncomingFile, ext: str, digest: str
) -> Document:
    doc_id = uuid.uuid4()
    filename = PurePosixPath(incoming.path).name[:255]
    doc = Document(
        id=doc_id,
        project_id=project.id,
        filename=filename,
        source_path=incoming.path[:500],
        content_type=CONTENT_TYPES[ext],
        size_bytes=len(incoming.data),
        sha256=digest,
        storage_key=storage.save(project.id, doc_id, ext, incoming.data),
        kind=DocumentKind.EMAIL if ext == ".eml" else DocumentKind.NOTE,
        status=DocumentStatus.PROCESSED,
        text="",
    )
    try:
        extracted = extract(filename, incoming.data)
    except ExtractionError as exc:
        doc.status = DocumentStatus.FAILED
        doc.error = str(exc)
    else:
        doc.kind = extracted.kind
        doc.text = extracted.text
        doc.word_count = len(extracted.text.split())
        doc.title = extracted.title
        doc.author = extracted.author
        doc.recipients = extracted.recipients
        doc.sent_at = extracted.sent_at
        doc.message_id = extracted.message_id
        doc.in_reply_to = extracted.in_reply_to
    db.add(doc)
    return doc


def sort_key(doc: Document) -> tuple:
    """Contracts first, then the conversation in date order, then everything else."""
    order = {DocumentKind.CONTRACT: 0, DocumentKind.EMAIL: 1, DocumentKind.NOTE: 2}
    ts = doc.sent_at.timestamp() if doc.sent_at else 0.0
    return (order.get(doc.kind, 3), ts, doc.source_path)


async def list_for_project(db: AsyncSession, project_id: uuid.UUID) -> list[Document]:
    result = await db.execute(select(Document).where(Document.project_id == project_id))
    return sorted(result.scalars(), key=sort_key)


async def get(db: AsyncSession, project_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
    doc = await db.get(Document, document_id)
    return doc if doc is not None and doc.project_id == project_id else None


async def delete_document(db: AsyncSession, doc: Document) -> None:
    await db.delete(doc)
    await db.commit()
    storage.delete(doc.storage_key)
