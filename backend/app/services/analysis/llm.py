"""Astropods gateway adapter. No secrets or document bodies are included in surfaced errors."""

import json
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class RagProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    async def structured(self, instructions: str, content: str, schema: type[T]) -> T: ...
    async def close(self) -> None: ...


class AstropodsProvider:
    def __init__(self, config):
        from openai import AsyncOpenAI

        if not config.ASTRO_GATEWAY_API_KEY.get_secret_value():
            raise ValueError("Set ASTRO_GATEWAY_API_KEY in backend/.env to use ANALYZER=rag")
        if not config.ASTRO_GATEWAY_URL:
            raise ValueError("Set ASTRO_GATEWAY_URL in backend/.env to use ANALYZER=rag")
        base = config.ASTRO_GATEWAY_URL.rstrip("/")
        self.client = AsyncOpenAI(
            base_url=base if base.endswith("/v1") else base + "/v1",
            api_key=config.ASTRO_GATEWAY_API_KEY.get_secret_value(),
            timeout=config.RAG_REQUEST_TIMEOUT_SECONDS,
            max_retries=1,
        )
        self.model = config.RAG_MODEL
        self.embedding_model = config.RAG_EMBEDDING_MODEL

    async def embed(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAIError

        vectors = []
        try:
            for start in range(0, len(texts), 64):
                batch = texts[start : start + 64]
                result = await self.client.embeddings.create(
                    model=self.embedding_model,
                    input=batch,
                    encoding_format="float",
                )
                ordered = sorted(result.data, key=lambda row: row.index)
                if [row.index for row in ordered] != list(range(len(batch))):
                    raise ValueError("Embedding provider returned an incomplete batch")
                vectors.extend(row.embedding for row in ordered)
        except OpenAIError as exc:
            raise RuntimeError(
                "Embedding provider failed; check credentials and availability"
            ) from exc
        return vectors

    async def structured(self, instructions: str, content: str, schema: type[T]) -> T:
        from openai import OpenAIError

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": instructions
                        + "\nReturn ONLY a JSON object matching this schema, without Markdown:\n"
                        + json.dumps(schema.model_json_schema()),
                    },
                    {"role": "user", "content": content},
                ],
            )
        except OpenAIError as exc:
            raise RuntimeError("AI provider failed; check credentials and availability") from exc
        if not response.choices or response.choices[0].finish_reason != "stop":
            raise RuntimeError("AI analysis was refused or incomplete")
        raw = response.choices[0].message.content
        if not raw:
            raise RuntimeError("AI analysis returned no text")
        try:
            return schema.model_validate_json(raw)
        except ValueError:
            raise RuntimeError("AI returned invalid structured data; try analysis again") from None

    async def close(self) -> None:
        await self.client.close()
