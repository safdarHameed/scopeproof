import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    source_path: str
    kind: str
    content_type: str
    size_bytes: int
    status: str
    error: str | None
    title: str | None
    author: str | None
    recipients: str | None
    sent_at: datetime | None
    word_count: int
    created_at: datetime


class DocumentDetail(DocumentRead):
    message_id: str | None
    in_reply_to: str | None
    text: str


class DocumentUpdate(BaseModel):
    kind: Literal["contract", "email", "note"]


class SkippedFile(BaseModel):
    filename: str
    reason: str


class UploadResult(BaseModel):
    documents: list[DocumentRead]
    skipped: list[SkippedFile]
