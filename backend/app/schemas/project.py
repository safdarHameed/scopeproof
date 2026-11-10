import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

CURRENCIES = ("EUR", "USD", "GBP")


def _check_currency(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.upper()
    if v not in CURRENCIES:
        raise ValueError(f"must be one of {', '.join(CURRENCIES)}")
    return v


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    currency: str = Field(default="EUR")
    client_name: str = Field(min_length=1, max_length=200)
    client_email: EmailStr
    client_company: str | None = Field(default=None, max_length=200)
    client_address: str | None = Field(default=None, max_length=1000)

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: str) -> str | None:
        return _check_currency(v)

    @field_validator("name", "client_name", "description", "client_company", "client_address")
    @classmethod
    def strip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    currency: str | None = None
    client_name: str | None = Field(default=None, min_length=1, max_length=200)
    client_email: EmailStr | None = None
    client_company: str | None = Field(default=None, max_length=200)
    client_address: str | None = Field(default=None, max_length=1000)

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: str | None) -> str | None:
        return _check_currency(v)


class ProjectStatsRead(BaseModel):
    document_count: int
    item_count: int
    pending_count: int
    flagged_count: int
    approved_total: float
    invoice_status: str | None
    invoice_number: str | None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    currency: str
    client_name: str
    client_email: str
    client_company: str | None
    client_address: str | None
    created_at: datetime
    updated_at: datetime


class ProjectSummary(ProjectRead):
    stats: ProjectStatsRead
