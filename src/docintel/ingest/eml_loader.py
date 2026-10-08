"""Email: headers and body as text, every attachment loaded as a child Document."""

from __future__ import annotations

import email
import email.policy
from datetime import datetime
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from pathlib import Path

from docintel.documents import Document, Kind, Severity, document_id
from docintel.ingest.registry import load_bytes, register
from docintel.ingest.security import strip_hidden_html
from docintel.ingest.text_loader import html_to_text

MAX_ATTACHMENTS = 20
_HEADERS = ("From", "To", "Cc", "Subject", "Date")


def _date(msg: EmailMessage) -> str | None:
    raw = str(msg.get("Date") or "")
    if not raw:
        return None
    try:
        parsed: datetime = parsedate_to_datetime(raw)
        return parsed.isoformat()
    except (TypeError, ValueError):
        return raw


def _text_of(part: EmailMessage) -> str:
    payload = part.get_content()
    return payload if isinstance(payload, str) else ""


@register("message/rfc822")
def load_email(path: Path, data: bytes, media_type: str) -> Document:
    msg = email.message_from_bytes(data, policy=email.policy.default)
    assert isinstance(msg, EmailMessage)
    doc = Document(id=document_id(data), source_path=path, kind=Kind.EMAIL, media_type=media_type)
    doc.metadata.update(
        {
            "from": msg.get("From", ""),
            "to": msg.get("To", ""),
            "cc": msg.get("Cc", ""),
            "subject": msg.get("Subject", ""),
            "date": _date(msg),
            "message_id": msg.get("Message-ID", ""),
            "in_reply_to": msg.get("In-Reply-To", ""),
        }
    )

    plain: str | None = None
    html: str | None = None
    attachments: list[tuple[str, bytes]] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        filename = part.get_filename()
        disposition = (part.get("Content-Disposition") or "").lower()
        if filename or disposition.startswith("attachment") or ctype.startswith("image/"):
            raw = part.get_payload(decode=True)
            if isinstance(raw, bytes) and raw:
                attachments.append((filename or f"part-{len(attachments) + 1}", raw))
            continue
        if ctype == "text/plain" and plain is None:
            plain = _text_of(part)
        elif ctype == "text/html" and html is None:
            html = _text_of(part)

    header_block = "\n".join(f"{h}: {msg.get(h)}" for h in _HEADERS if msg.get(h))
    body = plain or ""
    html_text = ""
    if html:
        doc.metadata["html_part"] = html
        clean_html, hidden = strip_hidden_html(html)
        if hidden:
            doc.metadata["hidden_html"] = hidden
        html_text = html_to_text(clean_html)
    if not body.strip() and html_text:
        body = html_text
        doc.flag("html_body_used", Severity.INFO, "no plain-text part; HTML part converted")
    elif html_text and len(html_text) > 1.5 * len(body):
        body = f"{body}\n\n--- HTML part ---\n{html_text}"
        doc.flag(
            "html_part_appended",
            Severity.INFO,
            "HTML part holds substantially more than the plain part; both kept",
        )
    doc.text = f"{header_block}\n\n{body}".strip()
    doc.text_quality = 1.0

    for name, raw in attachments[:MAX_ATTACHMENTS]:
        child = load_bytes(Path(name), raw)
        child.metadata["bytes"] = raw  # not on disk; kept so a page preview can be rendered
        child.parent_id = doc.id
        child.metadata["attachment_of"] = path.name
        doc.children.append(child)
    if len(attachments) > MAX_ATTACHMENTS:
        doc.flag(
            "attachment_cap",
            Severity.WARNING,
            f"{len(attachments)} attachments, first {MAX_ATTACHMENTS} loaded",
        )
    if attachments:
        doc.metadata["attachments"] = [n for n, _ in attachments]
    return doc
