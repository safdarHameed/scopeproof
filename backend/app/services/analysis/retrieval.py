"""Project-local retrieval. Offsets always address the original extracted text."""

import math
import re
from dataclasses import dataclass

from app.services.analysis.base import SourceDocument


@dataclass(frozen=True)
class Chunk:
    id: str
    document: SourceDocument
    start: int
    end: int

    @property
    def text(self) -> str:
        return self.document.text[self.start : self.end]

    def record(self) -> dict:
        d = self.document
        return {
            "chunk_id": self.id,
            "document_id": str(d.id),
            "filename": d.filename,
            "kind": d.kind,
            "title": d.title,
            "author": d.author,
            "recipients": d.recipients,
            "sent_at": d.sent_at.isoformat() if d.sent_at else None,
            "start": self.start,
            "end": self.end,
            "text": self.text,
        }


def chunk_documents(
    documents: list[SourceDocument], size: int = 1600, overlap: int = 200
) -> list[Chunk]:
    if not 0 <= overlap < size:
        raise ValueError("Chunk overlap must be smaller than chunk size")
    chunks = []
    for doc in sorted(documents, key=lambda d: str(d.id)):
        start = 0
        while start < len(doc.text):
            end = min(start + size, len(doc.text))
            if end < len(doc.text):
                boundary = doc.text.rfind("\n", start + size // 2, end)
                if boundary != -1:
                    end = boundary + 1
            if doc.text[start:end].strip():
                chunks.append(Chunk(f"{doc.id}:{start}:{end}", doc, start, end))
            if end == len(doc.text):
                break
            start = end - overlap
    return chunks


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.casefold()))


def cosine(a: list[float], b: list[float]) -> float:
    if not a or len(a) != len(b) or not all(math.isfinite(v) for v in (*a, *b)):
        raise ValueError("Invalid embedding dimensions or values")
    norm = math.sqrt(sum(v * v for v in a) * sum(v * v for v in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / norm if norm else 0.0


def retrieve(
    chunks: list[Chunk],
    vectors: list[list[float]],
    query: str,
    query_vector: list[float],
    limit: int = 16,
) -> list[Chunk]:
    """Semantic ranking plus exact-term matches; inputs contain one project's data only."""
    words = _tokens(query)
    ranked = sorted(
        zip(chunks, vectors, strict=True),
        key=lambda cv: (
            cosine(cv[1], query_vector)
            + 0.35 * len(words & _tokens(cv[0].text)) / max(1, len(words))
        ),
        reverse=True,
    )
    return [chunk for chunk, _ in ranked[:limit]]
