"""PDF: markdown from the text layer when it can be trusted, page images when it cannot.

Three kinds of PDF arrive, and the loader tells them apart by structure, not by name:

- a born-digital document with a real text layer: markdown with tables, no rendering
- a scan with no text layer: pages rendered for the vision path
- a scan whose scanner added an OCR layer: pages rendered, the layer kept as a
  cross-check with its measured quality, never trusted on its own
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pymupdf
import pymupdf4llm

from docintel.documents import Document, Kind, LoaderError, PageImage, Severity, document_id
from docintel.ingest.quality import QUALITY_THRESHOLD, text_quality
from docintel.ingest.registry import register

log = logging.getLogger(__name__)

MAX_PAGES = 60
RENDER_DPI = 150
MIN_TEXT_CHARS = 40
SCAN_COVERAGE = 0.85


def render_pages(doc: pymupdf.Document, pages: range, dpi: int = RENDER_DPI) -> list[PageImage]:
    out: list[PageImage] = []
    for i in pages:
        pix = doc[i].get_pixmap(dpi=dpi)
        out.append(
            PageImage(page=i + 1, png=pix.tobytes("png"), width=pix.width, height=pix.height)
        )
    return out


def is_scanned_page(page: pymupdf.Page) -> bool:
    """A page that is one image covering nearly all of it came from a scanner or camera."""
    area = page.rect.get_area()
    if area <= 0:
        return False
    try:
        for img in page.get_images(full=True):
            for rect in page.get_image_rects(img):
                if rect.get_area() / area >= SCAN_COVERAGE:
                    return True
    except Exception:  # a broken image object must not take the page down
        return False
    return False


def hidden_spans(pdf: pymupdf.Document, pages: range) -> list[str]:
    """Text a reader cannot see: tiny, off the page, or white with no dark fill beneath it.

    White text over a dark table header is normal and is not reported.
    """
    found: list[str] = []
    for i in pages:
        page = pdf[i]
        page_rect = page.rect
        dark: list[pymupdf.Rect] = []
        try:
            for d in page.get_drawings():
                fill = d.get("fill")
                if fill and sum(fill[:3]) / 3 < 0.5 and d.get("rect") is not None:
                    dark.append(pymupdf.Rect(d["rect"]))
        except Exception:  # drawings are optional evidence
            dark = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = str(span.get("text", "")).strip()
                    if not text:
                        continue
                    bbox = pymupdf.Rect(span["bbox"])
                    tiny = float(span.get("size", 10)) < 3
                    off_page = not page_rect.intersects(bbox)
                    white = int(span.get("color", 0)) == 0xFFFFFF
                    on_dark = any(r.intersects(bbox) for r in dark)
                    if tiny or off_page or (white and not on_dark):
                        found.append(text)
    return found


def _markdown(pdf: pymupdf.Document, pages: range) -> str:
    try:
        md = pymupdf4llm.to_markdown(pdf, pages=list(pages), use_ocr=False, show_progress=False)
    except TypeError:  # older pymupdf4llm without the OCR switch
        md = pymupdf4llm.to_markdown(pdf, pages=list(pages), show_progress=False)
    # Wrapped cells come back as <br> and bold runs per fragment; flatten both so names stay whole.
    text = str(md).replace("<br>", " ").replace("**", "")
    return re.sub(r"[ ]{2,}", " ", text).strip()


def _load_pdf(path: Path, data: bytes, media_type: str) -> Document:
    try:
        pdf = pymupdf.open(stream=data, filetype="pdf")
    except Exception as err:
        raise LoaderError("unreadable", f"not a readable PDF: {err}") from err
    with pdf:
        if pdf.needs_pass:
            raise LoaderError("encrypted", "password required to open this file")
        n_pages = len(pdf)
        if n_pages == 0:
            raise LoaderError("unreadable", "PDF has no pages")
        doc = Document(id=document_id(data), source_path=path, kind=Kind.PDF, media_type=media_type)
        if pdf.is_repaired:
            doc.flag(
                "repaired",
                Severity.WARNING,
                "file was damaged and repaired on open; content may be incomplete",
            )
        meta = {k: v for k, v in (pdf.metadata or {}).items() if v}
        doc.metadata.update({"pages": n_pages, **meta})
        pages = range(min(n_pages, MAX_PAGES))
        if n_pages > MAX_PAGES:
            doc.flag(
                "page_cap", Severity.WARNING, f"{n_pages} pages, only the first {MAX_PAGES} read"
            )

        raw = "\n\n".join(pdf[i].get_text("text") for i in pages).strip()
        hidden = hidden_spans(pdf, pages)
        if hidden:
            doc.metadata["hidden_text"] = hidden
        scanned = sum(1 for i in pages if is_scanned_page(pdf[i]))
        quality = text_quality(raw)
        doc.metadata["scanned_pages"] = scanned

        if len(raw) < MIN_TEXT_CHARS:
            doc.text = ""
            doc.text_quality = 0.0
            doc.images = render_pages(pdf, pages)
            doc.flag("no_text_layer", Severity.INFO, "no text layer; pages rendered for vision")
            return doc

        if scanned >= max(1, len(pages) // 2):
            doc.text = raw
            doc.text_quality = quality
            doc.images = render_pages(pdf, pages)
            doc.flag(
                "scanned_with_text_layer",
                Severity.WARNING,
                f"{scanned} of {len(pages)} pages are full-page images with a text layer "
                f"(scanner OCR, quality {quality:.2f}); pages rendered, "
                "layer kept as a cross-check",
            )
            return doc

        if quality < QUALITY_THRESHOLD:
            doc.text = raw
            doc.text_quality = quality
            doc.images = render_pages(pdf, pages)
            doc.flag(
                "text_layer_untrusted",
                Severity.WARNING,
                f"text layer quality {quality:.2f} below {QUALITY_THRESHOLD}; "
                "pages rendered, layer kept for cross-checks",
            )
            return doc

        try:
            doc.text = _markdown(pdf, pages) or raw
        except Exception as err:  # markdown is a nicety; the raw layer is the fallback
            log.warning("pymupdf4llm failed on %s: %s", path.name, err)
            doc.text = raw
            doc.flag("markdown_fallback", Severity.INFO, str(err))
        doc.text_quality = quality
    return doc


@register("application/pdf")
def load_pdf(path: Path, data: bytes, media_type: str) -> Document:
    doc = _load_pdf(path, data, media_type)
    for hidden in doc.metadata.get("hidden_text", []):
        doc.text = doc.text.replace(hidden, "")
    return doc
