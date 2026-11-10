"""Placeholder analyzer used until the RAG engine is ready.

It does a simple scan for money amounts and returns each one as a low-confidence item, so the
review flow works end to end. Replace it by setting ANALYZER=rag once the RAG analyzer exists.
"""

import re
from decimal import Decimal, InvalidOperation

from app.services.analysis.base import (
    EvidenceRole,
    EvidenceSuggestion,
    Flag,
    FlagCode,
    ItemSuggestion,
    ProjectContext,
    SourceDocument,
)


class PlaceholderAnalyzer:
    name = "placeholder"

    async def analyze(
        self, project: ProjectContext, documents: list[SourceDocument]
    ) -> list[ItemSuggestion]:
        return self._money_scan(documents, project.currency)

    _AMOUNT = re.compile(
        r"(?:(?P<cur1>EUR|USD|GBP|€|\$|£)\s?(?P<a1>\d[\d,]*(?:\.\d{1,2})?))"
        r"|(?:(?P<a2>\d[\d,]*(?:\.\d{1,2})?)\s?(?P<cur2>EUR|USD|GBP|€|euros?|dollars?))",
        re.I,
    )

    def _money_scan(self, docs: list[SourceDocument], currency: str) -> list[ItemSuggestion]:
        items: list[ItemSuggestion] = []
        seen: set[tuple[str, Decimal]] = set()
        for doc in docs:
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", doc.text):
                match = self._AMOUNT.search(sentence)
                if not match:
                    continue
                raw = (match.group("a1") or match.group("a2") or "").replace(",", "")
                try:
                    amount = Decimal(raw)
                except InvalidOperation:
                    continue
                key = (str(doc.id), amount)
                if amount <= 0 or key in seen:
                    continue
                seen.add(key)
                quote = sentence.strip()
                items.append(
                    ItemSuggestion(
                        description=quote[:120],
                        unit_price=amount,
                        confidence=0.2,
                        rationale="Placeholder analyzer: found a money amount in this document.",
                        flags=[
                            Flag(
                                FlagCode.LOW_CONFIDENCE,
                                "Found by a simple amount scan, not by the AI analysis. "
                                "Check the description, price and approval yourself.",
                            )
                        ],
                        evidence=[EvidenceSuggestion(doc.id, quote, EvidenceRole.PRICE)],
                    )
                )
                if len(items) >= 15:
                    return items
        return items
