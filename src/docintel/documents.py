"""The one shape every input becomes before extraction.

Format knowledge stops here. Downstream nodes see text, optional page images,
metadata and flags, and never ask what file type produced them.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Kind(StrEnum):
    """Coarse family of the source, for routing and reporting. Never for branching on suppliers."""

    JSON = "json"
    PDF = "pdf"
    IMAGE = "image"
    EMAIL = "email"
    SPREADSHEET = "spreadsheet"
    WORD = "word"
    HTML = "html"
    XML = "xml"
    CSV = "csv"
    CHAT = "chat"
    TEXT = "text"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"


@dataclass(frozen=True)
class Flag:
    """Something a reviewer should know. Stable machine-readable code, human detail."""

    code: str
    severity: Severity
    detail: str = ""
    field: str | None = None


@dataclass
class PageImage:
    """A rendered page, PNG bytes, for the vision path."""

    page: int
    png: bytes
    width: int
    height: int


class LoaderError(Exception):
    """A loader could not produce a Document. `reason` is a stable code, `detail` is for people."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


@dataclass
class Document:
    id: str
    source_path: Path
    kind: Kind
    media_type: str
    status: str = "loaded"
    text: str = ""
    images: list[PageImage] = field(default_factory=list)
    text_quality: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    flags: list[Flag] = field(default_factory=list)
    parent_id: str | None = None
    children: list[Document] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.source_path.name

    @property
    def failed(self) -> bool:
        return self.status == "failed"

    def flag(
        self, code: str, severity: Severity, detail: str = "", field: str | None = None
    ) -> None:
        self.flags.append(Flag(code, severity, detail, field))

    def has_flag(self, code: str) -> bool:
        return any(f.code == code for f in self.flags)

    def walk(self) -> list[Document]:
        """This document followed by every attachment, depth first."""
        out = [self]
        for child in self.children:
            out.extend(child.walk())
        return out


def document_id(data: bytes) -> str:
    """Content hash, so the same bytes under two names get the same id."""
    return hashlib.sha256(data).hexdigest()[:16]


def failed_document(path: Path, media_type: str, error: LoaderError, data: bytes = b"") -> Document:
    doc = Document(
        id=document_id(data) if data else document_id(path.name.encode()),
        source_path=path,
        kind=Kind.UNKNOWN,
        media_type=media_type,
        status="failed",
    )
    doc.flag(f"load_failed:{error.reason}", Severity.HIGH, error.detail)
    return doc
