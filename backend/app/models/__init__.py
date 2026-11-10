"""Import every model here so Alembic autogenerate can discover it."""

from app.db.base import Base
from app.models.analysis import AnalysisRun, Evidence, InvoiceItem
from app.models.document import Document
from app.models.invoice import Invoice, InvoiceLine
from app.models.project import Project
from app.models.user import User

__all__ = [
    "AnalysisRun",
    "Base",
    "Document",
    "Evidence",
    "Invoice",
    "InvoiceItem",
    "InvoiceLine",
    "Project",
    "User",
]
