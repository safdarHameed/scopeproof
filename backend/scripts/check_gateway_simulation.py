"""Exercise the real SDK against the local Postman fixture, not the real gateway.

Start simulation on 4511, then run from backend:
  uv run python -m scripts.check_gateway_simulation
"""

import asyncio
import uuid

from pydantic import SecretStr

from app.core.config import Settings
from app.services.analysis.base import ProjectContext, SourceDocument
from app.services.analysis.llm import AstropodsProvider
from app.services.analysis.rag import RagAnalyzer


async def main():
    config = Settings(
        ASTRO_GATEWAY_URL="http://127.0.0.1:4511/astropods",
        ASTRO_GATEWAY_API_KEY=SecretStr("test-key"),
    )
    provider = AstropodsProvider(config)
    try:
        items = await RagAnalyzer(provider).analyze(
            ProjectContext("Website", "EUR", "Maya", "maya@northstar.example"),
            [
                SourceDocument(
                    uuid.uuid4(),
                    "approval.eml",
                    "email",
                    "I approve authentication for EUR 200 and accept delivery.",
                    author="maya@northstar.example",
                )
            ],
        )
        assert len(items) == 1 and not items[0].flags
        assert str(items[0].unit_price) == "200"
        print("HTTP simulation: grounded EUR 200 item received through the real SDK")
    finally:
        await provider.close()
    config.ASTRO_GATEWAY_API_KEY = SecretStr("denied-test-key")
    provider = AstropodsProvider(config)
    try:
        await provider.embed(["test"])
        raise AssertionError("Expected access denial")
    except RuntimeError as exc:
        assert getattr(exc.__cause__, "status_code", None) == 403
        assert "denied-test-key" not in str(exc)
        print("HTTP simulation: 403 becomes a safe error")
    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
