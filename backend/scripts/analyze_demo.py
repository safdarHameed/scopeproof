"""Run real gateway analysis against fictional fixtures; does consume gateway credits.

From backend: uv run python -m scripts.analyze_demo [website|insufficient]
"""

import asyncio
import json
import sys
import uuid
import zipfile
from dataclasses import asdict
from pathlib import Path

from app.services.analysis.base import ProjectContext, SourceDocument
from app.services.analysis.rag import RagAnalyzer
from app.services.extraction import extract


async def main(name):
    root = Path(__file__).resolve().parents[2] / "demo"
    expected = json.loads((root / "expected.json").read_text())
    project = ProjectContext(**expected["project"])
    docs = []
    with zipfile.ZipFile(root / f"{name}.zip") as archive:
        for filename in archive.namelist():
            parsed = extract(filename, archive.read(filename))
            docs.append(
                SourceDocument(
                    id=uuid.uuid5(uuid.NAMESPACE_URL, f"scopeproof-demo/{name}/{filename}"),
                    filename=filename,
                    kind=parsed.kind,
                    text=parsed.text,
                    title=parsed.title,
                    author=parsed.author,
                    recipients=parsed.recipients,
                    sent_at=parsed.sent_at,
                )
            )
    items = await RagAnalyzer().analyze(project, docs)
    print(json.dumps([asdict(item) for item in items], indent=2, default=str))
    clear_total = sum(
        item.quantity * item.unit_price
        for item in items
        if not item.flags and item.unit_price is not None
    )
    target = expected[name]["expected_total_after_review"]
    print(f"Unflagged suggested total: {clear_total}; demo target after review: {target}")
    print("Check item identity, omissions and flags too; a matching total alone is insufficient.")


if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "website"
    if scenario not in {"website", "insufficient"}:
        raise SystemExit("Choose website or insufficient")
    asyncio.run(main(scenario))
