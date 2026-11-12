import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PayPalWebhookResource(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    status: str | None = None
    invoice: dict[str, Any] | None = None


class PayPalWebhookEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    create_time: datetime | str | None = None
    resource_type: str | None = None
    event_type: str
    summary: str | None = None
    resource: dict[str, Any] = Field(default_factory=dict)


class WebhookEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: str
    event_type: str
    provider: str
    provider_invoice_id: str | None
    status: str
    error: str | None
    processed_at: datetime | None
    created_at: datetime
