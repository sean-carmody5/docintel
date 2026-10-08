"""Decide what a file is from its bytes. The extension is a hint, never the answer."""

from __future__ import annotations

import json
import re
import zipfile
from io import BytesIO

EMPTY = "inode/x-empty"
UNKNOWN = "application/octet-stream"

_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"%PDF", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF8", "image/gif"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
    (b"BM", "image/bmp"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "application/x-ole-storage"),
    (b"\x1f\x8b", "application/gzip"),
    (b"Rar!", "application/vnd.rar"),
    (b"7z\xbc\xaf", "application/x-7z-compressed"),
)

_OOXML = {
    "word/": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xl/": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt/": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

_LEGACY_BY_SUFFIX = {
    ".doc": "application/msword",
    ".xls": "application/vnd.ms-excel",
    ".ppt": "application/vnd.ms-powerpoint",
}

_EMAIL_HEADER = re.compile(
    rb"^(From|To|Subject|Date|Message-ID|Received|Return-Path|MIME-Version):", re.M
)
_CHAT_LINE = re.compile(r"^\[?\d{1,2}[/.]\d{1,2}[/.]\d{2,4},? \d{1,2}:\d{2}(:\d{2})?\]? ", re.M)
_HTML = re.compile(rb"<\s*(!doctype\s+html|html|head|body)\b", re.I)
_XML = re.compile(rb"^\s*<\?xml|^\s*<[A-Za-z_][\w.-]*(\s[^>]*)?>", re.S)


def sniff(data: bytes, suffix: str = "") -> str:
    """Return a media type for the bytes. Suffix only breaks ties the bytes cannot settle."""
    if not data:
        return EMPTY
    head = data[:16]
    for magic, media in _MAGIC:
        if head.startswith(magic):
            if media == "application/x-ole-storage":
                return _LEGACY_BY_SUFFIX.get(suffix.lower(), media)
            return media
    if head.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"PK\x03\x04"):
        return _sniff_zip(data)
    return _sniff_text(data, suffix)


def _sniff_zip(data: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            names = zf.namelist()
    except zipfile.BadZipFile:
        return UNKNOWN
    if "[Content_Types].xml" in names:
        for prefix, media in _OOXML.items():
            if any(n.startswith(prefix) for n in names):
                return media
    return "application/zip"


def _decode(data: bytes) -> str | None:
    for enc in ("utf-8-sig", "utf-16"):
        try:
            text = data.decode(enc)
        except UnicodeDecodeError:
            continue
        if enc == "utf-16" and data[:2] not in (b"\xff\xfe", b"\xfe\xff"):
            continue
        return text
    try:
        text = data.decode("latin-1")
    except UnicodeDecodeError:
        return None
    # latin-1 always decodes; reject if it is clearly binary
    sample = text[:4096]
    control = sum(1 for ch in sample if ord(ch) < 32 and ch not in "\r\n\t\f")
    return text if control / max(1, len(sample)) < 0.05 else None


def _sniff_text(data: bytes, suffix: str) -> str:
    text = _decode(data)
    if text is None:
        return UNKNOWN
    head = data[:4096]
    stripped = text.lstrip()
    if stripped[:1] in "{[":
        try:
            json.loads(text)
            return "application/json"
        except ValueError:
            # Broken JSON is still best treated as JSON; the loader degrades gracefully.
            if stripped[:1] == "{" and '"' in stripped[:200]:
                return "application/json"
    # An email starts with header lines; check before HTML, since the body may hold an HTML part.
    if _EMAIL_HEADER.match(data[:256]) and len(_EMAIL_HEADER.findall(head)) >= 3:
        return "message/rfc822"
    if _HTML.search(head):
        return "text/html"
    if _XML.match(head) and b"<" in head and b">" in head:
        return "application/xml"
    if len(_CHAT_LINE.findall(text[:4096])) >= 3:
        return "text/x-chat"
    if _looks_like_csv(text[:8192]):
        return "text/csv"
    if suffix.lower() in (".md", ".markdown"):
        return "text/markdown"
    return "text/plain"


def _looks_like_csv(sample: str) -> bool:
    """A delimiter that appears the same number of times on most lines of a table.

    csv.Sniffer gives up on exports that put key/value rows above the table, so this
    counts candidate delimiters per line and looks for a dominant, repeated count.
    """
    lines = [ln for ln in sample.splitlines() if ln.strip()]
    if len(lines) < 3:
        return False
    best: tuple[int, int] = (0, 0)
    for delim in (",", ";", "\t", "|"):
        counts = [ln.count(delim) for ln in lines[:60]]
        nonzero = [c for c in counts if c > 0]
        if len(nonzero) < 3:
            continue
        mode = max(set(nonzero), key=lambda c: (nonzero.count(c), c))
        rows = nonzero.count(mode)
        if rows < 3:
            continue
        # Either most lines agree, or the agreeing lines are wide enough to be a real table.
        if rows >= len(lines) * 0.6 or mode >= 3:
            best = max(best, (rows, mode))
    return best[0] >= 3
