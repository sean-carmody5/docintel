"""Anything that decodes as text and has no better loader: plain text, chat exports, CSV, XML, HTML.

Specific loaders may replace any of these later by registering the exact media type.
"""

from __future__ import annotations

import re
from pathlib import Path

from docintel.documents import Document, Kind, Severity, document_id
from docintel.ingest.registry import register

_KIND_BY_MEDIA = {
    "text/csv": Kind.CSV,
    "text/x-chat": Kind.CHAT,
    "text/html": Kind.HTML,
    "application/xml": Kind.XML,
    "text/markdown": Kind.TEXT,
    "text/plain": Kind.TEXT,
}

_TAG = re.compile(r"<[^>]+>")
_SCRIPT_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)


def decode_text(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16"):
        try:
            text = data.decode(enc)
        except UnicodeDecodeError:
            continue
        if enc == "utf-16" and data[:2] not in (b"\xff\xfe", b"\xfe\xff"):
            continue
        return text
    return data.decode("latin-1")


def html_to_text(html: str) -> str:
    """Crude but dependable: drop scripts and styles, keep cell and row breaks, strip tags."""
    html = _SCRIPT_STYLE.sub(" ", html)
    html = re.sub(r"</(td|th)\s*>", " | ", html, flags=re.I)
    html = re.sub(r"</(tr|p|div|li|h[1-6]|dt|dd|br)\s*>|<br\s*/?>", "\n", html, flags=re.I)
    text = _TAG.sub("", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


@register("text/*", "application/xml")
def load_text(path: Path, data: bytes, media_type: str) -> Document:
    text = decode_text(data)
    kind = _KIND_BY_MEDIA.get(media_type, Kind.TEXT)
    doc = Document(id=document_id(data), source_path=path, kind=kind, media_type=media_type)
    if kind is Kind.HTML:
        doc.metadata["raw_html_chars"] = len(text)
        text = html_to_text(text)
    doc.text = text
    doc.text_quality = 1.0
    if media_type == "text/plain" and path.suffix.lower() not in (".txt", ".md", ".text", ""):
        doc.flag("extension_mismatch", Severity.INFO, f"{path.suffix} read as plain text")
    return doc
