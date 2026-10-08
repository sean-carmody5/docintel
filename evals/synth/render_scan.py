"""Scanned PDFs: page images wrapped in a PDF, with or without a bad OCR text layer.

A scanner produces an image-only PDF. Many scanners then add an OCR layer that is
invisible and often garbage. A pipeline that trusts the text layer of every PDF
will read that garbage with full confidence.
"""

from __future__ import annotations

import io
import random
from pathlib import Path

import pymupdf

from evals.synth.render_image import degrade_scanner, render_page

_SUBS = {
    "O": "0",
    "0": "O",
    "l": "1",
    "1": "l",
    "I": "l",
    "S": "5",
    "5": "S",
    "B": "8",
    "8": "B",
    "e": "c",
    "a": "o",
    "u": "n",
    "n": "u",
    "t": "f",
    "i": "j",
    ",": ".",
    ".": ",",
}


def garble(text: str, rng: random.Random, rate: float = 0.14) -> str:
    """Corrupt text the way a poor OCR engine does: swaps, drops, merged words."""
    out: list[str] = []
    for ch in text:
        r = rng.random()
        if ch in _SUBS and r < rate:
            out.append(_SUBS[ch])
        elif ch == " " and r < rate / 3:
            continue
        elif ch.isalnum() and r > 1 - rate / 5:
            out.append(ch + rng.choice("'~|"))
        else:
            out.append(ch)
    return "".join(out).replace("rn", "m").replace("cl", "d")


def write_scanned_pdf(src_pdf: Path, out_path: Path, variant: str, rng: random.Random) -> Path:
    with pymupdf.open(src_pdf) as src, pymupdf.open() as out:
        for i, page in enumerate(src):
            im = degrade_scanner(render_page(src_pdf, page=i, dpi=150), rng)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=rng.randint(45, 60), optimize=True)
            new = out.new_page(width=page.rect.width, height=page.rect.height)
            new.insert_image(new.rect, stream=buf.getvalue())
            if variant == "garbled_layer":
                # Invisible text (render mode 3), roughly where the real text sits.
                for block in page.get_text("blocks"):
                    x0, y0, x1, y1, text = block[:5]
                    if not text.strip():
                        continue
                    rect = pymupdf.Rect(x0, y0, x1 + 40, y1 + 20)
                    new.insert_textbox(rect, garble(text, rng), fontsize=7, render_mode=3)
        out.set_metadata(
            {
                "producer": "ScanSnap Manager 7.2",
                "creator": "Scanner",
                "creationDate": "D:20260814090000+00'00'",
                "modDate": "D:20260814090000+00'00'",
            }
        )
        out.save(out_path, deflate=True, garbage=3)
    return out_path
