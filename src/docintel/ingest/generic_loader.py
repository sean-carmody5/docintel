"""The long tail: anything markitdown can turn into markdown, with no code per format.

PowerPoint, legacy Excel, RTF and whatever arrives next. A format that needs real
care gets its own loader registered on the exact media type, which takes precedence.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docintel.documents import Document, Kind, LoaderError, Severity, document_id
from docintel.ingest.registry import register

_KIND = {
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": Kind.TEXT,
    "application/vnd.ms-excel": Kind.SPREADSHEET,
    "application/msword": Kind.WORD,
    "application/vnd.ms-powerpoint": Kind.TEXT,
    "application/rtf": Kind.TEXT,
}
_EXT = {
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.ms-excel": ".xls",
    "application/msword": ".doc",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/rtf": ".rtf",
}


@register(*_KIND)
def load_generic(path: Path, data: bytes, media_type: str) -> Document:
    try:
        from markitdown import MarkItDown
    except ImportError as err:  # the dependency is optional at runtime
        raise LoaderError("unsupported", f"{media_type}: markitdown not installed") from err
    try:
        result = MarkItDown().convert_stream(
            BytesIO(data), file_extension=_EXT.get(media_type, path.suffix)
        )
        text = (result.text_content or "").strip()
    except Exception as err:
        raise LoaderError(
            "unsupported", f"{media_type}: generic conversion failed ({type(err).__name__}: {err})"
        ) from err
    if not text:
        raise LoaderError("unsupported", f"{media_type}: generic conversion produced no text")
    doc = Document(
        id=document_id(data), source_path=path, kind=_KIND[media_type], media_type=media_type
    )
    doc.text = text
    doc.text_quality = 0.9
    doc.flag(
        "generic_conversion", Severity.INFO, "converted by markitdown; no format-specific loader"
    )
    return doc
