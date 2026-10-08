"""Source previews for the review page: the page image or the text each line came from.

Presentation only. A reviewer checks a number against the document, so the page
needs the document next to the fields: pages the pipeline already rendered for
scans, pages rendered here for born-digital PDFs, and the loader's text for
everything else so evidence quotes can be highlighted in place.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any

from PIL import Image

from docintel.documents import Document

log = logging.getLogger(__name__)

MAX_WIDTH = 2400  # enough to zoom into a price cell on a phone photo
JPEG_QUALITY = 76
MAX_TEXT = 200_000
PREVIEW_DPI = 170  # A4 at about 1400 px wide


def save_source(doc: Document, out_dir: Path) -> dict[str, Any]:
    """Write page previews under out_dir/sources/<doc id>/ and return what the page needs."""
    pngs = [p.png for p in doc.images]
    if not pngs and not doc.failed and doc.media_type == "application/pdf":
        pngs = _render_pdf(doc.source_path, doc.metadata.get("bytes"))
    pages: list[str] = []
    if pngs:
        folder = out_dir / "sources" / doc.id
        folder.mkdir(parents=True, exist_ok=True)
        for i, png in enumerate(pngs, start=1):
            try:
                _save_jpeg(png, folder / f"page-{i}.jpg")
            except Exception as exc:  # noqa: BLE001 - a preview is optional
                log.warning("could not save a preview of %s page %d: %s", doc.name, i, exc)
                continue
            pages.append(f"sources/{doc.id}/page-{i}.jpg")
    return {
        "id": doc.id,
        "name": doc.name,
        "path": str(doc.source_path),
        "pages": pages,
        "text": doc.text[:MAX_TEXT] if doc.text else "",
    }


def _save_jpeg(png: bytes, target: Path) -> None:
    im: Image.Image = Image.open(io.BytesIO(png))
    if im.width > MAX_WIDTH:
        size = (MAX_WIDTH, round(im.height * MAX_WIDTH / im.width))
        im = im.resize(size, Image.Resampling.LANCZOS)
    im.convert("RGB").save(target, "JPEG", quality=JPEG_QUALITY, optimize=True)


def _render_pdf(path: Path, data: bytes | None = None) -> list[bytes]:
    """Pages of a PDF, from disk or from the bytes an attachment or archive member arrived as."""
    if data is None and not path.is_file():
        return []
    try:
        import pymupdf

        args = (path,) if data is None else (None, data, "pdf")  # filename, stream, filetype
        with pymupdf.open(*args) as pdf:  # type: ignore[no-untyped-call]
            return [page.get_pixmap(dpi=PREVIEW_DPI).tobytes("png") for page in pdf]
    except Exception as exc:  # noqa: BLE001 - a preview is optional
        log.warning("could not render %s for a preview: %s", path.name, exc)
        return []
