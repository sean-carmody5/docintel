"""JSON of any shape. No field names are known here; the extractor reads the structure."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from docintel.documents import Document, Kind, LoaderError, Severity, document_id
from docintel.ingest.registry import register

_TRAILING_COMMA = re.compile(r",(\s*[}\]])")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def parse_lenient(text: str) -> tuple[Any, list[str]]:
    """Strict first. Then repair the two most common export bugs and say so."""
    try:
        return json.loads(text), []
    except ValueError:
        pass
    repaired = _CONTROL.sub("", text)
    repaired = _TRAILING_COMMA.sub(r"\1", repaired)
    try:
        return json.loads(repaired), ["parsed_leniently"]
    except ValueError as err:
        raise LoaderError("malformed_json", str(err)) from err


def _summarise(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return {"top_level_keys": list(obj.keys())[:40], "shape": "object"}
    if isinstance(obj, list):
        return {"length": len(obj), "shape": "array"}
    return {"shape": type(obj).__name__}


@register("application/json")
def load_json(path: Path, data: bytes, media_type: str) -> Document:
    text = _decode(data)
    doc = Document(id=document_id(data), source_path=path, kind=Kind.JSON, media_type=media_type)
    try:
        obj, notes = parse_lenient(text)
    except LoaderError as err:
        # Unparseable, but it is still text. Let the extractor read it and flag loudly.
        doc.text = text
        doc.text_quality = 0.5
        doc.flag("parsed_as_text", Severity.WARNING, err.detail)
        return doc
    doc.text = json.dumps(obj, indent=2, ensure_ascii=False)
    doc.text_quality = 1.0
    doc.metadata.update(_summarise(obj))
    for note in notes:
        doc.flag(note, Severity.WARNING, "trailing commas or control characters removed")
    return doc
