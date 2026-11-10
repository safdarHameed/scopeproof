import io
import json
import uuid
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.analysis.base import ProjectContext, SourceDocument
from app.services.analysis.rag import RagAnalyzer, to_suggestion
from app.services.analysis.rag_models import Candidates, Citation, Decision
from app.services.analysis.retrieval import chunk_documents, cosine, retrieve
from app.services.extraction import extract

PROJECT = ProjectContext("Northstar website", "EUR", "Maya Chen", "maya@northstar.example")


def source(text, author="Maya Chen <maya@northstar.example>"):
    return SourceDocument(
        uuid.uuid4(),
        "message.eml",
        "email",
        text,
        author=author,
        sent_at=datetime(2026, 10, 1, tzinfo=UTC),
    )


def decision(chunks, **overrides):
    values = dict(
        description="Authentication",
        category="extra",
        quantity="1",
        unit_price="200.00",
        currency="EUR",
        rationale="Agreed and accepted",
        price_approved=True,
        ready_to_invoice=True,
        conflicting_price=False,
        confidence=0.95,
        evidence=[
            Citation(chunk_id=chunks[0].id, quote=chunks[0].text, role=role)
            for role in ["price", "approval", "acceptance"]
        ],
    )
    values.update(overrides)
    return Decision(**values)


def test_chunks_keep_exact_offsets_and_cover_end():
    doc = source("alpha beta\n" * 600 + "FINAL CANCELLATION")
    chunks = chunk_documents([doc])
    assert all(c.text == doc.text[c.start : c.end] for c in chunks)
    assert chunks[-1].end == len(doc.text)
    assert "FINAL CANCELLATION" in chunks[-1].text
    assert all(a.end >= b.start for a, b in zip(chunks, chunks[1:], strict=False))


def test_retrieval_and_invalid_embeddings():
    chunks = chunk_documents([source("Authentication"), source("Dark theme")])
    wanted = next(c for c in chunks if c.text == "Authentication")
    vectors = [[1, 0] if c is wanted else [0, 1] for c in chunks]
    assert retrieve(chunks, vectors, "Authentication", [1, 0], 1) == [wanted]
    with pytest.raises(ValueError):
        cosine([1, 2], [1])
    with pytest.raises(ValueError):
        cosine([float("nan")], [1])


def test_supported_item_and_unapproved_sender():
    chunks = chunk_documents([source("I approve EUR 200 for authentication and accept delivery.")])
    result = to_suggestion(decision(chunks), chunks, PROJECT)
    assert result.unit_price == Decimal("200")
    assert not result.flags
    seller = chunk_documents([source(chunks[0].text, "Alex <alex@studio.example>")])
    result = to_suggestion(decision(seller), seller, PROJECT)
    assert {f.code for f in result.flags} >= {"missing_approval", "not_ready", "low_confidence"}


def test_hallucinated_citations_prices_and_currency_are_flagged():
    chunks = chunk_documents([source("I approve EUR 200 and accept delivery.")])
    bad = decision(
        chunks,
        unit_price="900",
        currency="USD",
        evidence=[
            Citation(chunk_id="outside-project", quote="Approved EUR 900", role="approval"),
        ],
    )
    result = to_suggestion(bad, chunks, PROJECT)
    assert result.unit_price is None
    assert not result.evidence
    assert {f.code for f in result.flags} >= {"unsupported", "unclear_price", "missing_approval"}
    for amount in ["NaN", "Infinity", "-1", "0.001", "100000000"]:
        with pytest.raises(ValueError):
            to_suggestion(decision(chunks, unit_price=amount), chunks, PROJECT)


def test_unresolved_conflict_and_partial_context_need_review():
    chunks = chunk_documents([source("I approve EUR 200 and accept delivery.")])
    result = to_suggestion(decision(chunks, conflicting_price=True), chunks, PROJECT, partial=True)
    assert result.unit_price is None
    assert {f.code for f in result.flags} >= {"conflicting_price", "low_confidence"}


class ScriptedProvider:
    """Tests orchestration and grounding, NOT the quality of an actual model."""

    def __init__(self):
        self.embed_calls = []
        self.decision_calls = []

    async def embed(self, texts):
        self.embed_calls.append(texts)
        return [[1.0, 0.0] for _ in texts]

    async def structured(self, instructions, content, schema):
        payload = json.loads(content)
        if schema is Candidates:
            return Candidates(work_items=["Authentication"])
        self.decision_calls.append(payload)
        c = payload["sources"][0]
        return Decision(
            description="Authentication",
            category="extra",
            quantity="1",
            unit_price="200",
            currency="EUR",
            rationale="Supported",
            price_approved=True,
            ready_to_invoice=True,
            conflicting_price=False,
            confidence=0.9,
            evidence=[
                Citation(chunk_id=c["chunk_id"], quote=c["text"], role=r)
                for r in ["price", "approval", "acceptance"]
            ],
        )

    async def close(self):
        pass


async def test_pipeline_embeds_retrieves_and_preserves_document_identity():
    provider = ScriptedProvider()
    doc = source("I approve authentication for EUR 200 and accept the delivery.")
    items = await RagAnalyzer(provider).analyze(PROJECT, [doc])
    assert len(provider.embed_calls) == 2
    assert provider.decision_calls[0]["sources"][0]["document_id"] == str(doc.id)
    assert len(items) == 1
    assert items[0].evidence[0].document_id == doc.id
    assert not items[0].flags


def test_demo_archives_parse_with_real_upload_extractor():
    demo = Path(__file__).resolve().parents[2] / "demo"
    for name in ["website", "insufficient"]:
        with zipfile.ZipFile(io.BytesIO((demo / f"{name}.zip").read_bytes())) as archive:
            assert not any("expected" in n for n in archive.namelist())
            for filename in archive.namelist():
                parsed = extract(filename, archive.read(filename))
                assert parsed.text
                if filename.endswith(".eml"):
                    assert parsed.author and parsed.sent_at and parsed.message_id
