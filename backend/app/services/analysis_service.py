import logging
import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalysisRun, Document, Evidence, InvoiceItem, Project
from app.models.document import DocumentStatus
from app.services.analysis import get_analyzer
from app.services.analysis.base import (
    Category,
    FlagCode,
    ItemSuggestion,
    ProjectContext,
    SourceDocument,
)

log = logging.getLogger(__name__)
CENT = Decimal("0.01")


class AnalysisError(Exception):
    pass


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


async def latest_run(db: AsyncSession, project_id: uuid.UUID) -> AnalysisRun | None:
    result = await db.execute(
        select(AnalysisRun)
        .where(AnalysisRun.project_id == project_id)
        .order_by(AnalysisRun.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def run(db: AsyncSession, project: Project) -> AnalysisRun:
    result = await db.execute(
        select(Document).where(
            Document.project_id == project.id, Document.status == DocumentStatus.PROCESSED
        )
    )
    documents = list(result.scalars())
    if not documents:
        raise AnalysisError("Upload at least one readable document before analyzing.")

    analyzer = get_analyzer()
    analysis = AnalysisRun(
        project_id=project.id,
        engine=analyzer.name,
        status="running",
        document_count=len(documents),
    )
    db.add(analysis)
    await db.flush()

    sources = [
        SourceDocument(
            id=d.id,
            filename=d.filename,
            kind=d.kind,
            text=d.text,
            title=d.title,
            author=d.author,
            recipients=d.recipients,
            sent_at=d.sent_at,
        )
        for d in documents
    ]
    context = ProjectContext(
        name=project.name,
        currency=project.currency,
        client_name=project.client_name,
        client_email=project.client_email,
        client_company=project.client_company,
        description=project.description,
    )
    try:
        suggestions = await analyzer.analyze(context, sources)
    except Exception as exc:
        log.exception("Analysis failed for project %s", project.id)
        analysis.status = "failed"
        analysis.error = str(exc) or exc.__class__.__name__
        analysis.finished_at = datetime.now(UTC)
        await db.commit()
        return analysis

    # A new analysis replaces earlier suggestions; manually added items stay.
    old_ids = select(InvoiceItem.id).where(
        InvoiceItem.project_id == project.id, InvoiceItem.origin == "analysis"
    )
    await db.execute(delete(Evidence).where(Evidence.item_id.in_(old_ids)))
    await db.execute(
        delete(InvoiceItem).where(
            InvoiceItem.project_id == project.id, InvoiceItem.origin == "analysis"
        )
    )

    by_id = {d.id: d for d in documents}
    for position, suggestion in enumerate(suggestions):
        db.add(_to_item(project, analysis, suggestion, position, by_id))

    analysis.status = "completed"
    analysis.item_count = len(suggestions)
    analysis.finished_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(analysis)
    return analysis


def _to_item(
    project: Project,
    analysis: AnalysisRun,
    s: ItemSuggestion,
    position: int,
    documents: dict[uuid.UUID, Document],
) -> InvoiceItem:
    flags = [{"code": f.code, "message": f.message} for f in s.flags]
    codes = {f["code"] for f in flags}

    evidence: list[Evidence] = []
    for i, ev in enumerate(s.evidence):
        doc_id, verified = _locate_quote(ev.quote, ev.document_id, documents)
        evidence.append(
            Evidence(
                document_id=doc_id,
                quote=ev.quote.strip(),
                role=ev.role,
                location=(ev.location or None) and ev.location[:200],
                verified=verified,
                position=i,
            )
        )

    if s.unit_price is None and FlagCode.UNCLEAR_PRICE not in codes:
        flags.append({"code": FlagCode.UNCLEAR_PRICE, "message": "No price found for this work."})
    if not any(e.verified for e in evidence):
        flags.append(
            {
                "code": FlagCode.UNSUPPORTED,
                "message": "None of the supporting quotes could be found in your documents.",
            }
        )

    return InvoiceItem(
        project_id=project.id,
        analysis_run_id=analysis.id,
        origin="analysis",
        category=s.category if s.category in Category.ALL else Category.OTHER,
        description=s.description.strip()[:500] or "Untitled item",
        rationale=s.rationale,
        quantity=Decimal(s.quantity).quantize(CENT),
        unit_price=None if s.unit_price is None else Decimal(s.unit_price).quantize(CENT),
        confidence=s.confidence,
        flags=flags,
        position=position,
        evidence=evidence,
    )


def _locate_quote(
    quote: str, document_id: uuid.UUID | None, documents: dict[uuid.UUID, Document]
) -> tuple[uuid.UUID | None, bool]:
    """Check the quote really appears in its document. If the engine didn't say which
    document, look for it in all of them. Never trust an id from outside this project."""
    needle = _norm(quote)
    if not needle:
        return None, False
    if document_id in documents:
        return document_id, needle in _norm(documents[document_id].text)
    for doc in documents.values():
        if needle in _norm(doc.text):
            return doc.id, True
    return None, False
