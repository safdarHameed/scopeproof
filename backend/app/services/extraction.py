"""Turn raw uploaded files into text + metadata, preserving authors, dates and references.

Supported: .eml (emails), .txt / .md (plain text), .pdf (text layer only, no OCR).
Kept free of database code so it can be reused and unit-tested on its own.
"""

import email
import html
import io
import re
from dataclasses import dataclass, field
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.utils import getaddresses, parsedate_to_datetime

from pypdf import PdfReader

from app.models.document import DocumentKind

SUPPORTED_EXTENSIONS = {".eml", ".txt", ".md", ".pdf"}
CONTENT_TYPES = {
    ".eml": "message/rfc822",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
}
CONTRACT_HINT = re.compile(
    r"contract|agreement|\bsow\b|statement[-_ ]of[-_ ]work|proposal|quote|terms", re.I
)


class ExtractionError(Exception):
    pass


@dataclass
class Extracted:
    kind: str
    text: str
    title: str | None = None
    author: str | None = None
    recipients: str | None = None
    sent_at: datetime | None = None
    message_id: str | None = None
    in_reply_to: str | None = None
    attachments: list[str] = field(default_factory=list)


def extension(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot != -1 else ""


def guess_kind(filename: str, ext: str) -> str:
    if ext == ".eml":
        return DocumentKind.EMAIL
    return DocumentKind.CONTRACT if CONTRACT_HINT.search(filename) else DocumentKind.NOTE


def extract(filename: str, data: bytes) -> Extracted:
    ext = extension(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise ExtractionError(f"Unsupported file type '{ext or filename}'")
    if ext == ".eml":
        return _extract_email(data)
    text = _extract_pdf(data) if ext == ".pdf" else _decode(data)
    text = normalize_text(text)
    if not text:
        raise ExtractionError("No text found (scanned PDFs are not supported yet)")
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), None)
    return Extracted(kind=guess_kind(filename, ext), text=text, title=_truncate(first_line, 500))


# --- helpers ---------------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _extract_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pypdf raises many different error types on bad input
        raise ExtractionError("Could not read PDF") from exc
    return "\n\n".join(p.strip() for p in pages if p.strip())


def _html_to_text(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", markup)
    markup = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>", "\n", markup)
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


_QUOTE_HEADER = re.compile(r"^On .{5,200} wrote:\s*$", re.M)


def strip_quoted_reply(body: str) -> str:
    """Drop the quoted earlier messages so evidence points at the email that said it first."""
    match = _QUOTE_HEADER.search(body)
    if match:
        body = body[: match.start()]
    lines = [line for line in body.splitlines() if not line.lstrip().startswith(">")]
    return "\n".join(lines)


def _format_addresses(values: list[str]) -> str | None:
    pairs = getaddresses(values)
    formatted = [f"{name} <{addr}>" if name else addr for name, addr in pairs if addr]
    return ", ".join(formatted) or None


def _extract_email(data: bytes) -> Extracted:
    try:
        msg = email.message_from_bytes(data, policy=policy.default)
    except Exception as exc:
        raise ExtractionError("Could not parse email") from exc
    if not isinstance(msg, EmailMessage) or not (msg["From"] or msg["Subject"]):
        raise ExtractionError("File does not look like an email (.eml)")

    body_part = msg.get_body(preferencelist=("plain", "html"))
    body = ""
    if body_part is not None:
        content = body_part.get_content()
        body = _html_to_text(content) if body_part.get_content_type() == "text/html" else content
    body = strip_quoted_reply(body)

    attachments: list[str] = []
    attachment_texts: list[str] = []
    for part in msg.iter_attachments():
        name = part.get_filename() or "attachment"
        attachments.append(name)
        ext = extension(name)
        if ext in {".txt", ".md", ".pdf"}:
            try:
                payload = part.get_payload(decode=True) or b""
                text = _extract_pdf(payload) if ext == ".pdf" else _decode(payload)
                attachment_texts.append(f"[Attachment: {name}]\n{normalize_text(text)}")
            except ExtractionError:
                attachment_texts.append(f"[Attachment: {name} (could not be read)]")
        else:
            attachment_texts.append(f"[Attachment: {name}]")

    text = normalize_text("\n\n".join([body, *attachment_texts]))

    sent_at = None
    if msg["Date"]:
        try:
            sent_at = parsedate_to_datetime(str(msg["Date"]))
        except (TypeError, ValueError):
            sent_at = None

    recipients = _format_addresses(
        [str(v) for v in (msg.get_all("To") or [])] + [str(v) for v in (msg.get_all("Cc") or [])]
    )
    return Extracted(
        kind=DocumentKind.EMAIL,
        text=text,
        title=_truncate(str(msg["Subject"] or "").strip() or None, 500),
        author=_truncate(_format_addresses([str(msg["From"] or "")]), 320),
        recipients=recipients,
        sent_at=sent_at,
        message_id=_truncate(str(msg["Message-ID"] or "").strip() or None, 500),
        in_reply_to=_truncate(str(msg["In-Reply-To"] or "").strip() or None, 500),
        attachments=attachments,
    )


def _truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value if len(value) <= limit else value[: limit - 1] + "…"
