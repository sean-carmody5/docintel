"""Images: no text, one page image per frame, for the vision path."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from docintel.documents import Document, Kind, LoaderError, PageImage, Severity, document_id
from docintel.ingest.registry import register

MAX_SIDE = 2400
MAX_FRAMES = 20


def to_page_image(im: Image.Image, page: int) -> PageImage:
    im = ImageOps.exif_transpose(im) or im
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    if max(im.size) > MAX_SIDE:
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    buf = BytesIO()
    im.save(buf, "PNG", optimize=True)
    return PageImage(page=page, png=buf.getvalue(), width=im.width, height=im.height)


@register("image/*")
def load_image(path: Path, data: bytes, media_type: str) -> Document:
    try:
        im = Image.open(BytesIO(data))
        im.load()
    except Exception as err:
        raise LoaderError("unreadable", f"not a decodable image: {err}") from err
    doc = Document(id=document_id(data), source_path=path, kind=Kind.IMAGE, media_type=media_type)
    doc.metadata.update(
        {"width": im.width, "height": im.height, "mode": im.mode, "format": im.format}
    )
    frames = getattr(im, "n_frames", 1)
    for i in range(min(frames, MAX_FRAMES)):
        if frames > 1:
            im.seek(i)
        doc.images.append(to_page_image(im.copy(), i + 1))
    if frames > MAX_FRAMES:
        doc.flag("page_cap", Severity.WARNING, f"{frames} frames, only the first {MAX_FRAMES} read")
    doc.text = ""
    doc.text_quality = None
    if min(im.width, im.height) < 600:
        doc.flag(
            "low_resolution", Severity.WARNING, f"{im.width}x{im.height} px; expect poor legibility"
        )
    return doc
